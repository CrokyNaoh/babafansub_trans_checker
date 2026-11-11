"""
Flask 后端 API - 支持多项目配置的翻译检查服务
"""

from flask import Flask, request, send_file, jsonify
import io
import os
import sys
import json
import re
import subprocess
import tempfile
import shutil
import threading
import time
from datetime import datetime
import logging

# 导入配置文件
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# 配置（从 config.py 导入）
UPLOAD_FOLDER = config.UPLOAD_FOLDER
DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.DATA_FOLDER_NAME)
MAX_FILE_SIZE = config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 子进程被系统强制结束时临时目录来不及删除：启动时清掉 1 小时以前的遗留目录
STALE_UPLOAD_SEC = 3600


def sweep_stale_uploads():
    now = time.time()
    for name in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, name)
        try:
            if now - os.path.getmtime(path) > STALE_UPLOAD_SEC:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
        except OSError:
            pass


sweep_stale_uploads()

# 检查在子进程中运行，结束后内存全部归还系统
CHECK_WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_worker.py')
# 同一时间只处理一个文件，避免两份大表格同时占用内存
_check_lock = threading.Lock()
# 排队等待的最长时间（秒）；排队 + 检查 (CHECK_TIMEOUT_SEC) 必须小于 nginx 的 proxy_read_timeout (300)
CHECK_QUEUE_WAIT_SEC = 45
XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# 加载项目配置
projects_config_path = os.path.join(DATA_FOLDER, 'projects.json')
with open(projects_config_path, 'r', encoding='utf-8') as f:
    PROJECTS = json.load(f)['projects']

# 加载通用错误词典
err_dict_path = os.path.join(DATA_FOLDER, 'errDict.json')
with open(err_dict_path, 'r', encoding='utf-8') as f:
    ERR_DICT_FULL = json.load(f)


# 文件名里不允许出现的字符：路径分隔符、Windows 保留字符、控制字符
UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def display_filename(filename, max_len=120):
    """保留中文等原始字符，只去掉路径和不安全字符；用于日志和下载文件名（服务器上实际文件名固定）"""
    name = filename.replace('\\', '/').rsplit('/', 1)[-1]
    name = UNSAFE_FILENAME_CHARS.sub('_', name).strip(' .')
    return name[:max_len] or 'file.xlsx'


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def filter_err_dict_by_tags(err_dict, project_tags):
    """根据项目标签过滤错误词典"""
    filtered = {
        'version': err_dict.get('version', ''),
        'err': {},
        'warn': err_dict.get('warn', {}),  # 全局生效
        'repeat': err_dict.get('repeat', []),  # 全局生效
        'transhint': err_dict.get('transhint', {})  # 全局生效
    }
    
    # 只保留匹配项目标签的错误词
    # 如果 tags 为空，则对所有项目生效
    for word, data in err_dict.get('err', {}).items():
        word_tags = data.get('tags', [])
        if not word_tags or any(tag in project_tags for tag in word_tags):
            filtered['err'][word] = data.get('fix',"")
    
    return filtered


def normalize_priority(project):
    """将 priority 统一转换为数字，非法值按 0 处理"""
    raw_priority = project.get('priority')
    if raw_priority is None:
        return 0
    try:
        return int(raw_priority)
    except (TypeError, ValueError):
        return 0


def get_visible_projects(projects):
    """項目列表與統計可見的專案：priority 為 -1 的專案隱藏。"""
    return {
        project_id: project
        for project_id, project in projects.items()
        if normalize_priority(project) != -1
    }


def load_project_dicts(project_id):
    """
    加载项目词典
    
    Returns:
        (err_dict, term_dict) 元组
    """
    if project_id not in PROJECTS:
        raise ValueError(f"无效的项目ID: {project_id}")
    
    project = PROJECTS[project_id]
    project_tags = project.get('tags', [])
    
    # 过滤错误词典
    err_dict = filter_err_dict_by_tags(ERR_DICT_FULL, project_tags)
    
    # 加载项目术语词典
    term_dict_file = project.get('termDict', f'termDict_{project_id}.json')
    term_dict_path = os.path.join(DATA_FOLDER, term_dict_file)
    
    with open(term_dict_path, 'r', encoding='utf-8') as f:
        term_dict = json.load(f)
    
    return err_dict, term_dict


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    # 只说明服务在运行，不返回项目列表（隐藏项目的 ID 不应外露）
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/client-config', methods=['GET'])
def client_config():
    """前端读取公开部署信息（不含密钥）。项目列表「打开项目」链接依赖 publicAppBaseUrl。"""
    base = config.get_public_app_base_url()
    return jsonify({
        'publicAppBaseUrl': base or None,
        'publicOrigin': config.PUBLIC_ORIGIN or None,
        'maxFileSizeMb': config.MAX_FILE_SIZE_MB,
        'maxRowsPerSheet': config.MAX_ROWS_PER_SHEET,
    })


# 词典版本缓存：{文件路径: (修改时间, 版本)}，文件没变就不重复解析
_term_version_cache = {}


def read_term_dict_version(project_id, project):
    """读取项目术语词典的版本（更新时间）；读取失败时返回空字符串"""
    term_dict_file = project.get('termDict', f'termDict_{project_id}.json')
    path = os.path.join(DATA_FOLDER, term_dict_file)
    try:
        mtime = os.path.getmtime(path)
        cached = _term_version_cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        with open(path, 'r', encoding='utf-8') as f:
            version = json.load(f).get('version', '')
        _term_version_cache[path] = (mtime, version)
        return version
    except (OSError, json.JSONDecodeError) as e:
        app.logger.warning(f"读取词典版本失败 {term_dict_file}: {e}")
        return ''


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表（管理页使用），附带各项目词库更新时间"""
    projects = {
        project_id: {**project, 'termDictVersion': read_term_dict_version(project_id, project)}
        for project_id, project in get_visible_projects(PROJECTS).items()
    }
    return jsonify({'projects': projects, 'errDictVersion': ERR_DICT_FULL.get('version', '')})


@app.route('/api/project/<project_id>', methods=['GET'])
def get_project_info(project_id):
    """获取项目信息"""
    if project_id not in PROJECTS:
        return jsonify({'error': '無效的項目ID'}), 404
    
    try:
        # 加载项目词典（包含版本号）
        err_dict, term_dict = load_project_dicts(project_id)
        
        return jsonify({
            'project': PROJECTS[project_id],
            'errDictVersion': err_dict.get('version', ''),
            'termDictVersion': term_dict.get('version', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reload-config', methods=['POST'])
def reload_config():
    """重新加载配置文件"""
    try:
        # 重新加载项目配置
        global PROJECTS
        with open(projects_config_path, 'r', encoding='utf-8') as f:
            PROJECTS = json.load(f)['projects']
        
        # 重新加载错误词典
        global ERR_DICT_FULL
        with open(err_dict_path, 'r', encoding='utf-8') as f:
            ERR_DICT_FULL = json.load(f)
        
        config.reload_deploy_env()
        
        visible_projects = get_visible_projects(PROJECTS)
        app.logger.info(
            f"reload {len(PROJECTS)} configs ({len(visible_projects)} visible)"
        )
        
        return jsonify({
            'success': True,
            'message': '配置文件重新加載成功',
            'projects_count': len(visible_projects),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"配置文件重新加载失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'重新加載失敗：{str(e)}'
        }), 500


class CheckError(Exception):
    """检查失败，message 直接展示给用户"""

    def __init__(self, message, status=500):
        super().__init__(message)
        self.status = status


def worker_env():
    """
    检查子进程的环境变量。
    去掉 OPENPYXL_LXML：子进程导入 openpyxl 时若读到它为 False，保存标红的富文本会报错。
    """
    env = dict(os.environ)
    env.pop('OPENPYXL_LXML', None)
    return env


def run_check_job(job_path):
    """
    在子进程中执行检查。

    Raises:
        CheckError: 检查失败、超时或子进程异常退出
    """
    try:
        result = subprocess.run(
            [sys.executable, CHECK_WORKER, job_path],
            cwd=os.path.dirname(CHECK_WORKER),
            capture_output=True,
            text=True,
            timeout=config.CHECK_TIMEOUT_SEC,
            env=worker_env(),
        )
    except subprocess.TimeoutExpired:
        raise CheckError(f'處理超時（超過 {config.CHECK_TIMEOUT_SEC} 秒），請拆分文件後重試')

    if result.returncode == 0:
        return

    if result.returncode < 0:
        # 被信号终止，通常是内存不足被系统杀掉
        app.logger.error(f"check worker killed by signal {-result.returncode}")
        raise CheckError('伺服器記憶體不足，處理中斷。請稍後重試，或拆分文件後再上傳')

    app.logger.error(f"check worker failed: {result.stderr[-2000:]}{result.stdout[-2000:]}")
    lines = result.stdout.strip().splitlines()
    try:
        info = json.loads(lines[-1]) if lines else {}
    except json.JSONDecodeError:
        info = {}
    # 行数超限、开着筛选属于用户可自行修正的问题
    status = 400 if info.get('kind') in ('row_limit', 'filter') else 500
    raise CheckError(info.get('error') or '處理失敗', status)


def validate_check_config(check_config):
    """校验并规范化列号，返回错误信息；无误时返回 None"""
    required_cols = ['inputCol', 'outputCol1']
    if check_config.get('mode') == 'common':
        required_cols.append('outputCol2')

    for col_name in required_cols:
        col = str(check_config.get(col_name, '')).upper()
        if len(col) != 1 or not 'A' <= col <= 'Z':
            return f'無效的列號: {col_name}'
        check_config[col_name] = col
    return None


@app.route('/api/check', methods=['POST'])
def check_excel():
    """
    检查 Excel 文件

    Form Data:
        file: Excel 文件
        config: JSON 配置字符串，包含：
            - project: 项目ID
            - mode: 'common' 或 'spec'
            - inputCol: 输入列 (A-Z)
            - outputCol1: 输出列1 (A-Z)
            - outputCol2: 输出列2 (A-Z, 仅 common 模式)
            - checkAllSheets: 是否检查所有工作表
            - includeTransHint: 是否包含易塞翻词（仅 spec 模式）

    Returns:
        处理后的 Excel 文件
    """
    # 1. 验证文件
    file = request.files.get('file')
    if file is None:
        return jsonify({'error': '沒有文件'}), 400
    if file.filename == '':
        return jsonify({'error': '文件名為空'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '僅支持.xlsx文件'}), 400

    # 2. 验证文件大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        return jsonify({
            'error': config.get_file_size_error_msg(file_size / 1024 / 1024)
        }), 400

    # 3. 解析并验证配置
    try:
        check_config = json.loads(request.form.get('config', '{}'))
    except json.JSONDecodeError:
        return jsonify({'error': '配置格式錯誤'}), 400
    if not isinstance(check_config, dict):
        return jsonify({'error': '配置格式錯誤'}), 400

    project_id = check_config.get('project')
    if not isinstance(project_id, str) or project_id not in PROJECTS:
        return jsonify({'error': '無效的項目ID'}), 400

    col_error = validate_check_config(check_config)
    if col_error:
        return jsonify({'error': col_error}), 400

    original_name = display_filename(file.filename)
    base_name = original_name.rsplit('.', 1)[0] or 'file'
    download_name = f"checked_{base_name}.xlsx"

    try:
        err_dict, term_dict = load_project_dicts(project_id)

        # 4. 临时目录在 with 结束时连同上传文件、结果文件一起删除
        # （上传目录在 /tmp 下，可能被系统定期清理，每次都确保它存在）
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=UPLOAD_FOLDER) as work_dir:
            input_path = os.path.join(work_dir, 'input.xlsx')
            output_path = os.path.join(work_dir, 'output.xlsx')
            job_path = os.path.join(work_dir, 'job.json')
            file.save(input_path)

            with open(job_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'input': input_path,
                    'output': output_path,
                    'err_dict': err_dict,
                    'term_dict': term_dict,
                    'config': check_config,
                    'max_rows': config.MAX_ROWS_PER_SHEET,
                }, f, ensure_ascii=False)

            app.logger.info(
                f"check start project={project_id} mode={check_config.get('mode')} "
                f"file={original_name} size={file_size // 1024}KB"
            )
            if not _check_lock.acquire(timeout=CHECK_QUEUE_WAIT_SEC):
                raise CheckError('目前檢查的人較多，請稍後再試', 503)
            try:
                run_check_job(job_path)
            finally:
                _check_lock.release()

            with open(output_path, 'rb') as f:
                result_bytes = f.read()

        app.logger.info(f"check done file={original_name}")
        return send_file(
            io.BytesIO(result_bytes),
            as_attachment=True,
            download_name=download_name,
            mimetype=XLSX_MIMETYPE,
        )

    except CheckError as e:
        app.logger.warning(f"check failed file={original_name}: {e}")
        return jsonify({'error': f'處理失敗：{e}'}), e.status
    except Exception as e:
        app.logger.error(f"处理失败: {e}", exc_info=True)
        return jsonify({'error': f'處理失敗：{str(e)}'}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """文件过大错误处理"""
    return jsonify({'error': config.get_upload_size_limit_msg()}), 413


@app.errorhandler(500)
def internal_server_error(error):
    """服务器错误处理"""
    app.logger.error(f"服务器错误: {error}", exc_info=True)
    return jsonify({'error': '伺服器內部錯誤'}), 500


if __name__ == '__main__':
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.DEBUG_MODE,
        threaded=config.THREADED
    )



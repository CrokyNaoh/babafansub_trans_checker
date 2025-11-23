"""
Flask 后端 API - 支持多项目配置的翻译检查服务
"""

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
import json
import time
from datetime import datetime
from checker_core import ExcelChecker
import logging

# 导入配置文件
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CORS(app)  # 允许跨域请求

# 配置（从 config.py 导入）
UPLOAD_FOLDER = config.UPLOAD_FOLDER
DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.DATA_FOLDER_NAME)
MAX_FILE_SIZE = config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 加载项目配置
projects_config_path = os.path.join(DATA_FOLDER, 'projects.json')
with open(projects_config_path, 'r', encoding='utf-8') as f:
    PROJECTS = json.load(f)['projects']

# 加载通用错误词典
err_dict_path = os.path.join(DATA_FOLDER, 'errDict.json')
with open(err_dict_path, 'r', encoding='utf-8') as f:
    ERR_DICT_FULL = json.load(f)


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
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'projects': list(PROJECTS.keys())
    })


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表（用于调试）"""
    return jsonify({'projects': PROJECTS})


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
        
        app.logger.info(f"reload {len(PROJECTS)} configs")
        
        return jsonify({
            'success': True,
            'message': '配置文件重新加载成功',
            'projects_count': len(PROJECTS),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"配置文件重新加载失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'重新加载失败: {str(e)}'
        }), 500


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
    try:
        # 1. 验证文件
        if 'file' not in request.files:
            return jsonify({'error': '沒有文件'}), 400
        
        file = request.files['file']
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
        
        # 3. 解析配置
        config_str = request.form.get('config', '{}')
        check_config = json.loads(config_str)
        
        project_id = check_config.get('project')
        if not project_id or project_id not in PROJECTS:
            return jsonify({'error': '無效的項目ID'}), 400
        
        # 4. 验证列号
        required_cols = ['inputCol', 'outputCol1']
        if check_config.get('mode') == 'common':
            required_cols.append('outputCol2')
        
        for col_name in required_cols:
            col = check_config.get(col_name, '').upper()
            if not col or len(col) != 1 or ord(col) < ord('A') or ord(col) > ord('Z'):
                return jsonify({'error': f'無效的列號: {col_name}'}), 400
            check_config[col_name] = col
        
        # 5. 保存上传的文件
        filename = file.filename
        filename = ".".join(filename.split(".")[:-1])
        filename = secure_filename(filename) + ".xlsx"
        timestamp = int(time.time() * 1000)
        input_filename = f"{timestamp}_{filename}"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        app.logger.info(f"save_file {input_path}")
        file.save(input_path)
        
        # 6. 加载项目词典
        err_dict, term_dict = load_project_dicts(project_id)
        app.logger.info(f"dict_loaded {project_id}")
        
        # 7. 创建检查器并处理文件
        checker = ExcelChecker(err_dict, term_dict)
        
        output_filename = f"{timestamp}_checked_{filename}"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        
        checker.process_file(input_path, output_path, check_config)
        app.logger.info(f"checked {output_path}")
        
        # 8. 返回处理后的文件
        response = send_file(
            output_path,
            as_attachment=True,
            download_name=f"checked_{filename}",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # 9. 清理临时文件（在后台延迟删除）
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    # 延迟删除，确保文件已发送
                    import threading
                    def delayed_remove():
                        time.sleep(5)
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    threading.Thread(target=delayed_remove).start()
                app.logger.info(f"cleanup")
            except Exception as e:
                app.logger.error(f"清理临时文件失败: {e}")
        
        return response
        
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



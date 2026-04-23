"""
Web_py 统一配置文件
修改此文件后需要重启后端服务
部署地址等请使用 deploy.env（从 deploy.env.template 复制，勿将 deploy.env 提交到 git）
"""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DEPLOY_ENV_PATH = _ROOT / "deploy.env"


def _parse_deploy_env_file(path: Path) -> dict:
    data = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] in '"\'' and v[0] == v[-1]:
            v = v[1:-1]
        data[k] = os.path.expandvars(v)
    return data


def _load_deploy_env():
    global PUBLIC_ORIGIN, NGINX_SERVER_NAME, _deploy_data
    _deploy_data = _parse_deploy_env_file(_DEPLOY_ENV_PATH)
    # 环境变量优先生效，便于容器/CI 覆盖
    PUBLIC_ORIGIN = os.environ.get(
        "TRANSTOOL_PUBLIC_ORIGIN", _deploy_data.get("PUBLIC_ORIGIN", "")
    ).strip().rstrip("/")
    NGINX_SERVER_NAME = os.environ.get(
        "TRANSTOOL_NGINX_SERVER_NAME", _deploy_data.get("NGINX_SERVER_NAME", "localhost")
    ).strip()


_deploy_data = {}
PUBLIC_ORIGIN = ""
NGINX_SERVER_NAME = "localhost"
_load_deploy_env()


def reload_deploy_env():
    """热更新 deploy.env（供 /api/reload-config 调用）"""
    _load_deploy_env()


def get_public_app_base_url() -> str:
    """项目列表页「打开项目」使用的基础 URL（到 index.html，无查询串）。"""
    if PUBLIC_ORIGIN:
        return f"{PUBLIC_ORIGIN}/transtool-py/index.html"
    return ""


# ==================== 文件上传配置 ====================

# 文件大小限制（单位：MB）
MAX_FILE_SIZE_MB = 10

# 计算字节数（程序内部使用）
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx'}

# ==================== 目录配置 ====================

# 临时文件上传目录
UPLOAD_FOLDER = '/tmp/transtool_uploads'

# 数据文件目录（相对于 backend 目录的父目录）
DATA_FOLDER_NAME = 'data'

# ==================== 服务器配置 ====================

# Flask 监听地址和端口
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000

# 是否启用调试模式（生产环境设为 False）
DEBUG_MODE = False

# 是否启用多线程
THREADED = True

# ==================== Nginx 配置建议 ====================

# 注意：修改 MAX_FILE_SIZE_MB 后，也需要同步修改由 nginx.conf.template 生成的 nginx.conf 中的：
# client_max_body_size {MAX_FILE_SIZE_MB}M;

def get_nginx_config_hint():
    """返回 Nginx 配置建议"""
    return f"""
请确保 nginx.conf 中设置了相应的文件大小限制：

location ^~ /transtool-py/api/ {{
    ...
    client_max_body_size {MAX_FILE_SIZE_MB}M;
    ...
}}
"""

# ==================== 错误提示文本 ====================

def get_file_size_error_msg(actual_size_mb):
    """生成文件过大错误提示"""
    return f'文件過大（{actual_size_mb:.1f}MB），建議小於 {MAX_FILE_SIZE_MB}MB'

def get_upload_size_limit_msg():
    """获取上传限制提示"""
    return f'文件過大，建議小於 {MAX_FILE_SIZE_MB}MB'



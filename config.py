"""
Web_py 统一配置文件
修改此文件后需要重启后端服务
"""

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

# 注意：修改 MAX_FILE_SIZE_MB 后，也需要同步修改 nginx.conf 中的：
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



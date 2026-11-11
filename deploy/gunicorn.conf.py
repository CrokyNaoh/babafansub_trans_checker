"""
gunicorn 配置（由 systemd 服务加载）

机器只有 2 核 1.6GB，检查本身在子进程里串行执行（见 backend/app.py），
这里只开 1 个 worker；用线程处理并发的轻量请求（项目信息、健康检查），
避免一个人检查时其他人打不开页面。
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
import config as app_config  # noqa: E402  （不能叫 config：会与 gunicorn 的同名设置冲突）

# 只监听本机：外部请求统一经 nginx 转发，后端端口不直接暴露
bind = f"127.0.0.1:{app_config.FLASK_PORT}"
chdir = os.path.join(_ROOT, 'backend')

workers = 1
worker_class = 'gthread'
threads = 8

# 单次请求最长：排队 45 秒 + 检查 CHECK_TIMEOUT_SEC + 余量
timeout = 45 + app_config.CHECK_TIMEOUT_SEC + 30
graceful_timeout = 30

accesslog = '-'
errorlog = '-'
loglevel = 'info'

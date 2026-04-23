#!/bin/bash
# 根据 deploy.env 与 nginx.conf.template 生成本地 nginx.conf（不提交到 git）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ENV_FILE="$SCRIPT_DIR/deploy.env"
TEMPLATE="$SCRIPT_DIR/nginx.conf.template"
OUT="$SCRIPT_DIR/nginx.conf"

if [ ! -f "$ENV_FILE" ]; then
  echo "错误: 未找到 $ENV_FILE"
  echo "请执行: cp deploy.env.template deploy.env 并填写 FRONTEND_ROOT、NGINX_SERVER_NAME 等"
  exit 1
fi

python3 - "$ENV_FILE" "$TEMPLATE" "$OUT" <<'PY'
import sys
from pathlib import Path

def load_deploy_env(path: Path) -> dict:
    data = {}
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
        data[k] = v
    return data

env_path, template_path, out_path = map(Path, sys.argv[1:4])
data = load_deploy_env(env_path)
name = data.get("NGINX_SERVER_NAME", "")
root = data.get("FRONTEND_ROOT", "")
if not name or not root:
    sys.stderr.write("错误: deploy.env 中需设置 NGINX_SERVER_NAME 与 FRONTEND_ROOT\n")
    sys.exit(1)
text = template_path.read_text(encoding="utf-8")
text = text.replace("__NGINX_SERVER_NAME__", name)
text = text.replace("__FRONTEND_ROOT__", root)
out_path.write_text(text, encoding="utf-8")
print(f"已生成: {out_path}")
print("可执行: sudo cp", out_path, "/etc/nginx/sites-available/transtool-py && sudo nginx -t && sudo systemctl reload nginx")
PY

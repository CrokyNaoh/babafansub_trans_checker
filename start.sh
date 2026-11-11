#!/bin/bash

# 翻译检查工具 - 启动脚本（后端版本）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/deploy.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/deploy.env"
  set +a
fi
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$SCRIPT_DIR/backend.pid"
LOG_DIR="$SCRIPT_DIR/logs"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python3"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== 翻译检查工具 - 后端启动 ===${NC}\n"

# 1. 检查 Python 环境
echo "1. 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 已安装${NC}\n"

# 2. 检查虚拟环境和依赖
echo "2. 检查 Python 依赖..."
cd "$BACKEND_DIR"

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}错误: 虚拟环境未找到，请运行: python3 -m venv $BACKEND_DIR/venv${NC}"
    exit 1
fi

if ! "$VENV_PYTHON" -c "import flask, openpyxl, lxml, gunicorn" 2>/dev/null; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    "$BACKEND_DIR/venv/bin/pip3" install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 依赖安装失败${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ 依赖已安装${NC}\n"

# 3. 检查词库文件
echo "3. 检查词库文件..."
DATA_DIR="$SCRIPT_DIR/data"

if [ ! -f "$DATA_DIR/projects.json" ]; then
    echo -e "${RED}错误: 缺少 projects.json${NC}"
    exit 1
fi

if [ ! -f "$DATA_DIR/errDict.json" ]; then
    echo -e "${RED}错误: 缺少 errDict.json${NC}"
    exit 1
fi

# 检查项目词典
PROJECTS=$("$VENV_PYTHON" -c "import json; data=json.load(open('$DATA_DIR/projects.json')); print(' '.join(data['projects'].keys()))")
for project in $PROJECTS; do
    TERM_DICT=$("$VENV_PYTHON" -c "import json; data=json.load(open('$DATA_DIR/projects.json')); print(data['projects']['$project'].get('termDict', 'termDict_${project}.json'))")
    if [ ! -f "$DATA_DIR/$TERM_DICT" ]; then
        echo -e "${RED}错误: 缺少项目 $project 的词典: $TERM_DICT${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ 词库文件完整${NC}\n"

# 4. 停掉旧版（nohup 方式）遗留的进程
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    # 确认 PID 仍是本工具的进程（避免 PID 被系统回收给其他程序后误杀）
    if ps -p "$OLD_PID" -o args= 2>/dev/null | grep -q "app.py"; then
        echo -e "${YELLOW}停止旧版后端进程 (PID: $OLD_PID)${NC}"
        kill "$OLD_PID"
        # 等旧进程退出、释放 5000 端口，最多 10 秒
        for i in $(seq 1 10); do
            ps -p "$OLD_PID" > /dev/null 2>&1 || break
            sleep 1
        done
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo -e "${RED}错误: 旧版后端进程未退出，请手动处理 (PID: $OLD_PID)${NC}"
            exit 1
        fi
    fi
    rm -f "$PID_FILE"
fi

# 5. 通过 systemd 用户服务启动（挂了自动重启、有内存上限）
echo "5. 启动后端服务..."
# 每次都重新渲染服务文件，模板改动（如内存上限）随代码一起生效
"$SCRIPT_DIR/deploy/install_service.sh" || exit 1
# 已在运行时用 restart，确保加载拉取后的新代码
systemctl --user restart transtool-py.service

# 等待服务启动
for i in $(seq 1 10); do
    sleep 1
    if curl -s http://localhost:5000/api/health > /dev/null; then
        break
    fi
done

# 6. 测试服务
echo "6. 测试服务..."
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo -e "${GREEN}✓ 服务正常运行${NC}\n"
else
    echo -e "${RED}错误: 服务未响应，请查看: systemctl --user status transtool-py 或 $LOG_DIR/backend.log${NC}"
    exit 1
fi

# 7. Nginx 配置提示
echo -e "${YELLOW}=== 下一步: 配置 Nginx ===${NC}\n"
echo "1. 生成本地 nginx.conf 并加入 Nginx:"
echo -e "   ${GREEN}$SCRIPT_DIR/render_nginx.sh${NC}"
echo -e "   ${GREEN}sudo cp $SCRIPT_DIR/nginx.conf /etc/nginx/sites-available/transtool-py${NC}"
echo -e "   ${GREEN}sudo ln -sf /etc/nginx/sites-available/transtool-py /etc/nginx/sites-enabled/${NC}"
echo ""
echo "2. 测试并重载 Nginx:"
echo -e "   ${GREEN}sudo nginx -t${NC}"
echo -e "   ${GREEN}sudo systemctl reload nginx${NC}"
echo ""
echo "3. 访问地址（PUBLIC_ORIGIN 在 deploy.env 中配置，未设置时见下方本机地址）:"
if [ -n "${PUBLIC_ORIGIN:-}" ]; then
  echo -e "   对外: ${GREEN}${PUBLIC_ORIGIN}/transtool-py/index.html?project=game1${NC}"
else
  echo "   提示: 复制 deploy.env.template 为 deploy.env 并设置 PUBLIC_ORIGIN 以显示公网/对外地址"
fi
echo -e "   本机: ${GREEN}http://127.0.0.1/transtool-py/index.html?project=game1${NC}"
echo ""
echo "后端日志: $LOG_DIR/backend.log"
echo -e "停止服务: ${GREEN}./stop.sh${NC}   查看状态: ${GREEN}./status.sh${NC}\n"

echo -e "${GREEN}=== 启动完成 ===${NC}"



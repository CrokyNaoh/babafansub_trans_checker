#!/bin/bash

# 翻译检查工具 - 状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/backend.pid"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== 翻译检查工具 - 服务状态 ===${NC}\n"

# 1. 后端状态
echo "【后端服务】"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "状态: ${GREEN}运行中${NC}"
        echo "PID: $PID"
        echo "内存: $(ps -o rss= -p $PID | awk '{print int($1/1024)"MB"}')"
        echo "运行时间: $(ps -o etime= -p $PID | xargs)"
    else
        echo -e "状态: ${RED}已停止${NC} (PID 文件存在但进程不存在)"
    fi
else
    echo -e "状态: ${YELLOW}未运行${NC}"
fi
echo ""

# 2. API 健康检查
echo "【API 健康检查】"
if curl -s -f http://localhost:5000/api/health > /dev/null; then
    echo -e "状态: ${GREEN}正常${NC}"
    RESPONSE=$(curl -s http://localhost:5000/api/health)
    echo "响应: $RESPONSE"
else
    echo -e "状态: ${RED}无响应${NC}"
fi
echo ""

# 3. Nginx 状态
echo "【Nginx 配置】"
if [ -f "/etc/nginx/sites-enabled/transtool-py" ]; then
    echo -e "配置: ${GREEN}已启用${NC}"
else
    echo -e "配置: ${YELLOW}未启用${NC}"
fi

if systemctl is-active --quiet nginx; then
    echo -e "Nginx: ${GREEN}运行中${NC}"
else
    echo -e "Nginx: ${RED}已停止${NC}"
fi
echo ""

# 4. 访问地址
echo "【访问地址】"
echo "http://139.224.225.128/transtool-py/index.html?project=game1"
echo "http://139.224.225.128/transtool-py/index.html?project=game2"
echo "http://139.224.225.128/transtool-py/index.html?project=novel"
echo ""

# 5. 日志文件
echo "【日志文件】"
LOG_DIR="$SCRIPT_DIR/logs"
if [ -f "$LOG_DIR/backend.log" ]; then
    SIZE=$(du -h "$LOG_DIR/backend.log" | cut -f1)
    LINES=$(wc -l < "$LOG_DIR/backend.log")
    echo "后端日志: $LOG_DIR/backend.log ($SIZE, $LINES 行)"
    echo "最后 5 行:"
    tail -5 "$LOG_DIR/backend.log" | sed 's/^/  /'
else
    echo "后端日志: 不存在"
fi



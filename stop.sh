#!/bin/bash

# 翻译检查工具 - 停止脚本（systemd 用户服务）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/backend.pid"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== 翻译检查工具 - 停止后端 ===${NC}\n"

# 无条件 stop：服务处于 activating / 自动重启等待中时 is-active 为假，但仍需要停掉
if systemctl --user cat transtool-py.service > /dev/null 2>&1; then
    systemctl --user stop transtool-py.service
    echo -e "${GREEN}✓ 后端服务已停止${NC}"
else
    echo -e "${YELLOW}后端服务未安装${NC}"
fi

# 兼容旧版 nohup 方式遗留的进程
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID" && echo -e "${GREEN}✓ 已停止旧版后端进程 (PID: $PID)${NC}"
    fi
    rm -f "$PID_FILE"
fi

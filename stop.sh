#!/bin/bash

# 翻译检查工具 - 停止脚本（后端版本）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/backend.pid"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== 翻译检查工具 - 停止后端 ===${NC}\n"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}后端未在运行${NC}"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}后端进程已停止 (PID: $PID)${NC}"
    rm "$PID_FILE"
    exit 0
fi

echo "正在停止后端服务 (PID: $PID)..."
kill "$PID"

# 等待进程停止
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 强制停止
echo -e "${YELLOW}强制停止后端服务...${NC}"
kill -9 "$PID" 2>/dev/null
rm "$PID_FILE"
echo -e "${GREEN}✓ 后端服务已强制停止${NC}"



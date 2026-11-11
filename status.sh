#!/bin/bash

# 翻译检查工具 - 状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/deploy.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/deploy.env"
  set +a
fi

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== 翻译检查工具 - 服务状态 ===${NC}\n"

# 1. 后端状态
echo "【后端服务】"
if systemctl --user is-active --quiet transtool-py.service; then
    echo -e "状态: ${GREEN}运行中${NC}"
    MAIN_PID=$(systemctl --user show -p MainPID --value transtool-py.service)
    MEM=$(systemctl --user show -p MemoryCurrent --value transtool-py.service)
    echo "PID: $MAIN_PID"
    [ -n "$MEM" ] && [ "$MEM" != "[not set]" ] && echo "内存: $((MEM / 1024 / 1024))MB（含检查子进程）"
    echo "启动时间: $(systemctl --user show -p ActiveEnterTimestamp --value transtool-py.service)"
    echo "自动重启次数: $(systemctl --user show -p NRestarts --value transtool-py.service)"
else
    echo -e "状态: ${RED}未运行${NC}"
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
if [ -n "${PUBLIC_ORIGIN:-}" ]; then
  for p in game1 game2 novel; do
    echo "${PUBLIC_ORIGIN}/transtool-py/index.html?project=$p"
  done
else
  echo "（在 deploy.env 中设置 PUBLIC_ORIGIN 以显示对外访问地址；以下为相对路径示例）"
  for p in game1 game2 novel; do
    echo "/transtool-py/index.html?project=$p"
  done
fi
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



#!/bin/bash

# 快速测试脚本

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== 翻译检查工具 - 功能测试 ===${NC}\n"

# 1. 测试后端健康检查
echo "1. 测试后端 API..."
HEALTH_RESPONSE=$(curl -s http://localhost:5000/api/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 后端 API 正常${NC}"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ 后端 API 无响应${NC}"
fi
echo ""

# 2. 测试项目信息接口
echo "2. 测试项目信息接口..."
for project in game1 game2 novel; do
    PROJECT_RESPONSE=$(curl -s http://localhost:5000/api/project/$project)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 项目 $project 信息正常${NC}"
        echo "   响应: $PROJECT_RESPONSE"
    else
        echo -e "${RED}✗ 项目 $project 获取失败${NC}"
    fi
done
echo ""

# 3. 测试 Nginx 代理
echo "3. 测试 Nginx 代理..."
NGINX_HEALTH=$(curl -s http://localhost/transtool-py/api/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Nginx 代理正常${NC}"
    echo "   响应: $NGINX_HEALTH"
else
    echo -e "${RED}✗ Nginx 代理失败${NC}"
fi
echo ""

# 4. 测试静态文件访问
echo "4. 测试静态文件访问..."
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/transtool-py/index.html)
if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}✓ 前端页面可访问 (HTTP $STATUS_CODE)${NC}"
else
    echo -e "${RED}✗ 前端页面访问失败 (HTTP $STATUS_CODE)${NC}"
fi
echo ""

# 5. 访问地址
echo -e "${YELLOW}=== 访问地址 ===${NC}"
echo -e "${GREEN}http://139.224.225.128/transtool-py/index.html?project=game1${NC}"
echo -e "${GREEN}http://139.224.225.128/transtool-py/index.html?project=game2${NC}"
echo -e "${GREEN}http://139.224.225.128/transtool-py/index.html?project=novel${NC}"



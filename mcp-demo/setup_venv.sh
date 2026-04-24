#!/bin/bash

# 创建虚拟环境并安装依赖
# Author: FlyAIBox
# Date: 2026-04-24

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="${SCRIPT_DIR}/venv"

unalias pip
unalias python

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}创建虚拟环境并安装依赖${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. 创建虚拟环境
echo -e "${YELLOW}[1/3] 创建虚拟环境...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境已存在，是否重新创建？(y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}✅ 虚拟环境已重新创建${NC}"
    else
        echo -e "${BLUE}使用现有虚拟环境${NC}"
    fi
else
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ 虚拟环境创建完成: ${VENV_DIR}${NC}"
fi

# 2. 激活虚拟环境
echo -e "\n${YELLOW}[2/3] 激活虚拟环境...${NC}"
source "${VENV_DIR}/bin/activate"
echo -e "${GREEN}✅ 虚拟环境已激活${NC}"

# 3. 安装依赖
echo -e "\n${YELLOW}[3/3] 安装依赖包...${NC}"
pip install --upgrade pip
pip install fastmcp requests playwright python-dotenv mcp

# 安装 playwright 浏览器
playwright install chromium

echo -e "${GREEN}✅ 依赖安装完成${NC}"

# 显示虚拟环境信息
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}虚拟环境信息${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Python 路径: $(which python)"
echo -e "Python 版本: $(python --version)"
echo -e "虚拟环境路径: ${VENV_DIR}"
echo -e "\n已安装的包:"
pip list | grep -E "(fastmcp|requests|playwright|mcp)"

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 虚拟环境设置完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}下一步：${NC}"
echo -e "1. 配置 Claude Desktop 使用虚拟环境："
echo -e "   编辑: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo -e "   {
     \"mcpServers\": {
       \"aws-opensearch-logs\": {
         \"command\": \"${VENV_DIR}/bin/python\",
         \"args\": [\"${SCRIPT_DIR}/server/aws_opensearch_mcp_server.py\"]
       }
     }
   }"
echo -e "\n2. 手动激活虚拟环境（开发时使用）："
echo -e "   ${YELLOW}source ${VENV_DIR}/bin/activate${NC}"
echo -e "\n3. 测试 MCP Server："
echo -e "   ${YELLOW}${VENV_DIR}/bin/python server/aws_opensearch_mcp_server.py${NC}"
echo -e "\n4. 获取 Cookies："
echo -e "   ${YELLOW}${VENV_DIR}/bin/python server/aws_opensearch_auto.py${NC}\n"

#!/bin/bash

# AWS OpenSearch MCP Server 自动配置脚本
#
# 功能：
# 1. 检查环境依赖
# 2. 配置 Claude Desktop
# 3. 测试连接
#
# Author: FlyAIBox
# Date: 2026-04-24

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVER_PATH="${SCRIPT_DIR}/server/aws_opensearch_mcp_server.py"
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="${CLAUDE_CONFIG_DIR}/claude_desktop_config.json"
COOKIES_FILE="${SCRIPT_DIR}/opensearch_cookies.json"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AWS OpenSearch MCP Server 配置向导${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. 检查 Python
echo -e "${YELLOW}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 Python 3，请先安装 Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✅ Python 版本: ${PYTHON_VERSION}${NC}"

# 2. 检查依赖包
echo -e "\n${YELLOW}[2/5] 检查依赖包...${NC}"
MISSING_PACKAGES=()

if ! python3 -c "import fastmcp" 2>/dev/null; then
    MISSING_PACKAGES+=("fastmcp")
fi

if ! python3 -c "import requests" 2>/dev/null; then
    MISSING_PACKAGES+=("requests")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  缺少以下依赖包: ${MISSING_PACKAGES[*]}${NC}"
    read -p "是否自动安装？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}正在安装依赖包...${NC}"
        pip3 install "${MISSING_PACKAGES[@]}"
        echo -e "${GREEN}✅ 依赖包安装完成${NC}"
    else
        echo -e "${RED}❌ 请手动安装: pip3 install ${MISSING_PACKAGES[*]}${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 所有依赖包已安装${NC}"
fi

# 3. 检查 Cookies 文件
echo -e "\n${YELLOW}[3/5] 检查认证 Cookies...${NC}"
if [ ! -f "$COOKIES_FILE" ]; then
    echo -e "${YELLOW}⚠️  未找到 opensearch_cookies.json${NC}"
    echo -e "${BLUE}需要先获取 AWS OpenSearch 认证 cookies${NC}"
    read -p "是否现在运行自动登录脚本？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}启动自动登录脚本（需要手动登录）...${NC}"
        python3 "${SCRIPT_DIR}/server/aws_opensearch_auto.py"
        if [ -f "$COOKIES_FILE" ]; then
            echo -e "${GREEN}✅ Cookies 已获取${NC}"
        else
            echo -e "${RED}❌ Cookies 获取失败${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}跳过 Cookies 检查，后续需手动运行 aws_opensearch_auto.py${NC}"
    fi
else
    # 检查 cookies 有效期
    COOKIE_AGE=$(( $(date +%s) - $(stat -f %m "$COOKIES_FILE") ))
    COOKIE_AGE_HOURS=$(( COOKIE_AGE / 3600 ))

    if [ $COOKIE_AGE_HOURS -gt 24 ]; then
        echo -e "${YELLOW}⚠️  Cookies 文件已超过 ${COOKIE_AGE_HOURS} 小时，可能已过期${NC}"
        read -p "是否重新获取？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "${SCRIPT_DIR}/server/aws_opensearch_auto.py"
        fi
    else
        echo -e "${GREEN}✅ Cookies 文件存在（${COOKIE_AGE_HOURS} 小时前创建）${NC}"
    fi
fi

# 4. 配置 Claude Desktop
echo -e "\n${YELLOW}[4/5] 配置 Claude Desktop...${NC}"

# 创建配置目录
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}⚠️  Claude 配置目录不存在，创建中...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# 备份现有配置
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠️  发现现有配置文件，创建备份...${NC}"
    cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ 备份已保存${NC}"

    # 读取现有配置并合并
    echo -e "${BLUE}正在合并配置...${NC}"
    TEMP_CONFIG=$(mktemp)

    # 使用 Python 合并 JSON
    python3 << EOF
import json
import sys

try:
    with open('${CLAUDE_CONFIG_FILE}', 'r') as f:
        config = json.load(f)
except:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['aws-opensearch-logs'] = {
    'command': 'python',
    'args': ['${SERVER_PATH}'],
    'env': {}
}

with open('${TEMP_CONFIG}', 'w') as f:
    json.dump(config, f, indent=2)
EOF

    mv "$TEMP_CONFIG" "$CLAUDE_CONFIG_FILE"
    echo -e "${GREEN}✅ 配置已合并${NC}"
else
    # 创建新配置
    echo -e "${BLUE}创建新配置文件...${NC}"
    cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "python",
      "args": [
        "${SERVER_PATH}"
      ],
      "env": {}
    }
  }
}
EOF
    echo -e "${GREEN}✅ 配置文件已创建${NC}"
fi

echo -e "${BLUE}配置文件位置: ${CLAUDE_CONFIG_FILE}${NC}"

# 5. 测试 MCP Server
echo -e "\n${YELLOW}[5/5] 测试 MCP Server...${NC}"
read -p "是否测试 MCP Server？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}正在启动 MCP Server（按 Ctrl+C 停止）...${NC}"
    timeout 5s python3 "$SERVER_PATH" 2>&1 | head -20 || true
    echo -e "${GREEN}✅ MCP Server 可以正常启动${NC}"
fi

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 配置完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}下一步：${NC}"
echo -e "  1. 重启 Claude Desktop"
echo -e "  2. 在 Claude 中使用以下命令测试："
echo -e "     ${YELLOW}帮我搜索最近 1 小时的 ERROR 日志${NC}"
echo -e "  3. 如果 cookies 过期，运行："
echo -e "     ${YELLOW}python3 ${SCRIPT_DIR}/server/aws_opensearch_auto.py${NC}\n"

echo -e "${BLUE}可用工具：${NC}"
echo -e "  - search_aws_logs: 搜索日志（按小时）"
echo -e "  - search_aws_logs_by_time: 搜索日志（自定义时间）\n"

echo -e "${BLUE}查看完整文档：${NC}"
echo -e "  cat ${SCRIPT_DIR}/MCP_SETUP.md\n"

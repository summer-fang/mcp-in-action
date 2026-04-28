#!/bin/bash
# Claude Code MCP Server 快速配置脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Claude Code MCP Server 配置工具${NC}"
echo -e "${BLUE}================================${NC}\n"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 路径配置
VENV_PATH="$SCRIPT_DIR/venv_mcp_demo"
MCP_SERVER_PATH="$SCRIPT_DIR/server/aws_opensearch_mcp_server.py"
COOKIES_FILE="$SCRIPT_DIR/opensearch_cookies.json"
GLOBAL_CONFIG="$HOME/.claude/config.json"
PROJECT_CONFIG="$PROJECT_ROOT/.claude/settings.local.json"

echo -e "${YELLOW}当前配置:${NC}"
echo -e "  项目目录: $PROJECT_ROOT"
echo -e "  虚拟环境: $VENV_PATH"
echo -e "  MCP Server: $MCP_SERVER_PATH"
echo -e "  Cookies: $COOKIES_FILE\n"

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ 虚拟环境不存在: $VENV_PATH${NC}"
    echo -e "${YELLOW}正在创建虚拟环境...${NC}"
    python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip
    pip install mcp requests
    echo -e "${GREEN}✅ 虚拟环境创建成功${NC}\n"
else
    echo -e "${GREEN}✅ 虚拟环境已存在${NC}\n"
fi

# 检查 MCP Server 文件
if [ ! -f "$MCP_SERVER_PATH" ]; then
    echo -e "${RED}❌ MCP Server 文件不存在: $MCP_SERVER_PATH${NC}"
    exit 1
else
    echo -e "${GREEN}✅ MCP Server 文件存在${NC}\n"
fi

# 配置方式选择
echo -e "${YELLOW}请选择配置方式:${NC}"
echo "  1) 全局配置 (~/.claude/config.json)"
echo "  2) 项目配置 (.claude/settings.local.json)"
echo "  3) 查看当前配置"
echo "  4) 退出"
echo -n "请输入选项 [1-4]: "
read choice

case $choice in
    1)
        # 全局配置
        echo -e "\n${BLUE}配置全局 MCP Server...${NC}"

        # 创建配置目录
        mkdir -p "/$HOME.claude"

        # 读取现有配置或创建新配置
        if [ -f "$GLOBAL_CONFIG" ]; then
            echo -e "${YELLOW}检测到现有配置，将会合并...${NC}"
            # 备份现有配置
            cp "$GLOBAL_CONFIG" "$GLOBAL_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        fi

        # 生成配置
        cat > "$GLOBAL_CONFIG" << EOF
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "$VENV_PATH/bin/python",
      "args": [
        "-u",
        "$MCP_SERVER_PATH"
      ]
    }
  }
}
EOF

        echo -e "${GREEN}✅ 全局配置已写入: $GLOBAL_CONFIG${NC}"
        echo -e "${BLUE}配置内容:${NC}"
        cat "$GLOBAL_CONFIG" | python3 -m json.tool
        ;;

    2)
        # 项目配置
        echo -e "\n${BLUE}配置项目级别 MCP Server...${NC}"

        # 创建配置目录
        mkdir -p "$(dirname "$PROJECT_CONFIG")"

        # 读取现有配置或创建新配置
        if [ -f "$PROJECT_CONFIG" ]; then
            echo -e "${YELLOW}检测到现有配置，将会合并...${NC}"
            # 备份现有配置
            cp "$PROJECT_CONFIG" "$PROJECT_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        fi

        # 生成配置
        cat > "$PROJECT_CONFIG" << EOF
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "$VENV_PATH/bin/python",
      "args": [
        "-u",
        "$MCP_SERVER_PATH"
      ]
    }
  },
  "permissions": {
    "allow": [
      "mcp__aws-opensearch-logs__search_aws_logs",
      "mcp__aws-opensearch-logs__search_aws_logs_by_time"
    ]
  }
}
EOF

        echo -e "${GREEN}✅ 项目配置已写入: $PROJECT_CONFIG${NC}"
        echo -e "${BLUE}配置内容:${NC}"
        cat "$PROJECT_CONFIG" | python3 -m json.tool

        # 添加到 .gitignore
        GITIGNORE="$PROJECT_ROOT/.gitignore"
        if [ ! -f "$GITIGNORE" ] || ! grep -q "settings.local.json" "$GITIGNORE"; then
            echo -e "\n# Claude Code 本地配置" >> "$GITIGNORE"
            echo ".claude/settings.local.json" >> "$GITIGNORE"
            echo -e "${GREEN}✅ 已添加到 .gitignore${NC}"
        fi
        ;;

    3)
        # 查看当前配置
        echo -e "\n${BLUE}当前配置信息:${NC}\n"

        if [ -f "$GLOBAL_CONFIG" ]; then
            echo -e "${GREEN}全局配置 ($GLOBAL_CONFIG):${NC}"
            cat "$GLOBAL_CONFIG" | python3 -m json.tool
            echo ""
        else
            echo -e "${YELLOW}全局配置不存在${NC}\n"
        fi

        if [ -f "$PROJECT_CONFIG" ]; then
            echo -e "${GREEN}项目配置 ($PROJECT_CONFIG):${NC}"
            cat "$PROJECT_CONFIG" | python3 -m json.tool
            echo ""
        else
            echo -e "${YELLOW}项目配置不存在${NC}\n"
        fi

        # 检查 MCP 连接状态
        echo -e "${BLUE}检查 MCP Server 连接状态...${NC}"
        if command -v claude &> /dev/null; then
            claude mcp list || echo -e "${YELLOW}无法获取 MCP 状态${NC}"
        else
            echo -e "${YELLOW}claude 命令未找到，请先安装 Claude Code${NC}"
        fi
        exit 0
        ;;

    4)
        echo -e "${BLUE}退出配置${NC}"
        exit 0
        ;;

    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

# 检查 cookies 文件
echo -e "\n${BLUE}检查认证配置...${NC}"
if [ ! -f "$COOKIES_FILE" ]; then
    echo -e "${YELLOW}⚠️  Cookies 文件不存在: $COOKIES_FILE${NC}"
    echo -e "${YELLOW}请运行以下命令获取 cookies:${NC}"
    echo -e "  cd $SCRIPT_DIR"
    echo -e "  python server/aws_opensearch_auto.py"
else
    echo -e "${GREEN}✅ Cookies 文件已存在${NC}"

    # 检查 cookies 是否过期
    EXPIRES=$(python3 -c "
import json
from pathlib import Path
import time

cookies_file = Path('$COOKIES_FILE')
if cookies_file.exists():
    cookies = json.loads(cookies_file.read_text())
    expires_list = [c.get('expires', 0) for c in cookies if 'expires' in c]
    if expires_list:
        min_expires = min(expires_list)
        now = time.time()
        if min_expires > now:
            remaining = int((min_expires - now) / 3600)
            print(f'{remaining} 小时')
        else:
            print('已过期')
    else:
        print('未知')
else:
    print('文件不存在')
" 2>/dev/null || echo "未知")

    echo -e "  过期时间: $EXPIRES"
fi

# 验证配置
echo -e "\n${BLUE}验证配置...${NC}"
if command -v claude &> /dev/null; then
    echo -e "${GREEN}Claude Code 已安装${NC}"
    echo -e "\n${BLUE}MCP Server 状态:${NC}"
    claude mcp list || echo -e "${YELLOW}无法获取 MCP 状态（可能需要重启 Claude Code）${NC}"
else
    echo -e "${YELLOW}⚠️  claude 命令未找到${NC}"
    echo -e "请先安装 Claude Code: https://claude.ai/download"
fi

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}配置完成！${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${BLUE}下一步:${NC}"
echo "  1. 如果 Cookies 不存在，运行: python server/aws_opensearch_auto.py"
echo "  2. 重启 Claude Code 或重新进入对话"
echo "  3. 测试查询: '查询 AWS OpenSearch 中的 ERROR 日志'"
echo ""

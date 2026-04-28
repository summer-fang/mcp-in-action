#!/bin/bash

# 将 .zshrc 中的 AWS 环境变量同步到系统级
# 这样 Claude Desktop 就能读取到这些环境变量
#
# 使用方式：
#   ./sync-aws-env-to-claude.sh
#
# Author: FlyAIBox
# Date: 2026-04-27

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}同步 AWS 环境变量到 Claude Desktop${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. 从 .zshrc 读取环境变量
echo -e "${YELLOW}[1/4] 从 .zshrc 读取环境变量...${NC}"

# 提取 AWS_BEARER_TOKEN_BEDROCK 的值
AWS_BEARER_TOKEN_BEDROCK=$(grep "export AWS_BEARER_TOKEN_BEDROCK" ~/.zshrc | sed 's/.*="\(.*\)"/\1/')

# 尝试读取其他 AWS 变量
AWS_REGION=$(grep "export AWS_REGION" ~/.zshrc 2>/dev/null | sed 's/.*="\(.*\)"/\1/' || echo "")
AWS_ACCESS_KEY_ID=$(grep "export AWS_ACCESS_KEY_ID" ~/.zshrc 2>/dev/null | sed 's/.*="\(.*\)"/\1/' || echo "")
AWS_SECRET_ACCESS_KEY=$(grep "export AWS_SECRET_ACCESS_KEY" ~/.zshrc 2>/dev/null | sed 's/.*="\(.*\)"/\1/' || echo "")

# 2. 检查必需的环境变量
echo -e "${YELLOW}[2/4] 检查环境变量...${NC}"

if [ -z "$AWS_BEARER_TOKEN_BEDROCK" ]; then
    echo -e "${RED}❌ 未找到 AWS_BEARER_TOKEN_BEDROCK${NC}"
    echo "请确保在 ~/.zshrc 中配置了此变量"
    exit 1
fi

echo -e "${GREEN}✅ AWS_BEARER_TOKEN_BEDROCK: ${AWS_BEARER_TOKEN_BEDROCK:0:20}...${NC}"

# 3. 设置系统级环境变量
echo -e "\n${YELLOW}[3/4] 设置系统级环境变量...${NC}"

# 设置 Bearer Token
launchctl setenv AWS_BEARER_TOKEN_BEDROCK "$AWS_BEARER_TOKEN_BEDROCK"
echo "✅ AWS_BEARER_TOKEN_BEDROCK 已设置"

# 设置其他 AWS 相关变量（如果存在）
if [ ! -z "$AWS_REGION" ]; then
    launchctl setenv AWS_REGION "$AWS_REGION"
    echo "✅ AWS_REGION: $AWS_REGION"
else
    launchctl setenv AWS_REGION "us-east-1"
    echo "✅ AWS_REGION: us-east-1 (默认)"
fi

if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    launchctl setenv AWS_ACCESS_KEY_ID "$AWS_ACCESS_KEY_ID"
    echo "✅ AWS_ACCESS_KEY_ID 已设置"
fi

if [ ! -z "$AWS_SECRET_ACCESS_KEY" ]; then
    launchctl setenv AWS_SECRET_ACCESS_KEY "$AWS_SECRET_ACCESS_KEY"
    echo "✅ AWS_SECRET_ACCESS_KEY 已设置"
fi

# 4. 验证
echo -e "\n${YELLOW}[4/4] 验证环境变量...${NC}"

TOKEN_CHECK=$(launchctl getenv AWS_BEARER_TOKEN_BEDROCK)
if [ ! -z "$TOKEN_CHECK" ]; then
    echo -e "${GREEN}✅ 系统环境变量已正确设置${NC}"
    echo "   Token (前 20 字符): ${TOKEN_CHECK:0:20}..."
else
    echo -e "${RED}❌ 环境变量设置失败${NC}"
    exit 1
fi

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 环境变量同步完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}下一步：${NC}"
echo "1. 重启 Claude Desktop（完全退出后重新打开）"
echo "2. Claude Desktop 现在可以使用 AWS Bedrock"
echo ""
echo -e "${YELLOW}注意：${NC}"
echo "- 每次更新 .zshrc 中的 token 后需要重新运行此脚本"
echo "- 系统重启后需要重新运行此脚本"
echo ""
echo -e "${BLUE}提示：${NC}"
echo "添加到启动项自动执行："
echo "  echo '$PWD/sync-aws-env-to-claude.sh' >> ~/.zprofile"
echo ""

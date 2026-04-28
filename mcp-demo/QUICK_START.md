# AWS OpenSearch MCP Server 快速开始

## 🚀 一键配置

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo

# 运行自动配置脚本
./setup_claude_code_mcp.sh
```

选择 **1** (全局配置) 或 **2** (项目配置)

## ✅ 验证

```bash
# 检查 MCP Server 状态
claude mcp list

# 应该看到：
# aws-opensearch-logs: ... - ✓ Connected
```

## 🔑 获取 Cookies

如果 cookies 不存在或已过期：

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo
python server/aws_opensearch_auto.py
# 选择 1: 获取 cookies
```

## 🧪 测试

在 Claude Code 中测试：

```
查询 AWS OpenSearch 中包含 "ERROR" 的日志
```

或

```
搜索最近2小时 *bts-bigaccount* 索引中的异常日志
```

## 📚 详细文档

查看完整配置文档：[MCP_SERVER_CONFIGURATION.md](./MCP_SERVER_CONFIGURATION.md)

---

## 核心配置变更

### 1. 代码修改

```python
# 导入 FastMCP
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("aws-opensearch-logs")

# 使用装饰器暴露工具
@mcp.tool()
def search_aws_logs(query: str, ...) -> str:
    """搜索日志"""
    # ...

# 启动服务器
if __name__ == "__main__":
    mcp.run(transport='stdio')
```

### 2. Claude Code 配置

**全局配置** (`~/.claude/config.json`):

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/path/to/venv/bin/python",
      "args": ["-u", "/path/to/aws_opensearch_mcp_server.py"]
    }
  }
}
```

**项目配置** (`.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/path/to/venv/bin/python",
      "args": ["-u", "/path/to/aws_opensearch_mcp_server.py"]
    }
  },
  "permissions": {
    "allow": [
      "mcp__aws-opensearch-logs__search_aws_logs",
      "mcp__aws-opensearch-logs__search_aws_logs_by_time"
    ]
  }
}
```

### 3. 关键变量

| 变量 | 说明 | 值 |
|------|------|-----|
| `AWS_OPENSEARCH_BASE_URL` | OpenSearch 地址 | 根据环境修改 |
| `COOKIES_FILE` | Cookies 文件路径 | `opensearch_cookies.json` |
| `PYTHON_VENV` | 虚拟环境 Python | `venv_mcp_demo/bin/python` |
| MCP Server 名称 | 在代码和配置中 | `"aws-opensearch-logs"` (必须一致) |

---

**作者:** FlyAIBox  
**更新:** 2026-04-28

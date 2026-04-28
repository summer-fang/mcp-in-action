# AWS OpenSearch MCP Server 配置文档

## 📋 概述

本文档说明如何将 `aws_opensearch_mcp_server.py` 配置为 MCP (Model Context Protocol) 服务器，供 **Claude Code CLI** 使用。

## 🏗️ 架构说明

```
Claude Code CLI
    ↓ (stdio transport)
MCP Server (aws_opensearch_mcp_server.py)
    ↓ (HTTP + Cookies)
AWS OpenSearch Service (SSO 认证)
```

## 📝 配置变更总结

### 从普通脚本到 MCP Server 的关键修改

| 修改项 | 原始代码 | MCP 配置 | 说明 |
|-------|---------|---------|------|
| **导入框架** | `import requests` | `from mcp.server.fastmcp import FastMCP` | 添加 MCP 框架支持 |
| **初始化** | 无 | `mcp = FastMCP("aws-opensearch-logs")` | 创建 MCP 服务器实例 |
| **函数装饰器** | `def search_logs(...)` | `@mcp.tool()`<br>`def search_aws_logs(...)` | 将函数暴露为 MCP 工具 |
| **启动方式** | `if __name__ == "__main__":`<br>&nbsp;&nbsp;&nbsp;&nbsp;`client.search(...)` | `if __name__ == "__main__":`<br>&nbsp;&nbsp;&nbsp;&nbsp;`mcp.run(transport='stdio')` | 使用 stdio 传输协议 |
| **返回类型** | `return dict` | `return str` | MCP 工具必须返回字符串 |
| **配置文件** | 无 | `~/.claude/config.json`<br>或 `.claude/settings.local.json` | Claude Code 配置 |

### 核心变量配置

| 变量名 | 值 | 作用 | 修改建议 |
|-------|-----|------|---------|
| `AWS_OPENSEARCH_BASE_URL` | `https://search-ops-log-alpha-...` | OpenSearch 服务地址 | 根据实际环境修改 |
| `COOKIES_FILE` | `Path(__file__).parent.parent / "opensearch_cookies.json"` | Cookies 存储路径 | 保持相对路径 |
| `COOKIE_REFRESH_SCRIPT` | `Path(...) / "server" / "aws_opensearch_auto.py"` | 自动刷新脚本路径 | 保持相对路径 |
| `PYTHON_VENV` | `Path(...) / "venv_mcp_demo" / "bin" / "python"` | 虚拟环境 Python | 确保虚拟环境存在 |
| MCP Server 名称 | `"aws-opensearch-logs"` | 在 FastMCP 和配置文件中 | 必须一致 |

## 🔧 核心配置文件

### 1. MCP Server 主文件

**文件路径:** `mcp-demo/server/aws_opensearch_mcp_server.py`

#### 主要修改点

##### 1.1 导入 FastMCP 框架

```python
from mcp.server.fastmcp import FastMCP
```

##### 1.2 初始化 MCP 服务器

```python
# 初始化 FastMCP 服务器
mcp = FastMCP("aws-opensearch-logs")
```

**变量说明:**
- `"aws-opensearch-logs"`: MCP 服务器名称（需要与 Claude Desktop 配置中的 key 一致）

##### 1.3 配置常量

```python
# AWS OpenSearch 配置
AWS_OPENSEARCH_BASE_URL = "https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com"
COOKIES_FILE = Path(__file__).parent.parent / "opensearch_cookies.json"

# Cookie刷新脚本路径
COOKIE_REFRESH_SCRIPT = Path(__file__).parent.parent / "server" / "aws_opensearch_auto.py"
PYTHON_VENV = Path(__file__).parent.parent / "venv_mcp_demo" / "bin" / "python"
```

**变量说明:**
- `AWS_OPENSEARCH_BASE_URL`: OpenSearch 服务器地址
- `COOKIES_FILE`: SSO cookies 存储文件路径
- `COOKIE_REFRESH_SCRIPT`: 自动刷新 cookies 的脚本路径
- `PYTHON_VENV`: Python 虚拟环境中的 Python 解释器路径

##### 1.4 使用 @mcp.tool() 装饰器暴露工具

**工具 1: search_aws_logs**

```python
@mcp.tool()
def search_aws_logs(
    query: str,
    index_pattern: str = "*bts-bigaccount*",
    hours_ago: int = 1,
    size: int = 20
) -> str:
    """
    在 AWS OpenSearch 中搜索日志（使用 SSO cookies 认证）
    
    参数:
        query: 搜索关键词（支持 Lucene 查询语法）
        index_pattern: 索引模式，默认 "*bts-bigaccount*"
        hours_ago: 查询最近多少小时的日志，默认 1 小时
        size: 返回结果数量，默认 20
    
    返回:
        格式化的日志搜索结果
    """
    # ... 实现代码
```

**工具 2: search_aws_logs_by_time**

```python
@mcp.tool()
def search_aws_logs_by_time(
    query: str,
    time_from: str,
    time_to: str = "now",
    index_pattern: str = "*bts-bigaccount*",
    size: int = 20
) -> str:
    """
    在 AWS OpenSearch 中按指定时间范围搜索日志
    
    参数:
        query: 搜索关键词
        time_from: 开始时间（如 "2026-04-24T10:00:00", "now-2h"）
        time_to: 结束时间，默认 "now"
        index_pattern: 索引模式
        size: 返回结果数量
    
    返回:
        格式化的日志搜索结果
    """
    # ... 实现代码
```

##### 1.5 启动 MCP 服务器

```python
if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run(transport='stdio')
```

**变量说明:**
- `transport='stdio'`: 使用标准输入/输出通信（Claude Desktop 通过 stdio 与 MCP Server 通信）

### 2. Claude Code CLI 配置

Claude Code 支持两种配置方式：**全局配置** 和 **项目配置**。

#### 方式 A: 全局配置（推荐）

**配置文件路径:** `~/.claude/config.json`

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv_mcp_demo/bin/python",
      "args": [
        "-u",
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
      ]
    }
  }
}
```

**优点:**
- 所有项目共享配置
- 一次配置，到处使用

#### 方式 B: 项目配置

**配置文件路径:** `<项目根目录>/.claude/settings.local.json`

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv_mcp_demo/bin/python",
      "args": [
        "-u",
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
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
```

**优点:**
- 项目级别隔离
- 可以配置权限自动允许 MCP 工具调用

**配置项说明:**

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `aws-opensearch-logs` | MCP Server 名称（与代码中 `FastMCP("aws-opensearch-logs")` 对应） | 必须一致 |
| `command` | Python 解释器路径（推荐使用虚拟环境） | `/path/to/venv/bin/python` |
| `args` | MCP Server 脚本路径和参数 | `["-u", "/path/to/aws_opensearch_mcp_server.py"]` |
| `args[-u]` | Python unbuffered 模式，实时输出日志 | 推荐添加 |
| `permissions.allow` | 自动允许的 MCP 工具（格式：`mcp__<server>__<tool>`） | 可选 |

### 3. 认证配置文件

**文件路径:** `mcp-demo/opensearch_cookies.json`

#### 文件格式

```json
[
  {
    "name": "REFRESH-TOKEN",
    "value": "eyJjdHkiOiJKV1Q...",
    "domain": ".ap-southeast-1.es.amazonaws.com",
    "path": "/",
    "expires": 1777021773,
    "httpOnly": true,
    "secure": true
  },
  {
    "name": "ID-TOKEN",
    "value": "eyJraWQiOiJDUm5O...",
    "domain": ".ap-southeast-1.es.amazonaws.com",
    "path": "/",
    "expires": 1777021773,
    "httpOnly": true,
    "secure": true
  },
  {
    "name": "ACCESS-TOKEN",
    "value": "eyJraWQiOiI4RTBv...",
    "domain": ".ap-southeast-1.es.amazonaws.com",
    "path": "/",
    "expires": 1777021773,
    "httpOnly": true,
    "secure": true
  }
]
```

**说明:**
- 该文件由 `aws_opensearch_auto.py` 自动生成
- 包含 SSO 认证所需的三个 token
- Token 有过期时间，需要定期刷新

## 🚀 配置步骤

### 快速配置（推荐）

使用自动配置脚本一键完成配置：

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo

# 运行配置脚本
./setup_claude_code_mcp.sh

# 选择配置方式：
# 1) 全局配置 - 所有项目可用
# 2) 项目配置 - 仅当前项目，支持权限管理
# 3) 查看当前配置
```

**脚本会自动完成:**
- ✅ 检查并创建虚拟环境
- ✅ 安装必要依赖 (mcp, requests)
- ✅ 生成配置文件
- ✅ 检查 cookies 状态
- ✅ 验证 MCP Server 连接

---

### 手动配置

如果需要手动配置，请按照以下步骤操作：

### Step 1: 安装依赖

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo

# 创建虚拟环境
python3 -m venv venv_mcp_demo

# 激活虚拟环境
source venv_mcp_demo/bin/activate

# 安装依赖
pip install mcp requests
```

**依赖包说明:**
- `mcp`: Model Context Protocol SDK（包含 FastMCP）
- `requests`: HTTP 请求库（用于调用 OpenSearch API）

### Step 2: 获取 OpenSearch Cookies

```bash
# 运行自动化脚本获取 cookies
python server/aws_opensearch_auto.py

# 选择选项 1: 获取 cookies
# 脚本会自动打开浏览器并引导你完成 SSO 登录
# 登录成功后会自动保存 cookies 到 opensearch_cookies.json
```

### Step 3: 配置 Claude Code

#### 选择一种配置方式

**方式 A: 全局配置（推荐）**

```bash
# 编辑全局配置文件
vim ~/.claude/config.json
```

添加或修改配置:

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv_mcp_demo/bin/python",
      "args": [
        "-u",
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
      ]
    }
  }
}
```

**方式 B: 项目配置**

```bash
# 创建项目配置目录
mkdir -p /Users/bjsttlp314/IdeaProjects/mcp-in-action/.claude

# 编辑项目配置文件
vim /Users/bjsttlp314/IdeaProjects/mcp-in-action/.claude/settings.local.json
```

添加配置:

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv_mcp_demo/bin/python",
      "args": [
        "-u",
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
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
```

**注意:** 
- 将路径替换为你的实际路径
- 如果使用项目配置，需要在项目目录下运行 `claude` 命令

### Step 4: 验证 MCP Server 连接

```bash
# 检查 MCP Server 状态
claude mcp list

# 应该看到类似输出：
# aws-opensearch-logs: /path/to/python /path/to/aws_opensearch_mcp_server.py - ✓ Connected
```

如果显示 `✓ Connected`，说明配置成功。

### Step 5: 测试 MCP 工具

在 Claude Code 中测试（在项目目录下运行 `claude`）:

```
请帮我搜索 AWS OpenSearch 中包含 "ERROR" 的日志
```

或

```
查询最近2小时内 *bts-bigaccount* 索引中的异常日志
```

## 🔄 自动刷新机制

### Cookie 自动刷新流程

当 MCP Server 检测到 cookies 过期时，会自动执行以下流程:

```python
def refresh_cookies() -> bool:
    """
    自动运行cookies刷新脚本
    
    返回:
        True: 刷新成功
        False: 刷新失败
    """
    try:
        logger.info("🔄 检测到 cookies 过期，正在自动刷新...")
        
        # 执行刷新脚本（选项1：获取cookies）
        process = subprocess.Popen(
            [str(PYTHON_VENV), "-u", str(COOKIE_REFRESH_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 自动输入选项1（获取cookies）
        stdout, stderr = process.communicate(input="1\n", timeout=300)
        
        # 检查cookies文件是否更新成功
        if COOKIES_FILE.exists():
            logger.info("✅ Cookies 文件已更新，重新加载客户端...")
            return True
        else:
            logger.error("❌ Cookies 文件未生成")
            return False
            
    except Exception as e:
        logger.error(f"❌ 刷新 cookies 失败: {e}")
        return False
```

**变量说明:**
- `PYTHON_VENV`: 虚拟环境的 Python 路径
- `COOKIE_REFRESH_SCRIPT`: cookies 刷新脚本路径
- `timeout=300`: 刷新超时时间（5分钟）

### 重新加载客户端

```python
def reload_client():
    """重新加载客户端（清除缓存）"""
    global _aws_opensearch_client
    _aws_opensearch_client = None
```

刷新成功后，会清除全局客户端缓存，下次调用时重新加载新的 cookies。

## 📊 完整的调用流程

```
1. 用户在 Claude Code CLI 中发送查询
   ↓
2. Claude 识别需要调用 MCP 工具
   ↓
3. Claude Code 通过 stdio 调用 aws_opensearch_mcp_server.py
   ↓
4. MCP Server 从 opensearch_cookies.json 加载 cookies
   ↓
5. MCP Server 使用 cookies 调用 AWS OpenSearch API
   ↓
6. 如果认证失败:
   ├─ 6a. 自动运行 aws_opensearch_auto.py 刷新 cookies
   ├─ 6b. 重新加载客户端
   └─ 6c. 重试查询
   ↓
7. 返回格式化的日志结果给 Claude Code
   ↓
8. Claude 将结果展示给用户
```

## 🔧 Claude Code 特有功能

### 1. 权限管理

Claude Code 可以配置自动允许 MCP 工具调用，避免每次都需要手动确认。

**在项目配置中添加:**

```json
{
  "permissions": {
    "allow": [
      "mcp__aws-opensearch-logs__search_aws_logs",
      "mcp__aws-opensearch-logs__search_aws_logs_by_time"
    ]
  }
}
```

**权限格式:** `mcp__<server-name>__<tool-name>`

### 2. 查看 MCP 工具列表

```bash
# 在 Claude Code 中使用命令
claude mcp list

# 或在对话中询问
# "显示可用的 MCP 工具"
```

### 3. 调试 MCP Server

```bash
# 查看 MCP Server 日志
tail -f ~/.claude/logs/mcp-server-aws-opensearch-logs.log

# 手动测试 MCP Server
/path/to/venv/bin/python -u /path/to/aws_opensearch_mcp_server.py
```

## 🔐 安全性说明

### Cookies 安全

1. **不要提交 cookies 文件到 Git**
   ```bash
   # .gitignore
   opensearch_cookies.json
   ```

2. **限制文件权限**
   ```bash
   chmod 600 opensearch_cookies.json
   ```

3. **定期刷新 cookies**
   - Cookies 有过期时间（通常几小时）
   - MCP Server 会自动检测并刷新

### MCP Server 安全

1. **使用虚拟环境隔离依赖**
2. **不在配置中硬编码敏感信息**
3. **日志中不输出完整 token 内容**

## 🐛 故障排查

### 1. MCP Server 无法启动

**检查项:**

```bash
# 检查 Python 路径是否正确
which python

# 检查依赖是否安装
pip list | grep mcp

# 手动测试启动
python server/aws_opensearch_mcp_server.py
```

### 2. Cookies 认证失败

**解决方案:**

```bash
# 手动刷新 cookies
python server/aws_opensearch_auto.py

# 检查 cookies 文件
cat opensearch_cookies.json | jq .
```

### 3. 查看日志

**MCP Server 日志:**
```bash
# Claude Code 的 MCP 日志位置
tail -f ~/.claude/logs/mcp-server-aws-opensearch-logs.log

# 或查看所有 MCP 日志
ls -la ~/.claude/logs/mcp-*
```

**测试日志输出:**
```python
logger.info("这是一条测试日志")
logger.error("这是一条错误日志")
```

**提示:** 在 `args` 中添加 `-u` 参数（unbuffered 模式）可以实时看到日志输出。

### 4. 使用 Claude Code 命令

```bash
# 列出所有 MCP Servers
claude mcp list

# 检查 MCP Server 健康状态
claude mcp health

# 重启 MCP Server（如果配置有更改）
# 直接重启 Claude Code CLI 即可（退出重新进入）
```

## 💡 最佳实践

### 1. 使用虚拟环境

始终使用虚拟环境隔离 MCP Server 的依赖:

```bash
python3 -m venv venv_mcp_demo
source venv_mcp_demo/bin/activate
pip install mcp requests
```

### 2. 使用 -u 参数

在配置中添加 `-u` 参数，实时查看日志:

```json
{
  "args": ["-u", "/path/to/aws_opensearch_mcp_server.py"]
}
```

### 3. 配置权限自动允许

在项目配置中预先允许常用的 MCP 工具，提升使用体验:

```json
{
  "permissions": {
    "allow": [
      "mcp__aws-opensearch-logs__search_aws_logs",
      "mcp__aws-opensearch-logs__search_aws_logs_by_time"
    ]
  }
}
```

### 4. 定期刷新 Cookies

AWS SSO cookies 会过期，建议:
- 使用自动刷新机制（已内置在代码中）
- 或手动定期运行 `python server/aws_opensearch_auto.py`

## 📚 参考资料

- [Claude Code 官方文档](https://docs.anthropic.com/claude-code)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [AWS OpenSearch Service](https://aws.amazon.com/opensearch-service/)

## 📋 配置方式对比

| 特性 | 全局配置 | 项目配置 |
|------|---------|---------|
| 配置文件路径 | `~/.claude/config.json` | `<项目>/.claude/settings.local.json` |
| 作用范围 | 所有项目 | 仅当前项目 |
| 权限管理 | 否 | 是 |
| 推荐场景 | 个人开发，常用工具 | 团队协作，项目特定工具 |
| Git 提交 | 不提交 | `.gitignore` 中排除 `settings.local.json` |

## 📝 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-04-24 | 初始版本，基于 FastMCP 实现 |
| 1.1 | 2026-04-28 | 添加自动刷新 cookies 机制 |
| 2.0 | 2026-04-28 | 更新为 Claude Code CLI 配置方式 |

---

**作者:** FlyAIBox  
**更新日期:** 2026-04-28

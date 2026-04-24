# 生产环境部署指南

## 🎯 使用虚拟环境正式运行

### 第一步：创建虚拟环境并安装依赖

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo
./setup_venv.sh
```

这个脚本会：
- ✅ 创建独立的虚拟环境 `venv/`
- ✅ 安装所有依赖包（fastmcp、requests、playwright、mcp）
- ✅ 安装 Playwright 浏览器
- ✅ 显示虚拟环境信息

### 第二步：获取 AWS OpenSearch Cookies

使用虚拟环境中的 Python 运行：

```bash
./venv/bin/python server/aws_opensearch_auto.py
```

会打开浏览器，登录后自动保存 cookies 到 `opensearch_cookies.json`

### 第三步：配置 Claude Desktop

编辑配置文件：

```bash
vim ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**重要：使用虚拟环境中的 Python 路径**

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv/bin/python",
      "args": [
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

### 第四步：重启 Claude Desktop

退出并重新启动 Claude Desktop，MCP server 就会自动加载。

---

## 🧪 测试验证

### 1. 测试 MCP Server 是否能启动

```bash
# 使用虚拟环境的 Python
./venv/bin/python server/aws_opensearch_mcp_server.py
```

应该看到：
```
正在启动 MCP AWS OpenSearch 日志服务器（SSO 认证）...
AWS OpenSearch URL: https://search-ops-log-alpha-...
提供工具:
  - search_aws_logs: 搜索日志（按小时范围）
  - search_aws_logs_by_time: 搜索日志（自定义时间范围）
```

按 `Ctrl+C` 停止。

### 2. 测试交互式客户端

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试客户端
python client/test_aws_opensearch_client.py
```

选择选项 1，输入：
- 搜索关键词: `ERROR`
- 索引模式: `*bts-bigaccount*`
- 小时数: `2`
- 结果数量: `10`

### 3. 在 Claude Desktop 中测试

打开 Claude Desktop，输入：

```
帮我搜索最近 2 小时的 ERROR 日志，索引是 *bts-bigaccount*
```

应该看到 Claude 自动调用 `search_aws_logs` 工具并返回结果。

---

## 📁 目录结构

```
mcp-in-action/mcp-demo/
├── venv/                          # 虚拟环境（独立的 Python 环境）
│   ├── bin/
│   │   ├── python                 # 虚拟环境的 Python
│   │   ├── pip                    # 虚拟环境的 pip
│   │   └── ...
│   └── lib/                       # 已安装的包
├── server/
│   ├── aws_opensearch_mcp_server.py  # MCP Server
│   ├── aws_opensearch_auto.py        # 自动获取 cookies
│   └── aws_opensearch_client.py      # OpenSearch 客户端
├── client/
│   └── test_aws_opensearch_client.py # 测试客户端
├── opensearch_cookies.json        # AWS 认证 cookies（自动生成）
├── setup_venv.sh                  # 虚拟环境安装脚本
└── PRODUCTION_SETUP.md            # 本文档
```

---

## 🔄 日常使用

### 开发时激活虚拟环境

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo
source venv/bin/activate
```

激活后，命令行提示符会显示 `(venv)`。

### 运行脚本

```bash
# 已激活虚拟环境
python server/aws_opensearch_mcp_server.py

# 或直接使用虚拟环境的 Python（无需激活）
./venv/bin/python server/aws_opensearch_mcp_server.py
```

### 退出虚拟环境

```bash
deactivate
```

### 更新 Cookies（定期执行）

```bash
./venv/bin/python server/aws_opensearch_auto.py
```

建议：
- 每天使用前更新一次
- 如果查询返回认证失败，立即更新

---

## 🛠️ 维护和更新

### 安装新的依赖包

```bash
source venv/bin/activate
pip install package-name
```

### 更新现有依赖

```bash
source venv/bin/activate
pip install --upgrade fastmcp requests playwright
```

### 查看已安装的包

```bash
./venv/bin/pip list
```

### 导出依赖列表

```bash
./venv/bin/pip freeze > requirements.txt
```

### 从 requirements.txt 安装

```bash
./venv/bin/pip install -r requirements.txt
```

---

## 🐛 常见问题

### Q1: Claude Desktop 提示找不到 Python 模块

**原因：** 配置文件中使用了系统 Python，而不是虚拟环境的 Python

**解决方案：** 确保配置文件中使用虚拟环境的完整路径：
```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/venv/bin/python",
      "args": [...]
    }
  }
}
```

### Q2: 虚拟环境损坏或包冲突

**解决方案：** 重新创建虚拟环境
```bash
rm -rf venv
./setup_venv.sh
```

### Q3: Playwright 浏览器未安装

**解决方案：**
```bash
source venv/bin/activate
playwright install chromium
```

### Q4: Cookies 过期

**症状：** 查询返回 401/403 错误

**解决方案：**
```bash
./venv/bin/python server/aws_opensearch_auto.py
```

---

## 🔐 安全最佳实践

1. **不要提交虚拟环境到 Git**
   ```bash
   # .gitignore 中已包含
   venv/
   opensearch_cookies.json
   ```

2. **定期更新依赖**
   ```bash
   source venv/bin/activate
   pip list --outdated
   pip install --upgrade [package-name]
   ```

3. **保护 Cookies 文件**
   ```bash
   chmod 600 opensearch_cookies.json
   ```

4. **使用环境变量**（可选）

   创建 `.env` 文件：
   ```bash
   AWS_OPENSEARCH_URL=https://your-domain.amazonaws.com
   DEFAULT_INDEX=*your-index*
   ```

   在代码中读取：
   ```python
   from dotenv import load_dotenv
   load_dotenv()

   base_url = os.getenv("AWS_OPENSEARCH_URL")
   ```

---

## 📊 监控和日志

### 查看 Claude Desktop MCP 日志

```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

### 查看 Python 虚拟环境信息

```bash
./venv/bin/python --version
./venv/bin/pip list
```

### 测试网络连接

```bash
curl -I https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com
```

---

## 🎯 完整工作流程

### 首次设置

```bash
# 1. 创建虚拟环境
./setup_venv.sh

# 2. 获取 cookies
./venv/bin/python server/aws_opensearch_auto.py

# 3. 配置 Claude Desktop（使用虚拟环境路径）
vim ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 4. 重启 Claude Desktop
```

### 日常使用

```bash
# 如果 cookies 过期，重新获取
./venv/bin/python server/aws_opensearch_auto.py

# 开发调试时，激活虚拟环境
source venv/bin/activate
python server/aws_opensearch_mcp_server.py
```

### 在 Claude Desktop 中使用

直接输入查询，例如：
```
帮我搜索最近 2 小时的 ERROR 日志，分析问题原因
```

---

## 📚 相关文档

- [快速开始](./QUICK_START.md)
- [使用示例](./CLAUDE_USAGE_EXAMPLES.md)
- [完整配置](./MCP_SETUP.md)

---

**更新日期：** 2026-04-24
**作者：** FlyAIBox

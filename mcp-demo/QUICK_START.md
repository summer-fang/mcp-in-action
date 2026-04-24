# AWS OpenSearch MCP - 快速开始

## 🚀 一键配置（推荐）

```bash
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo
./setup_claude_mcp.sh
```

这个脚本会自动：
- ✅ 检查 Python 和依赖包
- ✅ 帮助获取 AWS OpenSearch cookies
- ✅ 配置 Claude Desktop
- ✅ 测试 MCP Server

## 📝 手动配置（3 步）

### 1️⃣ 获取认证 Cookies

```bash
cd server
python aws_opensearch_auto.py
```

会打开浏览器，登录后自动保存 cookies 到 `opensearch_cookies.json`

### 2️⃣ 配置 Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "python",
      "args": [
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
      ]
    }
  }
}
```

### 3️⃣ 重启 Claude Desktop

重启后即可使用。

## 💡 使用示例

### 在 Claude Desktop 中输入：

**基础搜索：**
```
帮我搜索最近 1 小时的 ERROR 日志
```

**追踪问题：**
```
搜索包含 "NullPointerException" 的日志，
分析是什么原因导致的，给出修复建议
```

**性能分析：**
```
搜索最近 6 小时包含 "timeout" 的日志，
分析哪些接口响应慢，如何优化
```

**代码问题诊断：**
```
我的订单服务偶尔会超时，帮我：
1. 搜索相关日志
2. 分析根本原因
3. 建议代码改进方案
```

## 🔧 可用工具

Claude 会自动调用以下工具：

| 工具 | 说明 |
|------|------|
| `search_aws_logs` | 按小时范围搜索日志 |
| `search_aws_logs_by_time` | 自定义时间范围搜索 |

## 🐛 常见问题

### Q: 提示 "认证失败"？
A: Cookies 可能过期，重新运行：
```bash
python server/aws_opensearch_auto.py
```

### Q: Claude 看不到工具？
A:
1. 检查配置文件路径是否正确
2. 重启 Claude Desktop
3. 查看日志：`~/Library/Logs/Claude/mcp*.log`

### Q: 搜索返回空结果？
A: 检查：
- 索引模式是否正确（默认：`*bts-bigaccount*`）
- 时间范围是否合理
- 查询关键词是否存在

## 📚 更多文档

- [完整配置指南](./MCP_SETUP.md)
- [Server 源码](./server/aws_opensearch_mcp_server.py)
- [测试客户端](./client/test_aws_opensearch_client.py)

## 🎯 工作流程

```
┌─────────────────┐
│  Claude Desktop │
│  (用户输入)     │
└────────┬────────┘
         │
         │ MCP Protocol
         ▼
┌─────────────────────────────┐
│ aws_opensearch_mcp_server.py│
│  (FastMCP Server)           │
└────────┬────────────────────┘
         │
         │ HTTP + Cookies
         ▼
┌──────────────────────────────┐
│  AWS OpenSearch Dashboards   │
│  (ap-southeast-1)            │
└──────────────────────────────┘
```

---

**问题反馈：** 如有问题，请查看 [MCP_SETUP.md](./MCP_SETUP.md) 故障排查章节

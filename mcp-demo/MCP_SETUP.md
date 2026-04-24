# AWS OpenSearch MCP Server 配置指南

## 📋 概述

将 `aws_opensearch_mcp_server.py` 接入 Claude Desktop，让 Claude 能够：
- 🔍 检索 AWS OpenSearch 日志
- 📊 分析日志中的错误和异常
- 🐛 根据日志诊断代码问题
- 💡 提供修复建议

## 🚀 快速开始

### 1. 准备 Cookies

首先需要获取 AWS OpenSearch 的认证 cookies：

```bash
# 运行自动登录脚本（会打开浏览器）
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server
python aws_opensearch_auto.py
```

这会生成 `opensearch_cookies.json` 文件。

### 2. 配置 Claude Desktop

编辑 Claude Desktop 的配置文件：

**macOS 路径：**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**配置内容：**
```json
{
  "mcpServers": {
    "aws-opensearch-logs": {
      "command": "python",
      "args": [
        "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

### 3. 重启 Claude Desktop

配置完成后，重启 Claude Desktop 使配置生效。

### 4. 验证连接

在 Claude Desktop 中，你应该能看到以下工具：
- 🔧 `search_aws_logs` - 搜索日志（按小时范围）
- 🔧 `search_aws_logs_by_time` - 搜索日志（自定义时间范围）

## 💬 使用示例

### 示例 1: 查找错误日志并分析

```
我的应用最近有报错，帮我查一下最近 2 小时的 ERROR 日志，
索引是 *bts-bigaccount*，然后分析一下是什么问题。
```

Claude 会：
1. 调用 `search_aws_logs` 工具搜索 ERROR 日志
2. 分析日志内容
3. 识别错误类型和原因
4. 提供修复建议

### 示例 2: 追踪特定 TraceID

```
帮我查一下 traceId 为 "9a18bc0641e4444397e57f87007489bc" 的所有日志，
时间范围是最近 10 小时。
```

### 示例 3: 分析异常趋势

```
帮我搜索最近 24 小时内所有包含 "NullPointerException" 的日志，
并分析哪个服务出现次数最多。
```

### 示例 4: 诊断代码问题

```
我的服务在处理订单时偶尔会超时，帮我：
1. 搜索最近 6 小时包含 "timeout" 或 "超时" 的日志
2. 分析超时的原因
3. 建议如何优化代码
```

Claude 会结合日志信息和代码上下文给出具体的修复方案。

## 🔧 高级配置

### 自定义默认索引

修改 `aws_opensearch_mcp_server.py` 中的默认值：

```python
@mcp.tool()
def search_aws_logs(
    query: str,
    index_pattern: str = "*your-default-index*",  # 修改这里
    hours_ago: int = 1,
    size: int = 20
) -> str:
```

### 增加超时时间

如果查询响应慢，可以增加超时：

```python
response = self.session.post(url, json=payload, timeout=60)  # 改为 60 秒
```

### 使用环境变量

创建 `.env` 文件：

```bash
AWS_OPENSEARCH_URL=https://your-opensearch-domain.amazonaws.com
DEFAULT_INDEX_PATTERN=*your-index*
```

## 🔐 安全注意事项

1. **Cookies 过期**：
   - AWS 的 Cognito tokens 通常有效期较短
   - 如果查询失败，重新运行 `aws_opensearch_auto.py` 获取新 cookies

2. **权限控制**：
   - 确保 cookies 对应的用户有相应的索引访问权限
   - 避免在生产环境分享 cookies 文件

3. **敏感信息**：
   - 不要将 `opensearch_cookies.json` 提交到 git
   - 已在 `.gitignore` 中排除此文件

## 🐛 故障排查

### 问题 1: MCP Server 无法启动

**症状：** Claude Desktop 无法连接到 MCP server

**解决方案：**
```bash
# 测试 server 是否能正常启动
cd /Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server
python aws_opensearch_mcp_server.py
```

如果报错，检查：
- Python 版本（需要 3.9+）
- 依赖包是否安装：`pip install fastmcp requests`

### 问题 2: 搜索返回认证失败

**症状：** 返回 401 或 403 错误

**解决方案：**
```bash
# 重新获取 cookies
python aws_opensearch_auto.py
```

### 问题 3: 找不到日志

**症状：** 返回 0 条结果

**检查：**
1. 索引模式是否正确
2. 时间范围是否合适
3. 查询语法是否正确（Lucene 查询语法）

### 问题 4: Claude 看不到工具

**解决方案：**
1. 检查配置文件路径和格式是否正确
2. 重启 Claude Desktop
3. 查看 Claude Desktop 日志：
   ```bash
   ~/Library/Logs/Claude/mcp*.log
   ```

## 📊 工具参数说明

### search_aws_logs

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | string | (必填) | 搜索关键词，支持 Lucene 语法 |
| index_pattern | string | "*bts-bigaccount*" | 索引模式 |
| hours_ago | int | 1 | 查询最近多少小时 |
| size | int | 20 | 返回结果数量（建议 ≤ 50） |

**查询语法示例：**
- `ERROR` - 包含 ERROR
- `ERROR AND timeout` - 同时包含 ERROR 和 timeout
- `ERROR OR exception` - 包含 ERROR 或 exception
- `"exact phrase"` - 精确匹配短语
- `field:value` - 指定字段搜索

### search_aws_logs_by_time

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | string | (必填) | 搜索关键词 |
| time_from | string | (必填) | 开始时间 |
| time_to | string | "now" | 结束时间 |
| index_pattern | string | "*bts-bigaccount*" | 索引模式 |
| size | int | 20 | 返回结果数量 |

**时间格式示例：**
- `now-1h` - 1小时前
- `now-24h` - 24小时前
- `now-7d` - 7天前
- `2026-04-24T10:00:00` - 具体时间（ISO 8601）

## 🎯 最佳实践

1. **合理的查询范围**：
   - 优先使用较短的时间范围（1-2 小时）
   - 大范围查询可能响应较慢

2. **精确的查询条件**：
   - 使用字段搜索提高准确性：`level:ERROR`
   - 组合多个条件：`level:ERROR AND service:order`

3. **限制结果数量**：
   - 默认 20 条通常足够分析
   - 太多结果可能导致 Claude 响应慢

4. **定期更新 Cookies**：
   - 建议每天或每次使用前更新一次
   - 可以创建 cron job 自动更新

## 📚 相关文件

- `aws_opensearch_mcp_server.py` - MCP Server 主程序
- `aws_opensearch_auto.py` - 自动登录获取 cookies
- `aws_opensearch_client.py` - OpenSearch 客户端库
- `opensearch_cookies.json` - 认证 cookies（自动生成）
- `test_aws_opensearch_client.py` - 测试客户端

## 🔗 相关链接

- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [OpenSearch Lucene 查询语法](https://opensearch.org/docs/latest/query-dsl/full-text/query-string/)
- [Claude Desktop MCP 配置](https://docs.anthropic.com/claude/docs/model-context-protocol)

---

📝 **更新日期：** 2026-04-24
✍️ **作者：** FlyAIBox

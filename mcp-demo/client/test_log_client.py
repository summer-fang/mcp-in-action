#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenSearch 日志查询 MCP 客户端测试

用于测试 seach_log_server.py 提供的日志查询功能

Author: FlyAIBox
Date: 2025.05.03
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class LogSearchClient:
    """OpenSearch 日志查询客户端"""

    def __init__(self, server_path: str):
        """
        初始化日志查询客户端

        参数:
            server_path: 服务器脚本路径
        """
        self.server_path = server_path
        self.client = None
        self.tool_definitions = []
        self.exit_stack = AsyncExitStack()

    async def start(self):
        """启动客户端并连接到服务器"""
        print("🚀 启动 OpenSearch 日志查询服务器...")

        # 配置服务器参数
        server_params = StdioServerParameters(
            command='python',
            args=[self.server_path],
            env=None
        )

        # 启动服务器并获取通信流
        read_write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = read_write

        # 创建 MCP 客户端会话
        self.client = await self.exit_stack.enter_async_context(ClientSession(read, write))

        # 初始化连接
        await self.client.initialize()

        # 获取工具定义
        response = await self.client.list_tools()
        self.tool_definitions = response.tools

        print(f"✅ 已连接到服务器，可用工具: {len(self.tool_definitions)}")

        for tool in self.tool_definitions:
            print(f"  📌 {tool.name}: {tool.description}")

        print("\n💡 使用 'help' 查看帮助，使用 'exit' 退出")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[str]:
        """
        执行工具调用

        参数:
            tool_name: 要调用的工具名称
            params: 工具参数字典

        返回:
            工具执行结果或错误消息
        """
        # 检查工具是否存在
        tool_def = next((t for t in self.tool_definitions if t.name == tool_name), None)
        if not tool_def:
            return f"❌ 错误: 未找到工具 '{tool_name}'"

        try:
            print(f"⏳ 正在执行: {tool_name}({json.dumps(params, ensure_ascii=False)})")

            # 调用工具并等待结果
            result = await self.client.call_tool(tool_name, arguments=params)

            # 处理结果
            if result and hasattr(result, 'content'):
                # 提取文本内容
                if isinstance(result.content, list) and len(result.content) > 0:
                    return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                return str(result.content)
            else:
                return "⚠️ 工具执行未返回任何结果"

        except Exception as e:
            return f"❌ 执行过程中出错: {str(e)}"

    async def stop(self):
        """停止客户端和服务器"""
        print("\n🛑 正在关闭客户端...")
        await self.exit_stack.aclose()
        print("✅ 已关闭")

    def print_help(self):
        """打印帮助信息"""
        print("\n" + "="*60)
        print("📖 可用命令:")
        print("="*60)
        print("  help                    - 显示此帮助信息")
        print("  list                    - 列出可用工具和参数")
        print("  search <query>          - 快速搜索（默认最近1小时）")
        print("  call <tool> <params>    - 完整调用工具")
        print("  exit                    - 退出程序")
        print("\n" + "="*60)
        print("📝 示例:")
        print("="*60)
        print("  # 快速搜索（默认 fluentd-app-* 索引，最近1小时）")
        print('  search error OR exception')
        print()
        print("  # 搜索特定 TraceID")
        print('  search 900fdb1a55754882b8a0c21114563ec6')
        print()
        print("  # 完整调用（指定所有参数）")
        print('  call search_logs {"query":"error","index_pattern":"logs-*","hours_ago":2.0,"size":100}')
        print()
        print("  # 根据 TraceID 搜索")
        print('  call search_logs_by_traceid {"trace_id":"abc123","hours_ago":1.0}')
        print("="*60)

    def print_tools(self):
        """打印工具列表和描述"""
        print("\n" + "="*60)
        print("🔧 可用工具:")
        print("="*60)
        for tool in self.tool_definitions:
            print(f"\n📌 {tool.name}")
            print(f"   {tool.description}")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                props = tool.inputSchema.get('properties', {})
                if props:
                    print("   参数:")
                    for param_name, param_info in props.items():
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', '')
                        default = param_info.get('default', None)
                        default_str = f" (默认: {default})" if default is not None else ""
                        print(f"     • {param_name} ({param_type}){default_str}: {param_desc}")
        print("="*60)


async def main():
    """主函数"""
    # 确定服务器路径
    server_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "server",
        "seach_log_server.py"
    )

    # 检查服务器文件是否存在
    if not os.path.exists(server_path):
        print(f"❌ 错误: 服务器文件不存在: {server_path}")
        return

    # 创建客户端应用
    app = LogSearchClient(server_path)

    try:
        # 启动客户端
        await app.start()

        # 显示帮助
        app.print_help()

        # 主循环
        while True:
            try:
                # 获取用户输入
                command = input("\n🔍 > ").strip()

                # 处理命令
                if command == "exit":
                    break

                elif command == "help":
                    app.print_help()

                elif command == "list":
                    app.print_tools()

                elif command.startswith("search "):
                    # 快速搜索命令
                    query = command[7:].strip()
                    if not query:
                        print("❌ 错误: 请提供搜索关键词")
                        continue

                    params = {
                        "query": query,
                        "index_pattern": "fluentd-app-*",
                        "hours_ago": 1,
                        "size": 1
                    }

                    result = await app.execute_tool("search_logs", params)
                    print("\n" + "="*60)
                    print("📊 搜索结果:")
                    print("="*60)
                    print(result)
                    print("="*60)

                elif command.startswith("call "):
                    # 完整工具调用
                    parts = command[5:].strip().split(" ", 1)
                    if len(parts) < 1:
                        print("❌ 错误: 缺少工具名")
                        continue

                    tool_name = parts[0]

                    # 解析参数
                    params = {}
                    if len(parts) > 1:
                        params_str = parts[1]
                        try:
                            params = json.loads(params_str)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON 解析错误: {str(e)}")
                            print("💡 提示: 参数必须是有效的 JSON 格式")
                            continue

                    # 执行工具调用
                    result = await app.execute_tool(tool_name, params)
                    print("\n" + "="*60)
                    print("📊 执行结果:")
                    print("="*60)
                    print(result)
                    print("="*60)

                elif command == "":
                    continue

                else:
                    print(f"❌ 未知命令: {command}")
                    print("💡 使用 'help' 查看可用命令")

            except KeyboardInterrupt:
                print("\n⚠️ 操作被中断")
                break

            except Exception as e:
                print(f"❌ 错误: {str(e)}")

    except Exception as e:
        print(f"❌ 客户端错误: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 停止客户端
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
        sys.exit(0)

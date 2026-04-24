#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 AWS OpenSearch MCP Server

测试通过 SSO cookies 认证查询 AWS OpenSearch 日志

Author: FlyAIBox
Date: 2026.04.24
"""

import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def interactive_search():
    """交互式搜索日志"""

    # 配置 MCP server 启动参数
    server_params = StdioServerParameters(
        command="python",
        args=["/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()

            print("\n" + "=" * 80)
            print("✅ AWS OpenSearch MCP 交互式客户端")
            print("=" * 80)

            # 列出可用工具
            tools = await session.list_tools()
            print(f"\n📋 可用工具 ({len(tools.tools)} 个):")
            for i, tool in enumerate(tools.tools, 1):
                print(f"  {i}. {tool.name}")
                print(f"     {tool.description[:100]}...")

            # 交互式循环
            while True:
                print("\n" + "=" * 80)
                print("请选择操作:")
                print("  1. 搜索日志 (按小时范围)")
                print("  2. 搜索日志 (自定义时间范围)")
                print("  3. 退出")
                print("=" * 80)

                choice = input("\n请输入选项 (1/2/3): ").strip()

                if choice == "3":
                    print("\n👋 再见！")
                    break

                elif choice == "1":
                    # 搜索日志（按小时）
                    print("\n" + "-" * 80)
                    query = input("🔍 输入搜索关键词 (例如: ERROR, exception, traceId): ").strip()
                    if not query:
                        print("❌ 搜索关键词不能为空")
                        continue

                    index_pattern = input("📁 索引模式 (默认: *bts-bigaccount*): ").strip() or "*bts-bigaccount*"
                    hours_ago_str = input("⏰ 查询最近多少小时 (默认: 1): ").strip() or "1"
                    size_str = input("📊 返回结果数量 (默认: 10): ").strip() or "10"

                    try:
                        hours_ago = int(hours_ago_str)
                        size = int(size_str)
                    except ValueError:
                        print("❌ 小时数和结果数量必须是整数")
                        continue

                    print(f"\n🔍 正在搜索: {query} ...")
                    print("-" * 80)

                    try:
                        result = await session.call_tool(
                            "search_aws_logs",
                            arguments={
                                "query": query,
                                "index_pattern": index_pattern,
                                "hours_ago": hours_ago,
                                "size": size
                            }
                        )
                        print("\n📝 搜索结果:")
                        for content in result.content:
                            if hasattr(content, 'text'):
                                print(content.text)
                    except Exception as e:
                        print(f"\n❌ 搜索失败: {e}")

                elif choice == "2":
                    # 搜索日志（自定义时间范围）
                    print("\n" + "-" * 80)
                    query = input("🔍 输入搜索关键词: ").strip()
                    if not query:
                        print("❌ 搜索关键词不能为空")
                        continue

                    print("\n时间格式示例:")
                    print("  - now-1h (最近1小时)")
                    print("  - now-24h (最近24小时)")
                    print("  - 2026-04-24T10:00:00")

                    time_from = input("\n⏰ 开始时间 (默认: now-1h): ").strip() or "now-1h"
                    time_to = input("⏰ 结束时间 (默认: now): ").strip() or "now"
                    index_pattern = input("📁 索引模式 (默认: *bts-bigaccount*): ").strip() or "*bts-bigaccount*"
                    size_str = input("📊 返回结果数量 (默认: 10): ").strip() or "10"

                    try:
                        size = int(size_str)
                    except ValueError:
                        print("❌ 结果数量必须是整数")
                        continue

                    print(f"\n🔍 正在搜索: {query} ({time_from} 到 {time_to}) ...")
                    print("-" * 80)

                    try:
                        result = await session.call_tool(
                            "search_aws_logs_by_time",
                            arguments={
                                "query": query,
                                "time_from": time_from,
                                "time_to": time_to,
                                "index_pattern": index_pattern,
                                "size": size
                            }
                        )
                        print("\n📝 搜索结果:")
                        for content in result.content:
                            if hasattr(content, 'text'):
                                print(content.text)
                    except Exception as e:
                        print(f"\n❌ 搜索失败: {e}")

                else:
                    print("❌ 无效的选项，请输入 1、2 或 3")


async def test_simple_search():
    """简单的搜索测试"""
    server_params = StdioServerParameters(
        command="python",
        args=["/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/aws_opensearch_mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            logger.info("🔍 快速测试: 搜索 ERROR 日志")

            result = await session.call_tool(
                "search_aws_logs",
                arguments={
                    "query": "ERROR",
                    "hours_ago": 2,
                    "size": 10
                }
            )

            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)


if __name__ == "__main__":
    # 运行交互式搜索
    asyncio.run(interactive_search())

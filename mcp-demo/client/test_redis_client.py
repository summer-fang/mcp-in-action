#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 Redis MCP Server

通过 MCP stdio 协议测试本地 Redis 读写操作

Author: FlyAIBox
Date: 2026.04.28
"""

import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SERVER_PATH = "/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server/redis_mcp_server.py"


async def interactive_mode():
    """交互式 Redis 客户端"""
    server_params = StdioServerParameters(
        command="python",
        args=[SERVER_PATH],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n" + "=" * 60)
            print("  Redis MCP 交互式客户端")
            print("=" * 60)

            tools = await session.list_tools()
            print(f"\n可用工具 ({len(tools.tools)} 个):")
            for i, tool in enumerate(tools.tools, 1):
                print(f"  {i}. {tool.name} - {tool.description[:60]}...")

            while True:
                print("\n" + "=" * 60)
                print("请选择操作:")
                print("  1. redis_get     - 获取 key 的值")
                print("  2. redis_set     - 设置 key-value")
                print("  3. redis_delete  - 删除 key")
                print("  4. redis_keys    - 搜索匹配的 keys")
                print("  5. redis_hget    - 获取 hash 字段")
                print("  6. redis_hset    - 设置 hash 字段")
                print("  7. redis_hgetall - 获取整个 hash")
                print("  8. redis_ttl     - 查询过期时间")
                print("  0. 退出")
                print("=" * 60)

                choice = input("\n请输入选项 (0-8): ").strip()

                if choice == "0":
                    print("再见！")
                    break

                try:
                    if choice == "1":
                        key = input("key: ").strip()
                        result = await session.call_tool("redis_get", arguments={"key": key})
                    elif choice == "2":
                        key = input("key: ").strip()
                        value = input("value: ").strip()
                        expire = input("过期秒数 (0=永久, 默认0): ").strip() or "0"
                        result = await session.call_tool("redis_set", arguments={
                            "key": key, "value": value, "expire_seconds": int(expire)
                        })
                    elif choice == "3":
                        key = input("key (支持 * 通配符): ").strip()
                        result = await session.call_tool("redis_delete", arguments={"key": key})
                    elif choice == "4":
                        pattern = input("匹配模式 (默认 *): ").strip() or "*"
                        limit = input("显示数量 (默认 50): ").strip() or "50"
                        result = await session.call_tool("redis_keys", arguments={
                            "pattern": pattern, "limit": int(limit)
                        })
                    elif choice == "5":
                        key = input("key: ").strip()
                        field = input("field: ").strip()
                        result = await session.call_tool("redis_hget", arguments={
                            "key": key, "field": field
                        })
                    elif choice == "6":
                        key = input("key: ").strip()
                        field = input("field: ").strip()
                        value = input("value: ").strip()
                        result = await session.call_tool("redis_hset", arguments={
                            "key": key, "field": field, "value": value
                        })
                    elif choice == "7":
                        key = input("key: ").strip()
                        result = await session.call_tool("redis_hgetall", arguments={"key": key})
                    elif choice == "8":
                        key = input("key: ").strip()
                        result = await session.call_tool("redis_ttl", arguments={"key": key})
                    else:
                        print("无效选项")
                        continue

                    print("\n" + "-" * 40)
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(content.text)
                except Exception as e:
                    print(f"\n操作失败: {e}")


async def quick_test():
    """快速功能测试"""
    server_params = StdioServerParameters(
        command="python",
        args=[SERVER_PATH],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tests = [
                ("redis_set", {"key": "mcp:test:hello", "value": "world", "expire_seconds": 60}),
                ("redis_get", {"key": "mcp:test:hello"}),
                ("redis_ttl", {"key": "mcp:test:hello"}),
                ("redis_type", {"key": "mcp:test:hello"}),
                ("redis_set", {"key": "mcp:test:count", "value": "42"}),
                ("redis_keys", {"pattern": "mcp:test:*"}),
                ("redis_hset", {"key": "mcp:test:user", "field": "name", "value": "张三"}),
                ("redis_hset", {"key": "mcp:test:user", "field": "age", "value": "25"}),
                ("redis_hgetall", {"key": "mcp:test:user"}),
                ("redis_hget", {"key": "mcp:test:user", "field": "name"}),
                ("redis_delete", {"key": "mcp:test:hello"}),
                ("redis_delete", {"key": "mcp:test:count"}),
                ("redis_delete", {"key": "mcp:test:user"}),
                ("redis_get", {"key": "mcp:test:hello"}),
            ]

            print("\n" + "=" * 60)
            print("  Redis MCP 快速功能测试")
            print("=" * 60)

            passed = 0
            for tool_name, args in tests:
                try:
                    result = await session.call_tool(tool_name, arguments=args)
                    text = ""
                    for content in result.content:
                        if hasattr(content, 'text'):
                            text = content.text
                    ok = not text.startswith("❌")
                    status = "PASS" if ok else "FAIL"
                    if ok:
                        passed += 1
                    print(f"\n[{status}] {tool_name}({args})")
                    print(f"       {text[:120]}")
                except Exception as e:
                    print(f"\n[FAIL] {tool_name}({args}) -> {e}")

            print(f"\n{'=' * 60}")
            print(f"  结果: {passed}/{len(tests)} 通过")
            print("=" * 60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(quick_test())
    else:
        asyncio.run(interactive_mode())

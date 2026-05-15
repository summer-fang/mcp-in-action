#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速日志查询脚本

使用方式：
python quick_search.py
"""

import sys
import json
sys.path.insert(0, '/Users/bjsttlp314/IdeaProjects/mcp-in-action/mcp-demo/server')

from aws_opensearch_client import AWSOpenSearchClient

# TraceId
TRACE_ID = "848f986b1b28376436b905b885612c57f0c"

def main():
    # 创建客户端
    base_url = "https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com"
    client = AWSOpenSearchClient(base_url)

    # 加载 cookies
    try:
        with open('mcp-demo/opensearch_cookies.json', 'r') as f:
            cookies_list = json.load(f)
            cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
            client.session.cookies.update(cookies)
            print(f"✅ 已加载 {len(cookies)} 个 cookies")
    except FileNotFoundError:
        print("❌ 未找到 opensearch_cookies.json，请先获取 cookies")
        return

    print("\n" + "=" * 80)
    print(f"🔍 查询 TraceId: {TRACE_ID}")
    print("=" * 80)

    # 查询该 traceId 的所有日志
    result = client.search(
        query=TRACE_ID,
        index_pattern="*bts-bigaccount*",
        size=50,
        time_from="now-24h",
        time_to="now"
    )

    if not result:
        print("\n❌ 查询失败，可能原因：")
        print("  1. Cookies 已过期")
        print("  2. 网络连接问题")
        print("  3. 索引模式不正确")
        return

    hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
    total = result.get('rawResponse', {}).get('hits', {}).get('total', {})
    total_value = total.get('value', 0) if isinstance(total, dict) else total

    if not hits:
        print(f"\n⚠️  未找到 traceId {TRACE_ID} 的日志")
        print("可能原因：")
        print("  1. TraceId 不存在")
        print("  2. 日志已过期（超过 24 小时）")
        print("  3. 索引模式不匹配")
        return

    print(f"\n📊 找到 {total_value} 条相关日志\n")
    print("=" * 80)

    # 按时间排序
    hits_sorted = sorted(hits, key=lambda x: x.get('_source', {}).get('@timestamp', ''))

    # 分析日志
    errors = []
    warnings = []
    all_logs = []

    for i, hit in enumerate(hits_sorted, 1):
        source = hit.get('_source', {})
        timestamp = source.get('@timestamp', '未知时间')
        log = source.get('log', source.get('message', source.get('Message', '')))

        all_logs.append({
            'timestamp': timestamp,
            'log': log
        })

        # 检测错误和警告
        log_upper = log.upper()
        if 'ERROR' in log_upper or 'EXCEPTION' in log_upper:
            errors.append({'timestamp': timestamp, 'log': log})
        elif 'WARN' in log_upper:
            warnings.append({'timestamp': timestamp, 'log': log})

        print(f"\n[{i}/{len(hits_sorted)}] {timestamp}")
        print(f"    {log[:800]}")
        if len(log) > 800:
            print("    ... (已截断)")
        print("-" * 80)

    # 统计分析
    print("\n\n" + "=" * 80)
    print("📊 统计分析")
    print("=" * 80)
    print(f"总日志数: {len(hits_sorted)}")
    print(f"错误日志: {len(errors)}")
    print(f"警告日志: {len(warnings)}")
    print(f"普通日志: {len(hits_sorted) - len(errors) - len(warnings)}")

    # 显示关键错误
    if errors:
        print("\n\n" + "=" * 80)
        print("🔴 关键错误")
        print("=" * 80)
        for i, error in enumerate(errors[:5], 1):  # 只显示前5个错误
            print(f"\n[错误 {i}] {error['timestamp']}")
            print(f"    {error['log'][:1000]}")
            print("-" * 80)

    # 时间跨度
    if len(hits_sorted) > 1:
        first_time = hits_sorted[0].get('_source', {}).get('@timestamp', '')
        last_time = hits_sorted[-1].get('_source', {}).get('@timestamp', '')
        print(f"\n⏱️  时间跨度: {first_time} ~ {last_time}")

    print("\n\n" + "=" * 80)
    print("💡 建议")
    print("=" * 80)
    if errors:
        print("1. 检查上述错误日志，找出根本原因")
        print("2. 查看错误发生的时间点，是否有规律")
        print("3. 检查相关的堆栈跟踪信息")
    else:
        print("未发现明显错误，可能是：")
        print("1. 业务逻辑问题，非系统异常")
        print("2. 错误信息在其他索引或日志级别中")
        print("3. 需要查看更详细的上下文日志")

    print("\n💻 如需更详细的分析，建议在 Claude Desktop 中使用 MCP server")
    print("   直接输入查询需求，Claude 会自动分析并给出修复建议\n")


if __name__ == "__main__":
    main()

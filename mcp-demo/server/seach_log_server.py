#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP OpenSearch 日志查询服务器

提供日志查询工具：
1. search_logs: 在 OpenSearch Dashboards 中搜索日志
2. analyze_error_trend: 分析错误趋势（未来扩展）

Author: FlyAIBox
Date: 2025.05.03
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载 .env 文件中的环境变量
dotenv_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(dotenv_path)

# 初始化 FastMCP 服务器
mcp = FastMCP("opensearch-logs")

# 从环境变量读取配置
OPENSEARCH_BASE_URL = os.getenv("OPENSEARCH_BASE_URL", "https://opensearch.crm-prod.com")
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD")


class OpenSearchClient:
    """OpenSearch Dashboards 客户端"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = True  # 如果是自签名证书，改为 False

    def search(self, query: str, index_pattern: str = "*", size: int = 100,
               time_from: str = "now-1h", time_to: str = "now") -> Optional[Dict[str, Any]]:
        """
        搜索 OpenSearch Dashboards 日志

        Args:
            query: 搜索查询字符串（支持 Lucene 查询语法）
            index_pattern: 索引模式，默认 "*" 表示所有索引
            size: 返回结果数量，默认 100
            time_from: 开始时间，默认 "now-1h" (最近1小时)
            time_to: 结束时间，默认 "now"

        Returns:
            搜索结果字典，失败返回 None
        """
        url = f"{self.base_url}/_dashboards/internal/search/opensearch"

        # OpenSearch Dashboards 需要这个 header 来防止 CSRF 攻击
        headers = {
            'osd-xsrf': 'true',
            'Content-Type': 'application/json'
        }

        # 构建搜索请求体
        payload = {
            "params": {
                "index": index_pattern,
                "body": {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "query_string": {
                                        "query": query
                                    }
                                },
                                {
                                    "range": {
                                        "@timestamp": {
                                            "gte": time_from,
                                            "lte": time_to
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "size": size,
                    "sort": [{"@timestamp": {"order": "desc"}}]
                }
            }
        }

        try:
            logger.info(f"搜索日志: query={query}, index={index_pattern}, time={time_from} to {time_to}")
            response = self.session.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                hits = data.get('rawResponse', {}).get('hits', {}).get('hits', [])
                logger.info(f"搜索成功，返回 {len(hits)} 条结果")
                return data
            else:
                logger.error(f"请求失败: {response.status_code}, {response.text}")
                return None

        except Exception as e:
            logger.error(f"搜索异常: {e}")
            return None


# 全局客户端实例（懒加载）
_opensearch_client = None

def get_opensearch_client() -> OpenSearchClient:
    """获取 OpenSearch 客户端实例"""
    global _opensearch_client
    if _opensearch_client is None:
        if not OPENSEARCH_USERNAME or not OPENSEARCH_PASSWORD:
            raise ValueError("请在 .env 文件中配置 OPENSEARCH_USERNAME 和 OPENSEARCH_PASSWORD")
        _opensearch_client = OpenSearchClient(
            OPENSEARCH_BASE_URL,
            OPENSEARCH_USERNAME,
            OPENSEARCH_PASSWORD
        )
    return _opensearch_client


@mcp.tool()
def search_logs(
    query: str,
    index_pattern: str = "fluentd-app-*",
    hours_ago: int = 1,
    size: int = 50
) -> str:
    """
    在 OpenSearch 中搜索应用日志

    参数:
        query: 搜索关键词（支持 Lucene 查询语法，如 "error OR exception", "traceId:abc123"）
        index_pattern: 索引模式，默认 "fluentd-app-*"（应用日志）
        hours_ago: 查询最近多少小时的日志，默认 1.0 小时
        size: 返回结果数量，默认 50（最大建议不超过 200）

    返回:
        格式化的日志搜索结果

    示例:
        - search_logs("error OR exception")
        - search_logs("traceId:abc123", hours_ago=2.0)
        - search_logs("level:ERROR AND message:*timeout*", index_pattern="logs-*")
    """
    try:
        client = get_opensearch_client()

        # 计算时间范围
        time_from = f"now-{hours_ago}h"

        # 执行搜索
        result = client.search(
            query=query,
            index_pattern=index_pattern,
            size=size,
            time_from=time_from
        )

        if not result:
            return "搜索失败或 API 请求出错，请检查网络连接和认证信息。"

        logger.info(f"搜索结果: {result}")

        # 提取搜索结果
        hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
        total = result.get('rawResponse', {}).get('hits', {}).get('total', {})
        total_value = total.get('value', 0) if isinstance(total, dict) else total

        if not hits:
            return f"未找到匹配的日志（查询: {query}, 索引: {index_pattern}, 时间范围: 最近 {hours_ago} 小时）"

        # 格式化输出结果
        results = [f"找到 {total_value} 条匹配日志，显示前 {len(hits)} 条：\n"]

        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            timestamp = source.get('@timestamp', '未知时间')
            logger.info(f"日志详情{source.get('Message')}")
            message = source.get('Message', source.get('log', '无消息内容'))

            # 截取消息长度，避免过长
            if len(message) > 500:
                message = message[:500] + "..."

            # 提取其他有用字段
            extra_info = []
            for field in ['level', 'service', 'pod_name', 'namespace']:
                if field in source:
                    extra_info.append(f"{field}={source[field]}")

            extra_str = " | ".join(extra_info) if extra_info else ""

            results.append(f"\n[{i}] 时间: {timestamp}")
            if extra_str:
                results.append(f"    信息: {extra_str}")
            results.append(f"    内容: {message}")

        return "\n".join(results)

    except ValueError as e:
        return f"配置错误: {str(e)}"
    except Exception as e:
        logger.error(f"搜索日志时出错: {e}", exc_info=True)
        return f"搜索日志时出错: {str(e)}"


@mcp.tool()
def search_logs_by_traceid(trace_id: str, hours_ago: float = 1.0) -> str:
    """
    根据 TraceID 搜索相关的所有日志（用于链路追踪）

    参数:
        trace_id: 分布式追踪的 TraceID
        hours_ago: 查询最近多少小时的日志，默认 1.0 小时

    返回:
        该 TraceID 相关的所有日志
    """
    # 使用 search_logs 工具，指定 traceId 查询
    query = f'traceId:"{trace_id}" OR trace_id:"{trace_id}" OR traceID:"{trace_id}"'
    return search_logs(query=query, hours_ago=hours_ago, size=100)


if __name__ == "__main__":
    logger.info("正在启动 MCP OpenSearch 日志服务器...")
    logger.info("提供工具: search_logs, search_logs_by_traceid")
    logger.info("请确保在 .env 文件中配置:")
    logger.info("  - OPENSEARCH_BASE_URL")
    logger.info("  - OPENSEARCH_USERNAME")
    logger.info("  - OPENSEARCH_PASSWORD")
    logger.info("使用 Ctrl+C 停止服务器")

    # 初始化并运行服务器
    mcp.run(transport='stdio')
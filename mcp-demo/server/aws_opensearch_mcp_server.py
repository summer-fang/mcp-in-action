#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP AWS OpenSearch 日志查询服务器（SSO 认证）

提供日志查询工具：
1. search_aws_logs: 在 AWS OpenSearch 中搜索日志（使用 cookies 认证）
2. search_aws_logs_by_time: 指定时间范围搜索日志

Author: FlyAIBox
Date: 2026.04.24
"""

import os
import json
import logging
import requests
import traceback
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 FastMCP 服务器
mcp = FastMCP("aws-opensearch-logs")

# AWS OpenSearch 配置
AWS_OPENSEARCH_BASE_URL = "https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com"
COOKIES_FILE = Path(__file__).parent.parent / "opensearch_cookies.json"


class AWSOpenSearchClient:
    """AWS OpenSearch 客户端（SSO 认证）"""

    def __init__(self, base_url: str, cookies: Dict[str, str] = None):
        """
        初始化客户端

        参数:
            base_url: OpenSearch 基础 URL
            cookies: 从浏览器获取的 cookies 字典
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        if cookies:
            self.session.cookies.update(cookies)

        # 通用 headers
        self.session.headers.update({
            'osd-xsrf': 'true',
            'Content-Type': 'application/json'
        })

    def search(
        self,
        query: str,
        index_pattern: str = "*",
        size: int = 50,
        time_from: str = "now-1h",
        time_to: str = "now"
    ) -> Optional[Dict[str, Any]]:
        """
        搜索日志

        参数:
            query: 搜索查询字符串
            index_pattern: 索引模式
            size: 返回结果数量
            time_from: 开始时间
            time_to: 结束时间
        """
        url = f"{self.base_url}/_dashboards/internal/search/opensearch"

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
            logger.info(f"搜索日志: query={query}, index={index_pattern}")
            response = self.session.post(url, json=payload, timeout=30)

            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应 Content-Type: {response.headers.get('Content-Type')}")

            if response.status_code == 200:
                # 检查是否是 JSON 响应
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    logger.error(f"响应不是 JSON 格式，可能是登录页面。Content-Type: {content_type}")
                    logger.error(f"响应内容: {response.text[:1000]}")
                    return None

                try:
                    data = response.json()
                    hits = data.get('rawResponse', {}).get('hits', {}).get('hits', [])
                    logger.info(f"搜索成功，返回 {len(hits)} 条结果")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失败: {e}")
                    logger.error(f"响应内容: {response.text[:1000]}")
                    return None

            elif response.status_code == 401 or response.status_code == 403:
                logger.error("认证失败，请重新获取 cookies")
                logger.error(f"响应内容: {response.text[:1000]}")
                return None
            else:
                logger.error(f"请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text[:1000]}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"搜索异常: {e}")
            logger.error(traceback.format_exc())
            return None


# 全局客户端实例（懒加载）
_aws_opensearch_client = None
# Cookie刷新脚本路径
COOKIE_REFRESH_SCRIPT = Path(__file__).parent.parent / "server" / "aws_opensearch_auto.py"
PYTHON_VENV = Path(__file__).parent.parent / "venv_mcp_demo" / "bin" / "python"


def refresh_cookies() -> bool:
    """
    自动运行cookies刷新脚本

    返回:
        True: 刷新成功
        False: 刷新失败
    """
    try:
        logger.info("=" * 80)
        logger.info("🔄 检测到 cookies 过期，正在自动刷新...")
        logger.info(f"执行脚本: {COOKIE_REFRESH_SCRIPT}")
        logger.info("=" * 80)

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

        logger.info("刷新脚本输出:")
        logger.info(stdout)

        if stderr:
            logger.warning(f"刷新脚本错误输出: {stderr}")

        # 检查cookies文件是否更新成功
        if COOKIES_FILE.exists():
            logger.info("✅ Cookies 文件已更新，重新加载客户端...")
            return True
        else:
            logger.error("❌ Cookies 文件未生成")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ Cookies 刷新超时（5分钟）")
        process.kill()
        return False
    except Exception as e:
        logger.error(f"❌ 刷新 cookies 失败: {e}")
        logger.error(traceback.format_exc())
        return False


def reload_client():
    """重新加载客户端（清除缓存）"""
    global _aws_opensearch_client
    _aws_opensearch_client = None


def get_aws_opensearch_client() -> AWSOpenSearchClient:
    """获取 AWS OpenSearch 客户端实例"""
    global _aws_opensearch_client
    if _aws_opensearch_client is None:
        # 从文件加载 cookies
        try:
            with open(COOKIES_FILE, 'r') as f:
                cookies_list = json.load(f)
                # 转换为字典格式
                cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
                logger.info(f"已从 {COOKIES_FILE} 加载 {len(cookies)} 个 cookies")
                _aws_opensearch_client = AWSOpenSearchClient(AWS_OPENSEARCH_BASE_URL, cookies)
        except FileNotFoundError:
            raise ValueError(f"未找到 cookies 文件: {COOKIES_FILE}，请先运行 aws_opensearch_auto.py 获取 cookies")
    return _aws_opensearch_client


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
        query: 搜索关键词（支持 Lucene 查询语法，如 "ERROR", "exception", "traceId:abc123"）
        index_pattern: 索引模式，默认 "*bts-bigaccount*"
        hours_ago: 查询最近多少小时的日志，默认 1 小时
        size: 返回结果数量，默认 20（最大建议不超过 50）

    返回:
        格式化的日志搜索结果

    示例:
        - search_aws_logs("ERROR")
        - search_aws_logs("exception", index_pattern="*app*", hours_ago=2)
        - search_aws_logs("9a18bc0641e4444397e57f87007489bc")
    """
    try:
        client = get_aws_opensearch_client()

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
            logger.warning("首次搜索失败，尝试自动刷新 cookies...")

            # 自动刷新cookies
            if refresh_cookies():
                # 重新加载客户端
                reload_client()
                client = get_aws_opensearch_client()

                # 重试搜索
                logger.info("重新尝试搜索...")
                result = client.search(
                    query=query,
                    index_pattern=index_pattern,
                    size=size,
                    time_from=time_from
                )

                if not result:
                    return (
                        f"❌ 刷新 cookies 后仍然搜索失败\n"
                        f"可能原因：\n"
                        f"1. 网络连接问题\n"
                        f"2. 索引模式不存在: {index_pattern}\n"
                        f"3. OpenSearch 服务异常"
                    )
            else:
                return (
                    f"❌ 搜索失败且无法自动刷新 cookies\n"
                    f"请手动运行以下命令获取 cookies：\n"
                    f"python {COOKIE_REFRESH_SCRIPT}\n"
                    f"然后重试搜索"
                )

        # 提取搜索结果
        hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
        total = result.get('rawResponse', {}).get('hits', {}).get('total', {})
        total_value = total.get('value', 0) if isinstance(total, dict) else total

        if not hits:
            return (
                f"未找到匹配的日志\n"
                f"查询: {query}\n"
                f"索引: {index_pattern}\n"
                f"时间范围: 最近 {hours_ago} 小时"
            )

        # 格式化输出结果
        results = [f"✅ 找到 {total_value} 条匹配日志，显示前 {len(hits)} 条：\n"]
        results.append("=" * 80)

        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            timestamp = source.get('@timestamp', '未知时间')

            # 尝试获取日志消息（字段名可能不同）
            message = (
                source.get('log') or
                source.get('message') or
                source.get('Message') or
                source.get('msg') or
                '无消息内容'
            )

            # 截取消息长度
            if len(message) > 800:
                message = message[:800] + "\n... (已截断)"

            # 提取其他有用字段
            extra_info = []
            for field in ['level', 'severity', 'service', 'pod_name', 'namespace', 'container_name']:
                if field in source:
                    extra_info.append(f"{field}={source[field]}")

            results.append(f"\n📋 [{i}/{len(hits)}] {timestamp}")
            if extra_info:
                results.append(f"   ℹ️  {' | '.join(extra_info)}")
            results.append(f"   📝 {message}")
            results.append("-" * 80)

        return "\n".join(results)

    except ValueError as e:
        return f"❌ 配置错误: {str(e)}"
    except Exception as e:
        logger.error(f"搜索日志时出错: {e}", exc_info=True)
        return f"❌ 搜索日志时出错: {str(e)}"


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
        time_from: 开始时间（如 "2026-04-24T10:00:00", "now-2h", "now-1d"）
        time_to: 结束时间，默认 "now"
        index_pattern: 索引模式
        size: 返回结果数量

    返回:
        格式化的日志搜索结果

    示例:
        - search_aws_logs_by_time("ERROR", "now-12h", "now-6h")
        - search_aws_logs_by_time("exception", "2026-04-24T00:00:00", "2026-04-24T12:00:00")
    """
    try:
        client = get_aws_opensearch_client()

        # 执行搜索
        result = client.search(
            query=query,
            index_pattern=index_pattern,
            size=size,
            time_from=time_from,
            time_to=time_to
        )

        if not result:
            logger.warning("首次搜索失败，尝试自动刷新 cookies...")

            # 自动刷新cookies
            if refresh_cookies():
                # 重新加载客户端
                reload_client()
                client = get_aws_opensearch_client()

                # 重试搜索
                logger.info("重新尝试搜索...")
                result = client.search(
                    query=query,
                    index_pattern=index_pattern,
                    size=size,
                    time_from=time_from,
                    time_to=time_to
                )

                if not result:
                    return (
                        f"❌ 刷新 cookies 后仍然搜索失败\n"
                        f"可能原因：\n"
                        f"1. 网络连接问题\n"
                        f"2. 索引模式不存在: {index_pattern}\n"
                        f"3. OpenSearch 服务异常"
                    )
            else:
                return (
                    f"❌ 搜索失败且无法自动刷新 cookies\n"
                    f"请手动运行以下命令获取 cookies：\n"
                    f"python {COOKIE_REFRESH_SCRIPT}\n"
                    f"然后重试搜索"
                )

        # 使用相同的格式化逻辑
        hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
        total = result.get('rawResponse', {}).get('hits', {}).get('total', {})
        total_value = total.get('value', 0) if isinstance(total, dict) else total

        if not hits:
            return f"未找到匹配的日志（时间范围: {time_from} 到 {time_to}）"

        results = [f"✅ 找到 {total_value} 条匹配日志（{time_from} 到 {time_to}），显示前 {len(hits)} 条：\n"]
        results.append("=" * 80)

        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            timestamp = source.get('@timestamp', '未知时间')
            message = source.get('log', source.get('Message', source.get('message', '无消息内容')))

            if len(message) > 800:
                message = message[:800] + "\n... (已截断)"

            results.append(f"\n📋 [{i}/{len(hits)}] {timestamp}")
            results.append(f"   📝 {message}")
            results.append("-" * 80)

        return "\n".join(results)

    except Exception as e:
        logger.error(f"搜索日志时出错: {e}", exc_info=True)
        return f"❌ 搜索日志时出错: {str(e)}"


if __name__ == "__main__":
    logger.info("正在启动 MCP AWS OpenSearch 日志服务器（SSO 认证）...")
    logger.info(f"AWS OpenSearch URL: {AWS_OPENSEARCH_BASE_URL}")
    logger.info(f"Cookies 文件: {COOKIES_FILE}")
    logger.info("提供工具:")
    logger.info("  - search_aws_logs: 搜索日志（按小时范围）")
    logger.info("  - search_aws_logs_by_time: 搜索日志（自定义时间范围）")
    logger.info("\n⚠️  注意: 如果 cookies 过期，请运行 aws_opensearch_auto.py 重新获取")
    logger.info("使用 Ctrl+C 停止服务器\n")

    # 初始化并运行服务器
    mcp.run(transport='stdio')

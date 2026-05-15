#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP OpenSearch 日志查询服务器（多系统支持）

提供日志查询工具：
1. search_aws_logs: 在 OpenSearch 中搜索日志
2. search_aws_logs_by_time: 指定时间范围搜索日志

支持多系统认证：
- crm: 使用用户名密码认证（HTTPBasicAuth）
- test/prod (bts): 使用 SSO cookies 认证

Author: FlyAIBox
Date: 2026.04.24
"""

import os
import json
import logging
import requests
import traceback
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

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

# 多系统环境配置
# auth_type: "cookie" 使用 SSO cookies 认证, "password" 使用用户名密码认证
ENV_CONFIG = {
    "uat": {
        "name": "BTS UAT测试环境 (Uat)",
        "base_url": "https://search-ops-log-uat-hd4smt5lrsjtmbw2jxrd6k7mci.us-east-1.es.amazonaws.com",
        "auth_type": "cookie",
        "cookies_file": Path(__file__).parent / "opensearch_cookies_uat.json",
    },
    "alpha": {
        "name": "BTS Alpha测试环境 (Alpha)",
        "base_url": "https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com",
        "auth_type": "cookie",
        "cookies_file": Path(__file__).parent / "opensearch_cookies_alpha.json",
    },
    "prod": {
        "name": "BTS 线上环境 (Prod)",
        "base_url": "https://search-ops-log-prod-xqytgli2pwcl6yfaqeew3363gi.us-east-1.es.amazonaws.com",
        "auth_type": "cookie",
        "cookies_file": Path(__file__).parent / "opensearch_cookies_prod.json",
    },
    "crm": {
        "name": "CRM 环境",
        "base_url": os.getenv("OPENSEARCH_BASE_URL", "https://opensearch.crm-prod.com"),
        "auth_type": "password",
        "username": os.getenv("OPENSEARCH_USERNAME"),
        "password": os.getenv("OPENSEARCH_PASSWORD"),
    },
}
DEFAULT_ENV = "alpha"


class OpenSearchClient:
    """OpenSearch 客户端（支持密码认证和 Cookie 认证）"""

    def __init__(self, base_url: str, cookies: Dict[str, str] = None,
                 username: str = None, password: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)
        elif cookies:
            self.session.cookies.update(cookies)

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


# 全局客户端实例（按环境懒加载）
_opensearch_clients = {}
# Cookie刷新脚本路径
COOKIE_REFRESH_SCRIPT = Path(__file__).parent.parent / "server" / "aws_opensearch_auto.py"
PYTHON_VENV = Path(__file__).parent.parent / "venv_mcp_demo" / "bin" / "python"


def refresh_cookies(env: str = DEFAULT_ENV) -> bool:
    """
    自动运行cookies刷新脚本（仅适用于 cookie 认证环境）
    """
    env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
    if env_config.get("auth_type") != "cookie":
        return False

    cookies_file = env_config["cookies_file"]

    try:
        logger.info("=" * 80)
        logger.info(f"检测到 cookies 过期，正在自动刷新 [{env_config['name']}]...")
        logger.info(f"执行脚本: {COOKIE_REFRESH_SCRIPT}")
        logger.info("=" * 80)

        process = subprocess.Popen(
            [str(PYTHON_VENV), "-u", str(COOKIE_REFRESH_SCRIPT), "--auto-refresh", env],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(timeout=300)

        logger.info("刷新脚本输出:")
        logger.info(stdout)

        if stderr:
            logger.warning(f"刷新脚本错误输出: {stderr}")

        if cookies_file.exists():
            logger.info("Cookies 文件已更新，重新加载客户端...")
            return True
        else:
            logger.error("Cookies 文件未生成")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Cookies 刷新超时（5分钟）")
        process.kill()
        return False
    except Exception as e:
        logger.error(f"刷新 cookies 失败: {e}")
        logger.error(traceback.format_exc())
        return False


def reload_client(env: str = DEFAULT_ENV):
    """重新加载客户端（清除缓存）"""
    global _opensearch_clients
    _opensearch_clients.pop(env, None)


def get_opensearch_client(env: str = DEFAULT_ENV) -> OpenSearchClient:
    """获取 OpenSearch 客户端实例"""
    global _opensearch_clients
    if env not in _opensearch_clients:
        env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
        base_url = env_config["base_url"]
        auth_type = env_config.get("auth_type", "cookie")

        if auth_type == "password":
            username = env_config.get("username")
            password = env_config.get("password")
            if not username or not password:
                raise ValueError(f"请在 .env 文件中配置 OPENSEARCH_USERNAME 和 OPENSEARCH_PASSWORD [{env_config['name']}]")
            _opensearch_clients[env] = OpenSearchClient(base_url, username=username, password=password)
            logger.info(f"已创建密码认证客户端 [{env_config['name']}]")
        else:
            cookies_file = env_config["cookies_file"]
            try:
                with open(cookies_file, 'r') as f:
                    cookies_list = json.load(f)
                    cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
                    logger.info(f"已从 {cookies_file} 加载 {len(cookies)} 个 cookies [{env_config['name']}]")
                    _opensearch_clients[env] = OpenSearchClient(base_url, cookies=cookies)
            except FileNotFoundError:
                raise ValueError(f"未找到 cookies 文件: {cookies_file}，请先运行 aws_opensearch_auto.py 获取 [{env_config['name']}] 的 cookies")
    return _opensearch_clients[env]


@mcp.tool()
def search_aws_logs(
    query: str,
    index_pattern: str = "*bts-bigaccount*",
    hours_ago: int = 1,
    size: int = 20,
    env: str = "alpha"
) -> str:
    """
    在 OpenSearch 中搜索日志

    参数:
        query: 搜索关键词（支持 Lucene 查询语法，如 "ERROR", "exception", "traceId:abc123"）
        index_pattern: 索引模式，默认 "*bts-bigaccount*"
        hours_ago: 查询最近多少小时的日志，默认 1 小时
        size: 返回结果数量，默认 20（最大建议不超过 50）
        env: 环境选择: "crm" CRM系统（密码认证）, "alpha" BTS Alpha测试环境（默认，cookie认证）, "uat" BTS UAT测试环境, "prod" BTS线上环境（cookie认证）

    返回:
        格式化的日志搜索结果

    示例:
        - search_aws_logs("ERROR")
        - search_aws_logs("exception", index_pattern="*app*", hours_ago=2)
        - search_aws_logs("9a18bc0641e4444397e57f87007489bc", env="prod")
        - search_aws_logs("error OR exception", index_pattern="fluentd-app-*", env="crm")
    """
    try:
        try:
            client = get_opensearch_client(env)
        except ValueError:
            env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
            if env_config.get("auth_type") == "password":
                return f"配置错误: 请在 .env 文件中配置 OPENSEARCH_USERNAME 和 OPENSEARCH_PASSWORD"
            logger.warning(f"cookies 文件不存在，尝试自动刷新 [{env}]...")
            if refresh_cookies(env):
                reload_client(env)
                client = get_opensearch_client(env)
            else:
                return (
                    f"配置错误: cookies 文件不存在且自动刷新失败\n"
                    f"请手动运行以下命令获取 cookies：\n"
                    f"python {COOKIE_REFRESH_SCRIPT}\n"
                    f"然后重试搜索"
                )

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
            env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
            if env_config.get("auth_type") == "password":
                return (
                    f"搜索失败\n"
                    f"可能原因：\n"
                    f"1. 用户名或密码错误，请检查 .env 配置\n"
                    f"2. 网络连接问题\n"
                    f"3. 索引模式不存在: {index_pattern}\n"
                    f"4. OpenSearch 服务异常"
                )

            logger.warning(f"首次搜索失败，尝试自动刷新 cookies [{env}]...")

            if refresh_cookies(env):
                reload_client(env)
                client = get_opensearch_client(env)

                logger.info("重新尝试搜索...")
                result = client.search(
                    query=query,
                    index_pattern=index_pattern,
                    size=size,
                    time_from=time_from
                )

                if not result:
                    return (
                        f"刷新 cookies 后仍然搜索失败\n"
                        f"可能原因：\n"
                        f"1. 网络连接问题\n"
                        f"2. 索引模式不存在: {index_pattern}\n"
                        f"3. OpenSearch 服务异常"
                    )
            else:
                return (
                    f"搜索失败且无法自动刷新 cookies\n"
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
    size: int = 20,
    env: str = "alpha"
) -> str:
    """
    在 OpenSearch 中按指定时间范围搜索日志

    参数:
        query: 搜索关键词
        time_from: 开始时间（如 "2026-04-24T10:00:00", "now-2h", "now-1d"）
        time_to: 结束时间，默认 "now"
        index_pattern: 索引模式
        size: 返回结果数量
        env: 环境选择: "crm" CRM系统（密码认证）, "alpha" BTS Alpha测试环境（默认，cookie认证）, "uat" BTS UAT测试环境, "prod" BTS线上环境（cookie认证）

    返回:
        格式化的日志搜索结果

    示例:
        - search_aws_logs_by_time("ERROR", "now-12h", "now-6h")
        - search_aws_logs_by_time("exception", "2026-04-24T00:00:00", "2026-04-24T12:00:00", env="prod")
        - search_aws_logs_by_time("timeout", "now-3h", env="crm")
    """
    try:
        try:
            client = get_opensearch_client(env)
        except ValueError:
            env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
            if env_config.get("auth_type") == "password":
                return f"配置错误: 请在 .env 文件中配置 OPENSEARCH_USERNAME 和 OPENSEARCH_PASSWORD"
            logger.warning(f"cookies 文件不存在，尝试自动刷新 [{env}]...")
            if refresh_cookies(env):
                reload_client(env)
                client = get_opensearch_client(env)
            else:
                return (
                    f"配置错误: cookies 文件不存在且自动刷新失败\n"
                    f"请手动运行以下命令获取 cookies：\n"
                    f"python {COOKIE_REFRESH_SCRIPT}\n"
                    f"然后重试搜索"
                )

        # 执行搜索
        result = client.search(
            query=query,
            index_pattern=index_pattern,
            size=size,
            time_from=time_from,
            time_to=time_to
        )

        if not result:
            env_config = ENV_CONFIG.get(env, ENV_CONFIG[DEFAULT_ENV])
            if env_config.get("auth_type") == "password":
                return (
                    f"搜索失败\n"
                    f"可能原因：\n"
                    f"1. 用户名或密码错误，请检查 .env 配置\n"
                    f"2. 网络连接问题\n"
                    f"3. 索引模式不存在: {index_pattern}\n"
                    f"4. OpenSearch 服务异常"
                )

            logger.warning(f"首次搜索失败，尝试自动刷新 cookies [{env}]...")

            if refresh_cookies(env):
                reload_client(env)
                client = get_opensearch_client(env)

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
                        f"刷新 cookies 后仍然搜索失败\n"
                        f"可能原因：\n"
                        f"1. 网络连接问题\n"
                        f"2. 索引模式不存在: {index_pattern}\n"
                        f"3. OpenSearch 服务异常"
                    )
            else:
                return (
                    f"搜索失败且无法自动刷新 cookies\n"
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

            if len(message) > 10000:
                message = message[:10000] + "\n... (已截断)"

            results.append(f"\n📋 [{i}/{len(hits)}] {timestamp}")
            results.append(f"   📝 {message}")
            results.append("-" * 80)

        return "\n".join(results)

    except Exception as e:
        logger.error(f"搜索日志时出错: {e}", exc_info=True)
        return f"❌ 搜索日志时出错: {str(e)}"


if __name__ == "__main__":
    logger.info("正在启动 MCP OpenSearch 日志服务器（多系统支持）...")
    for env_key, env_val in ENV_CONFIG.items():
        auth_info = env_val.get("auth_type", "cookie")
        logger.info(f"  [{env_key}] {env_val['name']}: {env_val['base_url']} (认证: {auth_info})")
    logger.info("提供工具:")
    logger.info("  - search_aws_logs: 搜索日志（按小时范围）")
    logger.info("  - search_aws_logs_by_time: 搜索日志（自定义时间范围）")
    logger.info("支持环境: crm(密码认证), test(cookie认证), prod(cookie认证)")
    logger.info("使用 Ctrl+C 停止服务器\n")

    mcp.run(transport='stdio')

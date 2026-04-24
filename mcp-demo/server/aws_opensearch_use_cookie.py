#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS OpenSearch（内网 SSO 认证）日志查询客户端

适用于通过 SSO 认证的 AWS OpenSearch Service

Author: FlyAIBox
Date: 2025.05.03
"""

import requests
import json
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
            # 如果提供了 cookies 字典
            self.session.cookies.update(cookies)

        # 通用 headers
        self.session.headers.update({
            'osd-xsrf': 'true',
            'Content-Type': 'application/json'
        })

    def set_cookie_string(self, cookie_string: str):
        """
        从浏览器复制的 Cookie 字符串中解析并设置 cookies

        参数:
            cookie_string: 浏览器中复制的完整 Cookie 字符串
        """
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                self.session.cookies.set(key.strip(), value.strip())
        logger.info("已设置 cookies")

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
            logger.info(f"请求URL: {url}")
            response = self.session.post(url, json=payload, timeout=30)

            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应 Content-Type: {response.headers.get('Content-Type')}")

            # 打印响应前 500 字符用于调试
            response_preview = response.text[:500] if response.text else "(空响应)"
            logger.info(f"响应内容预览: {response_preview}")

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
            import traceback
            logger.error(traceback.format_exc())
            return None

    def search_direct_api(
        self,
        index: str,
        query_body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        直接调用 OpenSearch API（不通过 Dashboards）

        参数:
            index: 索引名称
            query_body: 完整的 DSL 查询体
        """
        url = f"{self.base_url}/{index}/_search"

        try:
            response = self.session.post(url, json=query_body, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"查询失败: {response.status_code}, {response.text}")
                return None

        except Exception as e:
            logger.error(f"查询异常: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    # AWS OpenSearch 地址
    base_url = "https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com"

    # 创建客户端
    client = AWSOpenSearchClient(base_url)

    # 方式1：设置 cookie 字符串（从浏览器开发者工具复制）
    cookie_string = """
    your_cookie_name_1=value1; your_cookie_name_2=value2; session_id=xxx
    """
    # client.set_cookie_string(cookie_string)

    # 方式2：从 opensearch_cookies.json 加载 cookies
    try:
        with open('../opensearch_cookies.json', 'r') as f:
            cookies_list = json.load(f)
            # 转换为字典格式
            cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
            client.session.cookies.update(cookies)
            logger.info(f"已从文件加载 {len(cookies)} 个 cookies")
    except FileNotFoundError:
        logger.warning("未找到 opensearch_cookies.json，使用硬编码的 cookies")
        # 备用：硬编码的 cookies（可能已过期）
        cookies = {
                      "REFRESH-TOKEN": "eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ.LAUd4vCyObxa_Jg2Ca5X6eSilBZXJBCd--i5zAeTLcTkyol_l2GkTuMayP6GiijB4M_uohE4yRzipRi27kebvawTh33Ajzb4axHNMyvuP942ddmgqp7Sbx55sf6yWacrMsdcVN5s_6DqOrLL2d7Lgk7eJiXLVgLMr6HWscdLK2Q4mc66UTlTlNrGtkfxZvg3QBxPDu94aK5uVRehjA3A22mS0MyWLIXIKS5Wm27zaWf2nQ5ZokAc1fDreevmO1n24gV7jSzwZJ4lrKDXLu46rVZGkWSkOD_wkI4ByMEhydd36taNlIvP76petSEmFlQ6yUXTOMcKG0zaq3FN8J5vbw.eVrBy7PODla1_8GB.R3hwn7TNFu8Ur1y4Z3KIuAa_QlyluyGQNmZiHQMcm5WgEGsRhBR2UfBnEo6GdFY0A6gg8yQn4U7ej-9fWdo191qH3xFCElI-VkKMdVY8B9hyI3_Stkyy6uH9W_tEIoNTvr5QrHHH5St6DJssV8aWWWas3YKXcAqlXcUQnkuNUt4XYaY8Vn-RMc-5HbemoA9fxEoSZ13FNOfwPidm-Ds4XhHXXl00LQ5sQYhcAfwR34xazIAdRnTG15pDWgVAeyYXoL4iUlg7_XPYTJYzoRn-PdzRfAGZM1Qrl8RTi4SitOfYKXFZeNyRrcskBUTITFmmAlXjSFYuylKwfrMw50FFdgzedyUf9KWAF5pW8c4VNicaM3OepUnpYD0TzU6VVNIm3Hclg4xNW-CYReehedbLz9RUhnTD1qknRTBI3gSHXqIAG6BJb5X2-bzHEYNgnN4yhPgdyteDi33nDuF_PwpsNKxGe2AoyfcvJpB6LKi1lyRSkzkly-5625B9MfFZ--t3IsPMbQjVEPU6RTkVs2OuAv-4AojzdII9np07lsv__F5R9Edh7GeBi19TKOlkCqEVnor3ph5tAhTunl3aZyfSyyo1JPnKVHVH0npcuib32gLJw0TYNQtwQiVUd8ypvkiAXXz3HcrqiP97rlZJ7I712ZF9PoOiS4HrNxPQsjTawA1Mf5E9l37rCV-G2-Lk_l_rC5mJCFhRFXuDE02KqBmQvZijPZinzehh1Q6hRSvaqcrm6rxydpJ0tsPuz4nE1WQESUZ9vQHmVXfM4DB0YTESKzgJV5WO1UU-FCrvuz-JmC_e1hENfXXrokJDxw6kzT8iZAPzZW_PMTMbfYUwSIIgT8HXrbhowPi0Bk_jSfnMT527_YiPg9YEnknkleksRFJXT-fJnY9BCOYoTOPDWicUAKFEfV8HRvYkFfb9YGjhmgsg5AccGLmYJ-FpHgw-Ww7My6bPNFS_p_JOPTvcuFMNucnpTOp8Luh_pOKz6rFehEw5fAT9RVjS436knGH0LIoDP11grkEVzkPHq6WwLKfTlm1LacCZTyioqss55IxFKmJDYO6WoRvk_RDdGaowkqQ5AnubjlfR6luMNcljdTC_hk_H7GCbyzGXz-Vj2Aft4TA_eP5N7U5KmEebZYfbxz4wjRCbAUESefxQVT9IKF_cgoss5zfR9ZWVLHN914iNHCxFBjdYUit-NeIbO0SRogL621VcCyoF0KyjypgPvl0Zcs0yRx8j6x9j88zkiqB2H6bS0nbMf_cnNpP5QU1ivH32-0LTeUCJevfSi4HhMHA.3gKvzpt2OxRJijBJgEn3DA",
                      "ID-TOKEN": "eyJraWQiOiJDUm5OZHB3eThhOVFNaFkyb00xVnVYRE5qN0hocmNCbmxhZkdoMUFVaVY0PSIsImFsZyI6IlJTMjU2In0.eyJhdF9oYXNoIjoiRjNXN0N3a1NTem9TM1N6Rlhpam0zdyIsInN1YiI6IjE5YmFlNTdjLTEwMTEtNzAwYi0yZmJkLTFhMzdlYTYwOTcxYiIsImNvZ25pdG86Z3JvdXBzIjpbImFwLXNvdXRoZWFzdC0xX1J0RG1TUXoxM19jYXNzZG9yIl0sImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmFwLXNvdXRoZWFzdC0xLmFtYXpvbmF3cy5jb21cL2FwLXNvdXRoZWFzdC0xX1J0RG1TUXoxMyIsImNvZ25pdG86dXNlcm5hbWUiOiJjYXNzZG9yX2UxNGZlM2EzLTlhNmEtNGU1Ny1iY2ZhLTdlODgxM2QyNWNhNCIsIm9yaWdpbl9qdGkiOiIyNjA0MTUwNi1lYTU0LTRkZTUtYjA2MS1iNzEwNDhiYjllMTEiLCJhdWQiOiIycHFtcm02MjdsZGkya2d2Mm03dmxsbnJmdSIsImlkZW50aXRpZXMiOlt7ImRhdGVDcmVhdGVkIjoiMTc1NzI5NTQ3NjcyOSIsInVzZXJJZCI6ImUxNGZlM2EzLTlhNmEtNGU1Ny1iY2ZhLTdlODgxM2QyNWNhNCIsInByb3ZpZGVyTmFtZSI6ImNhc3Nkb3IiLCJwcm92aWRlclR5cGUiOiJPSURDIiwiaXNzdWVyIjpudWxsLCJwcmltYXJ5IjoidHJ1ZSJ9XSwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE3NzU2Mjk5MDMsIm5hbWUiOiJMZW8gRmFuZyIsImV4cCI6MTc3NzAyMTc3MywiaWF0IjoxNzc3MDE4MTczLCJqdGkiOiIzNGVkN2FkZC0yYzVkLTQ4MDAtYmFhZS04ZWI3YmRlZDA3ZTYiLCJlbWFpbCI6Imxlby5mYW5nQGh5dGVjaGMuY29tIn0.Vo_YiAijyYIBTH77qjuAnyUfPFI0Qlps3pnwwNDJ2qu3jDHCB0bJmC5zj6FKQl2fopvDkDiw3gj5ITYiWZSFngBsr7tEUZGV62mgF3yK6v6FK42k5-KwaB4GsqlfQCXY-ZXaAKUFeGZYkQtNSLmHDaicOXzYsp2MlBL8hwDF0rsAJQA-Yf0moMp-FQpGuK-XD1XoqBcmls54W-l47wS0zuxE7yum_x2puheEcLeEY3ch8X7-who_TeFZobzGLRw-kHW9Z63SGg39TPdSo9g5ezL_Ss_HdyVWcVK7yVl4KMUBH2fcxPvseY4FyCFrM8JcW61tdwcbSfu4Oc4Mm4ZhIA",
                      "ACCESS-TOKEN": "eyJraWQiOiI4RTBvbTZnanVMa2U3eEo5TEpEOVhPckIrU3dPUzE5Q3R6NUxSeG8ramNBPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxOWJhZTU3Yy0xMDExLTcwMGItMmZiZC0xYTM3ZWE2MDk3MWIiLCJjb2duaXRvOmdyb3VwcyI6WyJhcC1zb3V0aGVhc3QtMV9SdERtU1F6MTNfY2Fzc2RvciJdLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuYXAtc291dGhlYXN0LTEuYW1hem9uYXdzLmNvbVwvYXAtc291dGhlYXN0LTFfUnREbVNRejEzIiwidmVyc2lvbiI6MiwiY2xpZW50X2lkIjoiMnBxbXJtNjI3bGRpMmtndjJtN3ZsbG5yZnUiLCJvcmlnaW5fanRpIjoiMjYwNDE1MDYtZWE1NC00ZGU1LWIwNjEtYjcxMDQ4YmI5ZTExIiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJwaG9uZSBvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF1dGhfdGltZSI6MTc3NTYyOTkwMywiZXhwIjoxNzc3MDIxNzczLCJpYXQiOjE3NzcwMTgxNzMsImp0aSI6Ijk5NzhhZWJkLWUwMTMtNDE0Yi1hMGExLWM4ZmUwMTBmMjkzNiIsInVzZXJuYW1lIjoiY2Fzc2Rvcl9lMTRmZTNhMy05YTZhLTRlNTctYmNmYS03ZTg4MTNkMjVjYTQifQ.0UCH-fL9gej0nz_Z_KyS6XgpJRJrFgGOHEzMG5bgNf5Uai2I8auOVQF-yISS-QpR8kLH_yYplLGoVq9eCEH8R9HpOJGKIvyCV9BgpjLZewf1EpmpaTE1tKZ3Po5F3hfIZw5r2qwTMmcPWNEFGCCetzLWo1KObV7gm70_ZRTlkOC7INM9RJPz_a1y4Y15X5RZ2QaCC2CB403U3YEwPKMzU5m1krKtuLG96l1HigvYCZGI1Jllh-G7B0vWtWEapd6T-wk7sJ1BeeYarUGxeTA_e3gEc6ih5C7gosMrcHY3BQe2qxwWTGvfrTSynnVDNGFoqaz7ppzScJ4vGJr197h7Lw"
                  }
        client.session.cookies.update(cookies)

    # 打印当前 cookies（用于调试）
    logger.info(f"当前 cookies: {list(client.session.cookies.keys())}")

    # 执行搜索
    result = client.search(
        query="ERROR",
        index_pattern="*bts-bigaccount*",
        size=10,
        time_from="now-10h",
        time_to="now"
    )

    if result:
        hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
        print(f"\n找到 {len(hits)} 条日志：\n")
        for i, hit in enumerate(hits, 1):
            source = hit['_source']
            print(f"[{i}] {source.get('@timestamp')}")
            print(f"    {source.get('log', source.get('log', ''))[:1000]}")
            print()
    else:
        print("搜索失败，请检查 cookies 是否有效")

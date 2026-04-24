import requests
import logging
from requests.auth import HTTPBasicAuth
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)

    def search(self, query, index_pattern="*", time_range=None):
        """
        搜索 OpenSearch Dashboards

        Args:
            query: 搜索查询字符串
            index_pattern: 索引模式，默认 "*" 表示所有索引
            time_range: 时间范围，例如 {"from": "now-1h", "to": "now"}
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
                        "query_string": {
                            "query": query
                        }
                    },
                    "size": 100  # 返回结果数量
                }
            }
        }

        # 如果指定了时间范围
        if time_range:
            payload["params"]["body"]["query"] = {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": query
                            }
                        },
                        {
                            "range": {
                                "@timestamp": time_range
                            }
                        }
                    ]
                }
            }

        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                verify=True  # 如果是自签名证书，改为 False
            )

            logger.info(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"搜索成功，返回 {len(data.get('rawResponse', {}).get('hits', {}).get('hits', []))} 条结果")
                return data
            else:
                logger.error(f"请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None

        except Exception as e:
            logger.error(f"请求异常: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = OpenSearchClient(
        base_url="https://opensearch.crm-prod.com",
        username="leo.fang",
        password="decay-34-focusing-Primary"
    )

    # 执行搜索
    # 示例1: 简单搜索
#     result = client.search(query="error OR exception")

    # 示例2: 带时间范围的搜索
    result = client.search(
        query="900fdb1a55754882b8a0c21114563ec61776413777270",
        index_pattern="fluentd-app-*",
        time_range={"from": "now-1h", "to": "now"}
    )

    if result:
        # 打印结果
        hits = result.get('rawResponse', {}).get('hits', {}).get('hits', [])
        for hit in hits:
            logger.info(f"日志: {json.dumps(hit['_source'], ensure_ascii=False, indent=2)}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP Redis 本地读写服务器

提供 Redis 操作工具：
1. redis_get: 获取指定 key 的值
2. redis_set: 设置 key-value（支持过期时间）
3. redis_delete: 删除指定 key
4. redis_keys: 搜索匹配的 keys
5. redis_hget: 获取 hash 中指定字段的值
6. redis_hset: 设置 hash 字段
7. redis_hgetall: 获取整个 hash

Author: FlyAIBox
Date: 2026.04.28
"""

import json
import logging
import traceback
from typing import Optional

import redis
from mcp.server.fastmcp import FastMCP

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 FastMCP 服务器
mcp = FastMCP("redis-local")

# Redis 连接配置（默认连本地）
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None

# 全局客户端（懒加载）
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端实例"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        _redis_client.ping()
        logger.info(f"已连接到 Redis: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    return _redis_client


@mcp.tool()
def redis_get(key: str) -> str:
    """
    获取 Redis 中指定 key 的值

    参数:
        key: Redis key 名称

    返回:
        key 对应的值

    示例:
        - redis_get("user:1001")
        - redis_get("config:app")
    """
    try:
        client = get_redis_client()
        value = client.get(key)
        if value is None:
            return f"(nil) key 不存在: {key}"
        return value
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_get 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_set(key: str, value: str, expire_seconds: int = 0) -> str:
    """
    设置 Redis key-value，支持过期时间

    参数:
        key: Redis key 名称
        value: 要设置的值
        expire_seconds: 过期时间（秒），0 表示永不过期，默认 0

    返回:
        操作结果

    示例:
        - redis_set("user:1001", "张三")
        - redis_set("session:abc", "token123", expire_seconds=3600)
    """
    try:
        client = get_redis_client()
        if expire_seconds > 0:
            client.setex(key, expire_seconds, value)
        else:
            client.set(key, value)
        ttl_info = f"，过期时间 {expire_seconds}s" if expire_seconds > 0 else "，永不过期"
        return f"✅ OK: {key} = {value}{ttl_info}"
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_set 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_delete(key: str) -> str:
    """
    删除 Redis 中指定 key

    参数:
        key: 要删除的 key 名称

    返回:
        操作结果（删除的 key 数量）

    示例:
        - redis_delete("user:1001")
        - redis_delete("temp:*")
    """
    try:
        client = get_redis_client()
        # 支持通配符批量删除
        if '*' in key or '?' in key:
            keys = client.keys(key)
            if not keys:
                return f"没有匹配的 key: {key}"
            count = client.delete(*keys)
            return f"✅ 删除了 {count} 个 key（模式: {key}）"
        else:
            count = client.delete(key)
            if count == 0:
                return f"key 不存在: {key}"
            return f"✅ 已删除: {key}"
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_delete 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_keys(pattern: str = "*", limit: int = 50) -> str:
    """
    搜索匹配模式的 Redis keys

    参数:
        pattern: 匹配模式，支持 * 和 ? 通配符，默认 "*"（所有 key）
        limit: 最多返回数量，默认 50

    返回:
        匹配的 key 列表

    示例:
        - redis_keys("user:*")
        - redis_keys("*session*", limit=20)
    """
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        total = len(keys)
        if total == 0:
            return f"没有匹配的 key: {pattern}"

        keys = keys[:limit]
        lines = [f"🔑 匹配 {pattern} 共 {total} 个 key，显示前 {len(keys)} 个："]
        for i, k in enumerate(keys, 1):
            ttl = client.ttl(k)
            key_type = client.type(k)
            ttl_str = f"ttl={ttl}s" if ttl > 0 else "永久" if ttl == -1 else f"剩余 {ttl}s"
            lines.append(f"  [{i}] {k}  (type={key_type}, {ttl_str})")
        return "\n".join(lines)
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_keys 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_hget(key: str, field: str) -> str:
    """
    获取 Redis hash 中指定字段的值

    参数:
        key: hash 的 key 名称
        field: hash 中的字段名

    返回:
        字段值

    示例:
        - redis_hget("user:1001", "name")
        - redis_hget("config:app", "version")
    """
    try:
        client = get_redis_client()
        value = client.hget(key, field)
        if value is None:
            return f"(nil) key={key}, field={field} 不存在"
        return value
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_hget 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_hset(key: str, field: str, value: str) -> str:
    """
    设置 Redis hash 字段

    参数:
        key: hash 的 key 名称
        field: 字段名
        value: 字段值

    返回:
        操作结果

    示例:
        - redis_hset("user:1001", "name", "张三")
        - redis_hset("user:1001", "age", "25")
    """
    try:
        client = get_redis_client()
        is_new = client.hset(key, field, value)
        action = "新增" if is_new else "更新"
        return f"✅ {action}: {key} -> {field} = {value}"
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_hset 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_hgetall(key: str) -> str:
    """
    获取 Redis hash 的全部字段和值

    参数:
        key: hash 的 key 名称

    返回:
        所有字段和值的格式化列表

    示例:
        - redis_hgetall("user:1001")
    """
    try:
        client = get_redis_client()
        data = client.hgetall(key)
        if not data:
            return f"(empty) hash {key} 不存在或为空"

        lines = [f"📋 Hash {key} ({len(data)} 个字段):"]
        for i, (field, value) in enumerate(data.items(), 1):
            lines.append(f"  [{i}] {field} = {value}")
        return "\n".join(lines)
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_hgetall 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_ttl(key: str) -> str:
    """
    查询 key 的剩余过期时间

    参数:
        key: Redis key 名称

    返回:
        剩余秒数，-1 表示永久，-2 表示 key 不存在

    示例:
        - redis_ttl("session:abc")
    """
    try:
        client = get_redis_client()
        ttl = client.ttl(key)
        if ttl == -2:
            return f"key 不存在: {key}"
        elif ttl == -1:
            return f"🔒 {key} 永不过期"
        else:
            return f"⏳ {key} 剩余 {ttl}s（约 {ttl // 60} 分钟）"
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_ttl 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


@mcp.tool()
def redis_type(key: str) -> str:
    """
    查询 key 的类型

    参数:
        key: Redis key 名称

    返回:
        key 的类型（string, hash, list, set, zset, stream, none）

    示例:
        - redis_type("user:1001")
    """
    try:
        client = get_redis_client()
        key_type = client.type(key)
        if key_type == "none":
            return f"key 不存在: {key}"
        return f"📌 {key} 类型: {key_type}"
    except redis.ConnectionError as e:
        return f"❌ Redis 连接失败: {e}"
    except Exception as e:
        logger.error(f"redis_type 出错: {e}", exc_info=True)
        return f"❌ 出错: {e}"


if __name__ == "__main__":
    logger.info("正在启动 MCP Redis 本地读写服务器...")
    logger.info(f"Redis 连接: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    logger.info("提供工具:")
    logger.info("  - redis_get: 获取 key 的值")
    logger.info("  - redis_set: 设置 key-value")
    logger.info("  - redis_delete: 删除 key")
    logger.info("  - redis_keys: 搜索匹配的 keys")
    logger.info("  - redis_hget: 获取 hash 字段")
    logger.info("  - redis_hset: 设置 hash 字段")
    logger.info("  - redis_hgetall: 获取整个 hash")
    logger.info("  - redis_ttl: 查询过期时间")
    logger.info("  - redis_type: 查询 key 类型")
    logger.info("使用 Ctrl+C 停止服务器\n")

    mcp.run(transport='stdio')

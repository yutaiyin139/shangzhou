# -*- coding: utf-8 -*-
"""
Redis 缓存与限流工具
提供 LLM 响应缓存、API 速率限制、工作流状态缓存等功能
"""

import json
import hashlib
import time
import functools
from flask import request, jsonify

# ============================================================
# Redis 连接管理
# ============================================================

_redis_client = None


def get_redis():
    """获取 Redis 连接（单例模式）"""
    global _redis_client
    if _redis_client is None:
        import redis
        from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=0,
            decode_responses=True,  # 自动解码为字符串
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client

# 兼容别名
get_redis_client = get_redis


def redis_available():
    """检查 Redis 是否可用"""
    try:
        r = get_redis()
        return r.ping()
    except Exception:
        return False


# ============================================================
# LLM 响应缓存
# ============================================================

def make_cache_key(prefix, *args, **kwargs):
    """生成缓存键"""
    raw = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, ensure_ascii=False)
    h = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return f"{prefix}:{h}"


def llm_cache_get(messages, model_name, temperature=0.7, max_tokens=2048):
    """
    获取 LLM 缓存
    返回缓存的响应内容，未命中返回 None
    """
    try:
        r = get_redis()
        key = make_cache_key('llc', messages, model_name, temperature, max_tokens)
        cached = r.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


def llm_cache_set(messages, model_name, temperature, max_tokens, response, ttl=3600):
    """
    设置 LLM 缓存
    ttl: 缓存过期时间（秒），默认 1 小时
    """
    try:
        r = get_redis()
        key = make_cache_key('llc', messages, model_name, temperature, max_tokens)
        r.setex(key, ttl, json.dumps(response, ensure_ascii=False))
    except Exception:
        pass


def llm_cache_clear():
    """清除所有 LLM 缓存"""
    try:
        r = get_redis()
        keys = r.keys('llc:*')
        if keys:
            r.delete(*keys)
        return len(keys)
    except Exception:
        return 0


# ============================================================
# API 速率限制（Rate Limiting）
# ============================================================

def rate_limit_check(key, limit, window=60):
    """
    滑动窗口速率限制检查

    参数:
    - key: 限流键（如 IP + 路由）
    - limit: 窗口期内最大请求数
    - window: 窗口大小（秒）

    返回:
    - (allowed: bool, remaining: int, reset_in: int)
    """
    try:
        r = get_redis()
        now = time.time()
        window_key = f"rl:{key}"

        # 使用 Redis  pipeline 保证原子性
        pipe = r.pipeline()
        # 移除窗口外的请求记录
        pipe.zremrangebyscore(window_key, 0, now - window)
        # 添加当前请求
        pipe.zadd(window_key, {str(now): now})
        # 设置过期时间
        pipe.expire(window_key, window + 1)
        # 获取窗口内请求数
        pipe.zcard(window_key)
        results = pipe.execute()

        count = results[3]
        allowed = count <= limit
        remaining = max(0, limit - count)
        reset_in = window - int(now - (now % window))

        return allowed, remaining, reset_in
    except Exception:
        # Redis 不可用时放行
        return True, limit, 0


def rate_limit(limit=60, window=60, key_func=None):
    """
    速率限制装饰器

    参数:
    - limit: 窗口期内最大请求数
    - window: 窗口大小（秒）
    - key_func: 自定义限流键函数，默认使用 IP + 路由

    用法:
    @rate_limit(limit=30, window=60)
    def my_endpoint():
        ...
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # 生成限流键
            if key_func:
                key = key_func()
            else:
                ip = request.remote_addr or 'unknown'
                route = request.endpoint or request.path
                key = f"{ip}:{route}"

            allowed, remaining, reset_in = rate_limit_check(key, limit, window)

            if not allowed:
                response = jsonify(code=429, msg=f'请求过于频繁，请在 {reset_in} 秒后重试')
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset_in)
                return response

            # 执行原函数
            resp = f(*args, **kwargs)

            # 添加限流头
            if hasattr(resp, 'headers'):
                resp.headers['X-RateLimit-Limit'] = str(limit)
                resp.headers['X-RateLimit-Remaining'] = str(remaining)
                resp.headers['X-RateLimit-Reset'] = str(reset_in)
            return resp
        return wrapped
    return decorator


# ============================================================
# 通用缓存工具
# ============================================================

def cache_get(key):
    """获取缓存"""
    try:
        r = get_redis()
        val = r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


def cache_set(key, value, ttl=3600):
    """设置缓存"""
    try:
        r = get_redis()
        r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception:
        pass


def cache_delete(key):
    """删除缓存"""
    try:
        r = get_redis()
        r.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern):
    """按模式删除缓存"""
    try:
        r = get_redis()
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
        return len(keys)
    except Exception:
        return 0


# ============================================================
# 工作流执行状态缓存
# ============================================================

def workflow_state_save(run_id, state, ttl=3600):
    """保存工作流执行状态（用于 Human Input 暂停恢复）"""
    try:
        r = get_redis()
        key = f"wf:state:{run_id}"
        r.setex(key, ttl, json.dumps(state, ensure_ascii=False))
    except Exception:
        pass


def workflow_state_get(run_id):
    """获取工作流执行状态"""
    try:
        r = get_redis()
        key = f"wf:state:{run_id}"
        val = r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


def workflow_state_delete(run_id):
    """删除工作流执行状态"""
    try:
        r = get_redis()
        key = f"wf:state:{run_id}"
        r.delete(key)
    except Exception:
        pass

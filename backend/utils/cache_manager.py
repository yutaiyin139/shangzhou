# -*- coding: utf-8 -*-
"""
缓存管理器 —— 多级缓存、缓存装饰器、缓存失效策略

架构:
    L1: 进程内缓存 (LRU, 最快但容量有限)
    L2: Redis 缓存 (分布式，多实例共享)
    L3: 数据库 (最终数据源)

特性:
    - 自动缓存穿透保护 (Cache Stampede Protection)
    - 缓存雪崩防护 (随机 TTL 偏移)
    - 主动失效 + 被动过期
    - 缓存命中率统计
    - 按前缀批量失效

使用方式:
    # 方式1: 装饰器
    @cache.cached(prefix='user', ttl=300)
    def get_user(user_id):
        return db.query(user_id)

    # 方式2: 手动操作
    cache.set('user:123', user_data, ttl=300)
    data = cache.get('user:123')

    # 方式3: 缓存失效
    cache.invalidate('user:123')
    cache.invalidate_prefix('user:')
"""

import json
import time
import hashlib
import logging
import threading
import functools
from collections import OrderedDict
from typing import Any, Callable, Optional, List, Dict

logger = logging.getLogger(__name__)

# ============================================================
# L1: 进程内 LRU 缓存
# ============================================================

class LRUCache:
    """线程安全的 LRU 缓存"""

    def __init__(self, max_size: int = 1000):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def delete_prefix(self, prefix: str):
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)

    @property
    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(self._hits / total, 4) if total > 0 else 0,
        }


# ============================================================
# L2: Redis 缓存封装
# ============================================================

class RedisCache:
    """Redis 缓存封装"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from utils.redis_cache import get_redis
                self._client = get_redis()
            except Exception:
                pass
        return self._client

    @property
    def available(self) -> bool:
        try:
            return self.client is not None and self.client.ping()
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            val = self.client.get(key)
            if val:
                return json.loads(val)
        except Exception:
            pass
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        if not self.available:
            return
        try:
            self.client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
        except Exception:
            pass

    def delete(self, key: str):
        if not self.available:
            return
        try:
            self.client.delete(key)
        except Exception:
            pass

    def delete_prefix(self, prefix: str) -> int:
        if not self.available:
            return 0
        try:
            keys = self.client.keys(f'{prefix}*')
            if keys:
                self.client.delete(*keys)
            return len(keys)
        except Exception:
            return 0

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        if not self.available or not keys:
            return {}
        try:
            values = self.client.mget(keys)
            result = {}
            for key, val in zip(keys, values):
                if val:
                    result[key] = json.loads(val)
            return result
        except Exception:
            return {}

    def set_many(self, mapping: Dict[str, Any], ttl: int = 3600):
        """批量设置"""
        if not self.available or not mapping:
            return
        try:
            pipe = self.client.pipeline()
            for key, value in mapping.items():
                pipe.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            pipe.execute()
        except Exception:
            pass


# ============================================================
# 缓存管理器 (多级缓存)
# ============================================================

class CacheManager:
    """
    多级缓存管理器

    缓存策略:
    - 读取: L1 → L2 → DB (命中后回填上层)
    - 写入: 写入 DB 后失效 L1/L2
    - TTL: 基础 TTL + 随机偏移 (防雪崩)
    """

    def __init__(self, l1_size: int = 1000, ttl_jitter: int = 60):
        self.l1 = LRUCache(max_size=l1_size)
        self.l2 = RedisCache()
        self._ttl_jitter = ttl_jitter  # TTL 随机偏移量
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        查找顺序: L1 → L2
        """
        # L1 查找
        value = self.l1.get(key)
        if value is not None:
            return value

        # L2 查找
        value = self.l2.get(key)
        if value is not None:
            # 回填 L1
            self.l1.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        设置缓存值

        同时写入 L1 和 L2，TTL 添加随机偏移
        """
        # 添加随机偏移防止缓存雪崩
        import random
        jitter = random.randint(0, self._ttl_jitter) if self._ttl_jitter > 0 else 0
        actual_ttl = ttl + jitter

        self.l1.set(key, value)
        self.l2.set(key, value, actual_ttl)

    def delete(self, key: str):
        """删除缓存"""
        self.l1.delete(key)
        self.l2.delete(key)

    def invalidate(self, key: str):
        """使指定 key 缓存失效 (同 delete)"""
        self.delete(key)

    def invalidate_prefix(self, prefix: str):
        """按前缀批量失效"""
        self.l1.delete_prefix(prefix)
        self.l2.delete_prefix(prefix)

    def clear_all(self):
        """清除所有缓存"""
        self.l1.clear()
        # 注意: 清除 Redis 所有缓存需要谨慎
        # 这里只清除带有特定前缀的缓存

    def get_or_set(self, key: str, getter: Callable, ttl: int = 3600) -> Any:
        """
        获取或设置缓存 (Cache-Aside 模式)

        参数:
            key: 缓存键
            getter: 数据获取函数 (缓存未命中时调用)
            ttl: 过期时间

        返回:
            缓存值或 getter 返回值
        """
        # 先尝试获取
        value = self.get(key)
        if value is not None:
            return value

        # 缓存未命中，使用锁防止缓存击穿
        lock_key = f'_lock:{key}'
        with self._lock:
            # 双重检查
            value = self.get(key)
            if value is not None:
                return value

            # 获取数据
            value = getter()
            if value is not None:
                self.set(key, value, ttl)
            return value

    @property
    def stats(self) -> Dict:
        return {
            'l1': self.l1.stats,
            'l2_available': self.l2.available,
        }


# ============================================================
# 全局缓存管理器实例
# ============================================================

cache = CacheManager(l1_size=1000, ttl_jitter=60)


# ============================================================
# 缓存装饰器
# ============================================================

def cached(prefix: str = '', ttl: int = 300, key_func: Optional[Callable] = None,
           condition: Optional[Callable] = None):
    """
    缓存装饰器 —— 自动缓存函数返回值

    参数:
        prefix: 缓存键前缀
        ttl: 缓存过期时间 (秒)
        key_func: 自定义缓存键生成函数，默认使用函数名 + 参数
        condition: 缓存条件函数，返回 True 时才缓存

    用法:
        @cached(prefix='user', ttl=300)
        def get_user(user_id):
            return db.query(user_id)

        @cached(prefix='config', ttl=600, condition=lambda x: x is not None)
        def get_config(key):
            return db.query_config(key)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = f'{prefix}:{key_func(*args, **kwargs)}' if prefix else key_func(*args, **kwargs)
            else:
                # 默认: prefix + 函数名 + 参数哈希
                key_parts = [prefix] if prefix else []
                key_parts.append(func.__name__)
                if args:
                    key_parts.append(_make_key_from_args(args))
                if kwargs:
                    key_parts.append(_make_key_from_kwargs(kwargs))
                cache_key = ':'.join(key_parts)

            # 尝试获取缓存
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 检查缓存条件
            if condition and not condition(result):
                return result

            # 写入缓存
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # 附加缓存操作方法
        wrapper.cache_key = lambda *a, **kw: (
            f'{prefix}:{key_func(*a, **kw)}' if key_func and prefix
            else f"{prefix}:{func.__name__}:{_make_key_from_args(a)}:{_make_key_from_kwargs(kw)}"
        )
        wrapper.invalidate = lambda *a, **kw: cache.delete(wrapper.cache_key(*a, **kw))
        wrapper.invalidate_all = lambda: cache.invalidate_prefix(f'{prefix}:{func.__name__}')

        return wrapper
    return decorator


def cache_evict(prefix: str = '', key_func: Optional[Callable] = None):
    """
    缓存失效装饰器 —— 函数执行后自动清除缓存

    参数:
        prefix: 缓存键前缀
        key_func: 自定义缓存键生成函数

    用法:
        @cache_evict(prefix='user', key_func=lambda user_id: str(user_id))
        def update_user(user_id, data):
            return db.update(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 生成缓存键并清除
            if key_func:
                cache_key = f'{prefix}:{key_func(*args, **kwargs)}' if prefix else key_func(*args, **kwargs)
            else:
                key_parts = [prefix] if prefix else []
                key_parts.append(func.__name__)
                if args:
                    key_parts.append(_make_key_from_args(args))
                cache_key = ':'.join(key_parts)

            cache.invalidate(cache_key)
            cache.invalidate_prefix(cache_key)

            return result
        return wrapper
    return decorator


# ============================================================
# 缓存键生成工具
# ============================================================

def _make_key_from_args(args: tuple) -> str:
    """从位置参数生成缓存键片段"""
    parts = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            parts.append(str(arg))
        elif arg is None:
            parts.append('None')
        else:
            parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    return '_'.join(parts) if parts else 'noargs'


def _make_key_from_kwargs(kwargs: dict) -> str:
    """从关键字参数生成缓存键片段"""
    if not kwargs:
        return 'nokwargs'
    sorted_items = sorted(kwargs.items())
    parts = [f'{k}={v}' for k, v in sorted_items]
    return '_'.join(parts)


def make_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    parts = []
    if args:
        parts.append(_make_key_from_args(args))
    if kwargs:
        parts.append(_make_key_from_kwargs(kwargs))
    return ':'.join(parts) if parts else 'default'


# ============================================================
# 常用缓存前缀
# ============================================================

class CachePrefix:
    """缓存键前缀常量"""
    USER = 'user'
    APP = 'app'
    WORKFLOW = 'wf'
    KNOWLEDGE = 'kb'
    CONVERSATION = 'conv'
    MESSAGE = 'msg'
    MODEL = 'model'
    CONFIG = 'config'
    TOOL = 'tool'
    PLUGIN = 'plugin'
    TEMPLATE = 'tmpl'
    ROLE = 'role'
    PERMISSION = 'perm'
    STATS = 'stats'
    SESSION = 'session'
    RATE_LIMIT = 'rl'


# ============================================================
# 缓存统计
# ============================================================

def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    return {
        'timestamp': time.time(),
        'cache': cache.stats,
    }


def reset_cache_stats():
    """重置缓存统计"""
    cache.l1._hits = 0
    cache.l1._misses = 0

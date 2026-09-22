# -*- coding: utf-8 -*-
"""
登录失败锁定机制 —— 防暴力破解保护

功能：
1. 基于用户名的失败次数统计
2. 基于 IP 的失败次数统计
3. 渐进式锁定时间（5次→15分钟，10次→1小时，20次→24小时）
4. 自动解锁（锁定时间到期后自动恢复）
5. 管理员手动解锁
6. 锁定状态查询
7. Redis + 内存回退双模式

安全策略：
- 同一用户名 5 次失败 → 锁定 15 分钟
- 同一用户名 10 次失败 → 锁定 1 小时
- 同一用户名 20 次失败 → 锁定 24 小时
- 同一 IP 20 次失败 → 锁定 30 分钟
- 同一 IP 50 次失败 → 锁定 2 小时

依赖：redis (可选，无 Redis 时使用内存存储)
"""

import os
import time
import logging
from datetime import datetime, timedelta
from flask import request

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

# 登录锁定开关：默认启用安全控制，仅在显式设置 LOGIN_LOCKOUT_ENABLED=false 时禁用
# 生产环境必须保持启用！可通过环境变量 LOGIN_LOCKOUT_ENABLED=false 临时关闭（调试用）
LOGIN_LOCKOUT_ENABLED = os.environ.get('LOGIN_LOCKOUT_ENABLED', 'true').lower() not in ('false', '0', 'no')

# 兼容旧代码：TESTING_MODE 为 True 时禁用锁定（仅用于单元测试）
TESTING_MODE = not LOGIN_LOCKOUT_ENABLED

# 用户名失败阈值 → 锁定时间（秒）
USERNAME_LOCKOUT_THRESHOLDS = [
    (5, 15 * 60),      # 5 次失败 → 锁定 15 分钟
    (10, 60 * 60),     # 10 次失败 → 锁定 1 小时
    (20, 24 * 60 * 60), # 20 次失败 → 锁定 24 小时
]

# 默认锁定时间（未达到阈值时的默认值）
USERNAME_DEFAULT_LOCKOUT = 5 * 60  # 5 分钟

# IP 失败阈值 → 锁定时间（秒）
IP_LOCKOUT_THRESHOLDS = [
    (20, 30 * 60),     # 20 次失败 → 锁定 30 分钟
    (50, 2 * 60 * 60), # 50 次失败 → 锁定 2 小时
]

# 默认 IP 锁定时间
IP_DEFAULT_LOCKOUT = 10 * 60  # 10 分钟

# 统计时间窗口（秒）- 只统计此窗口内的失败次数
FAILURE_WINDOW = 30 * 60  # 30 分钟

# Redis key 前缀
REDIS_KEY_PREFIX = 'login_lockout:'
REDIS_USERNAME_PREFIX = REDIS_KEY_PREFIX + 'user:'
REDIS_IP_PREFIX = REDIS_KEY_PREFIX + 'ip:'
REDIS_LOCK_PREFIX = REDIS_KEY_PREFIX + 'lock:'


# ============================================================
# 内存存储（Redis 不可用时的回退）
# ============================================================

class _MemoryStore:
    """内存存储，用于 Redis 不可用时的回退"""

    def __init__(self):
        self._failures = {}  # key: [(timestamp, ...)]
        self._locks = {}     # key: unlock_timestamp

    def add_failure(self, key):
        """记录一次失败"""
        now = time.time()
        if key not in self._failures:
            self._failures[key] = []
        self._failures[key].append(now)
        # 清理过期记录
        cutoff = now - FAILURE_WINDOW
        self._failures[key] = [t for t in self._failures[key] if t > cutoff]

    def get_failure_count(self, key):
        """获取窗口期内的失败次数"""
        if key not in self._failures:
            return 0
        now = time.time()
        cutoff = now - FAILURE_WINDOW
        self._failures[key] = [t for t in self._failures[key] if t > cutoff]
        return len(self._failures[key])

    def set_lock(self, key, duration_seconds):
        """设置锁定"""
        self._locks[key] = time.time() + duration_seconds

    def is_locked(self, key):
        """检查是否被锁定"""
        if key not in self._locks:
            return False
        if time.time() > self._locks[key]:
            # 锁定已过期，清除
            del self._locks[key]
            return False
        return True

    def get_lock_remaining(self, key):
        """获取剩余锁定时间（秒）"""
        if key not in self._locks:
            return 0
        remaining = int(self._locks[key] - time.time())
        return max(0, remaining)

    def get_lock_expires(self, key):
        """获取锁定过期时间"""
        if key not in self._locks:
            return None
        return datetime.fromtimestamp(self._locks[key])

    def clear(self, key):
        """清除锁定和失败记录"""
        self._failures.pop(key, None)
        self._locks.pop(key, None)

    def clear_all(self):
        """清除所有记录"""
        self._failures.clear()
        self._locks.clear()


_memory_store = _MemoryStore()


# ============================================================
# Redis 存储
# ============================================================

def _get_redis():
    """获取 Redis 连接，失败返回 None"""
    try:
        from utils.redis_cache import get_redis_client
        return get_redis_client()
    except Exception:
        return None


def _redis_add_failure(key):
    """Redis: 记录一次失败"""
    r = _get_redis()
    if not r:
        return False
    try:
        now = time.time()
        pipe = r.pipeline()
        # 使用有序集合，score 为时间戳
        pipe.zadd(key, {str(now): now})
        # 清理过期记录
        cutoff = now - FAILURE_WINDOW
        pipe.zremrangebyscore(key, 0, cutoff)
        # 设置 key 过期时间
        pipe.expire(key, FAILURE_WINDOW + 60)
        pipe.execute()
        return True
    except Exception as e:
        logger.warning(f'Redis 记录失败次数异常: {e}')
        return False


def _redis_get_failure_count(key):
    """Redis: 获取窗口期内的失败次数"""
    r = _get_redis()
    if not r:
        return -1  # 表示 Redis 不可用
    try:
        now = time.time()
        cutoff = now - FAILURE_WINDOW
        # 清理过期记录
        r.zremrangebyscore(key, 0, cutoff)
        # 统计数量
        return r.zcard(key)
    except Exception as e:
        logger.warning(f'Redis 获取失败次数异常: {e}')
        return -1


def _redis_set_lock(key, duration_seconds):
    """Redis: 设置锁定"""
    r = _get_redis()
    if not r:
        return False
    try:
        r.setex(key, duration_seconds, str(time.time() + duration_seconds))
        return True
    except Exception as e:
        logger.warning(f'Redis 设置锁定异常: {e}')
        return False


def _redis_is_locked(key):
    """Redis: 检查是否被锁定"""
    r = _get_redis()
    if not r:
        return None  # 表示 Redis 不可用
    try:
        return r.exists(key) > 0
    except Exception as e:
        logger.warning(f'Redis 检查锁定异常: {e}')
        return None


def _redis_get_lock_remaining(key):
    """Redis: 获取剩余锁定时间（秒）"""
    r = _get_redis()
    if not r:
        return -1
    try:
        ttl = r.ttl(key)
        return max(0, ttl)
    except Exception:
        return -1


def _redis_get_lock_expires(key):
    """Redis: 获取锁定过期时间"""
    r = _get_redis()
    if not r:
        return None
    try:
        val = r.get(key)
        if val:
            return datetime.fromtimestamp(float(val))
        return None
    except Exception:
        return None


def _redis_clear(key):
    """Redis: 清除锁定和失败记录"""
    r = _get_redis()
    if not r:
        return False
    try:
        r.delete(key)
        return True
    except Exception:
        return False


# ============================================================
# 统一接口
# ============================================================

def _get_client_ip():
    """获取客户端真实 IP"""
    try:
        # 优先从代理头获取
        from flask import request
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP').strip()
        return request.remote_addr or 'unknown'
    except Exception:
        return 'unknown'


def record_login_failure(username='', ip=None):
    """
    记录一次登录失败

    参数:
        username: 用户名（可选）
        ip: IP 地址（可选，默认从 request 获取）
    """
    # 测试模式：跳过失败记录
    if TESTING_MODE:
        return

    if not ip:
        ip = _get_client_ip()

    # 记录用户名失败
    if username:
        key = f'{REDIS_USERNAME_PREFIX}{username}'
        if not _redis_add_failure(key):
            _memory_store.add_failure(key)

    # 记录 IP 失败
    if ip and ip != 'unknown':
        key = f'{REDIS_IP_PREFIX}{ip}'
        if not _redis_add_failure(key):
            _memory_store.add_failure(key)


def get_failure_count(username='', ip=None):
    """
    获取失败次数

    返回:
        dict: {username_count, ip_count}
    """
    if not ip:
        ip = _get_client_ip()

    username_count = 0
    ip_count = 0

    # 用户名失败次数
    if username:
        key = f'{REDIS_USERNAME_PREFIX}{username}'
        count = _redis_get_failure_count(key)
        if count == -1:
            count = _memory_store.get_failure_count(key)
        username_count = count

    # IP 失败次数
    if ip and ip != 'unknown':
        key = f'{REDIS_IP_PREFIX}{ip}'
        count = _redis_get_failure_count(key)
        if count == -1:
            count = _memory_store.get_failure_count(key)
        ip_count = count

    return {
        'username_count': username_count,
        'ip_count': ip_count,
    }


def is_account_locked(username='', ip=None):
    """
    检查账号是否被锁定

    返回:
        dict: {
            locked: bool,
            reason: str,  # 'username' / 'ip' / None
            remaining_seconds: int,
            expires_at: datetime or None,
            message: str
        }
    """
    if not ip:
        ip = _get_client_ip()

    # 检查用户名锁定
    if username:
        key = f'{REDIS_LOCK_PREFIX}user:{username}'
        locked = _redis_is_locked(key)
        if locked is None:
            locked = _memory_store.is_locked(key)
        if locked:
            remaining = _redis_get_lock_remaining(key)
            if remaining == -1:
                remaining = _memory_store.get_lock_remaining(key)
            expires = _redis_get_lock_expires(key)
            if expires is None:
                expires = _memory_store.get_lock_expires(key)
            return {
                'locked': True,
                'reason': 'username',
                'remaining_seconds': remaining,
                'expires_at': expires,
                'message': f'账号已被锁定，请 { _format_duration(remaining) } 后再试',
            }

    # 检查 IP 锁定
    if ip and ip != 'unknown':
        key = f'{REDIS_LOCK_PREFIX}ip:{ip}'
        locked = _redis_is_locked(key)
        if locked is None:
            locked = _memory_store.is_locked(key)
        if locked:
            remaining = _redis_get_lock_remaining(key)
            if remaining == -1:
                remaining = _memory_store.get_lock_remaining(key)
            expires = _redis_get_lock_expires(key)
            if expires is None:
                expires = _memory_store.get_lock_expires(key)
            return {
                'locked': True,
                'reason': 'ip',
                'remaining_seconds': remaining,
                'expires_at': expires,
                'message': f'当前 IP 已被锁定，请 { _format_duration(remaining) } 后再试',
            }

    return {
        'locked': False,
        'reason': None,
        'remaining_seconds': 0,
        'expires_at': None,
        'message': '',
    }


def _calculate_lockout_duration(attempts, thresholds, default):
    """
    根据失败次数计算锁定时间

    参数:
        attempts: 失败次数
        thresholds: [(阈值, 锁定时间), ...] 按阈值升序排列
        default: 默认锁定时间

    返回:
        int: 锁定时间（秒）
    """
    duration = default
    for threshold, lockout_time in thresholds:
        if attempts >= threshold:
            duration = lockout_time
    return duration


def lock_account(username='', ip=None):
    """
    根据失败次数自动锁定账号

    参数:
        username: 用户名
        ip: IP 地址

    返回:
        dict: 锁定结果
    """
    # 测试模式：跳过账号锁定
    if TESTING_MODE:
        return {'username_locked': False, 'ip_locked': False}

    if not ip:
        ip = _get_client_ip()

    result = {'username_locked': False, 'ip_locked': False}

    # 锁定用户名
    if username:
        key = f'{REDIS_LOCK_PREFIX}user:{username}'
        failures_key = f'{REDIS_USERNAME_PREFIX}{username}'
        count = _redis_get_failure_count(failures_key)
        if count == -1:
            count = _memory_store.get_failure_count(failures_key)
        duration = _calculate_lockout_duration(count, USERNAME_LOCKOUT_THRESHOLDS, USERNAME_DEFAULT_LOCKOUT)
        if not _redis_set_lock(key, duration):
            _memory_store.set_lock(key, duration)
        result['username_locked'] = True
        result['username_duration'] = duration
        result['username_attempts'] = count
        logger.warning(f'账号锁定: {username}, 失败次数: {count}, 锁定时间: {duration}秒')

    # 锁定 IP
    if ip and ip != 'unknown':
        key = f'{REDIS_LOCK_PREFIX}ip:{ip}'
        failures_key = f'{REDIS_IP_PREFIX}{ip}'
        count = _redis_get_failure_count(failures_key)
        if count == -1:
            count = _memory_store.get_failure_count(failures_key)
        duration = _calculate_lockout_duration(count, IP_LOCKOUT_THRESHOLDS, IP_DEFAULT_LOCKOUT)
        if not _redis_set_lock(key, duration):
            _memory_store.set_lock(key, duration)
        result['ip_locked'] = True
        result['ip_duration'] = duration
        result['ip_attempts'] = count
        logger.warning(f'IP 锁定: {ip}, 失败次数: {count}, 锁定时间: {duration}秒')

    return result


def unlock_account(username='', ip=None):
    """
    手动解锁账号（管理员使用）

    参数:
        username: 用户名（可选）
        ip: IP 地址（可选）

    返回:
        dict: 解锁结果
    """
    if not ip:
        ip = _get_client_ip()

    result = {'username_unlocked': False, 'ip_unlocked': False}

    # 解锁用户名
    if username:
        # 清除锁定
        key = f'{REDIS_LOCK_PREFIX}user:{username}'
        _redis_clear(key)
        _memory_store.clear(key)
        # 清除失败记录
        failures_key = f'{REDIS_USERNAME_PREFIX}{username}'
        _redis_clear(failures_key)
        _memory_store.clear(failures_key)
        result['username_unlocked'] = True
        logger.info(f'账号手动解锁: {username}')

    # 解锁 IP
    if ip and ip != 'unknown':
        key = f'{REDIS_LOCK_PREFIX}ip:{ip}'
        _redis_clear(key)
        _memory_store.clear(key)
        failures_key = f'{REDIS_IP_PREFIX}{ip}'
        _redis_clear(failures_key)
        _memory_store.clear(failures_key)
        result['ip_unlocked'] = True
        logger.info(f'IP 手动解锁: {ip}')

    return result


def get_lock_status(username='', ip=None):
    """
    获取锁定状态（用于管理页面）

    返回:
        dict: 锁定状态详情
    """
    if not ip:
        ip = _get_client_ip()

    result = {
        'username': {
            'locked': False,
            'failures': 0,
            'remaining_seconds': 0,
            'expires_at': None,
        },
        'ip': {
            'locked': False,
            'failures': 0,
            'remaining_seconds': 0,
            'expires_at': None,
        },
    }

    # 用户名状态
    if username:
        lock_key = f'{REDIS_LOCK_PREFIX}user:{username}'
        failures_key = f'{REDIS_USERNAME_PREFIX}{username}'

        locked = _redis_is_locked(lock_key)
        if locked is None:
            locked = _memory_store.is_locked(lock_key)

        remaining = _redis_get_lock_remaining(lock_key)
        if remaining == -1:
            remaining = _memory_store.get_lock_remaining(lock_key)

        expires = _redis_get_lock_expires(lock_key)
        if expires is None:
            expires = _memory_store.get_lock_expires(lock_key)

        count = _redis_get_failure_count(failures_key)
        if count == -1:
            count = _memory_store.get_failure_count(failures_key)

        result['username'] = {
            'locked': locked,
            'failures': count,
            'remaining_seconds': remaining,
            'expires_at': expires.strftime('%Y-%m-%d %H:%M:%S') if expires else None,
        }

    # IP 状态
    if ip and ip != 'unknown':
        lock_key = f'{REDIS_LOCK_PREFIX}ip:{ip}'
        failures_key = f'{REDIS_IP_PREFIX}{ip}'

        locked = _redis_is_locked(lock_key)
        if locked is None:
            locked = _memory_store.is_locked(lock_key)

        remaining = _redis_get_lock_remaining(lock_key)
        if remaining == -1:
            remaining = _memory_store.get_lock_remaining(lock_key)

        expires = _redis_get_lock_expires(lock_key)
        if expires is None:
            expires = _memory_store.get_lock_expires(lock_key)

        count = _redis_get_failure_count(failures_key)
        if count == -1:
            count = _memory_store.get_failure_count(failures_key)

        result['ip'] = {
            'locked': locked,
            'failures': count,
            'remaining_seconds': remaining,
            'expires_at': expires.strftime('%Y-%m-%d %H:%M:%S') if expires else None,
        }

    return result


def _format_duration(seconds):
    """格式化持续时间"""
    if seconds < 60:
        return f'{seconds}秒'
    elif seconds < 3600:
        minutes = seconds // 60
        return f'{minutes}分钟'
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f'{hours}小时{minutes}分钟'
        return f'{hours}小时'
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f'{days}天{hours}小时'
        return f'{days}天'


# ============================================================
# 登录保护装饰器
# ============================================================

def check_login_allowed(username='', ip=None):
    """
    检查是否允许登录

    返回:
        tuple: (allowed: bool, message: str)
    """
    # 测试模式：跳过登录安全检查
    if TESTING_MODE:
        return True, ''

    # 先检查是否已被锁定
    lock_status = is_account_locked(username, ip)
    if lock_status['locked']:
        return False, lock_status['message']

    return True, ''

# -*- coding: utf-8 -*-
"""工具函数"""

import hashlib
import binascii
import base64
import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def now():
    """当前时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


CURRENT_USER_ID = 1  # 未登录/无登录态时回退的模拟当前用户（前端登录后会传 uid）


def _safe_uid(v):
    """解析 uid 参数：缺省/非法时回退 CURRENT_USER_ID，避免畸形参数触发 500"""
    try:
        return int(v) if v else CURRENT_USER_ID
    except (TypeError, ValueError):
        return CURRENT_USER_ID


# ═══════════════════════════════════════════
#  密码工具（Argon2id 优先，PBKDF2-SHA256 兼容）
# ═══════════════════════════════════════════

# 密码格式标识
_PBKDF2_PREFIX = '$pbkdf2$'
_ARGON2_PREFIX = '$argon2id$'

# PBKDF2 参数（升级到 600000 次迭代，符合 OWASP 2023 推荐）
PBKDF2_ITERATIONS = 600000

# Argon2id 参数（OWASP 2023 推荐最低配置）
ARGON2_TIME_COST = 3        # 迭代次数
ARGON2_MEMORY_COST = 65536  # 64MB (in KiB)
ARGON2_PARALLELISM = 4      # 并行度
ARGON2_HASH_LEN = 32        # 输出哈希长度
ARGON2_SALT_LEN = 16        # 盐值长度


def _hash_password_pbkdf2(password, salt_bytes):
    """PBKDF2-SHA256 密码加密（600000 次迭代）"""
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, PBKDF2_ITERATIONS)
    return binascii.hexlify(dk)


def _hash_password_argon2(password, salt_bytes):
    """Argon2id 密码加密（推荐）"""
    try:
        import argon2
        from argon2.low_level import hash_secret_raw, Type

        # 使用 low-level API 直接控制参数
        raw_hash = hash_secret_raw(
            secret=password.encode('utf-8'),
            salt=salt_bytes,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )
        return raw_hash
    except ImportError:
        # argon2-cffi 未安装，回退到 PBKDF2
        logger.warning('argon2-cffi 未安装，回退到 PBKDF2-SHA256')
        return _hash_password_pbkdf2(password, salt_bytes)


def _generate_password(password, use_argon2=True):
    """
    生成密码对：(base64_salt, base64_password)

    Args:
        password: 明文密码
        use_argon2: 是否使用 Argon2id（默认 True）

    Returns:
        tuple: (salt_b64, pwd_b64)
    """
    salt = os.urandom(ARGON2_SALT_LEN)
    salt_b64 = base64.b64encode(salt).decode()

    if use_argon2:
        try:
            import argon2
            pwd_raw = _hash_password_argon2(password, salt)
            pwd_b64 = base64.b64encode(pwd_raw).decode()
            return salt_b64, pwd_b64
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f'Argon2id 失败，回退到 PBKDF2: {e}')

    # PBKDF2 回退
    pwd_raw = _hash_password_pbkdf2(password, salt)
    pwd_b64 = base64.b64encode(pwd_raw).decode()
    return salt_b64, pwd_b64


def _compare_password(password, password_b64, salt_b64):
    """
    校验密码（自动识别 Argon2id 和 PBKDF2 格式）

    兼容旧版 PBKDF2（10000 次迭代）和新版 Argon2id/PBKDF2（600000 次迭代）
    """
    if not password_b64 or not salt_b64:
        return False
    try:
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(password_b64)

        # 尝试 Argon2id（如果安装了 argon2-cffi）
        if len(salt) == ARGON2_SALT_LEN:
            try:
                import argon2
                from argon2.low_level import hash_secret_raw, Type

                new_hash = hash_secret_raw(
                    secret=password.encode('utf-8'),
                    salt=salt,
                    time_cost=ARGON2_TIME_COST,
                    memory_cost=ARGON2_MEMORY_COST,
                    parallelism=ARGON2_PARALLELISM,
                    hash_len=len(stored_hash),
                    type=Type.ID,
                )
                return new_hash == stored_hash
            except ImportError:
                pass
            except Exception:
                pass

        # 尝试新版 PBKDF2（600000 次迭代）
        new_hash = _hash_password_pbkdf2(password, salt)
        if new_hash == stored_hash:
            return True

        # 兼容旧版 PBKDF2（10000 次迭代）
        old_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 10000)
        return binascii.hexlify(old_hash) == stored_hash

    except Exception:
        return False


def _needs_rehash(password_b64, salt_b64):
    """
    检查密码是否需要重新哈希（升级到更强的算法）

    返回 True 如果：
    - 旧版 PBKDF2（10000 次迭代）
    - 盐值长度不是 16 字节
    """
    if not password_b64 or not salt_b64:
        return False
    try:
        salt = base64.b64decode(salt_b64)
        # 盐值长度不是标准 Argon2 盐值长度，说明是旧版
        if len(salt) != ARGON2_SALT_LEN:
            return True
        return False
    except Exception:
        return False


def _valid_password(password):
    """密码规则：至少 8 位且同时包含字母和数字"""
    return bool(re.match(r'^(?=.*[a-zA-Z])(?=.*\d).{8,}$', password or ''))


def _gen_appkey():
    """生成 AppKey"""
    return 'sk-' + binascii.hexlify(os.urandom(16)).decode()


def _gen_web_token():
    """生成 16 位 Web app 访问 token"""
    import random
    import string
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

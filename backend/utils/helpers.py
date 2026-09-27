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


def _safe_uid(v):
    """当前操作者的账号 id（dify_accounts.id，UUID 字符串）；**查不到身份就返回空串**。

    只有一种身份来源：登录 token 里的 user_id（由 utils/api_guard.py 校验后放进
    request.user）。客户端传来的 uid / owner_id 一律不看 —— 包括闸门处于 off/warn
    的时候：那时 request.user 不存在，结果就是 ''（拒绝或报错交给调用方），而不是
    “没人登录就采信调用方自报的 id”。留这条口子等于把“我是谁”交回给调用方，
    正是当初 ?uid=<别人的账号> 能读改他人资料的根因。

    参数 v 只在**非 HTTP 上下文**（脚本、Celery 任务、引擎内部调用）生效，
    用来显式指定身份；HTTP 请求里传什么都不认。

    为什么不再有 CURRENT_USER_ID = 1 兜底：那是“users.id 与 dify_accounts.id 是两个
    体系”时代的遗留物，那个整数已不对应任何真实账号，拿它兜底只会造出写进 owner
    列、谁也看不见的无主数据（不报错也不可见，最难查）。
    """
    try:
        from flask import has_request_context, request
        if has_request_context():
            user = getattr(request, 'user', None) or {}
            return str(user.get('user_id') or '').strip()
    except Exception:
        pass
    return str(v).strip() if v else ''


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

    分支判据用“存上去的哈希长度”而不是盐长度：_generate_password 无论走 argon2
    还是 PBKDF2 回退，用的都是同一个 16 字节盐，所以旧的 len(salt) == ARGON2_SALT_LEN
    判据恒为真；再叠上 argon2 分支里一个 `return new_hash == stored_hash`，结果只要
    argon2-cffi 可导入，所有 PBKDF2 存量密码都会在这里被直接判 False 而落不到下面的
    PBKDF2 尝试（实测 18 个账号里 9 个登不上）。本地长期能登录只是因为该包没装。
    argon2 原始输出 32 字节，PBKDF2 存的是 hexlify 后的 64 字节 ASCII，两者不会撞。
    """
    if not password_b64 or not salt_b64:
        return False
    try:
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(password_b64)

        # 1) Argon2id：只在存储形态确实是原始字节输出时才试，不匹配则继续往下走
        if len(stored_hash) == ARGON2_HASH_LEN:
            try:
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
                if new_hash == stored_hash:
                    return True
            except ImportError:
                pass
            except Exception:
                pass

        # 2) 新版 PBKDF2（600000 次迭代）
        new_hash = _hash_password_pbkdf2(password, salt)
        if new_hash == stored_hash:
            return True

        # 3) 兼容旧版 PBKDF2（10000 次迭代）
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


def _valid_email(email):
    """邮箱格式：必须有 @ 与带点的域。

    只判“非空”会放进 'yutaiyin' 这种串：库里真实出现过 email='yutaiyin'，
    而它是另一个账号的登录名 —— 登录按 `name = %s OR email = %s` 找人，
    两个体系一撞车就变成“密码对不上人”。同时这种邮箱永远收不到重置邮件。
    """
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', (email or '').strip()))


def _check_account_identity(cur, name, email, exclude_id=None):
    """账号名 / 邮箱的全库唯一性（包含交叉唯一）；返回中文错误串， None 表示可以建。

    为什么要管“A 的名字 == B 的邮箱”这种跨列重名：/api/login 用
    `WHERE name = %s OR email = %s` 一个条件找两种输入，只要某人的邮箱恰好
    等于另一人的账号名，输入那个串就会命中两行 —— 靠 ORDER BY 只能保证
    “优先账号名”，保证不了不会因此登错人。建号/改资料时拦下来比事后清洗便宜。

    判定范围：新名字/新邮箱不得与库里**任何**账号的 name 或 email 相同（两个列共用
    一个全局命名空间），exclude_id 用于改自己资料时不算上自己。
    """
    name = (name or '').strip()
    email = (email or '').strip().lower()
    if not name:
        return '账号名不能为空'
    if not email:
        return '邮箱不能为空'
    if not _valid_email(email):
        return '邮箱格式不对：' + (email[:40] or '(空)')
    sql = r'''
        SELECT id, name, email FROM dify_accounts
        WHERE (email IN (%s, %s) OR name IN (%s, %s))
          AND (%s IS NULL OR id <> %s)
        LIMIT 1
    '''
    cur.execute(sql, (email, name, email, name, exclude_id, exclude_id))
    hit = cur.fetchone()
    if not hit:
        return None
    other_id = str(hit['id'])
    if exclude_id and other_id == str(exclude_id):
        return None
    if str(hit.get('name') or '') == name:
        return '账号名已被使用'
    if str(hit.get('email') or '').lower() == email:
        return '邮箱已被使用'
    # 走到这里就是“你的账号名是别人的邮箱”或反过来
    return '账号名与已有邮箱重复（登录时无法区分两个人），请换一个'


def _gen_appkey():
    """生成 AppKey"""
    return 'sk-' + binascii.hexlify(os.urandom(16)).decode()


def _gen_web_token():
    """生成 16 位 Web app 访问 token"""
    import random
    import string
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

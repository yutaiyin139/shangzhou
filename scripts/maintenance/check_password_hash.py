# -*- coding: utf-8 -*-
"""密码哈希可验证性体检（只读，不写库、不打印任何明文或哈希值）。

为什么需要它：_compare_password 靠 len(salt) == ARGON2_SALT_LEN 判断走 argon2 分支，
而 _generate_password 无论走 argon2 还是 PBKDF2 回退，用的都是同一个 16 字节盐 —— 也就是
这个判据恒为真。于是 argon2 分支里 `return new_hash == stored_hash` 会在不匹配时直接返回
False，永远落不到下面的 PBKDF2 尝试。后果：**只要 argon2-cffi 可导入，所有 PBKDF2 存量
密码都无法登录**。本地长期能登录只是因为该包没装（ImportError 才穿透），属于运气。

    python scripts/maintenance/check_password_hash.py

判读：
  [PASS] 全部账号可被正确验证，且格式与算法分支一致
  [FAIL] 列出会被误判的账号数与格式统计（不输出敏感值）
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from config import get_db  # noqa: E402
from utils.helpers import _compare_password, _generate_password  # noqa: E402


def classify(stored_bytes):
    """按存的字节判断是哪种格式；只看形态，不看内容。"""
    n = len(stored_bytes)
    if n == 32:
        return 'argon2_raw32'
    if n == 64:
        try:
            text = stored_bytes.decode('ascii')
        except (UnicodeDecodeError, AttributeError):
            return 'unknown(64)'
        if text and all(ch in '0123456789abcdef' for ch in text):
            return 'pbkdf2_hex64'
    return 'unknown(%d)' % n


def main():
    try:
        import argon2  # noqa: F401
        argon2_importable = True
    except Exception:
        argon2_importable = False

    print('argon2-cffi 可导入 : %s' % argon2_importable)

    # 先做与库无关的往返自证：这才是决定性证据，且不会碰到任何真实凭据
    probe = 'Zz-Probe@2026'
    salt_b64, hash_b64 = _generate_password(probe, use_argon2=False)
    pbkdf2_ok = _compare_password(probe, hash_b64, salt_b64)
    salt_b64b, hash_b64b = _generate_password(probe, use_argon2=True)
    argon2_ok = _compare_password(probe, hash_b64b, salt_b64b)
    print('PBKDF2 往返可验证  : %s' % ('[PASS]' if pbkdf2_ok else '[FAIL]'))
    print('Argon2 往返可验证  : %s' % ('[PASS]' if argon2_ok else '[FAIL]'))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, password, password_salt, status FROM dify_accounts")
    rows = cur.fetchall()
    db.close()

    stats = {}
    unverifiable = []
    argon2_blocked = []
    for r in rows:
        pwd_b64 = r.get('password') or ''
        salt_b64 = r.get('password_salt') or ''
        if not pwd_b64 or not salt_b64:
            stats['no-password'] = stats.get('no-password', 0) + 1
            continue
        try:
            salt = base64.b64decode(salt_b64)
            stored = base64.b64decode(pwd_b64)
        except Exception:
            stats['undecodable'] = stats.get('undecodable', 0) + 1
            continue
        fmt = classify(stored)
        stats['%s/salt=%d' % (fmt, len(salt))] = stats.get('%s/salt=%d' % (fmt, len(salt)), 0) + 1
        # 按“当前 _compare_password 到底会试哪些格式”判，而不是照旧 bug 的模式猜：
        #   argon2_raw32 → 靠 argon2 分支（包没装就验不了）
        #   pbkdf2_hex64 → 靠新旧两轮 PBKDF2（不依赖额外包）
        #   其他长度     → 三种算法的输出的形状都对不上，无法登录，只能重置密码
        name = str(r.get('name') or r['id'])
        if fmt == 'argon2_raw32' and not argon2_importable:
            argon2_blocked.append(name)
        elif fmt not in ('argon2_raw32', 'pbkdf2_hex64'):
            unverifiable.append('%s(%s)' % (name, fmt))

    print('账号总数           : %d' % len(rows))
    for k in sorted(stats):
        print('   %-28s %d' % (k, stats[k]))

    print('\n=== 结论 ===')
    problems = []
    if not pbkdf2_ok:
        problems.append('PBKDF2 往返自证失败：新写入的 PBKDF2 密码当场就验不过')
    if not argon2_ok and argon2_importable:
        problems.append('Argon2 往返自证失败：参数或依赖有问题')
    if argon2_blocked:
        problems.append('argon2-cffi 未安装，但有 %d 个账号的哈希是 argon2 格式（这些账号登不上）：%s'
                        % (len(argon2_blocked), ', '.join(argon2_blocked[:6])))
    if unverifiable:
        problems.append('%d 个账号的存量哈希形状不属于任何已知算法，无法登录，需管理员重置密码：%s'
                        % (len(unverifiable), ', '.join(unverifiable[:6])))
    if problems:
        for p in problems:
            print('  [X] ' + p)
        return 1
    print('  [OK] 两种格式均可被验证，没有形状不认识的存量哈希')
    return 0


if __name__ == '__main__':
    sys.exit(main())

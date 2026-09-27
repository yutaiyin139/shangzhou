# -*- coding: utf-8 -*-
"""密码哈希向后兼容回归。

起因：_compare_password 用 len(salt) == ARGON2_SALT_LEN 决定走不走 argon2 分支，但
_generate_password 两种算法都用同一个 16 字节盐，于是该判据恒真；argon2 分支里又是
`return new_hash == stored_hash`，只要 argon2-cffi 可导入，所有 PBKDF2 存量密码都会被
当场判为验证失败（本机实测 18 个账号里 9 个登不上，含真实账号）。这个缺陷长期没暴露，
只是因为开发机恰好没装 argon2-cffi —— 依赖装不齐 = 安全代码路径没被走过。

这些用例故意不依赖 argon2 是否安装：PBKDF2 那几条在没有 argon2 的环境里也必须通过，
这样无论 CI 机器装没装，算法回退链都被覆盖。
"""
import base64
import binascii
import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import argon2  # noqa: F401
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False

from utils.helpers import (_compare_password, _generate_password,  # noqa: E402
                           ARGON2_SALT_LEN, PBKDF2_ITERATIONS)

SECRET = 'Regression@2026'


class TestPasswordHashCompat(unittest.TestCase):

    def test_pbkdf2_record_verifies(self):
        """关键用例：PBKDF2 记录必须能验证通过。

        回归的就是"argon2 可导入时 PBKDF2 被提前判 False"这个缺陷。若 argon2 没装，
        这条走的是回退链，同样有意义。
        """
        salt_b64, hash_b64 = _generate_password(SECRET, use_argon2=False)
        self.assertTrue(_compare_password(SECRET, hash_b64, salt_b64),
                        'PBKDF2 存量密码无法验证 —— 用户会被挡在登录页外')
        self.assertFalse(_compare_password(SECRET + 'x', hash_b64, salt_b64))

    def test_pbkdf2_stored_shape_is_hex64(self):
        """钉住格式判据的依据：PBKDF2 存的是 64 字节 hex，不是 32 字节原始输出。

        _compare_password 现在靠哈希长度分分支，所以这个形状假设一旦变化，分支就会失效。
        """
        salt_b64, hash_b64 = _generate_password(SECRET, use_argon2=False)
        self.assertEqual(len(base64.b64decode(hash_b64)), 64)
        self.assertEqual(len(base64.b64decode(salt_b64)), ARGON2_SALT_LEN)

    @unittest.skipUnless(HAS_ARGON2, 'argon2-cffi 未安装')
    def test_argon2_record_verifies(self):
        salt_b64, hash_b64 = _generate_password(SECRET, use_argon2=True)
        self.assertEqual(len(base64.b64decode(hash_b64)), 32)
        self.assertTrue(_compare_password(SECRET, hash_b64, salt_b64))
        self.assertFalse(_compare_password('Wrong@2026x', hash_b64, salt_b64))

    def test_legacy_low_iteration_pbkdf2_verifies(self):
        """手工造一条 10000 次迭代的旧记录，确认兼容分支还在生效。"""
        salt = os.urandom(ARGON2_SALT_LEN)
        old = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', SECRET.encode('utf-8'), salt, 10000))
        self.assertTrue(_compare_password(
            SECRET, base64.b64encode(old).decode(), base64.b64encode(salt).decode()))

    def test_new_pbkdf2_uses_current_iteration_count(self):
        """同一条新记录不该被"旧迭代次数"分支命中——防止两轮尝试互相冒充。"""
        salt = os.urandom(ARGON2_SALT_LEN)
        stale_old = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', SECRET.encode('utf-8'), salt, 10000))
        current = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', SECRET.encode('utf-8'), salt, PBKDF2_ITERATIONS))
        self.assertNotEqual(stale_old, current)
        self.assertTrue(_compare_password(
            SECRET, base64.b64encode(current).decode(), base64.b64encode(salt).decode()))

    def test_empty_inputs_do_not_raise(self):
        for salt, pwd in (('', ''), ('abc', ''), ('', 'abc')):
            self.assertFalse(_compare_password(SECRET, pwd, salt))


if __name__ == '__main__':
    unittest.main(verbosity=2)

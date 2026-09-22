# -*- coding: utf-8 -*-
"""
P0 注册管控确定性回归（V1.0 发布前安全项）：

覆盖 routes/auth.py 的 _get_register_policy —— 它是 /api/register 拦截与
/api/register-config 输出的唯一真相来源：
  - allow_register：管理员开关；'0'/'false'/'off' 关闭，缺省/异常回退开放。
  - register_invite_code：非空则注册必须携带匹配邀请码；为空则不要求。
  - 邀请码匹配为路由内字符串相等比较（本测试断言策略能正确带出邀请码原文）。

特点：直接调用引擎函数 + 操作 system_settings 表，无需 HTTP、无需登录，
自建隔离数据并在 tearDown 精确还原，可反复运行。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db
from routes.auth import _get_register_policy

KEY_ALLOW = 'allow_register'
KEY_INVITE = 'register_invite_code'


def _fetchall(sql, params=None):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        db.close()


def _exec(sql, params=None):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql, params or ())
        db.commit()
        return cur.rowcount
    finally:
        db.close()


def _set_setting(key, value):
    _exec(
        "INSERT INTO system_settings (`key`, `value`) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
        (key, value),
    )


def _del_setting(key):
    _exec("DELETE FROM system_settings WHERE `key` = %s", (key,))


def _read_setting(key):
    rows = _fetchall("SELECT `value` FROM system_settings WHERE `key` = %s", (key,))
    return rows[0]['value'] if rows else None


def _policy():
    """用独立连接读取当前注册策略（等价于路由内的调用方式）。"""
    db = get_db()
    try:
        return _get_register_policy(db.cursor())
    finally:
        db.close()


class TestRegisterControl(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 快照既有值以便还原，避免污染真实环境
        cls._snap_allow = _read_setting(KEY_ALLOW)
        cls._snap_invite = _read_setting(KEY_INVITE)

    @classmethod
    def tearDownClass(cls):
        for key, snap in ((KEY_ALLOW, cls._snap_allow), (KEY_INVITE, cls._snap_invite)):
            _del_setting(key)
            if snap is not None:
                _set_setting(key, snap)

    def setUp(self):
        # 每个用例从干净状态开始
        _del_setting(KEY_ALLOW)
        _del_setting(KEY_INVITE)

    # ---------- allow_register 开关 ----------

    def test_01_default_open_when_unset(self):
        """两键均缺省 → 默认开放、无邀请码（与历史行为一致，向后兼容）。"""
        allow, invite = _policy()
        self.assertTrue(allow)
        self.assertEqual(invite, '')

    def test_02_open_when_flag_is_1(self):
        _set_setting(KEY_ALLOW, '1')
        allow, invite = _policy()
        self.assertTrue(allow)
        self.assertEqual(invite, '')

    def test_03_closed_when_flag_is_0(self):
        _set_setting(KEY_ALLOW, '0')
        allow, invite = _policy()
        self.assertFalse(allow)

    def test_04_closed_accepts_false_and_off(self):
        for token in ('false', 'off'):
            _set_setting(KEY_ALLOW, token)
            allow, _ = _policy()
            self.assertFalse(allow, msg='%s 应视为关闭' % token)

    # ---------- 邀请码 ----------

    def test_05_invite_code_carried_when_set(self):
        _set_setting(KEY_ALLOW, '1')
        _set_setting(KEY_INVITE, 'SHANGZHOU-2026')
        allow, invite = _policy()
        self.assertTrue(allow)
        self.assertEqual(invite, 'SHANGZHOU-2026')

    def test_06_blank_invite_code_means_not_required(self):
        """邀请码为空白 → 归一化为不要求（strip 后为空串）。"""
        _set_setting(KEY_INVITE, '   ')
        allow, invite = _policy()
        self.assertTrue(allow)
        self.assertEqual(invite, '')

    def test_07_closed_takes_precedence_over_invite(self):
        """注册关闭时，即便设了邀请码，路由也会先按 403 拦截（allow=False）。"""
        _set_setting(KEY_ALLOW, '0')
        _set_setting(KEY_INVITE, 'XYZ')
        allow, invite = _policy()
        self.assertFalse(allow)
        self.assertEqual(invite, 'XYZ')

    def test_08_required_invite_matches_route_equality(self):
        """复算路由内的相等判定：携带码==配置码 放行，否则拒绝。"""
        _set_setting(KEY_INVITE, 'SECRET-42')
        _, required = _policy()
        self.assertTrue(bool(required))  # require_invite_code 应为 True
        self.assertEqual('SECRET-42'.strip(), required)          # 正确邀请码
        self.assertNotEqual('wrong'.strip(), required)           # 错误邀请码
        self.assertNotEqual(''.strip(), required)                # 缺失邀请码


if __name__ == '__main__':
    unittest.main(verbosity=2)

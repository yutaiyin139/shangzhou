# -*- coding: utf-8 -*-
"""账号唯一真相源 = dify_accounts 的回归钉子。

users 表已合并进 dify_accounts 并删除。这个文件钉住"彻底解决"后的几条不变量，
任何一条被改回去都会在真实环境里造成账号接管级问题：

  1) 身份只来自登录 token：客户端传 ?uid= / body.uid / owner_id 一律不认。
  2) 权限级别只认角色名 == 'admin'：不再用 '管理员' in role_name 这种子串猜测
     （roles 表里遗留的"业务管理员"曾因此被静默提成 admin）。
  3) 刷新 Token 会从库里恢复身份（旧代码查 dify_accounts.role —— 没有这一列，
     语句每次报错走异常分支，"从库里恢复"这条路从未生效）；被禁账号不能续命。
  4) 建号/改资料守"账号名与邮箱全库交叉唯一"+ 邮箱格式：
     登录是 WHERE name=? OR email=?，一个条件找两种输入，撞车就会登错人。
  5) 用户/角色管理面只对管理员开放，而且判定实时查库（不信旧令牌里的 role）。
  6) 通知收件箱只认 token：?uid= 与 body.user_id 都不能把别人的收件箱指过来。

跑法：cd backend && python -m pytest tests/test_account_identity_single_source.py -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db  # noqa: E402


def _fetchall(sql, args=None):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql, args or ())
        return cur.fetchall()
    finally:
        db.close()


def _exec(sql, args=None):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(sql, args or ())
        db.commit()
        return cur.rowcount
    finally:
        db.close()


def _build_app():
    from app import app as _app
    _app.config['TESTING'] = True
    # 这几条用例测的就是"闸门关掉之后还有没有第二套身份定义"，
    # 所以必须显式打开 strict，否则测的是不真实的宽松模式
    _app.config['REQUIRE_LOGIN_FOR_API'] = 'strict'
    _app.config['OWNERSHIP_CHECK_MODE'] = 'strict'
    return _app


class TestIdentitySingleSource(unittest.TestCase):
    """身份与角色只能有一个出处"""

    @classmethod
    def setUpClass(cls):
        cls.app = _build_app()
        cls.client = cls.app.test_client()
        cls.accounts = _fetchall(
            "SELECT id, name, email, status FROM dify_accounts "
            "WHERE status = 'active' ORDER BY created_at")
        if not cls.accounts:
            raise unittest.SkipTest('库里没有可用账号，无法验证身份链路')

    def _token(self, acc, role='user'):
        from utils.auth import generate_token_pair
        return generate_token_pair(user_id=str(acc['id']), email=acc['email'] or '',
                                   username=acc['name'] or '', role=role)['access_token']

    def test_01_client_uid_is_ignored(self):
        """带上别人的 uid，也只能看到自己的账户信息"""
        me = self.accounts[0]
        other = next((a for a in self.accounts if a['id'] != me['id']), None)
        if not other:
            self.skipTest('库里只有一个账号，无法构造越权用例')
        headers = {'Authorization': 'Bearer ' + self._token(me, role='admin')}
        resp = self.client.get('/api/account?uid=%s' % other['id'], headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = (resp.get_json() or {}).get('data') or {}
        self.assertEqual(str(data.get('id')), str(me['id']),
                         '?uid= 被别人账号顶掉过：越权读他人资料（账号接管入口）')
        self.assertEqual(data.get('email'), me['email'])

    def test_02_no_token_is_rejected(self):
        """strict 闸门下不带 token 一律 401（不再有裸接口回真实数据）"""
        resp = self.client.get('/api/account')
        self.assertEqual(resp.status_code, 401)
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 401)

    def test_03_create_agent_ignores_body_uid(self):
        """创建智能体时 body.uid 不认，owner 只能是 token 里的账号"""
        me = self.accounts[0]
        other = next((a for a in self.accounts if a['id'] != me['id']), None)
        headers = {'Authorization': 'Bearer ' + self._token(me, role='admin')}
        import uuid as _uuid
        name = 'itest_%s' % _uuid.uuid4().hex[:8]
        resp = self.client.post('/api/agents', json={
            'name': name, 'role': '', 'description': '',
            'uid': other['id'] if other else '1'}, headers=headers)
        self.assertEqual(resp.status_code, 200, (resp.get_json() or {}).get('msg'))
        rows = _fetchall("SELECT owner FROM agents WHERE name = %s", (name,))
        _exec("DELETE FROM agents WHERE name = %s", (name,))
        self.assertTrue(rows)
        self.assertEqual(str(rows[0]['owner']), str(me['id']),
                         'owner 写成客户端给的 uid = 可以把资源塞进别人名下')

    def test_04_role_level_only_exact_admin(self):
        """'业务管理员' 这类遗留中文角色不得被提成 admin"""
        from utils.auth import get_account_role
        for acc in self.accounts:
            info = get_account_role(acc['id'])
            names = info['role_name']
            self.assertIn(info['level'], ('admin', 'user'))
            exact_admin = any(n.strip() == 'admin' for n in names.split(','))
            self.assertEqual(info['level'] == 'admin', exact_admin,
                             '%s 角色=%r 却被判成 %s' % (acc['name'], names, info['level']))
            if '管理员' in names and not exact_admin:
                self.assertEqual(info['level'], 'user',
                                 '遗留中文角色按子串被提成 admin（静默越权）')

    def test_05_get_account_role_is_deterministic(self):
        """同一账号重复查询角色结果一致（多角色时不能随机命中）"""
        from utils.auth import get_account_role
        acc = self.accounts[0]
        first = get_account_role(acc['id'])
        for _ in range(3):
            self.assertEqual(get_account_role(acc['id']), first)


class TestRefreshRestoresIdentity(unittest.TestCase):
    """刷新 Token 必须真的从库里恢复身份"""

    def test_01_dify_accounts_has_no_role_column(self):
        """旧写法 SELECT id,name,email,role FROM dify_accounts 是必报错的（本用例钉住原因）"""
        cols = {r['COLUMN_NAME'] for r in _fetchall(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'dify_accounts'")}
        self.assertNotIn('role', cols,
                         'dify_accounts 若真有了 role 列，就要同步改 utils/auth._get_user_by_id')
        self.assertIn('status', cols)

    def test_02_refresh_recovers_current_role_from_db(self):
        """角色变了，刷新后新 token 要带上新的 role"""
        from utils.auth import generate_token_pair, refresh_access_token
        acc = _fetchall("SELECT id, name, email FROM dify_accounts "
                        "WHERE status = 'active' ORDER BY created_at LIMIT 1")
        if not acc:
            self.skipTest('库里没有可用账号')
        acc = acc[0]
        tokens = generate_token_pair(user_id=str(acc['id']), email=acc['email'] or '',
                                    username=acc['name'] or '', role='user')
        new_pair, err = refresh_access_token(tokens['refresh_token'])
        self.assertIsNone(err, err)
        import jwt
        from utils.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(new_pair['access_token'], SECRET_KEY, algorithms=[ALGORITHM])
        expected = 'admin' if any(
            r['name'] == 'admin' for r in _fetchall(
                "SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id "
                "WHERE ur.user_id = %s", (acc['id'],))) else 'user'
        self.assertEqual(payload.get('role'), expected,
                         '刷新时没有从库里重读角色（旧实现每次都异常回退到旧声明）')

    def test_03_banned_account_cannot_refresh(self):
        """被禁账号不能靠 refresh token 无限续命"""
        from utils.auth import refresh_access_token, generate_token_pair
        tmp_id = '00000000-0000-4000-8000-000000000001'
        _exec("INSERT INTO dify_accounts (id, name, email, status) VALUES (%s, %s, %s, 'banned')",
              (tmp_id, 'itest_banned_%s' % tmp_id[-6:], 'itest-banned_%s@itest.com' % tmp_id[-6:]))
        try:
            tokens = generate_token_pair(user_id=tmp_id, email='', username='', role='admin')
            pair, err = refresh_access_token(tokens['refresh_token'])
            self.assertIsNone(pair, '被禁账号仍然刷新出了新 token')
            self.assertTrue(err)
        finally:
            _exec("DELETE FROM dify_accounts WHERE id = %s", (tmp_id,))


class TestAccountIdentityUniqueness(unittest.TestCase):
    """账号名与邮箱的全库交叉唯一 + 邮箱格式"""

    @classmethod
    def setUpClass(cls):
        cls.accounts = _fetchall(
            "SELECT id, name, email FROM dify_accounts WHERE status = 'active' ORDER BY created_at")

    def test_01_existing_data_has_no_cross_collision(self):
        """库里现存数据本身必须先满足不变量，否则"防再生"是空话"""
        names = {str(a['name'] or '').strip().lower() for a in self.accounts}
        emails = {str(a['email'] or '').strip().lower() for a in self.accounts}
        self.assertEqual(len(names), len(self.accounts), '存在重名账号：列表/登录都会歧义')
        self.assertEqual(len(emails), len(self.accounts), '存在重复邮箱：忘记密码会寻址到多人')
        overlap = names & emails
        self.assertFalse(overlap,
                         '这些值既是某人的账号名又是另一人的邮箱：%s（登录会命中两行）' % overlap)

    def test_02_invalid_email_shape_rejected(self):
        from utils.helpers import _valid_email
        self.assertFalse(_valid_email('yutaiyin'))
        self.assertFalse(_valid_email(''))
        self.assertFalse(_valid_email('a@b'))
        self.assertTrue(_valid_email('a@b.co'))

    def test_03_check_account_identity_blocks_cross_collision(self):
        from utils.helpers import _check_account_identity
        if not self.accounts:
            self.skipTest('库里没有账号')
        db = get_db()
        try:
            cur = db.cursor()
            me = self.accounts[0]
            # 自己的名字/邮箱配自己 -> 放行
            self.assertIsNone(_check_account_identity(cur, me['name'], me['email'],
                                                      exclude_id=me['id']))
            # 用别人的邮箱当账号名 -> 拒绝
            other = next((a for a in self.accounts if a['id'] != me['id']), None)
            if other:
                err = _check_account_identity(cur, other['email'], 'brand-new-%s@itest.com'
                                              % other['id'][:8])
                self.assertTrue(err, '账号名撞别人邮箱没有被拦下')
            # 非法邮箱格式 -> 拒绝
            self.assertTrue(_check_account_identity(cur, 'itest_shape_ok', 'not-an-email'))
        finally:
            db.close()


class TestPlatformAdminSurface(unittest.TestCase):
    """用户 / 角色管理面只认管理员，而且以**库里的角色**为准。

    补测缘由：这组接口以前只被集中闸门挡了一道（= 任何登录用户可用）。
    对真实后端打请求实测：普通用户 GET /api/users 能直接拉到全体账号的邮箱 + 手机号，
    而 POST /api/users 可以建一个 role=admin 的号、PUT /api/users/<id> 可以改任何人密码、
    PUT /api/users/<id>/roles 可以给自己加权 —— 账号接管与提权一条路走完。
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _build_app()
        cls.client = cls.app.test_client()
        from utils.auth import get_account_role
        acts = _fetchall("SELECT id, name, email FROM dify_accounts "
                         "WHERE status = 'active' ORDER BY created_at")
        cls.admin = cls.plain = None
        for a in acts:
            if get_account_role(a['id'])['level'] == 'admin':
                cls.admin = cls.admin or a
            else:
                cls.plain = cls.plain or a
        if not (cls.admin and cls.plain):
            raise unittest.SkipTest('库里缺一个管理员账号或一个普通账号，无法构造对照')

    def _hdr(self, acc, role='admin'):
        """故意把令牌载荷签成 admin：判据必须是库里的角色，不是调用方自带的声明"""
        from utils.auth import generate_token_pair
        return {'Authorization': 'Bearer ' + generate_token_pair(
            user_id=str(acc['id']), email=acc['email'] or '',
            username=acc['name'] or '', role=role)['access_token']}

    def test_01_non_admin_is_locked_out(self):
        h = self._hdr(self.plain)
        resp = self.client.get('/api/users', headers=h)
        self.assertEqual(resp.status_code, 403, '普通用户读到了全体账号的 PII')
        self.assertIn('管理员', str((resp.get_json() or {}).get('msg') or ''))
        for method, path, payload in (
                ('post', '/api/users', {'username': 'itest_hacker', 'password': 'Abcd1234',
                                        'email': 'itest-hacker@itest.com', 'role': 'admin'}),
                ('put', '/api/users/%s' % self.admin['id'], {'phone': 'ITEST-PROBE'}),
                ('put', '/api/users/%s/roles' % self.plain['id'], {'role': 'admin'}),
                ('post', '/api/roles', {'name': 'itest_role'}),
                ('put', '/api/roles/999999', {'name': 'itest_renamed'}),
                ('delete', '/api/roles/999999', None),
                ('put', '/api/roles/999999/permissions', {'permission_ids': []}),
        ):
            send = getattr(self.client, method)
            resp = send(path, json=payload, headers=h) if payload is not None else send(path, headers=h)
            self.assertEqual(resp.status_code, 403,
                             '%s %s 没被管理员校验拦住' % (method.upper(), path))
        # 被拦下就一定不能留下痕迹：拿不存在的角色号做写操作，回归时也不会真改到数据
        self.assertFalse(_fetchall("SELECT id FROM dify_accounts WHERE name = %s", ('itest_hacker',)))
        self.assertFalse(_fetchall("SELECT id FROM roles WHERE name LIKE 'itest%%'"))
        phone = _fetchall('SELECT phone FROM dify_accounts WHERE id = %s', (self.admin['id'],))[0]['phone']
        self.assertNotEqual(str(phone), 'ITEST-PROBE', '普通用户改掉了管理员的手机号')
        roles_now = [r['name'] for r in _fetchall(
            'SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = %s',
            (self.plain['id'],))]
        self.assertNotIn('admin', roles_now, '普通用户给自己提了权')

    def test_02_admin_still_can_use_the_surface(self):
        """不误伤：管理员（库里角色真的是 admin）读用户列表与角色表必须 200"""
        h = self._hdr(self.admin)
        resp = self.client.get('/api/users', headers=h)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue((resp.get_json() or {}).get('data'))
        resp = self.client.get('/api/roles', headers=h)
        self.assertEqual(resp.status_code, 200)

    def test_03_anonymous_is_rejected(self):
        for method, path in (('get', '/api/users'), ('post', '/api/users'), ('post', '/api/roles')):
            resp = getattr(self.client, method)(path, json={})
            self.assertEqual(resp.status_code, 401, '%s 匿名可访' % path)

    def test_04_reference_reads_stay_open_to_logged_in_users(self):
        """只收紧“全体账号 PII 的读”与“所有写”，不顺手锁掉业务页面要用的角色下拉"""
        resp = self.client.get('/api/roles', headers=self._hdr(self.plain, role='user'))
        self.assertEqual(resp.status_code, 200)


class TestNotificationInboxIsolation(unittest.TestCase):
    """通知中心只认 token：?uid= / body.user_id 都不能把收件箱指到别人名下。

    改之前这里读的是 getattr(g,'user_id') + ?uid= 回退：全仓从未写过 g.user_id，
    而 ?uid= 是调用方填的 —— 等于任何人能读/改别人的通知。"""

    @classmethod
    def setUpClass(cls):
        cls.app = _build_app()
        cls.client = cls.app.test_client()
        cls.accounts = _fetchall("SELECT id, name, email FROM dify_accounts "
                                 "WHERE status = 'active' ORDER BY created_at")
        if len(cls.accounts) < 2:
            raise unittest.SkipTest('库里不足两个账号，无法构造跨账号用例')

    def _hdr(self, acc):
        from utils.auth import generate_token_pair
        return {'Authorization': 'Bearer ' + generate_token_pair(
            user_id=str(acc['id']), email=acc['email'] or '',
            username=acc['name'] or '', role='user')['access_token']}

    def _mine(self):
        return _fetchall("SELECT id FROM user_notifications WHERE title = %s",
                         ('itest_notif_probe',))

    def test_01_post_cannot_target_another_inbox(self):
        me, other = self.accounts[0], self.accounts[1]
        _exec("DELETE FROM user_notifications WHERE title = %s", ('itest_notif_probe',))
        try:
            resp = self.client.post('/api/notifications',
                                    json={'user_id': str(other['id']),
                                          'title': 'itest_notif_probe', 'type': 'info'},
                                    headers=self._hdr(me))
            self.assertEqual(resp.status_code, 200)
            rows = self._mine()
            self.assertEqual(len(rows), 1, '探针通知没落在自己名下（body.user_id 被采信了）')
            nid = rows[0]['id']
            # 别人的令牌拿这个 id 标已读 / 删除：必须一行都动不了
            # （取默认值不能写 `or -1`：合法的 0 也是假值，会被换成 -1 把断言弄反）
            r = self.client.post('/api/notifications/%s/read' % nid, headers=self._hdr(other))
            self.assertEqual(r.status_code, 200)
            self.assertEqual(((r.get_json() or {}).get('data') or {}).get('updated'), 0,
                             '跨账号把别人通知标成了已读')
            r = self.client.delete('/api/notifications/%s' % nid, headers=self._hdr(other))
            self.assertEqual(((r.get_json() or {}).get('data') or {}).get('deleted'), 0,
                             '跨账号删掉了别人的通知')
            self.assertEqual(len(self._mine()), 1)
        finally:
            _exec("DELETE FROM user_notifications WHERE title = %s", ('itest_notif_probe',))
        self.assertFalse(self._mine(), '用例残留未清理')

    def test_02_list_ignores_uid_param(self):
        me, other = self.accounts[0], self.accounts[1]
        resp = self.client.get('/api/notifications?uid=%s' % other['id'], headers=self._hdr(me))
        self.assertEqual(resp.status_code, 200)
        data = (resp.get_json() or {}).get('data') or {}
        self.assertIsInstance(data.get('items'), list)

    def test_03_anonymous_cannot_read_notifications(self):
        resp = self.client.get('/api/notifications')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main(verbosity=2)

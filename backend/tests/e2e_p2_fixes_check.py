# -*- coding: utf-8 -*-
"""
P2 体验优化 E2E 测试
  - #11: 注册/密码重置页
  - #12: SMTP/系统设置页
  - #15: 工作流评论协作
"""
import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


class TestRegistration(unittest.TestCase):
    """用户注册测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls._created_emails = []

    @classmethod
    def tearDownClass(cls):
        """用例自己建的账号自己收走。

        注册会连带建租户与 join 记录，不清理就会像这次一样在库里堆出十几个 test_*
        账号（它们全都能登录）。本次发布前已用
        scripts/maintenance/cleanup_test_accounts.py 清过一轮，这里防它长回来。
        """
        emails = list(getattr(cls, '_created_emails', []))
        if not emails:
            return
        try:
            from config import get_db
        except Exception:
            return
        db = get_db()
        try:
            cur = db.cursor()
            for email in emails:
                cur.execute('SELECT id FROM dify_accounts WHERE email = %s', (email,))
                for row in cur.fetchall():
                    aid = str(row['id'])
                    cur.execute('SELECT tenant_id FROM dify_tenant_account_joins '
                                'WHERE account_id = %s', (aid,))
                    tids = [str(x['tenant_id']) for x in cur.fetchall()]
                    cur.execute('DELETE FROM user_roles WHERE user_id = %s', (aid,))
                    cur.execute('DELETE FROM dify_tenant_account_joins WHERE account_id = %s',
                                (aid,))
                    cur.execute('DELETE FROM dify_accounts WHERE id = %s', (aid,))
                    # 只删跑完之后再也没成员的租户，不能隔空扫掉共用工作区
                    for tid in tids:
                        cur.execute('SELECT COUNT(1) AS n FROM dify_tenant_account_joins '
                                    'WHERE tenant_id = %s', (tid,))
                        if not int((cur.fetchone() or {}).get('n') or 0):
                            cur.execute('DELETE FROM dify_tenants WHERE id = %s', (tid,))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def test_01_register_success(self):
        """注册成功"""
        import uuid
        username = f'test_reg_{uuid.uuid4().hex[:8]}'
        email = f'{username}@test.com'
        resp = self.client.post('/api/register', json={
            'username': username,
            'password': 'Test@1234',
            'email': email
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['code'], 200)
        self.assertIn('id', data.get('data', {}))
        TestRegistration._created_emails.append(email)

    def test_02_register_duplicate_email(self):
        """重复邮箱注册失败

        以前这里写的是开发者的真实邮箱（当作“肯定已存在的邮箱”），两个问题：
        换一个环境就假失败，且仓库里永留个人邮箱。现在改成“自己先注一个再用同一个邮箱重试”，
        用例自含、不依赖库里残留数据。
        """
        import uuid
        username = f'test_dup_{uuid.uuid4().hex[:8]}'
        email = f'{username}@test.com'
        first = self.client.post('/api/register', json={
            'username': username, 'password': 'Test@1234', 'email': email
        })
        # 首次注册可能因“未开放注册/需邀请码”被拦，那种情况下本用例无法验证重复分支
        if json.loads(first.data).get('code') != 200:
            self.skipTest('首次注册未成功（注册开关或邀请码限制），重复邮箱分支无法验证')
        TestRegistration._created_emails.append(email)
        resp = self.client.post('/api/register', json={
            'username': username + 'b',
            'password': 'Test@1234',
            'email': email
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_03_register_weak_password(self):
        """弱密码注册失败"""
        resp = self.client.post('/api/register', json={
            'username': 'weakpwd_user',
            'password': '123',
            'email': 'weak@test.com'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_04_register_missing_fields(self):
        """缺少必填字段"""
        resp = self.client.post('/api/register', json={
            'username': 'incomplete_user'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


class TestPasswordReset(unittest.TestCase):
    """密码重置测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_01_forgot_password_existing_email(self):
        """已存在邮箱发送重置链接

        断言本身是“无论邮箱存在与否返回相同提示”，所以不需要拿真实存活的邮箱去试；
        换成固定夹具邮箱，避免带真实个人的邮箱进入仓库，也避免 SMTP 配好时真的发信给对方。
        """
        resp = self.client.post('/api/password/forgot', json={
            'email': 'p2-fixture@example.com'
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        # 无论邮箱是否存在，返回相同提示
        self.assertIn('重置链接', data.get('msg', ''))

    def test_02_forgot_password_nonexistent_email(self):
        """不存在邮箱也返回相同提示（防枚举）"""
        resp = self.client.post('/api/password/forgot', json={
            'email': 'nonexistent_12345@test.com'
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('重置链接', data.get('msg', ''))

    def test_03_forgot_password_empty_email(self):
        """空邮箱返回错误"""
        resp = self.client.post('/api/password/forgot', json={
            'email': ''
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_04_reset_password_invalid_token(self):
        """无效 token 重置失败"""
        resp = self.client.post('/api/password/reset', json={
            'token': 'invalid_token_12345',
            'new_password': 'NewPass@1234'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_05_reset_password_weak_password(self):
        """弱密码重置失败"""
        resp = self.client.post('/api/password/reset', json={
            'token': 'some_token',
            'new_password': '123'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


class TestSystemSettings(unittest.TestCase):
    """系统设置测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # 不内置明文口令（错口令会触发登录失败锁定）；由 helper 取真实登录或签发 token
        import e2e_auth_helper
        cls.token = e2e_auth_helper.get_auth_header(verbose=True).get(
            'Authorization', '').replace('Bearer ', '')
        assert cls.token, '无法取得认证令牌'

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def test_01_get_settings_requires_auth(self):
        """获取设置需要认证"""
        resp = self.client.get('/api/system/settings')
        self.assertEqual(resp.status_code, 401)

    def test_02_get_settings_admin(self):
        """管理员获取设置"""
        resp = self.client.get('/api/system/settings', headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data'), dict)

    def test_03_save_settings(self):
        """保存设置"""
        resp = self.client.put('/api/system/settings', headers=self._headers(), json={
            'smtp_host': 'smtp.test.com',
            'smtp_port': '587',
            'site_name': '测试站点',
            'allow_register': '1'
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['code'], 200)

    def test_04_settings_persist(self):
        """设置持久化"""
        # Save
        self.client.put('/api/system/settings', headers=self._headers(), json={
            'site_name': '持久化测试站点'
        })
        # Read
        resp = self.client.get('/api/system/settings', headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(data['data'].get('site_name'), '持久化测试站点')

    def test_05_smtp_test_invalid(self):
        """无效 SMTP 测试失败"""
        resp = self.client.post('/api/system/smtp/test', headers=self._headers(), json={
            'smtp_host': 'invalid.smtp.host',
            'smtp_port': '587',
            'smtp_user': 'test',
            'smtp_password': 'wrong'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


class TestWorkflowComments(unittest.TestCase):
    """工作流评论协作测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # 不内置明文口令（错口令会触发登录失败锁定）；由 helper 取真实登录或签发 token
        import e2e_auth_helper
        cls.token = e2e_auth_helper.get_auth_header(verbose=True).get(
            'Authorization', '').replace('Bearer ', '')
        assert cls.token, '无法取得认证令牌'
        # Get an app_id
        resp = cls.client.get('/api/agents', headers={'Authorization': f'Bearer {cls.token}'})
        agents = json.loads(resp.data).get('data', [])
        cls.app_id = agents[0]['id'] if agents else '00000000-0000-0000-0000-000000000000'

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def test_01_list_comments_empty(self):
        """获取评论列表（初始为空）"""
        resp = self.client.get(f'/api/workflows/{self.app_id}/comments', headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data'), list)

    def test_02_add_comment(self):
        """添加评论"""
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': '测试评论内容',
            'position_x': 100,
            'position_y': 200
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('id', data.get('data', {}))
        self.comment_id = data['data']['id']

    def test_03_list_comments_after_add(self):
        """添加后列表包含评论"""
        resp = self.client.get(f'/api/workflows/{self.app_id}/comments', headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(data.get('data', [])), 1)

    def test_04_add_reply(self):
        """添加回复"""
        # First add a parent comment
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': '父评论'
        })
        parent_id = json.loads(resp.data)['data']['id']
        # Add reply
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': '回复内容',
            'parent_id': parent_id
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)

    def test_05_resolve_comment(self):
        """解决评论"""
        # Add comment
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': '待解决的评论'
        })
        comment_id = json.loads(resp.data)['data']['id']
        # Resolve
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments/{comment_id}/resolve',
                                headers=self._headers(), json={'resolved': True})
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)

    def test_06_delete_comment(self):
        """删除评论"""
        # Add comment
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': '将被删除的评论'
        })
        comment_id = json.loads(resp.data)['data']['id']
        # Delete
        resp = self.client.delete(f'/api/workflows/{self.app_id}/comments/{comment_id}',
                                  headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)

    def test_07_comments_require_auth(self):
        """评论操作需要认证"""
        resp = self.client.get(f'/api/workflows/{self.app_id}/comments')
        self.assertEqual(resp.status_code, 401)

    def test_08_empty_content_rejected(self):
        """空内容评论被拒绝"""
        resp = self.client.post(f'/api/workflows/{self.app_id}/comments', headers=self._headers(), json={
            'content': ''
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)

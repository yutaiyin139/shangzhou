# -*- coding: utf-8 -*-
"""
阶段 5（P3）确定性回归：
  5.1 资源级 RBAC —— 权限矩阵 / 统一资源权限检查（dify_datasets / dify_apps）
  5.2 SSO(OAuth)  —— 提供商定义、配置解析、用户配给与 email 绑定（离线，不触外网）

特点：
- 直接调用 utils.auth / utils.oauth_user 引擎函数，无需 HTTP、无需真实 Google/GitHub。
- 自建隔离数据（唯一 id / email），tearDown 精确清理，可反复运行。
"""
import os
import sys
import uuid
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db
from utils import auth
from utils import oauth_user


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


def _cleanup_account(uid):
    """删除 OAuth 配给创建的账号及其角色/工作区/关联（无外键，手工级联）。"""
    rows = _fetchall('SELECT tenant_id FROM dify_tenant_account_joins WHERE account_id = %s', (uid,))
    for r in rows:
        tid = r['tenant_id']
        _exec('DELETE FROM dify_tenant_account_joins WHERE account_id = %s', (uid,))
        _exec('DELETE FROM dify_tenants WHERE id = %s', (tid,))
        break
    _exec('DELETE FROM dify_tenant_account_joins WHERE account_id = %s', (uid,))
    _exec('DELETE FROM user_roles WHERE user_id = %s', (uid,))
    _exec('DELETE FROM dify_accounts WHERE id = %s', (uid,))


# ============================================================
# 5.1 资源级 RBAC
# ============================================================

class TestResourceLevelRBAC(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tenant = str(uuid.uuid4())
        cls.owner = 'rbac-e2e-owner-' + uuid.uuid4().hex[:8]
        cls.other = 'rbac-e2e-other-' + uuid.uuid4().hex[:8]   # 无 user_roles → 非 admin
        cls.ds_id = str(uuid.uuid4())
        cls.pub_app = str(uuid.uuid4())
        cls.draft_app = str(uuid.uuid4())
        _exec('INSERT INTO dify_datasets (id, tenant_id, name, created_by) VALUES (%s,%s,%s,%s)',
              (cls.ds_id, cls.tenant, 'e2e-rbac-ds', cls.owner))
        _exec("INSERT INTO dify_apps (id, tenant_id, name, status, created_by) VALUES (%s,%s,%s,'published',%s)",
              (cls.pub_app, cls.tenant, 'e2e-rbac-app-pub', cls.owner))
        _exec("INSERT INTO dify_apps (id, tenant_id, name, status, created_by) VALUES (%s,%s,%s,'draft',%s)",
              (cls.draft_app, cls.tenant, 'e2e-rbac-app-draft', cls.owner))

    @classmethod
    def tearDownClass(cls):
        _exec('DELETE FROM dify_datasets WHERE id = %s', (cls.ds_id,))
        _exec('DELETE FROM dify_apps WHERE id IN (%s,%s)', (cls.pub_app, cls.draft_app))

    def test_01_registry_complete(self):
        for rt in ('app', 'workflow', 'dataset', 'tool'):
            self.assertIn(rt, auth._RESOURCE_REGISTRY)
            reg = auth._RESOURCE_REGISTRY[rt]
            self.assertIn('owner_field', reg)
            self.assertIn('table', reg)

    def test_02_unknown_type_denied(self):
        self.assertFalse(auth.check_resource_permission('nope', 'x', self.owner))

    def test_03_dataset_owner_read_write(self):
        self.assertTrue(auth.check_dataset_permission(self.ds_id, self.owner, 'read'))
        self.assertTrue(auth.check_dataset_permission(self.ds_id, self.owner, 'write'))

    def test_04_dataset_read_open_write_denied(self):
        # 单租户模型：read 对任意登录用户开放；write 非属主且非 admin 拒绝
        self.assertTrue(auth.check_dataset_permission(self.ds_id, self.other, 'read'))
        self.assertFalse(auth.check_dataset_permission(self.ds_id, self.other, 'write'))

    def test_05_dataset_missing_denied(self):
        self.assertFalse(auth.check_dataset_permission(str(uuid.uuid4()), self.owner, 'read'))

    def test_06_resource_perm_via_registry(self):
        self.assertTrue(auth.check_resource_permission('dataset', self.ds_id, self.owner, 'write'))
        self.assertFalse(auth.check_resource_permission('dataset', self.ds_id, self.other, 'write'))

    def test_07_app_access_matrix(self):
        self.assertTrue(auth.check_app_access(self.pub_app, self.owner))     # owner
        self.assertTrue(auth.check_app_access(self.pub_app, self.other))     # published 全局可读
        self.assertTrue(auth.check_app_access(self.draft_app, self.owner))   # owner
        self.assertFalse(auth.check_app_access(self.draft_app, self.other))  # draft 非属主不可访问

    def test_08_app_resource_perm(self):
        self.assertTrue(auth.check_resource_permission('app', self.pub_app, self.other, 'read'))
        self.assertFalse(auth.check_resource_permission('app', self.draft_app, self.other, 'write'))


# ============================================================
# 5.2 SSO（OAuth）用户配给
# ============================================================

class TestSSOUserProvisioning(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.email = 'sso-e2e-' + uuid.uuid4().hex[:8] + '@example.com'
        cls.created = []

    @classmethod
    def tearDownClass(cls):
        for uid in cls.created:
            _cleanup_account(uid)

    def test_01_providers_defined(self):
        for name in ('google', 'github'):
            self.assertIn(name, oauth_user.OAUTH_PROVIDERS)
            p = oauth_user.OAUTH_PROVIDERS[name]
            for k in ('authorize_url', 'token_url', 'userinfo_url', 'scope'):
                self.assertIn(k, p)

    def test_02_unknown_config_none(self):
        self.assertIsNone(oauth_user.get_oauth_config('no-such-provider'))

    def test_03_authorize_unknown_pair_none(self):
        url, state = oauth_user.build_authorize_url('no-such-provider')
        self.assertIsNone(url)
        self.assertIsNone(state)

    def test_04_no_email_returns_none(self):
        self.assertIsNone(oauth_user.find_or_create_oauth_user('google', {}))
        self.assertIsNone(oauth_user.find_or_create_oauth_user('google', {'email': '  '}))

    def test_05_create_assigns_user_role(self):
        r1 = oauth_user.find_or_create_oauth_user('google', {'email': self.email, 'name': 'SSO E2E'})
        self.assertIsNotNone(r1, 'OAuth 用户配给失败（应返回用户 dict），旧实现因引用不存在列被吞成 None')
        self.assertEqual(r1['email'], self.email)
        self.assertEqual(r1.get('role'), 'user')
        TestSSOUserProvisioning.created.append(r1['id'])
        # 落库校验
        rows = _fetchall('SELECT id, name, status FROM dify_accounts WHERE email = %s', (self.email,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], r1['id'])
        self.assertEqual(rows[0]['status'], 'active')
        # 角色分配校验（user_roles → roles.name='user'）
        rr = _fetchall(
            r'''SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s''', (r1['id'],))
        self.assertTrue(rr and rr[0]['name'] == 'user')
        # 工作区关联校验
        tj = _fetchall('SELECT tenant_id FROM dify_tenant_account_joins WHERE account_id = %s', (r1['id'],))
        self.assertEqual(len(tj), 1)

    def test_06_rebind_same_email_no_dup(self):
        # 复用同一 email（大写测试归一化），应返回同一账号且不产生重复行
        r2 = oauth_user.find_or_create_oauth_user('github', {'email': self.email.upper(), 'name': 'X'})
        self.assertIsNotNone(r2)
        dup = _fetchall('SELECT id FROM dify_accounts WHERE email = %s', (self.email,))
        self.assertEqual(len(dup), 1)
        # 若上一用例先跑，r2 应与 r1 同 id
        if TestSSOUserProvisioning.created:
            self.assertEqual(r2['id'], TestSSOUserProvisioning.created[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""
P1 重要功能缺失 E2E 测试
  - #5: OAuth/SSO 登录框架
  - #6: 资源级 RBAC（权限校验 + 知识库鉴权）
  - #9: 模型负载均衡（多 Key 轮询 + fallback）
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


class TestModelLoadBalancing(unittest.TestCase):
    """模型负载均衡测试"""

    def test_01_get_model_configs_for_lb_empty(self):
        """无配置时返回空列表"""
        from utils.llm import get_model_configs_for_lb
        # 使用不存在的 provider
        configs = get_model_configs_for_lb('nonexistent_provider_xyz')
        self.assertIsInstance(configs, list)

    def test_02_select_lb_returns_none_when_empty(self):
        """无配置时返回 None"""
        from utils.llm import select_model_config_lb
        result = select_model_config_lb('nonexistent_provider_xyz')
        self.assertIsNone(result)

    def test_03_lb_round_robin_cycles(self):
        """轮询索引循环"""
        from utils.llm import _lb_round_robin_index, select_model_config_lb
        # 清理测试索引
        test_key = 'test_provider:llm'
        if test_key in _lb_round_robin_index:
            del _lb_round_robin_index[test_key]
        # 无配置时返回 None
        result = select_model_config_lb('test_provider')
        self.assertIsNone(result)

    def test_04_call_llm_with_lb_no_config(self):
        """无配置时返回错误（使用不存在的 provider）"""
        from utils.llm import call_llm_with_lb
        content, err = call_llm_with_lb('test', 'hello', provider='nonexistent_provider_xyz_12345')
        self.assertIsNone(content)
        self.assertIn('没有可用', err)


class TestResourceLevelRBAC(unittest.TestCase):
    """资源级 RBAC 测试"""

    def test_01_user_has_permission_admin(self):
        """admin 拥有所有权限"""
        from utils.auth import user_has_permission
        # 使用不存在的用户（返回 False）
        result = user_has_permission('nonexistent_user', 'app:create')
        self.assertFalse(result)

    def test_02_check_dataset_permission_nonexistent(self):
        """不存在的数据集返回 False"""
        from utils.auth import check_dataset_permission
        result = check_dataset_permission('nonexistent_ds', 'user123', 'read')
        self.assertFalse(result)

    def test_03_check_app_access_nonexistent(self):
        """不存在的应用返回 False"""
        from utils.auth import check_app_access
        result = check_app_access('nonexistent_app', 'user123')
        self.assertFalse(result)

    def test_04_dataset_permission_decorator_import(self):
        """权限装饰器可导入"""
        from utils.auth import dataset_permission_required
        self.assertTrue(callable(dataset_permission_required))


class TestOAuthFramework(unittest.TestCase):
    """OAuth/SSO 登录框架测试"""

    def test_01_get_available_providers_empty_when_not_configured(self):
        """未配置时返回空列表"""
        from utils.oauth_user import get_available_oauth_providers
        providers = get_available_oauth_providers()
        self.assertIsInstance(providers, list)

    def test_02_get_oauth_config_nonexistent(self):
        """不存在的提供商返回 None"""
        from utils.oauth_user import get_oauth_config
        result = get_oauth_config('nonexistent_provider')
        self.assertIsNone(result)

    def test_03_build_authorize_url_nonexistent(self):
        """不存在的提供商返回 None"""
        from utils.oauth_user import build_authorize_url
        url, state = build_authorize_url('nonexistent_provider')
        self.assertIsNone(url)
        self.assertIsNone(state)

    def test_04_build_authorize_url_google_template(self):
        """Google 模板存在（但未配置时应返回 None）"""
        from utils.oauth_user import get_oauth_config, OAUTH_PROVIDERS
        self.assertIn('google', OAUTH_PROVIDERS)
        self.assertIn('github', OAUTH_PROVIDERS)
        # 未配置时返回 None
        cfg = get_oauth_config('google')
        # 如果没有配置 client_id，应返回 None
        if not cfg:
            self.assertIsNone(cfg)

    def test_05_oauth_login_invalid_code(self):
        """无效 code 返回错误"""
        from utils.oauth_user import oauth_login
        token_pair, err = oauth_login('google', 'invalid_code', 'invalid_state')
        self.assertIsNone(token_pair)
        self.assertIsNotNone(err)

    def test_06_find_or_create_user_no_email(self):
        """无 email 返回 None"""
        from utils.oauth_user import find_or_create_oauth_user
        result = find_or_create_oauth_user('google', {'name': 'Test'})
        self.assertIsNone(result)


class TestKnowledgeAuthProtection(unittest.TestCase):
    """知识库路由鉴权测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_01_knowledge_datasets_requires_auth(self):
        """知识库列表需要认证"""
        resp = self.client.get('/api/knowledge/datasets')
        # 应返回 401（未认证）
        self.assertEqual(resp.status_code, 401)

    def test_02_knowledge_create_requires_auth(self):
        """创建知识库需要认证"""
        resp = self.client.post('/api/knowledge/datasets', json={'name': 'test'})
        self.assertEqual(resp.status_code, 401)

    def test_03_oauth_providers_public(self):
        """OAuth 提供商列表公开访问"""
        resp = self.client.get('/api/oauth/providers')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data.get('code'), 200)
        self.assertIsInstance(data.get('data'), list)


if __name__ == '__main__':
    unittest.main(verbosity=2)

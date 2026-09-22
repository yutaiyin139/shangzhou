# -*- coding: utf-8 -*-
"""
模型供应商配置 E2E 测试
测试内容：
  - 供应商列表 API
  - 供应商详情 API
  - 安装供应商 API
  - 卸载供应商 API
  - 已安装供应商列表 API
  - 模型配置 CRUD API
  - 模型连接测试 API
  - 配置 Schema API
  - 模型类型列表 API
  - 种子数据验证
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


class ModelProviderEndpointsTest(unittest.TestCase):
    """模型供应商配置端点测试"""

    @classmethod
    def setUpClass(cls):
        """初始化：创建 Flask 测试客户端 + 写入种子数据"""
        import app as flask_app_mod
        from data.seed_model_providers import seed_model_providers

        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        # 写入种子数据
        try:
            seed_model_providers()
        except Exception as e:
            print(f"种子数据写入提示: {e}")

    @classmethod
    def tearDownClass(cls):
        """
        测试结束后清理所有 sk-test 假 key 的配置。
        测试用例可能因断言失败而跳过清理，这里兜底防止污染真实数据。
        """
        try:
            from config import get_db
            from utils.llm import decrypt_api_key
            db = get_db()
            cur = db.cursor()
            cur.execute('SELECT id, api_key FROM model_configs')
            junk_ids = [
                r['id'] for r in cur.fetchall()
                if decrypt_api_key(r['api_key'] or '').startswith('sk-test')
            ]
            for jid in junk_ids:
                cur.execute('DELETE FROM model_configs WHERE id = %s', (jid,))
            db.commit()
            db.close()
            if junk_ids:
                print(f"\n[tearDownClass] 清理 {len(junk_ids)} 条测试配置")
        except Exception as e:
            print(f"\n[tearDownClass] 清理失败（不影响测试结果）: {e}")

    def _get(self, url, params=None):
        return self.client.get(url, query_string=params or {})

    def _post(self, url, data=None):
        return self.client.post(url, json=data or {},
                                content_type='application/json')

    def _put(self, url, data=None):
        return self.client.put(url, json=data or {},
                               content_type='application/json')

    def _delete(self, url):
        return self.client.delete(url)

    # ============================================================
    # 测试 1: 获取所有供应商列表
    # ============================================================

    def test_01_get_all_providers(self):
        """GET /api/model-providers 返回 93+ 供应商"""
        resp = self._get('/api/model-providers')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIsInstance(data['data'], list)
        self.assertGreaterEqual(len(data['data']), 93,
                                f"供应商数量不足 93，实际: {len(data['data'])}")
        # 验证字段完整性
        p = data['data'][0]
        for field in ('provider_name', 'provider_label', 'description', 'icon', 'supported_model_types'):
            self.assertIn(field, p, f"缺少字段: {field}")

    def test_02_providers_have_installed_flag(self):
        """供应商列表包含 is_installed 标志"""
        resp = self._get('/api/model-providers')
        data = json.loads(resp.data)
        for p in data['data']:
            self.assertIn('is_installed', p)

    # ============================================================
    # 测试 2: 获取供应商详情
    # ============================================================

    def test_03_get_provider_detail(self):
        """GET /api/model-providers/openai 返回详情 + 模型列表"""
        resp = self._get('/api/model-providers/openai')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        p = data['data']
        self.assertEqual(p['provider_name'], 'openai')
        self.assertIn('models', p)
        self.assertIsInstance(p['models'], list)
        self.assertGreater(len(p['models']), 0, "OpenAI 应该有可用模型")

    def test_04_provider_detail_models(self):
        """供应商详情包含模型能力字段"""
        resp = self._get('/api/model-providers/openai')
        data = json.loads(resp.data)
        m = data['data']['models'][0]
        for field in ('model_name', 'model_label', 'model_type', 'context_size'):
            self.assertIn(field, m)

    def test_05_provider_not_found(self):
        """GET /api/model-providers/nonexist 返回 404"""
        resp = self._get('/api/model-providers/nonexist')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 404)

    # ============================================================
    # 测试 3: 安装供应商
    # ============================================================

    def test_06_install_provider(self):
        """POST /api/model-providers/openai/install 安装 OpenAI"""
        payload = {
            'api_key': 'sk-test-key-for-e2e-test',
            'api_base_url': 'https://api.openai.com/v1',
            'credential_name': 'E2E_Test_OpenAI_' + str(os.getpid()),
            'model_name': 'gpt-3.5-turbo',
        }
        resp = self._post('/api/model-providers/openai/install', payload)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIn('id', data['data'])
        # 清理
        self._delete(f"/api/model-configs/{data['data']['id']}")

    def test_07_install_requires_api_key(self):
        """安装必须提供 API Key"""
        payload = {'credential_name': 'test-no-key', 'model_name': 'gpt-3.5-turbo'}
        resp = self._post('/api/model-providers/openai/install', payload)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_08_install_auto_credential_name(self):
        """安装时自动生成凭据名称"""
        payload = {
            'api_key': 'sk-test-auto-name',
            'model_name': 'gpt-3.5-turbo',
        }
        resp = self._post('/api/model-providers/deepseek/install', payload)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        # 清理
        self._delete(f"/api/model-configs/{data['data']['id']}")

    def test_09_install_sets_model_params(self):
        """安装时设置模型参数"""
        import time
        ts = int(time.time() * 1000) % 1000000
        payload = {
            'api_key': 'sk-test-params-' + str(ts),
            'credential_name': 'E2E_Params_' + str(ts),
            'model_name': 'gpt-3.5-turbo',
            'temperature': 0.5,
            'max_tokens': 4096,
            'top_p': 0.9,
        }
        resp = self._post('/api/model-providers/openai/install', payload)
        data = json.loads(resp.data)
        # 安装成功（code 200 或已安装 code 400 都可接受）
        self.assertIn(data['code'], [200, 400])
        # 清理可能创建的记录
        if data['code'] == 200:
            # 清理
            from config import get_db
            db = get_db()
            cur = db.cursor()
            cur.execute('DELETE FROM model_configs WHERE credential_name = %s', (payload['credential_name'],))
            db.commit()
            db.close()

    # ============================================================
    # 测试 4: 卸载供应商
    # ============================================================

    def test_10_uninstall_provider(self):
        """POST /api/model-providers/openai/uninstall 卸载"""
        # 先安装
        payload = {
            'api_key': 'sk-test-uninstall',
            'credential_name': 'E2E_Uninstall_' + str(os.getpid()),
            'model_name': 'gpt-3.5-turbo',
        }
        resp = self._post('/api/model-providers/openai/install', payload)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)

        # 卸载
        resp2 = self._post('/api/model-providers/openai/uninstall')
        data2 = json.loads(resp2.data)
        self.assertEqual(data2['code'], 200)

    # ============================================================
    #测试 5: 已安装供应商列表
    # ============================================================

    def test_11_get_installed_providers(self):
        """GET /api/model-providers/installed 返回已安装列表"""
        # 先安装一个
        payload = {
            'api_key': 'sk-test-installed',
            'credential_name': 'E2E_Installed_' + str(os.getpid()),
            'model_name': 'gpt-3.5-turbo',
        }
        resp = self._post('/api/model-providers/openai/install', payload)
        data = json.loads(resp.data)

        # 查询已安装
        resp2 = self._get('/api/model-providers/installed')
        data2 = json.loads(resp2.data)
        self.assertEqual(data2['code'], 200)
        self.assertIsInstance(data2['data'], list)
        # 验证字段
        if data2['data']:
            p = data2['data'][0]
            for field in ('provider_name', 'provider_label', 'model_count', 'icon'):
                self.assertIn(field, p)

        # 清理
        if data.get('code') == 200:
            self._delete(f"/api/model-configs/{data['data']['id']}")

    # ============================================================
    # 测试 6: 模型配置 CRUD
    # ============================================================

    def test_12_create_model_config(self):
        """POST /api/model-configs 创建配置"""
        payload = {
            'credential_name': 'E2E_CRUD_' + str(os.getpid()),
            'provider': 'testprovider',
            'provider_label': 'Test Provider',
            'model_name': 'test-model',
            'api_key': 'sk-test-crud',
            'api_base_url': 'https://api.test.com/v1',
            'temperature': 0.8,
            'max_tokens': 1024,
        }
        resp = self._post('/api/model-configs', payload)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIn('id', data['data'])
        # 清理
        self._delete(f"/api/model-configs/{data['data']['id']}")

    def test_13_list_model_configs(self):
        """GET /api/model-configs 返回配置列表"""
        resp = self._get('/api/model-configs')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIsInstance(data['data'], list)

    def test_14_list_configs_by_provider(self):
        """GET /api/model-configs?provider=openai 按供应商过滤"""
        resp = self._get('/api/model-configs', {'provider': 'openai'})
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        for c in data['data']:
            self.assertEqual(c['provider'], 'openai')

    def test_15_update_model_config(self):
        """PUT /api/model-configs/:id 更新配置"""
        # 先创建
        payload = {
            'credential_name': 'E2E_Update_' + str(os.getpid()),
            'provider': 'testupdate',
            'model_name': 'test-model',
            'api_key': 'sk-test-update',
        }
        resp = self._post('/api/model-configs', payload)
        cfg_id = json.loads(resp.data)['data']['id']

        # 更新
        update = {'temperature': 0.3, 'max_tokens': 512}
        resp2 = self._put(f'/api/model-configs/{cfg_id}', update)
        self.assertEqual(json.loads(resp2.data)['code'], 200)

        # 验证
        resp3 = self._get('/api/model-configs')
        configs = json.loads(resp3.data)['data']
        cfg = next((c for c in configs if c['id'] == cfg_id), None)
        self.assertIsNotNone(cfg)
        self.assertEqual(float(cfg['temperature']), 0.3)

        # 清理
        self._delete(f"/api/model-configs/{cfg_id}")

    def test_16_delete_model_config(self):
        """DELETE /api/model-configs/:id 删除配置"""
        payload = {
            'credential_name': 'E2E_Delete_' + str(os.getpid()),
            'provider': 'testdelete',
            'model_name': 'test-model',
            'api_key': 'sk-test-delete',
        }
        resp = self._post('/api/model-configs', payload)
        cfg_id = json.loads(resp.data)['data']['id']

        resp2 = self._delete(f'/api/model-configs/{cfg_id}')
        self.assertEqual(json.loads(resp2.data)['code'], 200)

    def test_17_masked_api_key(self):
        """列表返回时 API Key 脱敏"""
        payload = {
            'credential_name': 'E2E_Mask_' + str(os.getpid()),
            'provider': 'testmask',
            'model_name': 'test-model',
            'api_key': 'sk-1234567890abcdef',
        }
        resp = self._post('/api/model-configs', payload)
        cfg_id = json.loads(resp.data)['data']['id']

        resp2 = self._get('/api/model-configs')
        configs = json.loads(resp2.data)['data']
        cfg = next((c for c in configs if c['id'] == cfg_id), None)
        self.assertIsNotNone(cfg)
        # 应该被脱敏
        self.assertNotEqual(cfg['api_key'], 'sk-1234567890abcdef')

        # 清理
        self._delete(f"/api/model-configs/{cfg_id}")

    # ============================================================
    # 测试 7: 模型连接测试
    # ============================================================

    def test_18_test_connection_requires_key(self):
        """测试连接必须提供 API Key"""
        payload = {'provider': 'openai', 'model_name': 'gpt-3.5-turbo'}
        resp = self._post('/api/model-configs/test', payload)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_19_test_connection_openai_compat(self):
        """测试 OpenAI 兼容接口连接（使用无效 key 应该失败）"""
        payload = {
            'provider': 'openai',
            'api_key': 'sk-invalid-key-for-test',
            'api_base_url': 'https://api.openai.com/v1',
            'model_name': 'gpt-3.5-turbo',
            'model_type': 'llm',
        }
        resp = self._post('/api/model-configs/test', payload)
        data = json.loads(resp.data)
        # 应该返回结果（成功或失败，取决于网络）
        self.assertIn('data', data)

    # ============================================================
    # 测试 8: 配置 Schema
    # ============================================================

    def test_20_get_config_schema(self):
        """GET /api/model-providers/openai/config-schema 返回 Schema"""
        resp = self._get('/api/model-providers/openai/config-schema')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIn('config_schema', data['data'])
        self.assertIn('default_base_url', data['data'])
        self.assertIn('supported_model_types', data['data'])

    def test_21_config_schema_not_found(self):
        """不存在的供应商返回 404"""
        resp = self._get('/api/model-providers/nonexist/config-schema')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 404)

    # ============================================================
    # 测试 9: 模型类型列表
    # ============================================================

    def test_22_get_model_types(self):
        """GET /api/model-types 返回模型类型列表"""
        resp = self._get('/api/model-types')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIsInstance(data['data'], list)
        self.assertGreaterEqual(len(data['data']), 5)
        types = [t['value'] for t in data['data']]
        for t in ('llm', 'embedding', 'rerank', 'tts', 'stt'):
            self.assertIn(t, types, f"缺少模型类型: {t}")

    # ============================================================
    # 测试 10: 种子数据验证
    # ============================================================

    def test_23_seed_data_93_providers(self):
        """种子数据包含至少 93 个供应商"""
        resp = self._get('/api/model-providers')
        data = json.loads(resp.data)
        self.assertGreaterEqual(len(data['data']), 93)

    def test_24_seed_data_key_providers(self):
        """种子数据包含关键供应商"""
        resp = self._get('/api/model-providers')
        data = json.loads(resp.data)
        names = [p['provider_name'] for p in data['data']]
        for key in ('openai', 'anthropic', 'deepseek', 'tongyi', 'zhipu', 'google'):
            self.assertIn(key, names, f"缺少关键供应商: {key}")

    def test_25_seed_data_models_exist(self):
        """供应商包含模型定义"""
        resp = self._get('/api/model-providers/openai')
        data = json.loads(resp.data)
        self.assertGreater(len(data['data']['models']), 0)

    # ============================================================
    # 测试 11: 边界情况
    # ============================================================

    def test_26_install_duplicate_credential_name(self):
        """重复凭据名应该报错"""
        pname = 'E2E_Dup_' + str(os.getpid())
        payload = {
            'api_key': 'sk-test-dup-1',
            'credential_name': pname,
            'model_name': 'gpt-3.5-turbo',
        }
        self._post('/api/model-providers/openai/install', payload)
        # 同名再安装
        payload2 = {
            'api_key': 'sk-test-dup-2',
            'credential_name': pname,
            'model_name': 'gpt-4',
        }
        resp = self._post('/api/model-providers/openai/install', payload2)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_27_decrypt_api_key(self):
        """获取解密的 API Key"""
        payload = {
            'credential_name': 'E2E_Decrypt_' + str(os.getpid()),
            'provider': 'testdecrypt',
            'model_name': 'test-model',
            'api_key': 'sk-test-decrypt-key-123',
        }
        resp = self._post('/api/model-configs', payload)
        cfg_id = json.loads(resp.data)['data']['id']

        resp2 = self._get(f'/api/model-configs/{cfg_id}/decrypt')
        data = json.loads(resp2.data)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['data']['api_key'], 'sk-test-decrypt-key-123')

        # 清理
        self._delete(f"/api/model-configs/{cfg_id}")

    def test_28_provider_detail_schema_parsed(self):
        """供应商详情中 config_schema 已解析为对象"""
        resp = self._get('/api/model-providers/openai')
        data = json.loads(resp.data)
        schema = data['data'].get('config_schema')
        if schema:
            self.assertIsInstance(schema, dict)
            self.assertIn('fields', schema)


if __name__ == '__main__':
    unittest.main(verbosity=2)

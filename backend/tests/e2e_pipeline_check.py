# -*- coding: utf-8 -*-
"""
知识 Pipeline 引擎 E2E 测试（P2 #13）
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


class TestKnowledgePipeline(unittest.TestCase):
    """知识 Pipeline 引擎测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # 不内置明文口令（错口令会触发登录失败锁定）；由 helper 取真实登录或签发 token
        import e2e_auth_helper
        auth = e2e_auth_helper.get_auth_header(verbose=True)
        cls.token = auth.get('Authorization', '').replace('Bearer ', '')
        assert cls.token, '无法取得认证令牌'

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def test_01_get_stage_types(self):
        """获取阶段类型列表"""
        resp = self.client.get('/api/knowledge/pipelines/stage-types')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data'), list)
        self.assertGreaterEqual(len(data['data']), 5)
        types = [s['type'] for s in data['data']]
        self.assertIn('fetch', types)
        self.assertIn('parse', types)
        self.assertIn('segment', types)

    def test_02_create_pipeline(self):
        """创建 Pipeline"""
        resp = self.client.post('/api/knowledge/pipelines', headers=self._headers(), json={
            'name': '测试 Pipeline',
            'description': '测试用',
            'stages': [
                {'type': 'fetch', 'config': {'source_type': 'text', 'texts': ['测试文档']}},
                {'type': 'parse', 'config': {'strip_html': True}},
                {'type': 'segment', 'config': {'mode': 'general', 'max_tokens': 500}},
            ]
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('id', data.get('data', {}))
        self.__class__.pipeline_id = data['data']['id']

    def test_03_create_pipeline_invalid_stage(self):
        """无效阶段类型创建失败"""
        resp = self.client.post('/api/knowledge/pipelines', headers=self._headers(), json={
            'name': '无效 Pipeline',
            'stages': [{'type': 'invalid_stage', 'config': {}}]
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_04_create_pipeline_no_stages(self):
        """无阶段创建失败"""
        resp = self.client.post('/api/knowledge/pipelines', headers=self._headers(), json={
            'name': '空 Pipeline'
        })
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)

    def test_05_list_pipelines(self):
        """列出 Pipeline"""
        resp = self.client.get('/api/knowledge/pipelines', headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data'), list)

    def test_06_get_pipeline(self):
        """获取 Pipeline 详情"""
        if not hasattr(self.__class__, 'pipeline_id'):
            self.skipTest('No pipeline created')
        resp = self.client.get(f'/api/knowledge/pipelines/{self.__class__.pipeline_id}',
                               headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data', {}).get('stages'), list)

    def test_07_update_pipeline(self):
        """更新 Pipeline"""
        if not hasattr(self.__class__, 'pipeline_id'):
            self.skipTest('No pipeline created')
        resp = self.client.put(f'/api/knowledge/pipelines/{self.__class__.pipeline_id}',
                               headers=self._headers(), json={
            'name': '更新后的 Pipeline',
            'description': '已更新'
        })
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)

    def test_08_run_pipeline(self):
        """执行 Pipeline"""
        if not hasattr(self.__class__, 'pipeline_id'):
            self.skipTest('No pipeline created')
        resp = self.client.post(f'/api/knowledge/pipelines/{self.__class__.pipeline_id}/run',
                                headers=self._headers(), json={})
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('execution_id', data.get('data', {}))

    def test_09_list_execution_logs(self):
        """列出执行日志"""
        if not hasattr(self.__class__, 'pipeline_id'):
            self.skipTest('No pipeline created')
        resp = self.client.get(f'/api/knowledge/pipelines/{self.__class__.pipeline_id}/logs',
                               headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(data.get('data'), list)

    def test_10_pipeline_requires_auth(self):
        """Pipeline 操作需要认证"""
        resp = self.client.get('/api/knowledge/pipelines')
        self.assertEqual(resp.status_code, 401)

    def test_11_delete_pipeline(self):
        """删除 Pipeline"""
        if not hasattr(self.__class__, 'pipeline_id'):
            self.skipTest('No pipeline created')
        resp = self.client.delete(f'/api/knowledge/pipelines/{self.__class__.pipeline_id}',
                                  headers=self._headers())
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)

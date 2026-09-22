# -*- coding: utf-8 -*-
"""
阶段 4 新功能 E2E 测试
  4.1 模型 by-id 测试端点 (GET by-id + POST test-by-id)
  4.4 工作流版本 Diff (GET version detail + POST diff)
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


class Phase4ModelTestIdTest(unittest.TestCase):
    """4.1 模型 by-id 测试端点"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def _get(self, url):
        return self.client.get(url)

    def _post(self, url, data=None):
        return self.client.post(url, json=data or {}, content_type='application/json')

    def test_01_get_config_by_id(self):
        """GET /api/model-configs/<id> 返回脱敏配置"""
        resp = self._get('/api/model-configs/70')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        cfg = data['data']
        self.assertIn('provider', cfg)
        self.assertIn('model_name', cfg)
        # key 应该被脱敏
        self.assertNotIn('sk-', str(cfg.get('api_key', '')))

    def test_02_get_config_by_id_not_found(self):
        """GET /api/model-configs/99999 返回 404"""
        resp = self._get('/api/model-configs/99999')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 404)

    def test_03_test_by_id_success(self):
        """POST /api/model-configs/<id>/test 测试 deepseek 连接"""
        resp = self._post('/api/model-configs/70/test')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('data', data)
        result = data['data']
        self.assertIn('success', result)
        self.assertIn('elapsed_ms', result)
        self.assertIsInstance(result['elapsed_ms'], int)
        self.assertGreater(result['elapsed_ms'], 0)

    def test_04_test_by_id_not_found(self):
        """POST /api/model-configs/99999/test 返回 404"""
        resp = self._post('/api/model-configs/99999/test')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 404)

    def test_05_installed_has_latest_config_id(self):
        """GET /api/model-providers/installed 包含 latest_config_id"""
        resp = self._get('/api/model-providers/installed')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        for p in data['data']:
            self.assertIn('latest_config_id', p)
            self.assertIsNotNone(p['latest_config_id'])
            self.assertGreater(p['latest_config_id'], 0)


class Phase4VersionDiffTest(unittest.TestCase):
    """4.4 工作流版本 Diff"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # 找到有多个版本的应用
        from config import get_db
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT app_id, COUNT(*) as cnt FROM workflow_versions GROUP BY app_id HAVING cnt >= 2 LIMIT 1')
        row = cur.fetchone()
        cls.app_id = row['app_id'] if row else None
        if cls.app_id:
            cur2 = db.cursor()
            cur2.execute('SELECT id, version_number FROM workflow_versions WHERE app_id = %s ORDER BY version_number LIMIT 2', (cls.app_id,))
            versions = cur2.fetchall()
            cls.vid_a = versions[0]['version_number'] if len(versions) > 0 else None
            cls.vid_b = versions[1]['version_number'] if len(versions) > 1 else None
        db.close()

    def _get(self, url):
        return self.client.get(url)

    def _post(self, url, data=None):
        return self.client.post(url, json=data or {}, content_type='application/json')

    @unittest.skipUnless(lambda cls: cls.app_id is not None, "无多版本数据")
    def test_01_get_version_detail(self):
        """GET /api/workflows/<app_id>/versions/<vid> 返回完整 graph"""
        if not self.app_id or not self.vid_a:
            self.skipTest("无版本数据")
        resp = self._get(f'/api/workflows/{self.app_id}/versions/{self.vid_a}')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        self.assertIn('graph', data['data'])
        self.assertIn('nodes', data['data']['graph'])

    def test_02_get_version_detail_not_found(self):
        """GET 不存在的版本返回 404"""
        resp = self._get('/api/workflows/00000000-0000-0000-0000-000000000000/versions/999')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 404)

    @unittest.skipUnless(lambda cls: cls.app_id is not None, "无多版本数据")
    def test_03_diff_two_versions(self):
        """POST /api/workflows/<app_id>/versions/diff 返回结构化 diff"""
        if not self.app_id or not self.vid_a or not self.vid_b:
            self.skipTest("无足够版本数据")
        resp = self._post(f'/api/workflows/{self.app_id}/versions/diff', {
            'vid_a': self.vid_a, 'vid_b': self.vid_b
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 200)
        result = data['data']
        self.assertIn('summary', result)
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        summary = result['summary']
        self.assertIn('nodes_added', summary)
        self.assertIn('nodes_removed', summary)
        self.assertIn('nodes_changed', summary)
        self.assertIn('edges_added', summary)
        self.assertIn('edges_removed', summary)

    def test_04_diff_missing_params(self):
        """POST diff 缺少参数返回 400"""
        resp = self._post('/api/workflows/00000000-0000-0000-0000-000000000000/versions/diff', {'vid_a': 1})
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)

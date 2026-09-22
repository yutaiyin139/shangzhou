# -*- coding: utf-8 -*-
"""
阶段 4 确定性功能测试（补充 e2e_phase4_check 未覆盖的核心逻辑）
  4.2 模型负载均衡：多配置真实轮询循环 + 空配置边界
  4.4 工作流版本 Diff：节点/边增删改的精确结构化对比（经真实端点 + 自造版本数据）

设计：直接对 model_configs / workflow_versions 造独立测试数据（无外键约束），
测完即焚，不依赖模型网络/Dify/前端，可重复运行。
"""
import sys
import os
import json
import uuid
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from config import get_db


class TestModelLoadBalancingReal(unittest.TestCase):
    """4.2 多 Key 真实轮询"""

    @classmethod
    def setUpClass(cls):
        cls.provider = 'lb-e2e-' + uuid.uuid4().hex[:8]
        cls.ids = []
        db = get_db()
        try:
            cur = db.cursor()
            for i, mname in enumerate(['lb-model-A', 'lb-model-B']):
                cur.execute(
                    r'''INSERT INTO model_configs
                        (credential_name, provider, model_name, model_type, api_key, status)
                        VALUES (%s, %s, %s, 'llm', %s, 1)''',
                    (f'lb-cred-{i}', cls.provider, mname, 'dummy-key-' + mname))
                cls.ids.append(cur.lastrowid)
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('DELETE FROM model_configs WHERE id IN (%s, %s)' % ('%s', '%s'),
                        tuple(cls.ids))
            db.commit()
        finally:
            db.close()
        # 清理轮询索引，避免污染其他测试
        from utils.llm import _lb_round_robin_index
        _lb_round_robin_index.pop(f'{cls.provider}:llm', None)

    def test_01_get_configs_returns_both(self):
        from utils.llm import get_model_configs_for_lb
        configs = get_model_configs_for_lb(self.provider, 'llm')
        self.assertEqual(len(configs), 2, f'期望 2 个配置，实得 {len(configs)}')
        # 按 id 升序
        self.assertEqual([c['id'] for c in configs], sorted(self.ids))
        # api_key 已解密（dummy 明文原样返回，非 enc: 密文）
        for c in configs:
            self.assertFalse(str(c['api_key']).startswith('enc:'))

    def test_02_round_robin_cycles(self):
        from utils.llm import select_model_config_lb, _lb_round_robin_index
        _lb_round_robin_index.pop(f'{self.provider}:llm', None)
        seq = [select_model_config_lb(self.provider, 'llm')['model_name'] for _ in range(4)]
        # 配置按 id 升序为 [A, B]，轮询应从索引 0 起 A→B→A→B
        self.assertEqual(seq, ['lb-model-A', 'lb-model-B', 'lb-model-A', 'lb-model-B'],
                         f'轮询序列异常: {seq}')

    def test_03_index_stateless_per_key(self):
        """不同 provider 的轮询索引互相隔离"""
        from utils.llm import _lb_round_robin_index
        _lb_round_robin_index[f'{self.provider}:llm'] = 1
        # 不存在的 provider 不应读到该索引，返回 None
        from utils.llm import select_model_config_lb
        self.assertIsNone(select_model_config_lb('no-such-provider-xyz', 'llm'))

    def test_04_empty_provider_none(self):
        from utils.llm import select_model_config_lb, get_model_configs_for_lb
        self.assertEqual(get_model_configs_for_lb('no-such-provider-xyz', 'llm'), [])
        self.assertIsNone(select_model_config_lb('no-such-provider-xyz', 'llm'))


class TestVersionDiffExact(unittest.TestCase):
    """4.4 版本 Diff 精确结构化对比"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.app_id = str(uuid.uuid4())  # 合法 uuid，满足 _is_uuid 校验
        graph_v1 = {
            'nodes': [
                {'id': 'n1', 'type': 'llm', 'position': {'x': 0, 'y': 0}, 'data': {'title': '开始节点'}},
                {'id': 'n2', 'type': 'answer', 'position': {'x': 1, 'y': 1}, 'data': {'title': '被删除节点'}},
            ],
            'edges': [{'source': 'n1', 'target': 'n2'}],
        }
        graph_v2 = {
            'nodes': [
                {'id': 'n1', 'type': 'llm', 'position': {'x': 5, 'y': 5}, 'data': {'title': '开始节点改名'}},
                {'id': 'n3', 'type': 'tool', 'position': {'x': 2, 'y': 2}, 'data': {'title': '新增节点'}},
            ],
            'edges': [{'source': 'n1', 'target': 'n3'}],
        }
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO workflow_versions (app_id, version_number, name, graph_json)
                    VALUES (%s, 1, 'v1', %s)''',
                (cls.app_id, json.dumps(graph_v1, ensure_ascii=False)))
            cur.execute(
                r'''INSERT INTO workflow_versions (app_id, version_number, name, graph_json)
                    VALUES (%s, 2, 'v2', %s)''',
                (cls.app_id, json.dumps(graph_v2, ensure_ascii=False)))
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('DELETE FROM workflow_versions WHERE app_id = %s', (cls.app_id,))
            db.commit()
        finally:
            db.close()

    def _diff(self, vid_a, vid_b):
        resp = self.client.post(
            f'/api/workflows/{self.app_id}/versions/diff',
            json={'vid_a': vid_a, 'vid_b': vid_b}, content_type='application/json')
        return json.loads(resp.data)

    def test_01_diff_added_removed_changed(self):
        data = self._diff(1, 2)
        self.assertEqual(data['code'], 200, data)
        s = data['data']['summary']
        self.assertEqual(s['nodes_added'], 1, s)      # n3
        self.assertEqual(s['nodes_removed'], 1, s)    # n2
        self.assertEqual(s['nodes_changed'], 1, s)    # n1（位置+data 变）
        self.assertEqual(s['edges_added'], 1, s)      # n1->n3
        self.assertEqual(s['edges_removed'], 1, s)    # n1->n2

    def test_02_changed_node_keys(self):
        data = self._diff(1, 2)
        changed = data['data']['nodes']['changed']
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]['id'], 'n1')
        self.assertIn('position', changed[0]['changes'])
        self.assertIn('data', changed[0]['changes'])

    def test_03_added_removed_node_titles(self):
        data = self._diff(1, 2)
        added_ids = {n['id'] for n in data['data']['nodes']['added']}
        removed_ids = {n['id'] for n in data['data']['nodes']['removed']}
        self.assertEqual(added_ids, {'n3'})
        self.assertEqual(removed_ids, {'n2'})

    def test_04_identical_graph_zero_diff(self):
        data = self._diff(1, 1)
        self.assertEqual(data['code'], 200, data)
        s = data['data']['summary']
        self.assertTrue(all(v == 0 for v in s.values()), f'相同版本应零差异: {s}')

    def test_05_reverse_direction(self):
        """反向对比：v2→v1 增删互换"""
        data = self._diff(2, 1)
        s = data['data']['summary']
        self.assertEqual(s['nodes_added'], 1)   # n2
        self.assertEqual(s['nodes_removed'], 1)  # n3
        self.assertEqual(s['edges_added'], 1)
        self.assertEqual(s['edges_removed'], 1)

    def test_06_missing_version_404(self):
        data = self._diff(1, 999)
        self.assertEqual(data['code'], 404, data)

    def test_07_missing_params_400(self):
        resp = self.client.post(
            f'/api/workflows/{self.app_id}/versions/diff',
            json={'vid_a': 1}, content_type='application/json')
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)

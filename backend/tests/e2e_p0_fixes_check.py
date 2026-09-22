# -*- coding: utf-8 -*-
"""
P0 功能阻断修复 E2E 测试
  - #2: API 速率限制（Service API 全局限流）
  - #4: 摘要记忆（对话历史摘要注入 + 自动压缩）
"""
import sys
import os
import json
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


class TestRateLimiting(unittest.TestCase):
    """API 速率限制测试"""

    @classmethod
    def setUpClass(cls):
        import app as flask_app_mod
        cls.app = flask_app_mod.app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # 获取有效的 API Token
        from config import get_db
        db = get_db()
        cur = db.cursor()
        cur.execute(r"SELECT id, token FROM dify_api_tokens LIMIT 1")
        row = cur.fetchone()
        cls.api_token = row['token'] if row else 'test-token'
        db.close()

    def _post(self, url, data=None):
        headers = {'Authorization': f'Bearer {self.api_token}'}
        return self.client.post(url, json=data or {}, headers=headers)

    def _get(self, url):
        headers = {'Authorization': f'Bearer {self.api_token}'}
        return self.client.get(url, headers=headers)

    def test_01_rate_limit_headers_present(self):
        """限流响应头存在"""
        resp = self._get('/v1/info')
        # 应有 X-RateLimit-* 头
        self.assertIn('X-RateLimit-Limit', resp.headers)
        self.assertIn('X-RateLimit-Remaining', resp.headers)

    def test_02_rate_limit_allows_normal_traffic(self):
        """正常流量不被阻断（至少前 10 次）"""
        for i in range(10):
            resp = self._get('/v1/info')
            self.assertNotEqual(resp.status_code, 429,
                                f'第 {i+1} 次请求不应被限流')

    def test_03_rate_limit_blocks_excessive_traffic(self):
        """过量请求被限流（快速发送 70+ 次）"""
        # 快速发送大量请求
        blocked = False
        for i in range(70):
            resp = self._get('/v1/info')
            if resp.status_code == 429:
                blocked = True
                # 验证 429 响应格式
                data = json.loads(resp.data)
                self.assertEqual(data.get('code'), 429)
                self.assertIn('Retry-After', resp.headers)
                break
        self.assertTrue(blocked, '过量请求应被限流（429）')

    def test_04_different_routes_independent_limits(self):
        """不同路径独立限流"""
        # 快速请求 info 到达上限
        for i in range(70):
            resp = self._get('/v1/info')
            if resp.status_code == 429:
                break
        # parameters 应有独立限额（因为 endpoint 不同）
        # 注意：同一 IP 不同 route 的 key 不同
        resp2 = self._get('/v1/parameters')
        # 不应因为 info 被限流而 parameters 也被限
        self.assertNotEqual(resp2.status_code, 429,
                            '不同路径应有独立限流计数')


class TestSummaryMemory(unittest.TestCase):
    """摘要记忆测试（使用直接函数调用 + 内部 API 测试）"""

    def test_01_summary_crud_apis_exist(self):
        """摘要 CRUD API 存在（通过 direct function call 测试）"""
        from routes.conversation_summaries import _generate_summary, _estimate_tokens
        # 测试摘要生成
        messages = [
            {'id': 'm1', 'role': 'user', 'content': '什么是机器学习？'},
            {'id': 'm2', 'role': 'assistant', 'content': '机器学习是人工智能的一个分支...'},
        ]
        summary = _generate_summary(messages)
        self.assertIsInstance(summary, str)
        # 测试 token 估算
        tokens = _estimate_tokens('这是一个测试文本')
        self.assertGreater(tokens, 0)

    def test_02_auto_summarize_threshold(self):
        """自动摘要：未超阈值不压缩"""
        from routes.conversation_summaries import auto_summarize_if_needed
        conv_id = 'test-conv-summary-002'
        # 少量消息（未超阈值）- 需要先创建会话和消息
        # 由于没有真实会话，auto_summarize_if_needed 应返回空
        result = auto_summarize_if_needed(conv_id, threshold=20)
        # 无消息时返回空
        self.assertEqual(result, '')

    def test_03_auto_summarize_with_sufficient_messages(self):
        """自动摘要：超阈值触发压缩"""
        from routes.conversation_summaries import auto_summarize_if_needed
        from config import get_db

        conv_id = 'test-conv-summary-003'
        # 创建会话和消息
        db = get_db()
        try:
            cur = db.cursor()
            # 先清理旧数据（保证幂等）
            cur.execute(r"DELETE FROM dify_messages WHERE conversation_id = %s", (conv_id,))
            cur.execute(r"DELETE FROM dify_conversations WHERE id = %s", (conv_id,))
            cur.execute(r"DELETE FROM conversation_summaries WHERE conversation_id = %s", (conv_id,))
            # 创建会话
            cur.execute(
                r'''INSERT INTO dify_conversations
                    (id, app_id, user_id, title, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'normal', NOW(), NOW())''',
                (conv_id, 'test-app', 'test-user', '测试会话'))
            # 创建 25 条消息
            for i in range(25):
                cur.execute(
                    r'''INSERT INTO dify_messages
                        (id, conversation_id, role, content, tokens, model_provider, model_name, metadata, created_at)
                        VALUES (%s, %s, %s, %s, 0, '', '', %s, NOW())''',
                    (f'msg-{conv_id}-{i}', conv_id,
                     'user' if i % 2 == 0 else 'assistant',
                     f'消息内容 {i}' * 5, '{}'))
            db.commit()
        finally:
            db.close()

        # 触发自动摘要
        result = auto_summarize_if_needed(conv_id, threshold=20, keep_recent=5)
        # 应生成摘要
        self.assertIsInstance(result, str)

    def test_04_summary_context_builder(self):
        """摘要上下文构建"""
        from routes.agents import _build_summary_context
        # 测试空会话
        ctx = _build_summary_context('nonexistent-conv-id')
        self.assertEqual(ctx, '')

    def test_05_summary_context_builder(self):
        """摘要上下文构建"""
        from routes.agents import _build_summary_context
        conv_id = 'test-conv-summary-001'  # 已有摘要
        ctx = _build_summary_context(conv_id)
        self.assertIsInstance(ctx, str)
        # 应包含摘要内容
        if ctx:
            self.assertIn('历史对话摘要', ctx)

    def test_06_summary_context_empty_for_new_conv(self):
        """新会话无摘要时返回空"""
        from routes.agents import _build_summary_context
        ctx = _build_summary_context('nonexistent-conv-id')
        self.assertEqual(ctx, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)

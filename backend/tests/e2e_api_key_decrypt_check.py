# -*- coding: utf-8 -*-
"""
模型 API Key 解密修复回归测试

验证以下修复：
  Bug: 数据库中 api_key 使用 Fernet 加密存储（enc: 前缀），
       但调用 LLM API 时未解密直接放入 Authorization 头，
       导致模型供应商返回 401。
  同时验证: base_url 已含 /v1 时不再重复拼接（/v1/v1/ 问题）

测试方式: monkeypatch HTTP 层捕获实际发送的 headers 和 URL
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import unittest
from unittest.mock import patch


class ApiKeyDecryptFixTest(unittest.TestCase):
    """API Key 解密修复回归测试"""

    def setUp(self):
        from utils.encryption import encrypt_field
        self.encrypt_field = encrypt_field
        self.real_key = 'sk-regression-test-key-abcdef123456'

    # ============================================================
    # 1. utils/llm.py — _call_llm_with_config 必须发送解密后的 key
    # ============================================================

    def test_llm_module_sends_decrypted_key(self):
        """utils.llm._call_llm_with_config 发送解密后的 API Key"""
        from utils.llm import _call_llm_with_config

        captured = {}

        def fake_http(url, data, headers, **kw):
            captured['url'] = url
            captured['auth'] = headers.get('Authorization', '')
            return ('{"choices":[{"message":{"content":"ok"}}]}', None)

        cfg = {
            'api_key': self.encrypt_field(self.real_key),
            'api_base_url': 'https://api.deepseek.com/v1',
            'model_name': 'deepseek-chat',
            'credential_name': 'test',
            'provider': 'deepseek',
        }

        with patch('utils.llm._http_request', side_effect=fake_http), \
             patch('utils.llm._check_connectivity', return_value=True):
            content, err = _call_llm_with_config('sys', 'hello', cfg)

        self.assertIsNone(err)
        self.assertEqual(content, 'ok')
        # 关键断言：发送的是解密后的 key
        self.assertEqual(captured['auth'], 'Bearer ' + self.real_key)
        # URL 不应重复 /v1
        self.assertEqual(captured['url'], 'https://api.deepseek.com/v1/chat/completions')

    def test_llm_module_plaintext_key_passthrough(self):
        """未加密的旧数据（明文 key）原样发送，保证向后兼容"""
        from utils.llm import _call_llm_with_config

        captured = {}

        def fake_http(url, data, headers, **kw):
            captured['auth'] = headers.get('Authorization', '')
            return ('{"choices":[{"message":{"content":"ok"}}]}', None)

        cfg = {
            'api_key': self.real_key,  # 明文，无 enc: 前缀（旧数据）
            'api_base_url': 'https://api.deepseek.com',
            'model_name': 'deepseek-chat',
            'credential_name': 'test',
            'provider': 'deepseek',
        }

        with patch('utils.llm._http_request', side_effect=fake_http), \
             patch('utils.llm._check_connectivity', return_value=True):
            content, err = _call_llm_with_config('sys', 'hello', cfg)

        self.assertIsNone(err)
        self.assertEqual(captured['auth'], 'Bearer ' + self.real_key)

    # ============================================================
    # 2. workflow_runner.py — 工作流节点调用解密验证
    # ============================================================

    def test_workflow_runner_llm_call_decrypts(self):
        """engine.workflow_runner 的 LLM 节点调用前解密 api_key"""
        from engine.workflow_runner import decrypt_api_key

        # decrypt_api_key 应被正确导入（说明工作流运行时使用统一辅助函数）
        self.assertTrue(callable(decrypt_api_key))

        # 直接验证辅助函数行为
        enc = self.encrypt_field(self.real_key)
        self.assertEqual(decrypt_api_key(enc), self.real_key)
        self.assertEqual(decrypt_api_key(self.real_key), self.real_key)
        self.assertEqual(decrypt_api_key(None), None)

    # ============================================================
    # 3. URL 构建 — base_url 带/不带 /v1 都应正确
    # ============================================================

    def test_build_openai_url_no_double_v1(self):
        """build_openai_url 处理各种 base_url 形态"""
        from utils.llm import build_openai_url

        cases = [
            ('https://api.deepseek.com/v1', 'chat/completions',
             'https://api.deepseek.com/v1/chat/completions'),
            ('https://api.deepseek.com', 'chat/completions',
             'https://api.deepseek.com/v1/chat/completions'),
            ('https://api.moonshot.cn/v1/', 'chat/completions',
             'https://api.moonshot.cn/v1/chat/completions'),
            ('https://api.openai.com/v1', 'embeddings',
             'https://api.openai.com/v1/embeddings'),
            ('http://localhost:11434', 'chat/completions',
             'http://localhost:11434/v1/chat/completions'),
        ]
        for base, endpoint, expected in cases:
            self.assertEqual(build_openai_url(base, endpoint), expected,
                             f'{base} + {endpoint} 应得 {expected}')

    # ============================================================
    # 4. chat.py 导入验证 — 模块能正常导入且引用辅助函数
    # ============================================================

    def test_chat_module_uses_helpers(self):
        """routes/chat.py 导入 decrypt_api_key 和 build_openai_url"""
        import inspect
        from routes import chat as chat_module_src
        src = inspect.getsource(chat_module_src)
        self.assertIn('decrypt_api_key', src, 'chat.py 应使用 decrypt_api_key')
        self.assertIn('build_openai_url', src, 'chat.py 应使用 build_openai_url')

    def test_chat_stream_no_raw_api_key(self):
        """chat.py 流式端点不再出现 api_key = cfg['api_key'] 裸赋值"""
        import inspect
        from routes import chat as chat_module_src
        src = inspect.getsource(chat_module_src)
        self.assertNotIn("api_key = cfg['api_key']\n", src,
                         'chat.py 不应再直接赋值加密 key')

    # ============================================================
    # 5. embedding_service.py 解密验证
    # ============================================================

    def test_embedding_service_decrypts(self):
        """embedding_service 调用远端 embedding 前解密 api_key"""
        from engine import embedding_service

        captured = {}

        real_urlopen = embedding_service.urllib.request.urlopen

        class FakeResp:
            def read(self):
                return b'{"data":[{"embedding":[0.1,0.2,0.3]}]}'
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            captured['auth'] = req.headers.get('Authorization', '')
            captured['url'] = req.full_url
            return FakeResp()

        cfg = {
            'api_key': self.encrypt_field(self.real_key),
            'api_base_url': 'https://api.deepseek.com/v1',
            'model_name': 'bge-m3',
            'credential_name': 'test',
            'provider': 'test',
        }

        with patch.object(embedding_service, 'get_embedding_config', return_value=cfg), \
             patch.object(embedding_service.urllib.request, 'urlopen', side_effect=fake_urlopen):
            vec = embedding_service._try_remote_embedding('hello text')

        self.assertIsNotNone(vec)
        self.assertEqual(captured['auth'], 'Bearer ' + self.real_key)
        self.assertEqual(captured['url'], 'https://api.deepseek.com/v1/embeddings')

    # ============================================================
    # 6. 模型供应商 install -> 实际调用 全链路
    # ============================================================

    def test_full_chain_install_then_call(self):
        """模拟: install 写入加密 key -> LLM 调用时解密 -> 发送明文"""
        from utils.llm import _call_llm_with_config
        import json as _json

        # 模拟 install 端点的加密存储
        stored_key = self.encrypt_field(self.real_key)
        self.assertTrue(stored_key.startswith('enc:'))

        # 模拟从数据库读回（fetchone 返回 dict）
        cfg = {
            'id': 1,
            'credential_name': 'deepseek 凭据',
            'provider': 'deepseek',
            'provider_label': 'DeepSeek',
            'model_name': 'deepseek-chat',
            'api_key': stored_key,          # 库中是密文
            'api_base_url': 'https://api.deepseek.com/v1',
            'temperature': 0.7,
            'max_tokens': 2048,
            'status': 1,
        }

        captured = {}

        def fake_http(url, data, headers, **kw):
            captured['auth'] = headers.get('Authorization', '')
            captured['url'] = url
            captured['body'] = _json.loads(data.decode('utf-8'))
            return ('{"choices":[{"message":{"content":"回复"}}],"usage":{"total_tokens":10}}', None)

        with patch('utils.llm._http_request', side_effect=fake_http), \
             patch('utils.llm._check_connectivity', return_value=True):
            content, err = _call_llm_with_config('你是助手', '你好', cfg)

        self.assertIsNone(err)
        self.assertEqual(content, '回复')
        # 发送的必须是解密后的 key，而不是 enc:... 密文
        self.assertNotIn('enc:', captured['auth'])
        self.assertEqual(captured['auth'], 'Bearer ' + self.real_key)
        # 模型名称正确传递
        self.assertEqual(captured['body']['model'], 'deepseek-chat')


if __name__ == '__main__':
    unittest.main(verbosity=2)

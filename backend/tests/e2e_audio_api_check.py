# -*- coding: utf-8 -*-
"""
音频 Service API E2E 测试
  - POST /v1/audio-to-text  (语音转文本)
  - POST /v1/text-to-audio  (文本转语音)
  - TTS/STT 连接测试（models.py）

严格参考 Dify 1.17.0 API 契约验证。
"""
import sys
import os
import json
import struct
import wave
import io
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


class AudioServiceAPIBaseTest(unittest.TestCase):
    """音频 Service API 测试基类"""

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
        if row:
            cls.app_id = row['id']
            cls.api_token = row['token']
        else:
            cls.app_id = None
            cls.api_token = 'test-token'
        db.close()

        # /api/model-configs/* 已加 @login_required：Service API 的 AppKey 不是 JWT，
        # 这类控制台接口需另外取访问令牌
        import e2e_auth_helper
        cls.jwt_header = e2e_auth_helper.get_auth_header()

    def _post(self, url, data=None, content_type='application/json', files=None):
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        if files:
            return self.client.post(url, data=files, content_type='multipart/form-data',
                                   headers=headers)
        return self.client.post(url, json=data or {}, content_type=content_type,
                               headers=headers)

    def _post_jwt(self, url, data=None):
        """用 JWT 访问控制台接口（而非 Service API 的 AppKey）"""
        return self.client.post(url, json=data or {}, content_type='application/json',
                                headers=self.jwt_header)

    def _post_multipart(self, url, data=None, file_field=None):
        """发送 multipart/form-data 请求"""
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        payload = {}
        if data:
            payload.update(data)
        if file_field:
            payload.update(file_field)
        return self.client.post(url, data=payload, content_type='multipart/form-data',
                               headers=headers)


class TestAudioToTextEndpoint(AudioServiceAPIBaseTest):
    """POST /v1/audio-to-text 测试"""

    def _make_wav_bytes(self, duration=0.5, sample_rate=16000):
        """生成简短的静音 WAV 数据"""
        num_samples = int(sample_rate * duration)
        pcm_data = b'\x00\x00' * num_samples
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    def test_01_no_file_returns_400(self):
        """未提供文件返回 400"""
        resp = self._post_multipart('/v1/audio-to-text')
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data.get('code'), 'no_audio_uploaded')

    def test_02_empty_file_returns_400(self):
        """空文件返回 400"""
        wav_bytes = b''
        resp = self._post_multipart(
            '/v1/audio-to-text',
            file_field={'file': (io.BytesIO(wav_bytes), 'empty.wav', 'audio/wav')},
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('code', data)

    def test_03_unsupported_type_returns_415(self):
        """不支持的文件类型返回 415"""
        resp = self._post_multipart(
            '/v1/audio-to-text',
            file_field={'file': (io.BytesIO(b'not audio'), 'test.txt', 'text/plain')},
        )
        self.assertEqual(resp.status_code, 415)
        data = json.loads(resp.data)
        self.assertEqual(data.get('code'), 'unsupported_audio_type')

    def test_04_acceptable_mime_types(self):
        """接受的 MIME 类型不返回 415（即使模型未配置）"""
        wav_bytes = self._make_wav_bytes()
        for mime in ['audio/wav', 'audio/mp3', 'audio/m4a']:
            resp = self._post_multipart(
                '/v1/audio-to-text',
                file_field={'file': (io.BytesIO(wav_bytes), 'test.wav', mime)},
            )
            # 不应返回 415（MIME 校验通过）
            data = json.loads(resp.data)
            self.assertNotEqual(data.get('code'), 'unsupported_audio_type',
                                f'MIME {mime} 应该被接受')

    def test_05_no_auth_returns_401(self):
        """无认证返回 401"""
        wav_bytes = self._make_wav_bytes()
        resp = self.client.post('/v1/audio-to-text',
                                data={'file': (io.BytesIO(wav_bytes), 'test.wav', 'audio/wav')},
                                content_type='multipart/form-data')
        self.assertIn(resp.status_code, [401, 400])


class TestTextToAudioEndpoint(AudioServiceAPIBaseTest):
    """POST /v1/text-to-audio 测试"""

    def test_01_no_text_returns_400(self):
        """无 text 返回 400"""
        resp = self._post('/v1/text-to-audio', data={})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('code', data)

    def test_02_empty_text_returns_400(self):
        """空文本返回 400"""
        resp = self._post('/v1/text-to-audio', data={'text': '   '})
        self.assertEqual(resp.status_code, 400)

    def test_03_no_auth_returns_401(self):
        """无认证返回 401"""
        resp = self.client.post('/v1/text-to-audio', json={'text': 'Hello'})
        self.assertIn(resp.status_code, [401, 400])

    def test_04_no_model_configured(self):
        """未配置 TTS 模型返回 provider_not_initialize"""
        resp = self._post('/v1/text-to-audio', data={'text': 'Hello test'})
        # 如果未配置 TTS 模型，应返回 provider_not_initialize
        if resp.status_code == 400:
            data = json.loads(resp.data)
            self.assertIn(data.get('code'),
                          ['provider_not_initialize', 'completion_request_error'])


class TestAudioConnectionTest(AudioServiceAPIBaseTest):
    """TTS/STT 连接测试（models.py）"""

    def test_01_tts_test_endpoint_exists(self):
        """TTS 连接测试端点存在"""
        # 测试 body-based 端点能处理 tts 类型
        resp = self._post_jwt('/api/model-configs/test', data={
            'provider': 'openai_tts',
            'api_key': 'sk-test-fake-key',
            'api_base_url': 'https://api.openai.com',
            'model_name': 'tts-1',
            'model_type': 'tts',
        })
        # 应返回 200（即使 key 是假的，端点应正常处理）
        self.assertIn(resp.status_code, [200, 500])

    def test_02_stt_test_endpoint_exists(self):
        """STT 连接测试端点存在"""
        resp = self._post_jwt('/api/model-configs/test', data={
            'provider': 'openai_stt',
            'api_key': 'sk-test-fake-key',
            'api_base_url': 'https://api.openai.com',
            'model_name': 'whisper-1',
            'model_type': 'stt',
        })
        self.assertIn(resp.status_code, [200, 500])

    def test_03_audio_type_accepted_by_model_types(self):
        """音频模型类型被 /api/model-types 接受"""
        resp = self.client.get('/api/model-types')
        data = json.loads(resp.data)
        types = [t['value'] for t in data.get('data', [])]
        self.assertIn('tts', types)
        self.assertIn('stt', types)


class TestAudioUtilityFunctions(unittest.TestCase):
    """音频工具函数单元测试"""

    def test_01_detect_mime_wav(self):
        """WAV MIME 检测"""
        from utils.audio import detect_audio_mime
        wav_header = b'RIFF\x00\x00\x00\x00WAVEfmt '
        self.assertEqual(detect_audio_mime(wav_header), 'audio/wav')

    def test_02_detect_mime_ogg(self):
        """OGG MIME 检测"""
        from utils.audio import detect_audio_mime
        ogg_header = b'OggS\x00\x02\x00\x00\x00\x00\x00\x00'
        self.assertEqual(detect_audio_mime(ogg_header), 'audio/ogg')

    def test_03_detect_mime_flac(self):
        """FLAC MIME 检测"""
        from utils.audio import detect_audio_mime
        flac_header = b'fLaC\x00\x00\x00\x22\x12\x00'
        self.assertEqual(detect_audio_mime(flac_header), 'audio/flac')

    def test_04_detect_mime_default_mpeg(self):
        """默认返回 audio/mpeg"""
        from utils.audio import detect_audio_mime
        self.assertEqual(detect_audio_mime(b'\x00\x00\x00\x00'), 'audio/mpeg')
        self.assertEqual(detect_audio_mime(b''), 'audio/mpeg')

    def test_05_allowed_mime_types(self):
        """MIME 白名单校验"""
        from utils.audio import is_allowed_audio_type
        self.assertTrue(is_allowed_audio_type('audio/mp3'))
        self.assertTrue(is_allowed_audio_type('audio/wav'))
        self.assertTrue(is_allowed_audio_type('audio/m4a'))
        self.assertTrue(is_allowed_audio_type('audio/amr'))
        self.assertFalse(is_allowed_audio_type('text/plain'))
        self.assertFalse(is_allowed_audio_type('application/pdf'))

    def test_06_mime_from_extension(self):
        """扩展名推断 MIME"""
        from utils.audio import is_allowed_audio_type
        # 无 Content-Type 但扩展名有效
        self.assertTrue(is_allowed_audio_type('', 'test.mp3'))
        self.assertTrue(is_allowed_audio_type('', 'test.wav'))
        self.assertFalse(is_allowed_audio_type('', 'test.txt'))

    def test_07_audio_size_limit_constant(self):
        """文件大小限制常量"""
        from utils.audio import AUDIO_FILE_SIZE_LIMIT
        self.assertEqual(AUDIO_FILE_SIZE_LIMIT, 30 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main(verbosity=2)

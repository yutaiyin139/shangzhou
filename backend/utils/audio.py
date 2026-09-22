# -*- coding: utf-8 -*-
"""
音频工具函数 —— TTS（文本转语音）/ STT（语音转文本）

严格参考 Dify 1.17.0 设计：
- POST /v1/audio-to-text  → speech_to_text()
- POST /v1/text-to-audio  → text_to_speech()

支持提供商：
- OpenAI（TTS-1 / Whisper）— 完整实现
- Azure / ElevenLabs / 其他 — 扩展点（暂返回未支持）
"""
import os
import uuid
import requests as http_requests

from config import get_db
from utils.llm import decrypt_api_key, build_openai_url


# ============================================================
# 常量
# ============================================================

# Dify 规范的音频 MIME 白名单（STT 输入）
AUDIO_MIME_WHITELIST = {
    'audio/mp3', 'audio/mpga', 'audio/mpeg',
    'audio/m4a', 'audio/x-m4a',
    'audio/wav', 'audio/x-wav',
    'audio/amr',
}

# 文件扩展名 → MIME（用于无 Content-Type 时的推断）
EXT_TO_MIME = {
    '.mp3': 'audio/mp3',
    '.mpga': 'audio/mpga',
    '.m4a': 'audio/m4a',
    '.wav': 'audio/wav',
    '.amr': 'audio/amr',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.aac': 'audio/aac',
    '.webm': 'audio/webm',
}

# Dify 规范的 30MB 文件上限
AUDIO_FILE_SIZE_LIMIT = 30 * 1024 * 1024

# 魔法字节检测表（TTS 输出 MIME 推断）
MAGIC_BYTES = [
    (b'RIFF', 'audio/wav'),
    (b'OggS', 'audio/ogg'),
    (b'fLaC', 'audio/flac'),
    (b'ftyp', 'audio/mp4'),
    (b'ID3', 'audio/mpeg'),
    (b'\xff\xfb', 'audio/mpeg'),
    (b'\xff\xf3', 'audio/mpeg'),
    (b'\xff\xf2', 'audio/mpeg'),
]


# ============================================================
# 公共：配置查询
# ============================================================

def get_default_audio_config(model_type='tts'):
    """
    查找默认 TTS/STT 模型配置。
    取最新启用的配置（ORDER BY updated_at DESC, id DESC）。

    返回 dict 或 None（未配置时）。
    """
    if model_type not in ('tts', 'stt'):
        return None
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'''SELECT * FROM model_configs
                WHERE model_type = %s AND status = 1
                ORDER BY updated_at DESC, id DESC LIMIT 1''',
            (model_type,))
        row = cur.fetchone()
        if not row:
            return None
        # 解密 API Key
        row = dict(row)
        row['api_key'] = decrypt_api_key(row['api_key'])
        return row
    finally:
        db.close()


def get_audio_config_by_app(app_id, model_type='tts'):
    """
    查找指定应用关联的 TTS/STT 模型配置。
    优先取应用关联的配置，无则取全局默认。
    """
    if model_type not in ('tts', 'stt'):
        return None
    db = get_db()
    try:
        cur = db.cursor()
        # 先找应用关联的配置
        cur.execute(
            r'''SELECT c.* FROM model_configs c
                JOIN dify_app_model_configs ac ON ac.model_id = c.model_name
                WHERE ac.app_id = %s AND c.model_type = %s AND c.status = 1
                ORDER BY c.updated_at DESC LIMIT 1''',
            (app_id, model_type))
        row = cur.fetchone()
        if not row:
            # 回退到全局默认
            cur.execute(
                r'''SELECT * FROM model_configs
                    WHERE model_type = %s AND status = 1
                    ORDER BY updated_at DESC, id DESC LIMIT 1''',
                (model_type,))
            row = cur.fetchone()
        if not row:
            return None
        row = dict(row)
        row['api_key'] = decrypt_api_key(row['api_key'])
        return row
    finally:
        db.close()


# ============================================================
# 公共：MIME 检测
# ============================================================

def detect_audio_mime(audio_bytes: bytes) -> str:
    """通过魔法字节检测音频 MIME 类型（TTS 输出）"""
    if not audio_bytes:
        return 'audio/mpeg'
    header = audio_bytes[:12]
    for magic, mime in MAGIC_BYTES:
        if header.startswith(magic):
            return mime
    return 'audio/mpeg'


def is_allowed_audio_type(content_type: str, filename: str = '') -> bool:
    """检查 MIME 类型是否在白名单中（STT 输入校验）"""
    if content_type and content_type.lower() in AUDIO_MIME_WHITELIST:
        return True
    # 回退到扩展名推断
    if filename:
        ext = os.path.splitext(filename)[-1].lower()
        if ext in EXT_TO_MIME:
            return True
    return False


# ============================================================
# TTS：文本 → 语音
# ============================================================

def text_to_speech(text, model_cfg, voice=None):
    """
    文本转语音。

    参数:
        text: 要合成的文本
        model_cfg: 模型配置 dict（含 provider, api_key, api_base_url, model_name）
        voice: 声音标识（可选，如 OpenAI 的 alloy/echo/fable/onyx/nova/shimmer）

    返回:
        bytes — 音频二进制数据

    抛出:
        NotImplementedError — 提供商不支持
        Exception — API 调用失败
    """
    if not text or not text.strip():
        raise ValueError('TTS 文本不能为空')

    provider = (model_cfg or {}).get('provider', '')
    api_key = (model_cfg or {}).get('api_key', '')
    base_url = (model_cfg or {}).get('api_base_url', '')
    model_name = (model_cfg or {}).get('model_name', '')

    # 根据提供商分发
    if provider in ('openai_tts', 'openai'):
        return _tts_openai(text, api_key, base_url, model_name, voice)
    elif provider == 'azure_tts':
        return _tts_azure(text, api_key, base_url, model_name, voice)
    else:
        raise NotImplementedError(
            f'暂不支持 {provider} 的 TTS 实现。当前仅支持 openai。'
        )


def _tts_openai(text, api_key, base_url, model_name, voice):
    """OpenAI TTS API: POST /v1/audio/speech"""
    if not api_key:
        raise ValueError('缺少 OpenAI API Key')
    if not base_url:
        base_url = 'https://api.openai.com'

    url = build_openai_url(base_url, 'audio/speech')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model_name or 'tts-1',
        'input': text,
        'voice': voice or 'alloy',
        'response_format': 'mp3',
    }

    resp = http_requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 200:
        return resp.content
    else:
        raise Exception(
            f'OpenAI TTS 失败 (HTTP {resp.status_code}): {resp.text[:300]}'
        )


def _tts_azure(text, api_key, base_url, model_name, voice):
    """Azure TTS REST API（扩展点，暂返回未支持）"""
    raise NotImplementedError(
        'Azure TTS 暂未实现。请配置 OpenAI TTS 模型。'
    )


# ============================================================
# STT：语音 → 文本
# ============================================================

def speech_to_text(audio_bytes, filename, model_cfg):
    """
    语音转文本。

    参数:
        audio_bytes: 音频文件二进制数据
        filename: 原始文件名（用于 MIME 推断）
        model_cfg: 模型配置 dict

    返回:
        str — 识别的文本

    抛出:
        NotImplementedError — 提供商不支持
        Exception — API 调用失败
    """
    if not audio_bytes:
        raise ValueError('音频数据为空')

    provider = (model_cfg or {}).get('provider', '')
    api_key = (model_cfg or {}).get('api_key', '')
    base_url = (model_cfg or {}).get('api_base_url', '')
    model_name = (model_cfg or {}).get('model_name', '')

    if provider in ('openai_stt', 'openai'):
        return _stt_openai(audio_bytes, filename, api_key, base_url, model_name)
    elif provider == 'azure_stt':
        return _stt_azure(audio_bytes, filename, api_key, base_url, model_name)
    else:
        raise NotImplementedError(
            f'暂不支持 {provider} 的 STT 实现。当前仅支持 openai。'
        )


def _stt_openai(audio_bytes, filename, api_key, base_url, model_name):
    """OpenAI Whisper API: POST /v1/audio/transcriptions"""
    if not api_key:
        raise ValueError('缺少 OpenAI API Key')
    if not base_url:
        base_url = 'https://api.openai.com'

    url = build_openai_url(base_url, 'audio/transcriptions')
    headers = {
        'Authorization': f'Bearer {api_key}',
    }

    # 推断 MIME 类型
    ext = os.path.splitext(filename)[-1].lower() if filename else '.mp3'
    mime = EXT_TO_MIME.get(ext, 'audio/mpeg')

    files = {
        'file': (filename or 'audio.mp3', audio_bytes, mime),
    }
    data = {
        'model': model_name or 'whisper-1',
        'response_format': 'text',
    }

    resp = http_requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if resp.status_code == 200:
        return resp.text.strip()
    else:
        raise Exception(
            f'OpenAI STT 失败 (HTTP {resp.status_code}): {resp.text[:300]}'
        )


def _stt_azure(audio_bytes, filename, api_key, base_url, model_name):
    """Azure STT REST API（扩展点，暂返回未支持）"""
    raise NotImplementedError(
        'Azure STT 暂未实现。请配置 OpenAI Whisper 模型。'
    )


# ============================================================
# 辅助：保存音频文件
# ============================================================

def save_audio_file(audio_bytes, suffix='.mp3'):
    """
    保存音频字节到 uploads/audio/ 目录。
    返回可访问的 URL 路径。
    """
    upload_dir = os.path.join('uploads', 'audio')
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f'{file_id}{suffix}')

    with open(file_path, 'wb') as f:
        f.write(audio_bytes)

    return f'/uploads/audio/{file_id}{suffix}'

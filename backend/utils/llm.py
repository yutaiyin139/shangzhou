# -*- coding: utf-8 -*-
"""LLM 调用工具"""

import json
import socket
import urllib.request
import urllib.error
from config import get_db


def decrypt_api_key(api_key):
    """
    解密 API Key（如果已加密），解密失败返回原值（兼容旧明文数据）

    数据库中的 api_key 字段使用 Fernet 加密存储（enc: 前缀），
    实际调用模型 API 前必须先解密，否则会导致 401 鉴权失败。
    """
    if api_key and isinstance(api_key, str) and api_key.startswith('enc:'):
        try:
            from utils.encryption import decrypt_field
            return decrypt_field(api_key)
        except Exception:
            return api_key
    return api_key


def build_openai_url(base_url, endpoint):
    """
    构建 OpenAI 兼容 API URL，自动处理 base_url 末尾已带 /v1 的情况

    参数:
        base_url: API Base URL，如 https://api.deepseek.com 或 https://api.deepseek.com/v1
        endpoint: 'chat/completions' 或 'embeddings'

    示例:
        >>> build_openai_url('https://api.deepseek.com/v1', 'chat/completions')
        'https://api.deepseek.com/v1/chat/completions'
        >>> build_openai_url('https://api.deepseek.com', 'chat/completions')
        'https://api.deepseek.com/v1/chat/completions'
    """
    base = (base_url or '').rstrip('/')
    if base.endswith('/v1'):
        return f'{base}/{endpoint}'
    return f'{base}/v1/{endpoint}'


def get_model_configs_for_lb(provider='', model_type='llm'):
    """
    获取可用于负载均衡的模型配置列表（同一提供商的多 Key 轮询）。

    参数:
        provider: 供应商标识（如 'openai', 'deepseek'），为空则取所有匹配类型
        model_type: 模型类型（默认 'llm'）

    返回:
        list[dict] — 配置列表（API Key 已解密），按 id ASC 排列
    """
    db = get_db()
    try:
        cur = db.cursor()
        if provider:
            cur.execute(
                r'''SELECT * FROM model_configs
                    WHERE status = 1 AND model_type = %s AND provider = %s
                    ORDER BY id ASC''',
                (model_type, provider))
        else:
            cur.execute(
                r'''SELECT * FROM model_configs
                    WHERE status = 1 AND model_type = %s
                    ORDER BY id ASC''',
                (model_type,))
        rows = cur.fetchall()
        configs = []
        for row in rows:
            cfg = dict(row)
            cfg['api_key'] = decrypt_api_key(cfg['api_key'])
            configs.append(cfg)
        return configs
    finally:
        db.close()


_lb_round_robin_index = {}


def select_model_config_lb(provider='', model_type='llm'):
    """
    负载均衡选择：纯轮询（Round-Robin）选择模型配置。

    使用内存中的轮询索引，每次调用按顺序选择下一个配置。
    如果某个配置调用失败，调用方应重试（会自动切换到下一个配置）。

    返回:
        dict — 选中的模型配置（API Key 已解密），无可用配置返回 None
    """
    configs = get_model_configs_for_lb(provider, model_type)
    if not configs:
        return None

    key = f"{provider}:{model_type}"
    if key not in _lb_round_robin_index:
        _lb_round_robin_index[key] = 0

    idx = _lb_round_robin_index[key] % len(configs)
    _lb_round_robin_index[key] = (idx + 1) % len(configs)

    return configs[idx]


def call_llm_with_lb(system_prompt, user_content, provider='', temperature=0.4, max_retries=None):
    """
    带负载均衡的 LLM 调用：多 Key 轮询 + 失败自动切换。

    参数:
        system_prompt: 系统提示词
        user_content: 用户消息
        provider: 供应商标识（用于筛选配置）
        temperature: 温度
        max_retries: 最大重试次数（默认=配置数量，即每个 Key 试一次）

    返回:
        (content, err) — 成功时 err 为 None
    """
    configs = get_model_configs_for_lb(provider, 'llm')
    if not configs:
        return None, '没有可用的模型配置，请先在模型页面添加'

    if max_retries is None:
        max_retries = len(configs)

    last_err = None
    for attempt in range(min(max_retries, len(configs))):
        cfg = select_model_config_lb(provider, 'llm')
        if not cfg:
            break

        # 复用已有的调用逻辑
        content, err = _call_llm_with_config(
            system_prompt, user_content, cfg, temperature)
        if not err:
            return content, None
        last_err = err

    return None, f'所有模型配置均失败（已尝试 {min(max_retries, len(configs))} 个 Key）: {last_err}'


def _check_connectivity(host, port, timeout=5):
    """检查目标主机端口是否可连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _http_request(url, data, headers, method='POST', timeout=60, retries=2):
    """发送 HTTP 请求，带重试逻辑"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8'), None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')[:200]
            last_err = '模型API请求失败 (HTTP %d): %s' % (e.code, err_body)
        except urllib.error.URLError as e:
            last_err = '模型API连接失败: %s' % str(e.reason)
        except socket.timeout:
            last_err = '模型API请求超时'
        except Exception as e:
            last_err = '模型API调用异常: ' + str(e)
        if attempt < retries:
            import time
            time.sleep(1)
    return None, last_err


def _call_llm(system_prompt, user_content, temperature=0.4):
    """调用最新启用的模型配置，返回回复文本"""
    return _call_llm_with_config(system_prompt, user_content, None, temperature)


def _call_llm_with_config(system_prompt, user_content, model_cfg=None, temperature=0.4):
    """调用指定模型配置的 LLM，model_cfg 为 None 时取最新启用的"""
    if model_cfg is None:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
            model_cfg = cur.fetchone()
        finally:
            db.close()
    if not model_cfg:
        return None, '没有可用的模型配置，请先在模型页面添加'
    api_key = decrypt_api_key(model_cfg['api_key'])
    base_url = (model_cfg['api_base_url'] or '').rstrip('/')
    chat_url = build_openai_url(base_url, 'chat/completions')
    model_name = model_cfg['model_name'] or model_cfg['credential_name'] or model_cfg['provider']

    # 预检查连接性
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    host = parsed.hostname or 'api.openai.com'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    if not _check_connectivity(host, port, timeout=5):
        return None, '无法连接到模型 API 服务器 (%s:%s)。请检查网络连接或更换为可访问的模型提供商（如 DeepSeek）。' % (host, port)

    payload = json.dumps({
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content}
        ],
        'temperature': temperature,
        'max_tokens': 2048,
        'stream': False
    }).encode('utf-8')

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}
    result_str, err = _http_request(chat_url, data=payload, headers=headers, timeout=60, retries=2)
    if err:
        return None, err

    try:
        result = json.loads(result_str)
        content = ''
        if 'choices' in result and result['choices']:
            content = result['choices'][0].get('message', {}).get('content', '')
        if not content:
            return None, '模型未返回内容，请重试'
        return content.strip(), None
    except Exception as e:
        return None, '解析模型响应失败: ' + str(e)


def _extract_json(text):
    """从 LLM 返回文本中提取 JSON 对象（兼容 markdown 代码块与前后杂质）"""
    import re as _re
    if not text:
        return None
    m = _re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1)
    start, end = text.find('{'), text.rfind('}')
    if start > -1 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except Exception:
        return None

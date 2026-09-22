# -*- coding: utf-8 -*-
"""
LLM 节点执行模块

负责执行大语言模型（LLM）调用节点，支持：
- 变量替换（{{variable}} 语法）
- 系统提示词与用户提示词分离
- 多 provider 模型配置匹配
- OpenAI 兼容 API 调用
- API Key 解密与 URL 构建
- JSON Schema 结构化输出（response_format）
"""

import json
from utils.llm import decrypt_api_key, build_openai_url


def _find_model_config(provider):
    """
    查找模型配置，支持多种 provider 格式匹配：
    - 精确匹配：provider 完全一致
    - langgenius 前缀：langgenius/openai/openai -> openai
    - 后缀匹配：openai -> 匹配包含 /openai 的记录
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        if not provider:
            cur.execute('SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
            return cur.fetchone()

        # 1. 精确匹配
        cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (provider,))
        cfg = cur.fetchone()
        if cfg:
            return cfg

        # 2. 从 langgenius/provider/provider 格式提取短名称匹配
        if provider.startswith('langgenius/'):
            parts = provider.split('/')
            if len(parts) >= 2:
                short_provider = parts[1]
                cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (short_provider,))
                cfg = cur.fetchone()
                if cfg:
                    return cfg

        # 3. 反向匹配：数据库存储的是 langgenius 格式，查询的是短名称
        cur.execute('SELECT * FROM model_configs WHERE provider LIKE %s AND status = 1 LIMIT 1', ('%/' + provider,))
        cfg = cur.fetchone()
        if cfg:
            return cfg

        # 4. 最后尝试取 provider 的最后一段进行匹配
        if '/' in provider:
            last_part = provider.split('/')[-1]
            cur.execute('SELECT * FROM model_configs WHERE provider = %s AND status = 1 LIMIT 1', (last_part,))
            return cur.fetchone()

        return None
    finally:
        db.close()


def _node_llm(data, context, model_cfg):
    """执行 LLM 节点"""
    # 解析 prompt_template
    prompt_template = data.get('prompt_template', [])
    system_text = ''
    user_text = ''
    for pt in prompt_template:
        if pt.get('role') == 'system':
            system_text = pt.get('text', '')
        elif pt.get('role') == 'user':
            user_text = pt.get('text', '')

    # 变量替换
    for k, v in context.items():
        if k.startswith('__'):
            continue  # 引擎内部键不参与替换
        if isinstance(v, (str, int, float)):
            sv = str(v)
            system_text = system_text.replace('{{' + k + '}}', sv)
            user_text = user_text.replace('{{' + k + '}}', sv)

    # 获取模型配置
    model = data.get('model', {})
    provider = model.get('provider', '')
    model_name = model.get('name', '')

    # 优先使用节点模型，否则使用应用默认模型
    if not model_name and model_cfg:
        try:
            m = json.loads(model_cfg.get('model', '{}'))
            model_name = m.get('name', '')
            provider = m.get('provider', '')
        except Exception:
            pass

    # 从 model_configs 表查找 API 凭证（支持多种 provider 格式匹配）
    cfg = _find_model_config(provider)

    if not cfg:
        raise Exception('没有可用的模型配置')

    # 安全加固：解密 API Key（如果已加密）
    api_key = decrypt_api_key(cfg['api_key'])
    base_url = (cfg['api_base_url'] or '').rstrip('/')
    final_model = model_name or cfg['model_name'] or cfg['credential_name'] or cfg['provider']
    completion_params = model.get('completion_params', {})
    temperature = completion_params.get('temperature', 0.7)

    # 调用 OpenAI 兼容 API
    messages = []
    if system_text:
        messages.append({'role': 'system', 'content': system_text})
    messages.append({'role': 'user', 'content': user_text or context.get('query', '')})

    payload_dict = {
        'model': final_model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': 2048,
        'stream': False
    }

    # JSON Schema 结构化输出（对齐 Dify 1.17 的 structured output）
    response_format = data.get('response_format') or completion_params.get('response_format')
    if response_format and isinstance(response_format, dict):
        # 支持两种格式：
        # 1. OpenAI 原生: {"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}
        # 2. 简化格式: {"type": "json_object"} 或 {"type": "json_schema", "schema": {...}}
        fmt_type = response_format.get('type', '')
        if fmt_type == 'json_schema':
            json_schema = response_format.get('json_schema', {})
            # 简化格式兼容：直接传 schema
            if 'schema' in json_schema:
                payload_dict['response_format'] = {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': json_schema.get('name', 'response'),
                        'strict': json_schema.get('strict', True),
                        'schema': json_schema['schema'],
                    }
                }
            else:
                payload_dict['response_format'] = response_format
        elif fmt_type == 'json_object':
            payload_dict['response_format'] = {'type': 'json_object'}

    payload = json.dumps(payload_dict, ensure_ascii=False).encode('utf-8')

    api_url = build_openai_url(base_url, 'chat/completions')
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}

    try:
        resp = _http_request(api_url, data=payload, headers=headers, method='POST', timeout=120)
        result = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise Exception(f'模型 API 连接失败，请检查网络连接。URL: {api_url}, 错误: {e}') from e

    content = ''
    total_tokens = 0
    structured_output = None
    if 'choices' in result and result['choices']:
        message = result['choices'][0].get('message', {})
        content = message.get('content', '')
        # 结构化输出：尝试解析 JSON
        if response_format and content:
            try:
                parsed = json.loads(content)
                structured_output = parsed
            except (json.JSONDecodeError, TypeError):
                pass
    if 'usage' in result:
        total_tokens = result['usage'].get('total_tokens', 0)

    return {
        'text': content,
        'output': content,
        'total_tokens': total_tokens,
        'structured_output': structured_output,
    }


def _http_request(url, data=None, headers=None, method='POST', timeout=120, retries=2):
    """
    带重试机制的 HTTP 请求函数

    参数:
        url: 请求 URL
        data: 请求体 (bytes)
        headers: 请求头字典
        method: HTTP 方法
        timeout: 超时时间 (秒)
        retries: 重试次数

    返回:
        响应对象
    """
    import time
    import logging
    import urllib.request
    import urllib.error
    import socket

    logger = logging.getLogger(__name__)

    # 预检查：解析 URL 并测试 connectivity
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if host:
            reachable, conn_err = _check_connectivity(host, port, timeout=5)
            if not reachable:
                error_msg = (
                    f'无法连接到模型 API 服务器 ({host}:{port})。'
                    f'请检查网络连接或更换为可访问的模型提供商（如 DeepSeek）。'
                    f'详情: {conn_err}'
                )
                logger.error(f'[HTTP] {error_msg}')
                raise ConnectionError(error_msg)
    except (ValueError, ImportError):
        pass  # URL 解析失败时跳过预检查

    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
            # 使用自定义 SSL 上下文和超时
            ctx = _create_ssl_context()
            response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return response
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            last_error = e
            # 检查是否是连接超时
            if 'WinError 10060' in str(e) or 'timed out' in str(e).lower():
                error_msg = (
                    f'连接模型 API 超时 ({url})。'
                    f'可能原因：1) 网络不稳定 2) API 服务器被防火墙阻止 3) 需要使用代理。'
                    f'建议更换为 DeepSeek 等国内可访问的模型。'
                )
                logger.error(f'[HTTP] {error_msg}')
                raise ConnectionError(error_msg) from e
            if attempt < retries:
                wait_time = 2 * (attempt + 1)
                logger.warning(f'[HTTP] 请求失败 (尝试 {attempt + 1}/{retries + 1}): {url}, 错误: {e}, {wait_time}秒后重试...')
                time.sleep(wait_time)
            else:
                logger.error(f'[HTTP] 请求最终失败: {url}, 错误: {e}')
                raise
        except Exception as e:
            logger.error(f'[HTTP] 请求异常: {url}, 错误: {type(e).__name__}: {e}')
            raise

    raise last_error


def _create_ssl_context():
    """创建 SSL 上下文，兼容各种证书配置"""
    import ssl
    ctx = ssl.create_default_context()
    return ctx


def _check_connectivity(host, port=443, timeout=5):
    """
    检查目标主机端口是否可达

    返回:
        (是否可达, 错误信息)
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, None
        else:
            return False, f'无法连接到 {host}:{port} (错误码: {result})'
    except socket.gaierror:
        return False, f'DNS 解析失败: {host}'
    except Exception as e:
        return False, f'网络检查失败: {e}'

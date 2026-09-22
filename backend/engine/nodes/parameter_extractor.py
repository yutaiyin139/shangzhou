# -*- coding: utf-8 -*-
"""
Parameter Extractor 参数提取节点执行模块

负责使用 LLM 从文本中提取结构化参数，支持：
- 参数定义（name / description / type / required）
- 多 provider 模型配置匹配
- API Key 解密与 OpenAI 兼容 API 调用
- JSON 结果解析与正则回退提取
- 类型转换（number / integer / boolean / array / string）
- 必填参数缺失检测
"""

import json
import re
from config import get_db
from utils.llm import decrypt_api_key, build_openai_url


def _node_parameter_extractor(data, context, model_cfg):
    """
    Parameter Extractor 节点 —— 使用 LLM 从文本中提取结构化参数。

    节点数据结构:
    - query: 要提取参数的输入文本变量选择器 ["node_id", "variable"]
    - parameters: 要提取的参数列表 [{name, description, type, required}]
    - model: 模型配置 {provider, name, completion_params}
    - reasoning_mode: 推理模式（prompt/function_call）
    - output: 输出变量名（默认 'extracted_params'）

    返回:
    - extracted_params: 提取的参数 {param_name: value, ...}
    - missing_required: 缺失的必填参数列表
    - raw_response: LLM 原始响应
    """
    # 获取要提取参数的输入文本
    query_selector = data.get('query', [])
    query = _resolve_selector(context, query_selector) if query_selector else context.get('query', '')

    if not query:
        return {
            'extracted_params': {},
            'missing_required': [],
            'raw_response': '',
        }

    # 获取要提取的参数定义
    parameters = data.get('parameters', [])
    if not parameters:
        return {
            'extracted_params': {},
            'missing_required': [],
            'raw_response': '',
        }

    # 获取输出变量名
    output_var = data.get('output', 'extracted_params')

    # 构建参数描述
    params_desc = []
    for param in parameters:
        param_name = param.get('name', '')
        param_desc = param.get('description', '')
        param_type = param.get('type', 'string')
        param_required = param.get('required', False)
        required_str = '（必填）' if param_required else '（可选）'
        params_desc.append(f'- {param_name}{required_str}: {param_desc} (类型: {param_type})')

    # 构建系统提示词
    system_text = f"""你是一个参数提取器。请从用户输入中提取以下参数：

{chr(10).join(params_desc)}

请以 JSON 格式返回提取结果，格式如下：
{{"参数名1": "值1", "参数名2": "值2", ...}}

规则：
1. 如果某个参数在输入中找不到，则不包含在结果中（不要写 null）
2. 参数值必须符合指定的类型
3. 只返回 JSON，不要返回其他内容
4. 保持原始文本中的准确信息，不要修改或推断"""

    user_text = f"用户输入：{query}"

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
    temperature = completion_params.get('temperature', 0.3)  # 参数提取使用较低温度

    # 调用 LLM
    messages = [
        {'role': 'system', 'content': system_text},
        {'role': 'user', 'content': user_text}
    ]

    llm_result = _call_llm(messages, final_model, api_key, base_url, temperature=temperature)
    response_text = llm_result.get('content', '')

    # 解析 JSON 结果
    extracted_params = {}
    missing_required = []

    try:
        # 尝试从响应中提取 JSON
        json_str = response_text
        # 如果响应包含 ```json 代码块，提取其中的内容
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0].strip()

        # 尝试解析 JSON
        extracted_params = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        # JSON 解析失败，尝试从文本中提取
        for param in parameters:
            param_name = param.get('name', '')
            # 尝试从响应中查找 "param_name": "value" 格式
            pattern = f'"{param_name}"\\s*:\\s*"([^"]*)"'
            match = re.search(pattern, response_text)
            if match:
                value = match.group(1)
                param_type = param.get('type', 'string')
                extracted_params[param_name] = _convert_type(value, param_type)

    # 检查必填参数
    for param in parameters:
        if param.get('required', False):
            param_name = param.get('name', '')
            if param_name not in extracted_params or extracted_params[param_name] in (None, ''):
                missing_required.append(param_name)

    # 类型转换
    for param in parameters:
        param_name = param.get('name', '')
        if param_name in extracted_params:
            param_type = param.get('type', 'string')
            extracted_params[param_name] = _convert_type(
                extracted_params[param_name], param_type
            )

    return {
        output_var: extracted_params,
        'extracted_params': extracted_params,
        'missing_required': missing_required,
        'raw_response': response_text,
    }


def _convert_type(value, target_type):
    """将值转换为目标类型"""
    if value is None:
        return None
    try:
        if target_type == 'number':
            if isinstance(value, (int, float)):
                return value
            return float(value)
        elif target_type == 'integer':
            if isinstance(value, int):
                return value
            return int(float(value))
        elif target_type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', '是')
            return bool(value)
        elif target_type == 'array' or target_type == 'list':
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(',') if v.strip()]
            return [value]
        else:
            return str(value)
    except (ValueError, TypeError):
        return value


def _resolve_selector(context, selector):
    """根据选择器路径从上下文中获取变量值"""
    if not selector:
        return None
    if isinstance(selector, str):
        selector = [selector]

    value = context
    for key in selector:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


def _find_model_config(provider):
    """
    查找模型配置，支持多种 provider 格式匹配：
    - 精确匹配：provider 完全一致
    - langgenius 前缀：langgenius/openai/openai -> openai
    - 后缀匹配：openai -> 匹配包含 /openai 的记录
    """
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


def _call_llm(messages, model_name, api_key, base_url, temperature=0.7, max_tokens=2048):
    """
    调用 OpenAI 兼容 API
    返回: {content: str, total_tokens: int}
    """
    payload = json.dumps({
        'model': model_name,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False
    }).encode('utf-8')

    api_url = build_openai_url(base_url, 'chat/completions')
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}

    try:
        resp = _http_request(api_url, data=payload, headers=headers, method='POST', timeout=120)
        result = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise Exception(f'模型 API 连接失败，请检查网络连接。URL: {api_url}, 错误: {e}') from e

    content = ''
    total_tokens = 0
    if 'choices' in result and result['choices']:
        content = result['choices'][0].get('message', {}).get('content', '')
    if 'usage' in result:
        total_tokens = result['usage'].get('total_tokens', 0)

    return {'content': content, 'total_tokens': total_tokens}


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

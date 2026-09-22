# -*- coding: utf-8 -*-
"""
Question Classifier 问题分类节点执行模块

负责使用 LLM 对问题进行分类，支持：
- 基于类别列表的自动分类
- 多 provider 模型配置匹配
- API Key 解密与 OpenAI 兼容 API 调用
- 分类结果解析（class_id / class_label / class_name / class_index）
"""

import json
from config import get_db
from utils.llm import decrypt_api_key, build_openai_url


def _node_question_classifier(data, context, model_cfg):
    """
    Question Classifier 节点 —— 使用 LLM 对问题进行分类。

    节点数据结构:
    - query_variable_selector: 要分类的查询变量选择器 ["node_id", "query"]
    - classes: 分类类别列表 [{id, label, name}]
    - model: 模型配置 {provider, name, completion_params}
    - output: 输出变量名（默认 'classification'）

    返回:
    - classification: 分类结果 {class_id, class_label, class_name, class_index}
    - class_id: 分类 ID
    - class_label: 分类标签
    """
    # 获取要分类的查询
    query_selector = data.get('query_variable_selector', [])
    query = _resolve_selector(context, query_selector) if query_selector else context.get('query', '')

    if not query:
        return {
            'classification': None,
            'class_id': None,
            'class_label': None,
            'class_index': -1,
        }

    # 获取分类类别
    classes = data.get('classes', [])
    if not classes:
        return {
            'classification': None,
            'class_id': None,
            'class_label': None,
            'class_index': -1,
        }

    # 获取输出变量名
    output_var = data.get('output', 'classification')

    # 构建分类提示
    classes_desc = []
    for i, cls in enumerate(classes):
        cls_id = cls.get('id', str(i + 1))
        cls_label = cls.get('label', cls.get('name', f'类别{i + 1}'))
        cls_name = cls.get('name', '')
        classes_desc.append(f'类别 {cls_id} ({cls_label}): {cls_name}')

    system_text = f"""你是一个问题分类器。请将用户的问题分类到以下类别中：

{chr(10).join(classes_desc)}

请严格按照以下格式输出：
类别ID: <类别ID>
类别名称: <类别名称>

只输出类别ID和类别名称，不要输出其他内容。"""

    user_text = f"用户问题：{query}"

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
    temperature = completion_params.get('temperature', 0.3)  # 分类使用较低温度

    # 调用 LLM
    messages = [
        {'role': 'system', 'content': system_text},
        {'role': 'user', 'content': user_text}
    ]

    llm_result = _call_llm(messages, final_model, api_key, base_url, temperature=temperature)
    response_text = llm_result.get('content', '')

    # 解析分类结果
    class_id = None
    class_label = None
    class_index = -1

    # 尝试从响应中解析类别ID
    for line in response_text.split('\n'):
        line = line.strip()
        if '类别ID' in line or 'class_id' in line.lower() or 'ID' in line:
            # 提取 ID
            for cls in classes:
                if cls.get('id', '') in line:
                    class_id = cls.get('id')
                    class_label = cls.get('label', cls.get('name', ''))
                    class_index = classes.index(cls)
                    break
        if '类别名称' in line or 'label' in line.lower():
            # 提取标签
            for cls in classes:
                if cls.get('label', '') in line:
                    class_label = cls.get('label')
                    if not class_id:
                        class_id = cls.get('id')
                        class_index = classes.index(cls)
                    break

    # 如果上面没匹配到，尝试直接搜索类别标签
    if not class_id:
        for i, cls in enumerate(classes):
            cls_label = cls.get('label', '')
            cls_id = cls.get('id', '')
            if cls_label in response_text or cls_id in response_text:
                class_id = cls_id
                class_label = cls_label
                class_index = i
                break

    # 如果还是没匹配到，尝试用第一个类别作为默认
    if not class_id and classes:
        class_id = classes[0].get('id')
        class_label = classes[0].get('label', classes[0].get('name', ''))
        class_index = 0

    class_name = ''
    if class_index >= 0 and class_index < len(classes):
        class_name = classes[class_index].get('name', '')

    return {
        # 路由句柄：与画布边的 sourceHandle（== class id）对齐，见 engine/graph_scheduler.py
        '__branch__': class_id,
        output_var: {
            'class_id': class_id,
            'class_label': class_label,
            'class_name': class_name,
            'class_index': class_index,
        },
        'class_id': class_id,
        'class_label': class_label,
        'class_name': class_name,
        'class_index': class_index,
        'raw_response': response_text,
    }


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

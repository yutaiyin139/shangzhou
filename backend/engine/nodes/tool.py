# -*- coding: utf-8 -*-
"""
工具节点执行模块

负责执行工具调用节点，支持：
- 内置工具（time/code/webscraper/audio）
- 自定义工具（从数据库加载，支持 http/code/knowledge/calculator 类型）
- 统一工具运行时（engine.tool_runtime）调用
- 变量引用解析（{{variable}} 与 {{#node.var#}} 语法）
- 工具调用日志记录
"""

import json
import urllib.request


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


def _node_tool(data, context, model_cfg=None):
    """
    工具节点 —— 实际调用工具并返回结果。

    节点数据结构:
    - provider_id: 工具提供者 ID（audio/code/time/webscraper 或自定义工具 ID）
    - tool_name: 工具名称（如 current_time, run_code, web_scraper）
    - tool_parameters: 参数配置 {param_name: {value: ..., type: ...}}
    - output: 输出变量名（默认 'tool_output'）

    返回: context + {output: 工具结果, tool_output: 工具结果}
    """
    import time
    start_time = time.time()

    provider_id = data.get('provider_id', '')
    tool_name = data.get('tool_name', '')
    tool_parameters = data.get('tool_parameters', {})
    output_var = data.get('output', 'tool_output')

    if not provider_id or not tool_name:
        return {output_var: '', 'tool_output': '', 'tool_error': '未配置工具'}

    # 解析变量引用
    resolved_params = _resolve_tool_parameters(tool_parameters, context)

    # 调用工具
    try:
        result = _invoke_tool(provider_id, tool_name, resolved_params, context)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 记录工具调用日志
        try:
            from routes.tools import log_tool_call
            log_tool_call(
                workflow_run_id=context.get('__workflow_run_id__', ''),
                node_id=data.get('_node_id', ''),
                node_type='tool',
                provider_id=provider_id,
                tool_name=tool_name,
                parameters=resolved_params,
                result=result,
                status='success',
                elapsed_ms=elapsed_ms
            )
        except Exception:
            pass

        return {
            output_var: str(result),
            'tool_output': result,
            'tool_status': 'success',
            'tool_provider': provider_id,
            'tool_name': tool_name,
            'tool_elapsed_ms': elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 记录错误日志
        try:
            from routes.tools import log_tool_call
            log_tool_call(
                workflow_run_id=context.get('__workflow_run_id__', ''),
                node_id=data.get('_node_id', ''),
                node_type='tool',
                provider_id=provider_id,
                tool_name=tool_name,
                parameters=resolved_params,
                result='',
                status='error',
                error_message=str(e),
                elapsed_ms=elapsed_ms
            )
        except Exception:
            pass

        return {
            output_var: f'工具调用错误: {str(e)}',
            'tool_output': '',
            'tool_status': 'error',
            'tool_error': str(e),
            'tool_elapsed_ms': elapsed_ms,
        }


def _resolve_tool_parameters(tool_parameters, context):
    """
    解析工具参数中的变量引用。

    支持格式:
    - 字符串: "value" 或 "{{#node.var#}}" 或 "{{var}}"
    - 对象: {"value": "...", "type": "string"}
    """
    resolved = {}
    for k, v in tool_parameters.items():
        if isinstance(v, dict):
            val = v.get('value', '')
            if isinstance(val, str):
                resolved[k] = _resolve_variable_references(val, context)
            else:
                resolved[k] = val
        elif isinstance(v, str):
            resolved[k] = _resolve_variable_references(v, context)
        else:
            resolved[k] = v
    return resolved


def _resolve_variable_references(value, context):
    """
    解析变量引用。
    支持格式:
    - {{#node.var#}}: 从上下文中按路径取值
    - {{var}}: 从上下文中直接取值
    """
    if not isinstance(value, str):
        return value

    import re
    # 替换 {{#node.var#}} 格式
    for match in re.finditer(r'\{\{#(.+?)#\}\}', value):
        selector = match.group(1).split('.')
        val = _resolve_selector(context, selector)
        if val is not None:
            value = value.replace(match.group(0), str(val))

    # 替换 {{var}} 格式（简单变量名）
    for match in re.finditer(r'\{\{([^{}#]+?)\}\}', value):
        key = match.group(1).strip()
        if key in context:
            val = context[key]
            if val is not None:
                value = value.replace(match.group(0), str(val))

    return value


def _invoke_tool(provider_id, tool_name, params, context):
    """
    调用指定工具。

    统一入口在 engine.tool_runtime:
    - tool_builtin_providers 已安装内置工具（calculator/json/file/time/code 等）
    - tool_api_providers 自定义 OpenAPI 工具（HTTP，SSRF 防护）
    - dify_tool_providers 旧版自定义工具
    """
    from engine.tool_runtime import invoke_tool, ToolNotConfigured
    try:
        return invoke_tool(provider_id, tool_name, params, context)
    except ToolNotConfigured as e:
        return str(e)


def _invoke_builtin_tool(provider_id, tool_name, params, context):
    """
    调用内置工具。

    内置工具列表:
    - time/current_time: 获取当前时间
    - code/run_code: 执行 Python 代码
    - webscraper/web_scraper: 抓取网页内容
    - audio/text_to_speech: 文本转语音（需外部 API）
    - audio/speech_to_text: 语音转文本（需外部 API）
    """
    if provider_id == 'time' and tool_name == 'current_time':
        from datetime import datetime
        fmt = params.get('format', '%Y-%m-%d %H:%M:%S')
        return datetime.now().strftime(fmt)

    elif provider_id == 'code' and tool_name == 'run_code':
        code = params.get('code', '')
        lang = params.get('language', 'python')
        if lang == 'python':
            # 安全加固：使用子进程隔离沙箱执行
            from utils.sandbox import execute_code_safely
            result = execute_code_safely(code, params, timeout=60)
            if result['success']:
                return str(result['result']) if result['result'] is not None else ''
            return f'代码执行错误: {result["error"]}'
        return '仅支持 Python 语言'

    elif provider_id == 'webscraper' and tool_name == 'web_scraper':
        url = params.get('url', '')
        if not url:
            return '错误：未提供 URL'
        # 安全加固：SSRF 防护检查
        from utils.ssrf import is_safe_url
        if not is_safe_url(url):
            return '错误：URL 被安全策略禁止（SSRF 防护）'
        req = urllib.request.Request(url, headers={
            'User-Agent': params.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8', errors='replace')
            # 简单提取正文（去除 HTML 标签）
            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:5000]

    elif provider_id == 'audio':
        return _invoke_audio_tool(tool_name, params, context)

    return f'未知工具: {provider_id}/{tool_name}'


def _invoke_audio_tool(tool_name, params, context):
    """
    在工作流中调用音频工具（TTS/STT）。

    参数:
        tool_name: 'text_to_speech' 或 'speech_to_text'
        params: 工具参数
        context: 工作流上下文

    返回:
        TTS: JSON 字符串 {'audio_url': '/uploads/audio/xxx.mp3'}
        STT: 识别的文本字符串
    """
    from utils.audio import (
        text_to_speech, speech_to_text, get_default_audio_config,
        save_audio_file,
    )

    if tool_name == 'text_to_speech':
        cfg = get_default_audio_config('tts')
        if not cfg:
            return '错误：TTS 模型未配置，请先在模型管理中添加 TTS 模型'
        text = str(params.get('text', ''))
        if not text:
            return '错误：TTS 文本不能为空'
        voice = params.get('voice') or None
        try:
            audio_bytes = text_to_speech(text, cfg, voice=voice)
            audio_url = save_audio_file(audio_bytes)
            import json
            return json.dumps({'audio_url': audio_url}, ensure_ascii=False)
        except Exception as e:
            return f'错误：TTS 调用失败 - {str(e)}'

    elif tool_name == 'speech_to_text':
        cfg = get_default_audio_config('stt')
        if not cfg:
            return '错误：STT 模型未配置，请先在模型管理中添加 STT 模型'
        audio_file = params.get('audio_file', '')
        if not audio_file:
            return '错误：未提供音频文件'
        try:
            import os
            if isinstance(audio_file, str) and audio_file.startswith('/uploads/'):
                file_path = audio_file.lstrip('/')
                with open(file_path, 'rb') as f:
                    audio_bytes = f.read()
                filename = os.path.basename(file_path)
            else:
                return '错误：不支持的音频文件来源（仅支持本地上传文件）'
            text = speech_to_text(audio_bytes, filename, cfg)
            return text
        except Exception as e:
            return f'错误：STT 调用失败 - {str(e)}'

    return f'未知音频工具: {tool_name}'


def _invoke_custom_tool(provider_id, tool_name, params, context):
    """
    调用自定义工具（从数据库加载工具定义）。

    自定义工具存储在 dify_tool_providers 表中，
    支持 http/code/knowledge/calculator 等类型。
    """
    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT * FROM dify_tool_providers
            WHERE id = %s OR name = %s
            LIMIT 1
        ''', (provider_id, provider_id))
        tool_provider = cur.fetchone()
    finally:
        db.close()

    if not tool_provider:
        return f'未找到自定义工具: {provider_id}'

    # 解析工具定义
    try:
        tools_json = tool_provider.get('tools', '[]')
        tools = json.loads(tools_json) if isinstance(tools_json, str) else tools_json
    except Exception:
        tools = []

    # 查找匹配的工具
    tool_def = None
    for t in tools:
        if t.get('name') == tool_name:
            tool_def = t
            break

    if not tool_def:
        return f'工具 {tool_name} 未在提供者 {provider_id} 中找到'

    # 根据工具类型执行
    tool_type = tool_def.get('type', 'http')
    if tool_type == 'http':
        return _tool_http(tool_def, params, context)
    elif tool_type == 'code':
        return _tool_code(tool_def, params, context)
    elif tool_type == 'knowledge':
        return _tool_knowledge(tool_def, params, context)
    elif tool_type == 'calculator':
        return _tool_calculator(tool_def, params, context)
    else:
        return f'不支持的工具类型: {tool_type}'

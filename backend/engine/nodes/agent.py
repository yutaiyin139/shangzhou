# -*- coding: utf-8 -*-
"""
Agent 节点执行模块

负责执行智能体（Agent）节点，支持多种策略运行时（agent_v2）：
- react: ReAct 循环（文本格式解析，默认）
- function_call: OpenAI tools 协议（原生函数调用）
- plan_execute: 规划-执行（先规划步骤，再逐步执行）

内置工具类型：
- http: HTTP 请求工具（含 SSRF 防护）
- code: Python 代码执行工具（安全沙箱隔离）
- knowledge: 知识库检索工具
- calculator: 计算器工具
"""

import json
import urllib.request
import urllib.error

from config import get_db
from utils.llm import decrypt_api_key


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

        # 精确匹配
        cur.execute('SELECT * FROM model_configs WHERE status = 1 AND provider = %s ORDER BY updated_at DESC LIMIT 1', (provider,))
        row = cur.fetchone()
        if row:
            return row

        # 去掉 langgenius/<provider>/<model> 包裹，用中间短名匹配（与 nodes/llm.py 一致）
        if provider.startswith('langgenius/'):
            parts = provider.split('/')
            short_provider = parts[1] if len(parts) >= 3 else provider[len('langgenius/'):]
            cur.execute('SELECT * FROM model_configs WHERE status = 1 AND provider = %s ORDER BY updated_at DESC LIMIT 1', (short_provider,))
            row = cur.fetchone()
            if row:
                return row

        # 后缀匹配（数据库存 langgenius 格式，查询用短名）
        cur.execute('SELECT * FROM model_configs WHERE status = 1 AND provider LIKE %s ORDER BY updated_at DESC LIMIT 1', (f'%/{provider}',))
        row = cur.fetchone()
        if row:
            return row

        # 末段匹配（如 deepseek）
        if '/' in provider:
            cur.execute('SELECT * FROM model_configs WHERE status = 1 AND provider = %s ORDER BY updated_at DESC LIMIT 1', (provider.split('/')[-1],))
            row = cur.fetchone()
            if row:
                return row

        # 任意可用模型
        cur.execute('SELECT * FROM model_configs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1')
        return cur.fetchone()
    finally:
        db.close()


def _node_agent(data, context, model_cfg):
    """
    Agent 节点 —— 支持多种策略的智能体运行时（agent_v2）。

    支持策略（通过 data.strategy 或 data.config.strategy 指定）：
    - react: ReAct 循环（文本格式解析，默认）
    - function_call: OpenAI tools 协议（原生函数调用）
    - plan_execute: 规划-执行（先规划步骤，再逐步执行）

    节点数据结构:
    - model: 模型配置 {provider, name, completion_params}
    - prompt: 系统提示词（Agent 角色定义）
    - user_prompt: 用户任务/问题
    - tools: 可用工具列表 [{name, description, type, parameters}]
    - max_iterations: 最大迭代次数（默认 5）
    - output: 输出变量名（默认 'output'）
    - strategy: 策略类型（react / function_call / plan_execute）
    - config: 策略配置 {strategy, max_iterations, output_format, fallback_model}
    """
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

    # 获取 Agent 配置
    system_prompt = data.get('prompt', '你是一个智能助手，可以使用工具来帮助用户解决问题。')
    user_prompt = data.get('user_prompt', context.get('query', ''))
    # 变量替换
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            user_prompt = user_prompt.replace('{{' + k + '}}', str(v))
            system_prompt = system_prompt.replace('{{' + k + '}}', str(v))

    tools = data.get('tools', [])
    max_iterations = data.get('max_iterations', 5)
    output_var = data.get('output', 'output')

    # 解析策略配置
    agent_config = data.get('config', {})
    strategy_name = data.get('strategy') or agent_config.get('strategy', 'react')

    # 构建 LLM 配置
    llm_config = {
        'model': final_model,
        'api_key': api_key,
        'base_url': base_url,
        'temperature': temperature,
        'max_tokens': completion_params.get('max_tokens', 2048),
        'max_iterations': agent_config.get('max_iterations', max_iterations),
    }

    # 构建消息列表
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    # 使用策略抽象层执行
    try:
        from engine.agent_strategies import execute_agent_strategy
        result = execute_agent_strategy(strategy_name, messages, tools, context, llm_config)
    except ImportError:
        # 兼容：策略模块不存在时回退到原生 ReAct
        result = _run_react_fallback(messages, tools, context, llm_config)
    except ValueError as e:
        # 未知策略，回退到 react
        result = _run_react_fallback(messages, tools, context, llm_config)

    final_answer = result.get('output', '')
    tool_calls_history = result.get('tool_calls', [])
    thought_chain = result.get('thought_chain', [])
    total_tokens = result.get('tokens', 0)
    iterations_used = result.get('iterations', 0)

    return {
        output_var: final_answer,
        'agent_output': final_answer,
        'tool_calls': tool_calls_history,
        'thought_chain': thought_chain,
        'total_tokens': total_tokens,
        'iterations_used': iterations_used,
        'strategy_used': strategy_name,
    }


def _run_react_fallback(messages, tools, context, llm_config):
    """
    ReAct 回退实现 —— 当策略模块不可用时使用
    保留原有逻辑，确保向后兼容
    """
    from engine.agent_strategies import ReActStrategy
    strategy = ReActStrategy()
    return strategy.run(messages, tools, context, llm_config)


def _build_tool_descriptions(tools):
    """构建工具描述文本"""
    if not tools:
        return ''

    descriptions = []
    for i, tool in enumerate(tools):
        name = tool.get('name', '')
        desc = tool.get('description', '')
        tool_type = tool.get('type', 'http')
        params = tool.get('parameters', {})

        desc_text = f'{i + 1}. {name}'
        if desc:
            desc_text += f': {desc}'
        desc_text += f' (类型: {tool_type})'
        if params:
            desc_text += f'\n   参数: {json.dumps(params, ensure_ascii=False)}'
        descriptions.append(desc_text)

    return '\n'.join(descriptions)


def _parse_agent_response(response):
    """
    解析 Agent 节点的 LLM 响应
    支持格式：
    - Action: xxx / Action Input: xxx
    - Final Answer: xxx
    - JSON 格式: {"action": "xxx", "action_input": {...}}
    """
    if not response:
        return {'type': 'unknown', 'content': ''}

    response = response.strip()

    # 尝试解析 JSON 格式
    try:
        if response.startswith('{') or response.startswith('['):
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                if 'action' in parsed:
                    return {
                        'type': 'action',
                        'action': parsed.get('action', ''),
                        'action_input': parsed.get('action_input', parsed.get('input', {}))
                    }
                elif 'final_answer' in parsed or 'answer' in parsed:
                    return {
                        'type': 'final_answer',
                        'content': parsed.get('final_answer', parsed.get('answer', ''))
                    }
    except json.JSONDecodeError:
        pass

    # 解析文本格式
    lines = response.split('\n')
    result = {}

    for line in lines:
        line = line.strip()
        if line.lower().startswith('action:'):
            result['action'] = line[7:].strip()
        elif line.lower().startswith('action input:'):
            input_str = line[13:].strip()
            try:
                result['action_input'] = json.loads(input_str)
            except json.JSONDecodeError:
                result['action_input'] = input_str
        elif line.lower().startswith('final answer:'):
            result['final_answer'] = line[13:].strip()
        elif line.lower().startswith('observation:'):
            result['observation'] = line[12:].strip()

    if 'final_answer' in result:
        return {'type': 'final_answer', 'content': result['final_answer']}
    elif 'action' in result:
        return {
            'type': 'action',
            'action': result['action'],
            'action_input': result.get('action_input', {})
        }
    else:
        return {'type': 'unknown', 'content': response}


def _execute_agent_tool(tool_name, tool_input, tools, context):
    """
    执行 Agent 工具
    支持的工具类型：
    - http: HTTP 请求
    - code: Python 代码执行
    - knowledge: 知识库检索
    - calculator: 计算器
    """
    # 查找工具定义
    tool_def = None
    for t in tools:
        if t.get('name') == tool_name:
            tool_def = t
            break

    if not tool_def:
        return f'错误：未找到工具 "{tool_name}"'

    tool_type = tool_def.get('type', 'http')

    try:
        if tool_type == 'http':
            return _tool_http(tool_def, tool_input, context)
        elif tool_type == 'code':
            return _tool_code(tool_def, tool_input, context)
        elif tool_type == 'knowledge':
            return _tool_knowledge(tool_def, tool_input, context)
        elif tool_type == 'calculator':
            return _tool_calculator(tool_def, tool_input, context)
        else:
            return f'错误：不支持的工具类型 "{tool_type}"'
    except Exception as e:
        return f'工具执行错误: {str(e)}'


def _tool_http(tool_def, tool_input, context):
    """HTTP 请求工具（含 SSRF 防护）"""
    url = tool_def.get('url', '')
    method = tool_def.get('method', 'get').upper()

    # 变量替换
    if isinstance(tool_input, dict):
        for k, v in tool_input.items():
            url = url.replace('{{' + k + '}}', str(v))
    url = url.replace('{{query}}', str(tool_input))

    # 从上下文替换变量
    for k, v in context.items():
        if isinstance(v, str):
            url = url.replace('{{' + k + '}}', v)

    # 安全加固：SSRF 防护检查
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        return '错误：URL 被安全策略禁止（SSRF 防护）'

    headers = {}
    headers_str = tool_def.get('headers', '')
    if headers_str:
        for line in headers_str.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip()] = v.strip()

    body = None
    if method in ('POST', 'PUT', 'PATCH') and tool_input:
        body = json.dumps(tool_input, ensure_ascii=False).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='replace')[:2000]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')[:500]
        return f'HTTP {e.code}: {err_body}'


def _tool_code(tool_def, tool_input, context):
    """代码执行工具—— 安全沙箱隔离执行"""
    code = tool_def.get('code', '')
    if not code:
        return '错误：未配置代码'

    # 构建输入变量
    input_vars = dict(context)
    if isinstance(tool_input, dict):
        input_vars.update(tool_input)
    else:
        input_vars['input'] = tool_input

    # 安全加固：使用子进程隔离沙箱执行
    from utils.sandbox import execute_code_safely
    result = execute_code_safely(code, input_vars, timeout=60)
    if result['success']:
        return str(result['result']) if result['result'] is not None else ''
    return f'代码执行错误: {result["error"]}'


def _tool_knowledge(tool_def, tool_input, context):
    """知识库检索工具"""
    dataset_ids = tool_def.get('dataset_ids', [])
    query = str(tool_input) if tool_input else context.get('query', '')

    if not dataset_ids or not query:
        return '错误：未配置知识库或查询内容'

    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(dataset_ids))
        cur.execute(f'''
            SELECT content FROM dify_document_segments
            WHERE dataset_id IN ({placeholders}) AND enabled = 1 AND status = 'completed'
            ORDER BY hit_count DESC LIMIT 5
        ''', dataset_ids)
        rows = cur.fetchall()
    finally:
        db.close()

    if not rows:
        return '知识库中未找到相关内容'

    return '\n\n'.join((r['content'] or '') for r in rows)


def _tool_calculator(tool_def, tool_input, context):
    """计算器工具"""
    expression = str(tool_input) if tool_input else ''
    if not expression:
        return '错误：未提供计算表达式'

    # 安全计算：只允许基本数学运算
    try:
        # 清理表达式，只允许数字和运算符
        allowed_chars = set('0123456789+-*/().%^ ')
        if not all(c in allowed_chars for c in expression):
            return '错误：表达式包含不允许的字符'

        # 使用 eval 计算（在安全环境下）
        result = eval(expression, {'__builtins__': {}}, {})
        return str(result)
    except Exception as e:
        return f'计算错误: {str(e)}'

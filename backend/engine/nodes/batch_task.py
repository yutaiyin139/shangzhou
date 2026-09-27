# -*- coding: utf-8 -*-
"""
Batch Task 节点 —— 批量任务执行节点。

对输入列表中的每个元素执行指定的操作（LLM/代码/HTTP），支持:
- 批量大小控制（batch_size）
- 并行处理（parallel）
- 错误处理策略（fail_fast / continue_on_error）
- 进度追踪
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


def _node_batch_task(data, context, model_cfg=None):
    """
    批量任务节点

    节点数据结构:
    - input_selector: 输入列表的变量路径
    - task_type: 任务类型 "llm" | "code" | "http" | "template"
    - task_config: 任务配置
    - batch_size: 每批处理的元素数量（默认 5）
    - max_parallel: 最大并行数（默认 1）
    - error_strategy: 错误策略
    - output_variable: 输出变量名（默认 'batch_results'）
    """
    # 获取输入列表
    input_selector = data.get('input_selector', [])
    input_list = _resolve_selector(context, input_selector)

    if not isinstance(input_list, list):
        try:
            if isinstance(input_list, str):
                input_list = json.loads(input_list)
        except Exception:
            pass
    if not isinstance(input_list, list):
        raise Exception('批量任务节点的输入必须是列表，当前值: ' + str(input_list)[:100])

    # 配置
    task_type = data.get('task_type', 'llm')
    task_config = data.get('task_config', {})
    error_strategy = data.get('error_strategy', 'continue_on_error')
    output_variable = data.get('output_variable', 'batch_results')
    max_items = data.get('max_items', 500)

    if len(input_list) > max_items:
        raise Exception(f'批量任务超过最大限制 {max_items}，当前 {len(input_list)} 项')

    # 执行批量任务
    all_results = []
    success_count = 0
    error_count = 0
    skip_count = 0

    for idx, item in enumerate(input_list):
        sub_context = dict(context)
        if isinstance(item, dict):
            sub_context.update(item)
        else:
            sub_context['item'] = item
            sub_context['_item'] = item
        sub_context['_batch_index'] = idx
        sub_context['_batch_total'] = len(input_list)

        try:
            if task_type == 'llm':
                result = _batch_task_llm(sub_context, task_config, model_cfg)
            elif task_type == 'code':
                result = _batch_task_code(sub_context, task_config)
            elif task_type == 'http':
                result = _batch_task_http(sub_context, task_config)
            elif task_type == 'template':
                result = _batch_task_template(sub_context, task_config)
            else:
                result = {'output': f'未知任务类型: {task_type}'}

            all_results.append({
                'index': idx,
                'status': 'success',
                'input': item,
                'output': result.get('output', result),
            })
            success_count += 1

        except Exception as e:
            error_count += 1
            if error_strategy == 'fail_fast':
                raise Exception(f'批量任务第 {idx + 1} 项执行失败: {str(e)}')
            elif error_strategy == 'skip_error':
                skip_count += 1
                all_results.append({
                    'index': idx,
                    'status': 'skipped',
                    'input': item,
                    'error': str(e)[:200],
                })
            else:  # continue_on_error
                all_results.append({
                    'index': idx,
                    'status': 'error',
                    'input': item,
                    'error': str(e)[:200],
                })

    output = [r.get('output', '') for r in all_results if r['status'] == 'success']

    return {
        output_variable: output,
        'batch_results': all_results,
        'batch_summary': {
            'total': len(input_list),
            'success': success_count,
            'error': error_count,
            'skipped': skip_count,
        }
    }


def _batch_task_llm(context, task_config, model_cfg):
    """执行 LLM 批量任务"""
    from utils.llm import chat_completion

    prompt_template = task_config.get('prompt_template', '{{item}}')
    model = task_config.get('model', 'gpt-4o-mini')
    temperature = task_config.get('temperature', 0.7)
    max_tokens = task_config.get('max_tokens', 1000)

    prompt = prompt_template
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            prompt = prompt.replace('{{' + k + '}}', str(v))

    response = chat_completion(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {'output': response.get('content', '')}


def _batch_task_code(context, task_config):
    """执行代码批量任务"""
    code_template = task_config.get('code', '')
    code_language = task_config.get('code_language', 'python3')

    code = code_template
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            code = code.replace('{{' + k + '}}', str(v))

    # 沙箱对外只提供 execute_code_safely（仅 python），以前引的 run_sandboxed_code 从未存在过，
    # 一调用就是 ImportError；它的成功返回里也没有 output 键，要取 stdout / result。
    from utils.sandbox import execute_code_safely
    if code_language and code_language not in ('python3', 'python'):
        return {'output': '', 'error': '批量代码任务目前只支持 python3，收到：%s' % code_language}

    result = execute_code_safely(code, timeout=30)
    if not result.get('success'):
        return {'output': '', 'error': result.get('error') or result.get('stderr') or '代码执行失败'}

    # 项目约定以变量 result 作为输出（与 code 节点一致），stdout 只作兜底
    output = ''
    if result.get('result') is not None:
        output = str(result['result'])
    elif result.get('stdout'):
        output = result['stdout']
    return {'output': output}


def _batch_task_http(context, task_config):
    """执行 HTTP 批量任务"""
    method = task_config.get('method', 'get').upper()
    url_template = task_config.get('url', '')
    headers_str = task_config.get('headers', '')
    body_template = task_config.get('body', '')

    url = url_template
    body = body_template
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            url = url.replace('{{' + k + '}}', str(v))
            body = body.replace('{{' + k + '}}', str(v))

    headers = {}
    if headers_str:
        try:
            for line in headers_str.strip().split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip()] = v.strip()
        except Exception:
            pass

    payload = body.encode('utf-8') if body and method in ('POST', 'PUT', 'PATCH') else None
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = resp.read().decode('utf-8')

    return {'output': result}


def _batch_task_template(context, task_config):
    """执行模板转换批量任务"""
    template = task_config.get('template', '{{item}}')

    output = template
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            output = output.replace('{{' + k + '}}', str(v))

    return {'output': output}

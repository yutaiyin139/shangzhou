# -*- coding: utf-8 -*-
"""工具运行时 —— tool 节点的实际执行层

三层查找（与 routes/tools.py 的提供者模型一致）:
1. tool_builtin_providers  —— 平台内置工具（本地可算的直接执行；
   依赖外部 API 的给出明确的"未配置"提示而不是静默失败）
2. tool_api_providers       —— 自定义 OpenAPI 工具（HTTP 调用，SSRF 防护）
3. dify_tool_providers      —— 旧版自定义工具（tool_name 匹配，修正原 name 列 bug）

历史缺陷（本次修复）:
- _invoke_tool 只认硬编码 4 个内置提供者，DB 里已安装的 calculator/json/file 等
  12 个提供者全部落到 custom 分支后报 SQL 错误（dify_tool_providers 无 name 列）。
"""
import ast
import io
import json
import os
import re
import urllib.request

from config import get_db


class ToolNotConfigured(Exception):
    """工具依赖的外部服务未配置（SMTP / API Key 等）"""


# ---------------------------------------------------------------
# 1. 本地可算的内置动作
# ---------------------------------------------------------------

def _safe_eval(expr):
    """安全算术表达式求值（仅允许数值运算节点）"""
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError('只允许数值常量')
        if isinstance(node, ast.BinOp):
            l, r = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Add):
                return l + r
            if isinstance(node.op, ast.Sub):
                return l - r
            if isinstance(node.op, ast.Mult):
                return l * r
            if isinstance(node.op, ast.Div):
                return l / r
            if isinstance(node.op, ast.Pow):
                return l ** r
            if isinstance(node.op, ast.Mod):
                return l % r
            if isinstance(node.op, ast.FloorDiv):
                return l // r
            raise ValueError('不支持的运算符')
        if isinstance(node, ast.UnaryOp):
            v = _eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return +v
            raise ValueError('不支持的一元运算符')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            import math
            fn = getattr(math, node.func.id, None)
            if fn is None or node.func.id.startswith('_'):
                raise ValueError(f'不允许的函数: {node.func.id}')
            return fn(*[_eval(a) for a in node.args])
        raise ValueError('表达式包含不允许的语法')
    return _eval(ast.parse(expr, mode='eval'))


_UNIT_TABLE = {
    # 类别: (单位 -> 到基准单位的乘数)
    'length': {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'km': 1000.0,
               'in': 0.0254, 'ft': 0.3048, 'yd': 0.9144, 'mi': 1609.344},
    'weight': {'mg': 0.001, 'g': 1.0, 'kg': 1000.0, 't': 1e6,
               'oz': 28.3495, 'lb': 453.592},
    'time': {'ms': 0.001, 's': 1.0, 'min': 60.0, 'h': 3600.0, 'd': 86400.0},
}


def _convert_unit(value, from_unit, to_unit):
    for table in _UNIT_TABLE.values():
        if from_unit in table and to_unit in table:
            return value * table[from_unit] / table[to_unit]
    # 温度特判
    if from_unit == 'c' and to_unit == 'f':
        return value * 9 / 5 + 32
    if from_unit == 'f' and to_unit == 'c':
        return (value - 32) * 5 / 9
    if from_unit == 'c' and to_unit == 'k':
        return value + 273.15
    if from_unit == 'k' and to_unit == 'c':
        return value - 273.15
    raise ValueError(f'不支持的单位换算: {from_unit} -> {to_unit}')


def _safe_file_path(name):
    """限制文件操作在 uploads/tools 目录内（防路径穿越）"""
    base = os.path.abspath(os.path.join('uploads', 'tools'))
    path = os.path.abspath(os.path.join(base, name))
    if not path.startswith(base + os.sep):
        raise ValueError('非法文件路径')
    return path


def run_builtin_action(provider_name, action_name, params):
    """执行内置工具动作。返回值一律为字符串或结构化数据。"""
    p, a = provider_name, action_name

    if p == 'calculator' and a == 'calculate':
        expr = str(params.get('expression', '')).strip()
        if not expr:
            return '错误：未提供表达式'
        try:
            return str(_safe_eval(expr))
        except Exception as e:
            return f'表达式错误: {e}'

    if p == 'calculator' and a == 'convert_unit':
        try:
            return str(round(_convert_unit(float(params.get('value', 0)),
                                           str(params.get('from_unit', '')).lower(),
                                           str(params.get('to_unit', '')).lower()), 6))
        except Exception as e:
            return f'单位换算错误: {e}'

    if p == 'time' and a == 'current_time':
        from datetime import datetime
        return datetime.now().strftime(params.get('format', '%Y-%m-%d %H:%M:%S'))

    if p == 'code' and a == 'run_code':
        from utils.sandbox import execute_code_safely
        code = params.get('code', '')
        if not code:
            return '错误：未提供代码'
        result = execute_code_safely(code, params, timeout=60)
        if result['success']:
            return '' if result['result'] is None else str(result['result'])
        return f'代码执行错误: {result["error"]}'

    if p == 'json' and a == 'parse_json':
        text = params.get('text', '')
        try:
            return json.loads(text) if isinstance(text, str) else text
        except Exception as e:
            return f'JSON 解析错误: {e}'

    if p == 'json' and a == 'to_json':
        obj = params.get('data', params.get('object', ''))
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception as e:
            return f'JSON 序列化错误: {e}'

    if p == 'file' and a in ('read_file', 'write_file'):
        try:
            path = _safe_file_path(str(params.get('path') or params.get('filename') or ''))
            if a == 'read_file':
                if not os.path.exists(path):
                    return f'文件不存在: {path}'
                with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            content = params.get('content', '')
            with io.open(path, 'w', encoding='utf-8') as f:
                f.write(str(content))
            return f'已写入 {len(str(content))} 字符: {path}'
        except Exception as e:
            return f'文件操作错误: {e}'

    if p == 'webscraper' and a == 'web_scraper':
        return _fetch_url_text(params.get('url', ''), params.get('selector', ''))

    if p == 'search' and a == 'fetch_url':
        return _fetch_url_text(params.get('url', ''), '')

    if p == 'database' and a == 'execute_sql':
        sql = str(params.get('sql', '')).strip()
        if not re.match(r'^\s*select\b', sql, re.I):
            return '错误：仅允许 SELECT 查询'
        if len(sql) > 2000:
            return '错误：SQL 过长'
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
            return json.dumps(rows, ensure_ascii=False, default=str)[:5000]
        except Exception as e:
            return f'SQL 执行错误: {str(e)[:200]}'
        finally:
            db.close()

    if p == 'email' and a == 'send_email':
        # 3.6: SMTP 已落地，启用邮件工具
        from engine.human_input_delivery import get_smtp_config, send_email
        cfg = get_smtp_config()
        if not cfg:
            raise ToolNotConfigured('邮件服务未配置 SMTP，请先在系统设置中配置')
        to = str(params.get('to', '')).strip()
        subject = str(params.get('subject', '')).strip()
        body = str(params.get('body', '')).strip()
        if not to or not subject:
            return '错误：收件人(to)和主题(subject)不能为空'
        ok, err = send_email(to, subject, body.replace('\n', '<br>'), body)
        if ok:
            return json.dumps({'sent': True, 'to': to}, ensure_ascii=False)
        return f'发送失败: {err}'

    if p in ('translate', 'weather') or a == 'web_search':
        raise ToolNotConfigured(f'{p}/{a} 需要外部 API Key，当前未配置')

    if p == 'audio':
        return _invoke_audio_tool(a, params or {})

    # ---- 新增 7 个工具包执行逻辑（Phase 2 P1）----

    if p == 'image_generator' and a == 'generate_image':
        return _invoke_image_generator(params)

    if p == 'web_reader' and a == 'read_url':
        return _invoke_web_reader(params)

    if p == 'chart' and a == 'generate_chart':
        return _invoke_chart(params)

    if p == 'pdf':
        return _invoke_pdf(a, params)

    if p == 'text_analyzer':
        return _invoke_text_analyzer(a, params)

    if p == 'file_converter':
        return _invoke_file_converter(a, params)

    if p == 'email_reader':
        return _invoke_email_reader(a, params)

    raise ValueError(f'未知内置动作: {p}/{a}')


def _fetch_url_text(url, selector=''):
    if not url:
        return '错误：未提供 URL'
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        return '错误：URL 被安全策略禁止（SSRF 防护）'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8', errors='replace')
    text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:5000]


def _invoke_audio_tool(tool_name, params):
    """
    调用音频工具（TTS/STT）。

    参数:
        tool_name: 'text_to_speech' 或 'speech_to_text'
        params: {'text': ..., 'model': ..., 'voice': ..., 'audio_file': ...}

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
            raise ToolNotConfigured('TTS 模型未配置，请先在模型页面添加 TTS 模型')
        text = str(params.get('text', ''))
        if not text:
            return json.dumps({'error': 'TTS 文本不能为空'}, ensure_ascii=False)
        voice = params.get('voice') or None
        audio_bytes = text_to_speech(text, cfg, voice=voice)
        audio_url = save_audio_file(audio_bytes)
        return json.dumps({'audio_url': audio_url}, ensure_ascii=False)

    elif tool_name == 'speech_to_text':
        cfg = get_default_audio_config('stt')
        if not cfg:
            raise ToolNotConfigured('STT 模型未配置，请先在模型页面添加 STT 模型')
        audio_file = params.get('audio_file', '')
        if not audio_file:
            return '错误：未提供音频文件'
        # audio_file 可能是文件路径或 URL
        if isinstance(audio_file, str) and audio_file.startswith('/uploads/'):
            # 本地文件路径
            file_path = audio_file.lstrip('/')
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()
            filename = os.path.basename(file_path)
        elif isinstance(audio_file, str) and audio_file.startswith('http'):
            # URL 下载
            from utils.ssrf import is_safe_url
            if not is_safe_url(audio_file):
                return '错误：URL 被安全策略禁止（SSRF 防护）'
            resp = urllib.request.urlopen(audio_file, timeout=30)
            audio_bytes = resp.read()
            filename = audio_file.rsplit('/', 1)[-1] or 'audio.mp3'
        else:
            return '错误：不支持的音频文件来源'
        text = speech_to_text(audio_bytes, filename, cfg)
        return text

    raise ValueError(f'未知音频工具: {tool_name}')


# ---------------------------------------------------------------
# 2. 提供者查找与分发
# ---------------------------------------------------------------

def find_builtin_provider(provider_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT provider_name, actions_json FROM tool_builtin_providers"
            " WHERE provider_name = %s OR id = %s LIMIT 1",
            (provider_id, provider_id))
        return cur.fetchone()
    finally:
        db.close()


def provider_has_action(actions_json, action_name):
    try:
        actions = json.loads(actions_json or '[]')
    except Exception:
        return False
    return any(a.get('name') == action_name for a in actions)


def invoke_tool(provider_id, tool_name, params, context=None):
    """工具节点统一入口：builtin -> api provider -> legacy custom"""
    # 1) 内置提供者（DB 安装表）
    row = find_builtin_provider(provider_id)
    if row and provider_has_action(row['actions_json'], tool_name):
        return run_builtin_action(row['provider_name'], tool_name, params or {})

    # 2) 自定义 API 提供者（OpenAPI 工具）
    result = _try_api_provider(provider_id, tool_name, params or {})
    if result is not None:
        return result

    # 3) 旧版 dify_tool_providers（修正：无 name 列，用 tool_name）
    return _try_legacy_custom_tool(provider_id, tool_name, params or {})


def _try_api_provider(provider_id, tool_name, params):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT server_url, actions_json, auth_type, auth_config, headers_json, timeout_ms"
            " FROM tool_api_providers WHERE (id = %s OR name = %s) AND status = 'active' LIMIT 1",
            (provider_id, provider_id))
        row = cur.fetchone()
    finally:
        db.close()
    if not row:
        return None
    try:
        actions = json.loads(row['actions_json'] or '[]')
    except Exception:
        actions = []
    action = next((a for a in actions if a.get('name') == tool_name), None)
    if not action:
        return f'工具 {tool_name} 未在 API 提供者中找到'

    base = (row['server_url'] or '').rstrip('/')
    path = action.get('path') or action.get('url') or ''
    url = path if path.startswith('http') else base + path
    if not url.startswith('http'):
        return f'API 提供者未配置 server_url: {provider_id}'

    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        return '错误：工具回调地址未通过 SSRF 安全校验'

    headers = {'Content-Type': 'application/json'}
    try:
        headers.update(json.loads(row['headers_json'] or '{}'))
    except Exception:
        pass
    try:
        cfg = json.loads(row['auth_config'] or '{}')
    except Exception:
        cfg = {}
    if row['auth_type'] == 'api_key' and cfg.get('api_key'):
        headers[cfg.get('header_name') or 'X-API-Key'] = cfg['api_key']
    elif row['auth_type'] == 'bearer' and cfg.get('token'):
        headers['Authorization'] = 'Bearer ' + cfg['token']

    method = (action.get('method') or 'POST').upper()
    body = json.dumps(params, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=body if method != 'GET' else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=(row['timeout_ms'] or 30000) / 1000) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            try:
                return json.dumps(json.loads(text), ensure_ascii=False)[:5000]
            except Exception:
                return text[:5000]
    except Exception as e:
        return f'API 工具调用失败: {str(e)[:200]}'


def _try_legacy_custom_tool(provider_id, tool_name, params):
    db = get_db()
    try:
        cur = db.cursor()
        # 修正历史 bug：该表只有 tool_name 列，原查询引用不存在的 name 列
        cur.execute(
            "SELECT * FROM dify_tool_providers WHERE id = %s OR tool_name = %s LIMIT 1",
            (provider_id, provider_id))
        tool_provider = cur.fetchone()
    finally:
        db.close()
    if not tool_provider:
        return f'未找到工具提供者: {provider_id}'
    return f"旧版自定义工具 {provider_id}/{tool_name} 暂不支持执行（请迁移到 API 工具提供者）"


# ---------------------------------------------------------------
# 新增工具包执行逻辑（Phase 2 P1）
# ---------------------------------------------------------------

def _invoke_image_generator(params):
    """AI 图片生成 —— 调用兼容 OpenAI 的图像生成 API"""
    prompt = str(params.get('prompt', '')).strip()
    if not prompt:
        return json.dumps({'error': '缺少 prompt 参数'}, ensure_ascii=False)

    size = params.get('size', '1024x1024')
    model = params.get('model', 'dall-e-3')

    # 从环境变量或默认配置获取图像生成 API
    api_key = os.environ.get('IMAGE_GEN_API_KEY', os.environ.get('OPENAI_API_KEY', ''))
    base_url = os.environ.get('IMAGE_GEN_BASE_URL', 'https://api.openai.com/v1')

    if not api_key:
        raise ToolNotConfigured('图片生成需要配置 IMAGE_GEN_API_KEY 或 OPENAI_API_KEY 环境变量')

    payload = json.dumps({
        'model': model,
        'prompt': prompt,
        'size': size,
        'n': 1,
    }).encode('utf-8')

    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        if 'data' in result and result['data']:
            image_url = result['data'][0].get('url', '')
            return json.dumps({'image_url': image_url, 'prompt': prompt}, ensure_ascii=False)
        return json.dumps({'error': '图片生成失败，无返回数据'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'图片生成失败: {str(e)[:200]}'}, ensure_ascii=False)


def _invoke_web_reader(params):
    """智能网页正文提取 —— 带正文提取和摘要"""
    url = str(params.get('url', '')).strip()
    if not url:
        return json.dumps({'error': '缺少 url 参数'}, ensure_ascii=False)

    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        return json.dumps({'error': 'URL 被安全策略禁止（SSRF 防护）'}, ensure_ascii=False)

    extract_mode = params.get('extract_mode', 'text')  # text / markdown / summary
    max_length = int(params.get('max_length', 10000))

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8', errors='replace')

        # 去除 script / style
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S | re.I)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S | re.I)

        if extract_mode == 'markdown':
            # 简单 HTML → Markdown 转换
            text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', lambda m: '#' * int(m.group(0)[2]) + ' ' + re.sub(r'<[^>]+>', '', m.group(1)) + '\n', text, flags=re.S | re.I)
            text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.S | re.I)
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
            text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.S | re.I)
            text = re.sub(r'<[^>]+>', '', text)
        else:
            text = re.sub(r'<[^>]+>', ' ', text)

        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'\s+', ' ', text).strip()

        result = {
            'url': url,
            'extract_mode': extract_mode,
            'content_length': len(text),
            'content': text[:max_length],
        }

        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.S | re.I)
        if title_match:
            result['title'] = re.sub(r'\s+', ' ', title_match.group(1)).strip()

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'网页读取失败: {str(e)[:200]}'}, ensure_ascii=False)


def _invoke_chart(params):
    """数据可视化图表生成 —— 输出 Chart.js 配置或 ASCII 图表"""
    chart_type = params.get('type', 'bar')  # bar / line / pie / radar / ascii
    data = params.get('data', [])
    title = params.get('title', '')

    if not data:
        return json.dumps({'error': '缺少 data 参数（需要数组数据）'}, ensure_ascii=False)

    if chart_type == 'ascii':
        return _generate_ascii_chart(data, title, params)

    # 输出 Chart.js 配置（前端可直接渲染）
    labels = [str(item.get('label', item.get('name', f'Item {i}'))) for i, item in enumerate(data)]
    values = [float(item.get('value', 0)) for item in data]

    colors = [
        'rgba(46, 99, 240, 0.7)', 'rgba(255, 99, 132, 0.7)',
        'rgba(75, 192, 192, 0.7)', 'rgba(255, 206, 86, 0.7)',
        'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)',
    ]

    chart_config = {
        'type': chart_type,
        'data': {
            'labels': labels,
            'datasets': [{
                'label': title or '数据',
                'data': values,
                'backgroundColor': colors[:len(values)],
                'borderColor': [c.replace('0.7', '1') for c in colors[:len(values)]],
                'borderWidth': 1,
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {'title': {'display': bool(title), 'text': title}},
        }
    }

    return json.dumps({
        'chart_type': chart_type,
        'chart_config': chart_config,
        'summary': {
            'total': sum(values),
            'average': round(sum(values) / len(values), 2) if values else 0,
            'max': max(values) if values else 0,
            'min': min(values) if values else 0,
        }
    }, ensure_ascii=False)


def _generate_ascii_chart(data, title, params):
    """生成 ASCII 文本图表（无需前端渲染）"""
    labels = [str(item.get('label', item.get('name', '')))[:10] for item in data]
    values = [float(item.get('value', 0)) for item in data]
    if not values:
        return json.dumps({'error': '无有效数据'}, ensure_ascii=False)

    max_val = max(values) if max(values) > 0 else 1
    bar_width = 40
    lines = []
    if title:
        lines.append(f'  {title}')
        lines.append('  ' + '─' * (bar_width + 15))

    for label, val in zip(labels, values):
        bar_len = int(val / max_val * bar_width)
        bar = '█' * bar_len + '░' * (bar_len < bar_width)
        lines.append(f'  {label:>10s} │ {bar} {val}')

    lines.append('  ' + '─' * (bar_width + 15))

    return json.dumps({
        'chart_type': 'ascii',
        'ascii_chart': '\n'.join(lines),
        'summary': {
            'total': sum(values),
            'average': round(sum(values) / len(values), 2),
            'max': max(values),
            'min': min(values),
        }
    }, ensure_ascii=False)


def _invoke_pdf(action, params):
    """PDF 处理：提取文本 / 生成 PDF"""
    if action == 'extract_pdf_text':
        return _extract_pdf_text(params)
    elif action == 'generate_pdf':
        return _generate_pdf(params)
    raise ValueError(f'未知 PDF 动作: {action}')


def _extract_pdf_text(params):
    """从 PDF 提取文本"""
    file_path = str(params.get('file_path', params.get('path', ''))).strip()
    url = str(params.get('url', '')).strip()

    if not file_path and not url:
        return json.dumps({'error': '需要 file_path 或 url 参数'}, ensure_ascii=False)

    try:
        from pypdf import PdfReader
    except ImportError:
        return json.dumps({'error': 'pypdf 未安装，请运行: pip install pypdf'}, ensure_ascii=False)

    try:
        if url:
            from utils.ssrf import is_safe_url
            if not is_safe_url(url):
                return json.dumps({'error': 'URL 被安全策略禁止'}, ensure_ascii=False)
            resp = urllib.request.urlopen(url, timeout=30)
            pdf_bytes = resp.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))
        else:
            path = _safe_file_path(file_path)
            if not os.path.exists(path):
                return json.dumps({'error': f'文件不存在: {path}'}, ensure_ascii=False)
            reader = PdfReader(path)

        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = '\n\n'.join(text_parts)
        return json.dumps({
            'page_count': len(reader.pages),
            'text_length': len(full_text),
            'text': full_text[:20000],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'PDF 提取失败: {str(e)[:200]}'}, ensure_ascii=False)


def _generate_pdf(params):
    """生成简单 PDF 文档"""
    content = str(params.get('content', params.get('text', ''))).strip()
    title = str(params.get('title', '生成文档')).strip()

    if not content:
        return json.dumps({'error': '缺少 content 参数'}, ensure_ascii=False)

    try:
        from fpdf import FPDF
    except ImportError:
        return json.dumps({'error': 'fpdf2 未安装，请运行: pip install fpdf2'}, ensure_ascii=False)

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.ln(5)
        pdf.set_font('Helvetica', '', 11)

        for line in content.split('\n'):
            pdf.multi_cell(0, 6, line)

        output_dir = os.path.abspath(os.path.join('uploads', 'tools'))
        os.makedirs(output_dir, exist_ok=True)
        filename = f'generated_{int(time.time())}.pdf'
        path = os.path.join(output_dir, filename)
        pdf.output(path)

        return json.dumps({
            'file_url': f'/uploads/tools/{filename}',
            'title': title,
            'page_count': len(pdf.pages),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'PDF 生成失败: {str(e)[:200]}'}, ensure_ascii=False)


def _invoke_text_analyzer(action, params):
    """文本分析：情感分析 / 摘要 / 关键词提取"""
    text = str(params.get('text', '')).strip()
    if not text:
        return json.dumps({'error': '缺少 text 参数'}, ensure_ascii=False)

    if action == 'sentiment_analysis':
        return _analyze_sentiment(text)
    elif action == 'summarize':
        return _summarize_text(text, params)
    elif action == 'extract_keywords':
        return _extract_keywords(text, params)
    raise ValueError(f'未知文本分析动作: {action}')


def _analyze_sentiment(text):
    """轻量级情感分析（基于关键词，无需外部 API）"""
    positive_words = ['好', '棒', '优秀', '喜欢', '满意', '感谢', '推荐', '完美', '不错', '赞',
                      'good', 'great', 'excellent', 'love', 'best', 'amazing', 'wonderful', 'perfect']
    negative_words = ['差', '烂', '糟糕', '失望', '讨厌', '问题', '错误', '不行', '垃圾', '慢',
                      'bad', 'terrible', 'awful', 'hate', 'worst', 'poor', 'horrible', 'broken']

    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    total = pos_count + neg_count
    if total == 0:
        sentiment = 'neutral'
        score = 0.5
    elif pos_count > neg_count:
        sentiment = 'positive'
        score = round(pos_count / total, 2)
    else:
        sentiment = 'negative'
        score = round(1 - neg_count / total, 2)

    return json.dumps({
        'sentiment': sentiment,
        'score': score,
        'positive_signals': pos_count,
        'negative_signals': neg_count,
        'confidence': round(min(total / 5, 1.0), 2),
    }, ensure_ascii=False)


def _summarize_text(text, params):
    """文本摘要（抽取式：取关键句）"""
    max_sentences = int(params.get('max_sentences', 3))
    max_length = int(params.get('max_length', 500))

    # 分句
    sentences = re.split(r'[。！？\n.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if not sentences:
        return json.dumps({'summary': text[:max_length], 'method': 'truncated'}, ensure_ascii=False)

    # 简单抽取：取前 N 句 + 包含关键词的句子
    if len(sentences) <= max_sentences:
        summary = '。'.join(sentences) + '。'
    else:
        # 取首句 + 尾句 + 中间均匀采样
        indices = [0]
        if max_sentences > 2:
            step = len(sentences) / (max_sentences - 1)
            indices.extend(int(i * step) for i in range(1, max_sentences - 1))
        indices.append(len(sentences) - 1)
        indices = sorted(set(indices))
        summary = '。'.join(sentences[i] for i in indices if i < len(sentences)) + '。'

    return json.dumps({
        'summary': summary[:max_length],
        'original_length': len(text),
        'summary_length': len(summary),
        'compression_ratio': round(len(summary) / max(len(text), 1), 2),
        'method': 'extractive',
    }, ensure_ascii=False)


def _extract_keywords(text, params):
    """关键词提取（基于词频 + TF 启发式）"""
    max_keywords = int(params.get('max_keywords', 10))
    min_length = int(params.get('min_length', 2))

    # 简单中文分词（按字符 n-gram）+ 英文单词提取
    words = re.findall(r'[a-zA-Z]{3,}|[一-鿿]{%d,%d}' % (min_length, min_length + 2), text)

    # 停用词
    stopwords = {'the', 'and', 'this', 'that', 'with', 'from', 'have', 'been', 'were',
                 'they', 'what', 'when', 'which', 'will', 'would', 'could', 'should',
                 '的是', '一个', '没有', '可以', '这个', '那个', '什么', '怎么', '如果'}

    # 词频统计
    freq = {}
    for w in words:
        w_lower = w.lower()
        if w_lower in stopwords:
            continue
        freq[w_lower] = freq.get(w_lower, 0) + 1

    # 按频率排序
    sorted_kw = sorted(freq.items(), key=lambda x: -x[1])[:max_keywords]

    return json.dumps({
        'keywords': [{'word': w, 'frequency': f} for w, f in sorted_kw],
        'total_words': len(words),
        'unique_words': len(freq),
        'method': 'frequency',
    }, ensure_ascii=False)


def _invoke_file_converter(action, params):
    """文件格式转换"""
    if action == 'html_to_markdown':
        return _html_to_markdown(params)
    elif action == 'csv_to_json':
        return _csv_to_json(params)
    elif action == 'json_to_csv':
        return _json_to_csv(params)
    raise ValueError(f'未知文件转换动作: {action}')


def _html_to_markdown(params):
    """HTML → Markdown 转换"""
    html = str(params.get('html', '')).strip()
    if not html:
        return json.dumps({'error': '缺少 html 参数'}, ensure_ascii=False)

    try:
        import markdownify
        md = markdownify.markdownify(html, heading_style='ATX')
        return json.dumps({'markdown': md, 'original_length': len(html), 'converted_length': len(md)}, ensure_ascii=False)
    except ImportError:
        # 降级：简单正则转换
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', html, flags=re.S | re.I)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=re.S | re.I)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=re.S | re.I)
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.S | re.I)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.S | re.I)
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.S | re.I)
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return json.dumps({'markdown': text, 'original_length': len(html), 'converted_length': len(text), 'method': 'regex_fallback'}, ensure_ascii=False)


def _csv_to_json(params):
    """CSV → JSON 转换"""
    csv_text = str(params.get('csv', params.get('text', ''))).strip()
    delimiter = params.get('delimiter', ',')
    if not csv_text:
        return json.dumps({'error': '缺少 csv 参数'}, ensure_ascii=False)

    try:
        import csv
        from io import StringIO
        reader = csv.DictReader(StringIO(csv_text), delimiter=delimiter)
        rows = [dict(r) for r in reader]
        return json.dumps({'json': rows, 'count': len(rows), 'fields': list(rows[0].keys()) if rows else []}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'CSV 解析失败: {str(e)[:200]}'}, ensure_ascii=False)


def _json_to_csv(params):
    """JSON → CSV 转换"""
    data = params.get('data', params.get('json', []))
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return json.dumps({'error': 'JSON 解析失败'}, ensure_ascii=False)

    if not isinstance(data, list) or not data:
        return json.dumps({'error': '需要非空数组'}, ensure_ascii=False)

    try:
        import csv
        from io import StringIO
        output = StringIO()
        if isinstance(data[0], dict):
            fields = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output)
            for row in data:
                writer.writerow(row if isinstance(row, list) else [row])
        return json.dumps({'csv': output.getvalue(), 'count': len(data)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'CSV 生成失败: {str(e)[:200]}'}, ensure_ascii=False)


def _invoke_email_reader(action, params):
    """邮件读取工具（IMAP 协议）"""
    if action == 'fetch_emails':
        return _fetch_emails(params)
    elif action == 'read_email':
        return _read_email(params)
    raise ValueError(f'未知邮件动作: {action}')


def _fetch_emails(params):
    """通过 IMAP 获取邮件列表"""
    host = str(params.get('imap_host', os.environ.get('IMAP_HOST', ''))).strip()
    port = int(params.get('imap_port', int(os.environ.get('IMAP_PORT', '993'))))
    user = str(params.get('username', os.environ.get('EMAIL_USERNAME', ''))).strip()
    password = str(params.get('password', os.environ.get('EMAIL_PASSWORD', ''))).strip()
    folder = str(params.get('folder', 'INBOX'))
    limit = int(params.get('limit', 10))

    if not all([host, user, password]):
        raise ToolNotConfigured('邮件读取需要配置 IMAP_HOST / EMAIL_USERNAME / EMAIL_PASSWORD')

    try:
        import imaplib
        import email
        from email.header import decode_header

        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select(folder)

        status, messages_data = mail.search(None, 'ALL')
        if status != 'OK':
            return json.dumps({'error': '搜索邮件失败'}, ensure_ascii=False)

        msg_ids = messages_data[0].split()
        msg_ids = msg_ids[-limit:]  # 取最新 N 封

        emails = []
        for msg_id in reversed(msg_ids):
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # 解码主题
            subject = ''
            raw_subject = msg.get('Subject', '')
            if raw_subject:
                decoded_parts = decode_header(raw_subject)
                for part, charset in decoded_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(charset or 'utf-8', errors='replace')
                    else:
                        subject += part

            emails.append({
                'id': msg_id.decode(),
                'subject': subject,
                'from': msg.get('From', ''),
                'date': msg.get('Date', ''),
            })

        mail.logout()
        return json.dumps({'emails': emails, 'total': len(emails), 'folder': folder}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'邮件获取失败: {str(e)[:200]}'}, ensure_ascii=False)


def _read_email(params):
    """读取单封邮件的完整内容"""
    host = str(params.get('imap_host', os.environ.get('IMAP_HOST', ''))).strip()
    user = str(params.get('username', os.environ.get('EMAIL_USERNAME', ''))).strip()
    password = str(params.get('password', os.environ.get('EMAIL_PASSWORD', ''))).strip()
    msg_id = str(params.get('message_id', '')).strip()
    folder = str(params.get('folder', 'INBOX'))

    if not all([host, user, password, msg_id]):
        raise ToolNotConfigured('需要 imap_host / username / password / message_id')

    try:
        import imaplib
        import email
        from email.header import decode_header

        mail = imaplib.IMAP4_SSL(host, int(os.environ.get('IMAP_PORT', '993')))
        mail.login(user, password)
        mail.select(folder)

        status, msg_data = mail.fetch(msg_id.encode(), '(RFC822)')
        mail.logout()

        if status != 'OK':
            return json.dumps({'error': '获取邮件失败'}, ensure_ascii=False)

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # 解码主题
        subject = ''
        raw_subject = msg.get('Subject', '')
        if raw_subject:
            decoded_parts = decode_header(raw_subject)
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(charset or 'utf-8', errors='replace')
                else:
                    subject += part

        # 提取正文
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    charset = part.get_content_charset() or 'utf-8'
                    body += part.get_payload(decode=True).decode(charset, errors='replace')
        else:
            charset = msg.get_content_charset() or 'utf-8'
            body = msg.get_payload(decode=True).decode(charset, errors='replace')

        return json.dumps({
            'message_id': msg_id,
            'subject': subject,
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'date': msg.get('Date', ''),
            'body': body[:10000],
            'body_length': len(body),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'邮件读取失败: {str(e)[:200]}'}, ensure_ascii=False)

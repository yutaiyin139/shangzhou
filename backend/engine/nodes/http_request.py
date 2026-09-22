# -*- coding: utf-8 -*-
"""
HTTP 请求节点执行模块

负责执行 HTTP 请求节点，支持：
- GET/POST/PUT/PATCH/DELETE 方法
- 自定义请求头与请求体
- 变量替换（{{variable}} 语法）
- SSRF 防护安全检查
"""

import urllib.request
import urllib.error


def _node_http_request(data, context, model_cfg=None):
    """HTTP 请求节点（含 SSRF 防护）"""
    method = data.get('method', 'get').upper()
    url = data.get('url', '')
    headers_str = data.get('headers', '')
    body_str = data.get('body', '')

    # 变量替换
    for k, v in context.items():
        if k.startswith('__'):
            continue
        if isinstance(v, str):
            url = url.replace('{{' + k + '}}', v)

    # 安全加固：SSRF 防护检查
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        return {'body': '错误：URL 被安全策略禁止（SSRF 防护）', 'status_code': 403}

    headers = {}
    if headers_str:
        for line in headers_str.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip()] = v.strip()

    body = body_str.encode('utf-8') if body_str and method in ('POST', 'PUT', 'PATCH') else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        return {'body': content, 'status_code': resp.status}
    except urllib.error.HTTPError as e:
        return {'body': e.read().decode('utf-8', errors='replace'), 'status_code': e.code}

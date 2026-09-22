# -*- coding: utf-8 -*-
"""
数据源节点引擎 —— 工作流 datasource 节点的实际执行

支持两类来源:
    1. builtin   内置数据源（credentials 存于 data_sources 表 config 字段）
       已实现: jina-reader / firecrawl / tavily / github / gitlab / notion
    2. connector 自定义连接器（custom_connectors 表，endpoint + auth_type）

节点数据结构（node.data）:
    source_type: 'builtin' | 'connector'
    source_key:  内置数据源 key，或连接器 ID（字符串/数字）
    operation:   'fetch' | 'search' | 'list'（不同源语义不同）
    query:       查询词 / URL（支持 {{变量}} 替换）
    limit:       返回条数上限（默认 10）

输出变量:
    documents:        文档/结果列表
    content:          第一条结果的文本（便于直接接下游 LLM）
    datasource_output: 原始返回
    datasource_status: 'success' / 'error'
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from config import get_db


class DatasourceError(Exception):
    """数据源调用失败"""


def _http_json(method, url, headers=None, payload=None, timeout=30):
    """发起 HTTP 请求并解析 JSON 响应"""
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        raise DatasourceError(f'HTTP {e.code}: {body}')
    except Exception as e:
        raise DatasourceError(f'请求失败: {str(e)[:200]}')
    try:
        return json.loads(text)
    except Exception:
        return {'raw': text}


def _http_text(url, headers=None, timeout=30):
    """发起 HTTP 请求并返回纯文本"""
    req = urllib.request.Request(url, method='GET')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        raise DatasourceError(f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:300]}')
    except Exception as e:
        raise DatasourceError(f'请求失败: {str(e)[:200]}')


def _check_url_safe(url):
    from utils.ssrf import is_safe_url
    if not is_safe_url(url):
        raise DatasourceError('URL 被安全策略禁止（SSRF 防护）')


def _load_builtin_config(key):
    """读取内置数据源配置（data_sources 表），返回 (installed, config_dict)"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT status, config FROM data_sources WHERE ds_key = %s', (key,))
        row = cur.fetchone()
    finally:
        db.close()
    if not row:
        return False, {}
    try:
        cfg = json.loads(row['config'] or '{}')
    except Exception:
        cfg = {}
    return True, cfg


def _load_connector(connector_id):
    """读取自定义连接器"""
    from models.tables import CUSTOM_CONNECTORS_TABLE_SQL
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(CUSTOM_CONNECTORS_TABLE_SQL)
        cur.execute('SELECT * FROM custom_connectors WHERE id = %s', (connector_id,))
        return cur.fetchone()
    finally:
        db.close()


# ============================================================
# 内置数据源实现
# ============================================================

def _src_jina_reader(cfg, operation, query, limit):
    """Jina Reader：抓取任意网页正文（免 key 可用，有 key 更高限额）"""
    target = (query or '').strip()
    if not target:
        raise DatasourceError('请提供要抓取的 URL（query 字段）')
    if not target.startswith('http'):
        target = 'https://' + target
    _check_url_safe(target)
    url = 'https://r.jina.ai/' + target
    headers = {}
    if cfg.get('api_key'):
        headers['Authorization'] = 'Bearer ' + cfg['api_key']
    text = _http_text(url, headers=headers, timeout=60)
    return [{'content': text, 'source': target}]


def _src_firecrawl(cfg, operation, query, limit):
    """Firecrawl：网页抓取 / 搜索"""
    if not cfg.get('api_key'):
        raise DatasourceError('Firecrawl 未配置 API Key，请先在「连接器」页配置')
    if operation == 'search':
        data = _http_json('POST', 'https://api.firecrawl.dev/v1/search',
                          headers={'Authorization': 'Bearer ' + cfg['api_key']},
                          payload={'query': query, 'limit': limit})
        items = data.get('data', []) if isinstance(data, dict) else []
        return [{'content': it.get('markdown') or it.get('content') or it.get('url', ''),
                 'source': it.get('url', ''), 'title': it.get('title', '')} for it in items]
    target = (query or '').strip()
    if not target.startswith('http'):
        target = 'https://' + target
    _check_url_safe(target)
    data = _http_json('POST', 'https://api.firecrawl.dev/v1/scrape',
                      headers={'Authorization': 'Bearer ' + cfg['api_key']},
                      payload={'url': target})
    d = data.get('data', data) if isinstance(data, dict) else {}
    return [{'content': d.get('markdown') or d.get('content') or json.dumps(data, ensure_ascii=False)[:5000],
             'source': target, 'title': d.get('metadata', {}).get('title', '')}]


def _src_tavily(cfg, operation, query, limit):
    """Tavily：搜索提取"""
    if not cfg.get('api_key'):
        raise DatasourceError('Tavily 未配置 API Key，请先在「连接器」页配置')
    if not query:
        raise DatasourceError('请提供搜索关键词（query 字段）')
    data = _http_json('POST', 'https://api.tavily.com/search',
                      payload={'api_key': cfg['api_key'], 'query': query, 'max_results': limit})
    items = data.get('results', []) if isinstance(data, dict) else []
    return [{'content': it.get('content', ''), 'source': it.get('url', ''),
             'title': it.get('title', '')} for it in items]


def _src_github(cfg, operation, query, limit):
    """GitHub：仓库搜索 / 我的仓库列表"""
    headers = {'Accept': 'application/vnd.github+json'}
    if cfg.get('token'):
        headers['Authorization'] = 'Bearer ' + cfg['token']
    if operation == 'list' or not query:
        data = _http_json('GET', f'https://api.github.com/user/repos?per_page={limit}&sort=updated',
                          headers=headers)
        items = data if isinstance(data, list) else []
        return [{'content': it.get('full_name', ''), 'source': it.get('html_url', ''),
                 'title': it.get('description') or ''} for it in items]
    q = urllib.parse.quote(query)
    data = _http_json('GET',
                      f'https://api.github.com/search/repositories?q={q}&per_page={limit}',
                      headers=headers)
    items = data.get('items', []) if isinstance(data, dict) else []
    return [{'content': it.get('full_name', ''), 'source': it.get('html_url', ''),
             'title': it.get('description') or ''} for it in items]


def _src_gitlab(cfg, operation, query, limit):
    """GitLab：项目搜索 / 我的项目列表"""
    headers = {}
    if cfg.get('token'):
        headers['PRIVATE-TOKEN'] = cfg['token']
    if operation == 'list' or not query:
        url = f'https://gitlab.com/api/v4/projects?per_page={limit}&order_by=last_activity_at'
    else:
        url = f'https://gitlab.com/api/v4/projects?search={urllib.parse.quote(query)}&per_page={limit}'
    data = _http_json('GET', url, headers=headers)
    items = data if isinstance(data, list) else []
    return [{'content': it.get('path_with_namespace', ''), 'source': it.get('web_url', ''),
             'title': it.get('description') or ''} for it in items]


def _src_notion(cfg, operation, query, limit):
    """Notion：页面/数据库搜索"""
    if not cfg.get('token'):
        raise DatasourceError('Notion 未配置集成令牌，请先在「连接器」页配置')
    headers = {
        'Authorization': 'Bearer ' + cfg['token'],
        'Notion-Version': '2022-06-28',
    }
    payload = {'page_size': min(limit, 100)}
    if query:
        payload['query'] = query
    data = _http_json('POST', 'https://api.notion.com/v1/search',
                      headers=headers, payload=payload)
    items = data.get('results', []) if isinstance(data, dict) else []
    docs = []
    for it in items:
        title = ''
        props = it.get('properties', {})
        for prop in props.values():
            if isinstance(prop, dict) and prop.get('type') == 'title':
                title = ''.join(t.get('plain_text', '') for t in prop.get('title', []))
                break
        if not title and it.get('title'):
            title = ''.join(t.get('plain_text', '') for t in it.get('title', []))
        docs.append({'content': title or it.get('id', ''), 'source': it.get('url', ''),
                     'title': title, 'object_type': it.get('object', '')})
    return docs


BUILTIN_SOURCE_RUNNERS = {
    'jina-reader': _src_jina_reader,
    'firecrawl': _src_firecrawl,
    'tavily': _src_tavily,
    'github': _src_github,
    'gitlab': _src_gitlab,
    'notion': _src_notion,
}


# ============================================================
# 入口
# ============================================================

def run_datasource(data, context):
    """
    执行 datasource 节点，返回输出变量字典

    失败不抛出：返回 datasource_status='error' 与错误信息，
    使工作流可结合错误分支继续运行（与 Dify 节点错误处理语义一致）。
    """
    start = time.time()
    source_type = data.get('source_type', 'builtin')
    source_key = data.get('source_key', '')
    operation = data.get('operation', 'search')
    query = data.get('query', '') or ''
    limit = int(data.get('limit') or 10)

    # 变量替换 {{var}}
    for k, v in context.items():
        if isinstance(v, str):
            query = query.replace('{{' + k + '}}', v)

    try:
        if source_type == 'connector':
            docs = _run_connector(str(source_key), operation, query, limit, context)
        else:
            runner = BUILTIN_SOURCE_RUNNERS.get(str(source_key))
            if not runner:
                raise DatasourceError(
                    f'数据源「{source_key}」暂不支持节点调用，当前支持: '
                    + ', '.join(BUILTIN_SOURCE_RUNNERS.keys())
                )
            installed, cfg = _load_builtin_config(str(source_key))
            if not installed:
                raise DatasourceError(f'数据源「{source_key}」未安装，请先在「连接器」页安装并配置')
            docs = runner(cfg, operation, query, limit)

        first = docs[0]['content'] if docs else ''
        return {
            'documents': docs,
            'content': first,
            'datasource_output': docs,
            'datasource_status': 'success',
            'datasource_count': len(docs),
            'datasource_elapsed_ms': int((time.time() - start) * 1000),
        }
    except DatasourceError as e:
        return {
            'documents': [],
            'content': '',
            'datasource_output': [],
            'datasource_status': 'error',
            'datasource_error': str(e),
            'datasource_elapsed_ms': int((time.time() - start) * 1000),
        }
    except Exception as e:
        return {
            'documents': [],
            'content': '',
            'datasource_output': [],
            'datasource_status': 'error',
            'datasource_error': f'未知错误: {str(e)[:200]}',
            'datasource_elapsed_ms': int((time.time() - start) * 1000),
        }


def _run_connector(connector_id, operation, query, limit, context):
    """调用自定义连接器（endpoint + auth）"""
    if not connector_id:
        raise DatasourceError('未配置连接器')
    row = _load_connector(connector_id)
    if not row:
        raise DatasourceError(f'连接器 #{connector_id} 不存在')
    endpoint = (row['endpoint'] or '').strip()
    if not endpoint:
        raise DatasourceError(f'连接器「{row["name"]}」未配置 endpoint')

    method = 'GET'
    headers = {}
    auth_type = row['auth_type'] or 'none'
    auth_value = row['auth_value'] or ''
    if auth_type == 'api_key' and auth_value:
        headers['X-API-Key'] = auth_value
        headers['Authorization'] = 'Bearer ' + auth_value
    elif auth_type == 'bearer' and auth_value:
        headers['Authorization'] = 'Bearer ' + auth_value

    sep = '&' if '?' in endpoint else '?'
    if operation == 'fetch' or not query:
        url = endpoint
    else:
        url = f'{endpoint}{sep}q={urllib.parse.quote(query)}&limit={limit}'
    _check_url_safe(url)

    if method == 'GET':
        data = _http_json('GET', url, headers=headers)
    else:
        data = _http_json(method, endpoint, headers=headers,
                          payload={'query': query, 'limit': limit})
    # 统一为 documents 列表
    if isinstance(data, list):
        docs = [{'content': json.dumps(it, ensure_ascii=False) if not isinstance(it, str) else it,
                 'source': endpoint} for it in data[:limit]]
    elif isinstance(data, dict):
        raw = json.dumps(data, ensure_ascii=False)
        docs = [{'content': raw[:8000], 'source': endpoint, 'title': row['name']}]
    else:
        docs = [{'content': str(data)[:8000], 'source': endpoint}]
    return docs

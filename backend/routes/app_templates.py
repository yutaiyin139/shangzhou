# -*- coding: utf-8 -*-
"""应用模板路由：同步 Dify Marketplace 模板并支持基于模板创建工作流应用（MySQL 版，脱离 Dify）"""

import json
import os
import re
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from flask import jsonify, request
import yaml

from config import (
    get_db, MARKETPLACE_API_BASE, MARKETPLACE_TEMPLATE_IDS,
    MARKETPLACE_CATEGORY_MAP, MARKETPLACE_SYNC_ALL
)
from models.tables import (
    APP_TEMPLATES_TABLE_SQL,
    DIFY_APPS_TABLE_SQL,
    DIFY_WORKFLOWS_TABLE_SQL,
    DIFY_APP_MODEL_CONFIGS_TABLE_SQL,
    DIFY_SITES_TABLE_SQL,
    DIFY_ACCOUNTS_TABLE_SQL,
    DIFY_TENANTS_TABLE_SQL,
    DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL,
    INSTALLED_APPS_TABLE_SQL,
)
from utils.helpers import now


CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'templates')


def _ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def _ensure_dify_tables():
    """确保所有 Dify 兼容表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOWS_TABLE_SQL)
        cur.execute(DIFY_APP_MODEL_CONFIGS_TABLE_SQL)
        cur.execute(DIFY_SITES_TABLE_SQL)
        cur.execute(DIFY_ACCOUNTS_TABLE_SQL)
        cur.execute(DIFY_TENANTS_TABLE_SQL)
        cur.execute(DIFY_TENANT_ACCOUNT_JOINS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _resolve_display_category(categories):
    """把 Marketplace 英文分类映射为中文展示分类"""
    for cat in (categories or []):
        if cat in (MARKETPLACE_CATEGORY_MAP or {}):
            return MARKETPLACE_CATEGORY_MAP[cat]
    return '新手入门'


def _ensure_app_templates_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(APP_TEMPLATES_TABLE_SQL)
        # 显式指定 utf8mb4，防止表默认字符集被改成 utf8mb3 时把 4 字节 emoji（如模板图标）静默写为 '?'，
        # 从而破坏 DSL YAML（icon: ? 会触发 yaml 报 'mapping keys are not allowed here'）。
        cur.execute(r'ALTER TABLE app_templates MODIFY COLUMN dsl_yaml LONGTEXT CHARACTER SET utf8mb4')
        cur.execute(r'ALTER TABLE app_templates MODIFY COLUMN overview LONGTEXT CHARACTER SET utf8mb4')
        for col_sql in [
            r'ALTER TABLE app_templates ADD COLUMN display_category VARCHAR(50) DEFAULT ""',
            r'ALTER TABLE app_templates ADD COLUMN icon VARCHAR(50) DEFAULT ""',
        ]:
            try:
                cur.execute(col_sql)
            except Exception:
                pass
        db.commit()
    finally:
        db.close()


def _marketplace_request(url, method='GET', data=None, headers=None, timeout=60):
    """向 Dify Marketplace 发起请求并返回 bytes"""
    default_headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    if headers:
        default_headers.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        default_headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=default_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {'status': r.status, 'body': r.read()}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'body': e.read()}


def _fetch_marketplace_template(template_id):
    """获取单个模板详情"""
    url = '%s/templates/%s' % (MARKETPLACE_API_BASE, template_id)
    res = _marketplace_request(url)
    if res['status'] != 200:
        return None
    try:
        data = json.loads(res['body'].decode('utf-8'))
    except Exception:
        return None
    if data.get('code') != 0:
        return None
    return data.get('data')


def _fetch_marketplace_templates_list():
    """分页获取 Marketplace 全部模板列表"""
    items = []
    page = 1
    page_size = 100
    while True:
        url = '%s/templates?page_size=%s&page=%s' % (MARKETPLACE_API_BASE, page_size, page)
        res = _marketplace_request(url)
        if res['status'] != 200:
            break
        try:
            data = json.loads(res['body'].decode('utf-8'))
        except Exception:
            break
        if data.get('code') != 0:
            break
        page_items = data.get('data', {}).get('templates', [])
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < page_size:
            break
        page += 1
    return items


def _download_dsl(template_id):
    """下载模板 DSL YAML，返回 yaml 字符串"""
    url = '%s/templates/%s/dsl' % (MARKETPLACE_API_BASE, template_id)
    res = _marketplace_request(url, headers={'Accept': 'application/x-yaml'}, timeout=120)
    if res['status'] != 200 or not res['body']:
        return None
    return res['body'].decode('utf-8')


def _download_dsl_with_retry(template_id, tries=3):
    """带重试的 DSL 下载，用于按需创建"""
    for attempt in range(1, tries + 1):
        try:
            dsl = _download_dsl(template_id)
            if dsl:
                return dsl
        except Exception:
            pass
    return None


def _dsl_parses(text):
    """判断 DSL 文本是否为可正常解析的 YAML 映射（用于识别被 MySQL 字符集破坏成 '?' 的脏数据）"""
    if not text:
        return False
    try:
        return isinstance(yaml.safe_load(text), dict)
    except Exception:
        return False


def _load_valid_dsl(template_id, db_yaml):
    """按 数据库副本 -> 本地缓存文件 -> 重新下载 的顺序，返回第一份可正常解析的 DSL。

    历史坑：早期同步时 app_templates 列字符集不能存 4 字节 emoji，DSL 里的图标（如 app.icon: 🤖）
    被写成 '?'，导致 yaml.safe_load 报 'mapping keys are not allowed here'。本地缓存文件是以 UTF-8
    原样写入的，未被破坏，可作为可靠来源回退，并顺带回写修复数据库副本。
    返回 (dsl_yaml, source)；source 为 'db' / 'cache' / 'download'，全部失败时返回 (None, None)。
    """
    if _dsl_parses(db_yaml):
        return db_yaml, 'db'
    capath = os.path.join(CACHE_DIR, template_id, 'dsl.yaml')
    if os.path.exists(capath):
        try:
            with open(capath, 'r', encoding='utf-8') as f:
                cached = f.read()
        except Exception:
            cached = ''
        if _dsl_parses(cached):
            return cached, 'cache'
    fresh = _download_dsl_with_retry(template_id)
    if _dsl_parses(fresh):
        return fresh, 'download'
    return None, None


def _parse_template_detail(detail, dsl_yaml, display_category=''):
    """把 marketplace 详情解析为数据库字段"""
    app = {}
    if dsl_yaml:
        try:
            app = yaml.safe_load(dsl_yaml) or {}
        except Exception:
            app = {}
    app_info = app.get('app') or {}
    categories = detail.get('categories') or []
    deps = detail.get('deps_plugins') or []
    tags = list(set(categories + [d.split('/')[-1] for d in deps if d]))
    icon_url = ''
    if detail.get('icon_file_key'):
        icon_url = 'https://marketplace.dify.ai/%s' % detail['icon_file_key']
    return {
        'marketplace_id': detail.get('id'),
        'name': detail.get('template_name') or app_info.get('name') or '未命名模板',
        'description': (detail.get('overview') or app_info.get('description') or '')[:2000],
        'overview': detail.get('overview') or '',
        'kind': detail.get('kind') or app_info.get('mode') or 'workflow',
        'icon': detail.get('icon') or app_info.get('icon') or '',
        'categories_json': json.dumps(categories, ensure_ascii=False),
        'display_category': display_category or '',
        'tags_json': json.dumps(tags, ensure_ascii=False),
        'icon_url': icon_url,
        'icon_background': detail.get('icon_background') or app_info.get('icon_background') or '',
        'dsl_path': 'cache/templates/%s/dsl.yaml' % detail.get('id'),
        'dsl_yaml': dsl_yaml or '',
        'deps_json': json.dumps(deps, ensure_ascii=False),
        'source': 'dify-marketplace',
        'status': 'active',
        'synced_at': now()
    }


def _save_template_metadata(row):
    """写入或更新模板元数据（不覆盖 DSL）"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            INSERT INTO app_templates
            (marketplace_id, name, description, overview, kind, icon, categories_json, display_category, tags_json,
             icon_url, icon_background, dsl_path, dsl_yaml, deps_json, source, status, synced_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name=VALUES(name), description=VALUES(description), overview=VALUES(overview),
            kind=VALUES(kind), icon=VALUES(icon), categories_json=VALUES(categories_json), display_category=VALUES(display_category),
            tags_json=VALUES(tags_json), icon_url=VALUES(icon_url), icon_background=VALUES(icon_background),
            dsl_path=COALESCE(NULLIF(VALUES(dsl_path),''), dsl_path),
            dsl_yaml=COALESCE(NULLIF(VALUES(dsl_yaml),''), dsl_yaml),
            deps_json=VALUES(deps_json),
            source=VALUES(source), status=VALUES(status), synced_at=VALUES(synced_at)
        ''', (
            row['marketplace_id'], row['name'], row['description'], row['overview'], row['kind'], row.get('icon') or '',
            row['categories_json'], row['display_category'], row['tags_json'], row['icon_url'], row['icon_background'],
            row['dsl_path'], row.get('dsl_yaml') or '', row['deps_json'], row['source'], row['status'], row['synced_at']
        ))
        db.commit()
    finally:
        db.close()


def _save_template_to_db(row):
    """写入或更新 app_templates 表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            INSERT INTO app_templates
            (marketplace_id, name, description, overview, kind, icon, categories_json, display_category, tags_json,
             icon_url, icon_background, dsl_path, dsl_yaml, deps_json, source, status, synced_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name=VALUES(name), description=VALUES(description), overview=VALUES(overview),
            kind=VALUES(kind), icon=VALUES(icon), categories_json=VALUES(categories_json), display_category=VALUES(display_category),
            tags_json=VALUES(tags_json), icon_url=VALUES(icon_url), icon_background=VALUES(icon_background),
            dsl_path=VALUES(dsl_path), dsl_yaml=VALUES(dsl_yaml), deps_json=VALUES(deps_json),
            source=VALUES(source), status=VALUES(status), synced_at=VALUES(synced_at)
        ''', (
            row['marketplace_id'], row['name'], row['description'], row['overview'], row['kind'], row.get('icon') or '',
            row['categories_json'], row['display_category'], row['tags_json'], row['icon_url'], row['icon_background'],
            row['dsl_path'], row['dsl_yaml'], row['deps_json'], row['source'], row['status'], row['synced_at']
        ))
        db.commit()
    finally:
        db.close()


def _save_dsl_file(template_id, dsl_yaml):
    """保存 DSL 文件到本地缓存"""
    _ensure_dir(CACHE_DIR)
    tpl_dir = os.path.join(CACHE_DIR, template_id)
    _ensure_dir(tpl_dir)
    path = os.path.join(tpl_dir, 'dsl.yaml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dsl_yaml)
    return path


def _update_template_dsl(marketplace_id, dsl_yaml):
    """更新已存在模板的 DSL 内容"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE app_templates SET dsl_yaml = %s, dsl_path = %s WHERE marketplace_id = %s',
                    (dsl_yaml, 'cache/templates/%s/dsl.yaml' % marketplace_id, marketplace_id))
        db.commit()
    finally:
        db.close()


def _get_dify_account_by_email(email):
    """根据邮箱在 MySQL 中查找账户及默认租户"""
    if not email:
        return None
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT a.id AS account_id, t.id AS tenant_id
            FROM dify_accounts a
            JOIN dify_tenant_account_joins taj ON taj.account_id = a.id
            JOIN dify_tenants t ON t.id = taj.tenant_id
            WHERE LOWER(a.email) = LOWER(%s) AND taj.current = true
            LIMIT 1
        ''', (email,))
        row = cur.fetchone()
    finally:
        db.close()
    if row:
        return {'account_id': str(row['account_id']), 'tenant_id': str(row['tenant_id'])}
    return None


def _get_default_dify_owner():
    """获取 MySQL 中第一个 owner 账号作为默认创建者"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT a.id AS account_id, taj.tenant_id
            FROM dify_accounts a
            JOIN dify_tenant_account_joins taj ON taj.account_id = a.id
            WHERE taj.role = 'owner'
            ORDER BY a.created_at ASC
            LIMIT 1
        ''')
        row = cur.fetchone()
    finally:
        db.close()
    if row:
        return {'account_id': str(row['account_id']), 'tenant_id': str(row['tenant_id'])}
    return None


def _is_uuid(value):
    return bool(re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', value or ''))


def _resolve_dify_owner(uid):
    """根据本地用户 ID 或 Dify account_id 解析创建者；解析失败时使用默认 owner"""
    owner = None
    uid = (uid or '').strip()
    if uid:
        if _is_uuid(uid):
            # 若 uid 是 Dify UUID，直接按 account_id 查找对应 email
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    SELECT id, email FROM dify_accounts WHERE id = %s AND status = 'active' LIMIT 1
                ''', (uid,))
                row = cur.fetchone()
            finally:
                db.close()
            if row:
                owner = _get_dify_account_by_email(row['email'])
        if not owner:
            # 否则当成本地 dify_accounts.id，反查 email
            db = get_db()
            try:
                cur = db.cursor()
                # 使用 dify_accounts 表（users 表已合并）
                cur.execute(r'SELECT email FROM dify_accounts WHERE id = %s', (str(uid),))
                row = cur.fetchone()
                if row and row['email']:
                    owner = _get_dify_account_by_email(row['email'])
            finally:
                db.close()
    if not owner:
        owner = _get_default_dify_owner()
    return owner


def _sanitize_graph_for_import(graph):
    """导入模板时清洗 graph：清空占位 dataset_ids、补全 HTTP URL 协议前缀、移除 Docker 内部 mock 节点"""
    if not isinstance(graph, dict):
        return graph
    nodes = graph.get('nodes') or []
    edges = graph.get('edges') or []
    # 1. 清空占位 dataset_ids / 补全 HTTP URL
    for node in nodes:
        data = node.get('data') or {}
        if data.get('type') == 'knowledge-retrieval':
            data['dataset_ids'] = []
        elif data.get('type') == 'http-request':
            url = (data.get('url') or '').strip()
            if url and not url.lower().startswith(('http://', 'https://')):
                data['url'] = 'http://' + url
    # 2. 移除指向 docker 内部 mock 服务的 http 节点（如 host.docker.internal/log），并重连上下
    remove_ids = {n['id'] for n in nodes
                  if (n.get('data') or {}).get('type') == 'http-request'
                  and 'host.docker.internal' in ((n.get('data') or {}).get('url') or '')}
    if remove_ids:
        # 收集每个被删节点的上游 source 与下游 target
        sources = {}
        targets = {}
        for e in edges:
            if e['source'] in remove_ids:
                targets.setdefault(e['source'], set()).add(e['target'])
            if e['target'] in remove_ids:
                sources.setdefault(e['target'], set()).add(e['source'])
        new_edges = [e for e in edges if e['source'] not in remove_ids and e['target'] not in remove_ids]
        for rid in remove_ids:
            for src in sources.get(rid, []):
                for tgt in targets.get(rid, []):
                    new_edges.append({
                        'id': '%s-source-%s-target' % (src, tgt),
                        'source': src, 'target': tgt,
                        'sourceHandle': 'source', 'targetHandle': 'target',
                        'type': 'custom', 'zIndex': 0, 'data': {}
                    })
        nodes = [n for n in nodes if n['id'] not in remove_ids]
        edges = new_edges
    graph['nodes'] = nodes
    graph['edges'] = edges
    return graph


def _extract_model_from_dsl(dsl):
    """从 DSL 的 model_config 中提取默认模型配置"""
    mc = dsl.get('model_config') or {}
    m = mc.get('model') or {}
    if not m.get('provider') or not m.get('name'):
        return None
    return {
        'provider': m['provider'],
        'name': m['name'],
        'mode': m.get('mode', 'chat'),
        'completion_params': m.get('completion_params') or {'temperature': 0.7}
    }


def _build_graph_from_model_config(graph, mode, dsl):
    """对无 graph 的 classic/chat/completion/agent 类模板，根据 model_config 生成最小可编辑 graph"""
    if graph and graph.get('nodes'):
        return graph, mode
    model = _extract_model_from_dsl(dsl) or {
        'provider': 'langgenius/openai/openai',
        'name': 'gpt-4o-mini',
        'mode': 'chat',
        'completion_params': {'temperature': 0.7}
    }
    start_id = 'start-' + str(uuid.uuid4())[:8]
    if mode in ('completion', 'workflow'):
        llm_id = 'llm-' + str(uuid.uuid4())[:8]
        end_id = 'end-' + str(uuid.uuid4())[:8]
        nodes = [
            {'id': start_id, 'type': 'custom', 'position': {'x': 80, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'start', 'title': '开始', 'variables': []}},
            {'id': llm_id, 'type': 'custom', 'position': {'x': 360, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'llm', 'title': 'LLM', 'model': model, 'prompt_template': [],
                      'context': {'enabled': False, 'variable_selector': []}, 'vision': {'enabled': False}}},
            {'id': end_id, 'type': 'custom', 'position': {'x': 640, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'end', 'title': '结束', 'outputs': []}}
        ]
        edges = [
            {'id': '%s-%s' % (start_id, llm_id), 'source': start_id, 'target': llm_id, 'type': 'custom'},
            {'id': '%s-%s' % (llm_id, end_id), 'source': llm_id, 'target': end_id, 'type': 'custom'}
        ]
        new_mode = 'workflow'
    else:
        llm_id = 'llm-' + str(uuid.uuid4())[:8]
        answer_id = 'answer-' + str(uuid.uuid4())[:8]
        nodes = [
            {'id': start_id, 'type': 'custom', 'position': {'x': 80, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'start', 'title': '开始', 'variables': []}},
            {'id': llm_id, 'type': 'custom', 'position': {'x': 360, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'llm', 'title': 'LLM', 'model': model, 'prompt_template': [],
                      'context': {'enabled': False, 'variable_selector': []}, 'vision': {'enabled': False}}},
            {'id': answer_id, 'type': 'custom', 'position': {'x': 640, 'y': 200}, 'width': 240, 'height': 90,
             'data': {'type': 'answer', 'title': '直接回复', 'answer': ''}}
        ]
        edges = [
            {'id': '%s-%s' % (start_id, llm_id), 'source': start_id, 'target': llm_id, 'type': 'custom'},
            {'id': '%s-%s' % (llm_id, answer_id), 'source': llm_id, 'target': answer_id, 'type': 'custom'}
        ]
        new_mode = 'advanced-chat' if mode == 'agent-chat' else 'chat'
    return {'nodes': nodes, 'edges': edges, 'viewport': {'x': 0, 'y': 0, 'zoom': 1}}, new_mode


def _create_app_from_dsl(dsl_yaml, name, description, owner):
    """解析 DSL 并直接写入 MySQL 创建应用；对无 graph 的 classic 类模板自动生成可编辑 graph"""
    _ensure_dify_tables()
    dsl = yaml.safe_load(dsl_yaml)
    app_info = dsl.get('app') or {}
    wf_info = dsl.get('workflow') or {}

    mode = app_info.get('mode') or 'workflow'
    graph = wf_info.get('graph') or {}
    if not graph.get('nodes'):
        graph, mode = _build_graph_from_model_config(graph, mode, dsl)
    graph = _sanitize_graph_for_import(graph)
    wf_info['graph'] = graph

    # 统一应用模式为原生编辑器支持的类型
    wf_type_map = {'advanced-chat': 'chat', 'agent-chat': 'chat', 'chat': 'chat',
                   'chatflow': 'chat', 'workflow': 'workflow', 'completion': 'workflow'}
    wf_type = wf_type_map.get(mode) or mode
    app_mode = {
        'chat': 'chat', 'agent-chat': 'agent-chat', 'agent': 'agent',
        'advanced-chat': 'advanced-chat', 'chatflow': 'chat',
        'workflow': 'workflow', 'completion': 'workflow'
    }.get(mode) or mode
    app_id = str(uuid.uuid4())
    wf_id = str(uuid.uuid4())
    cfg_id = str(uuid.uuid4()) if app_mode in ('advanced-chat', 'chat', 'agent-chat', 'agent') else None
    site_id = str(uuid.uuid4()) if app_mode in ('advanced-chat', 'chat', 'agent-chat', 'agent') else None
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    tenant_id = owner['tenant_id']
    account_id = owner['account_id']

    app_name = name or app_info.get('name') or '未命名应用'
    app_desc = description or app_info.get('description') or ''
    icon = app_info.get('icon') or '🤖'
    icon_bg = app_info.get('icon_background') or '#FFEAD5'
    use_icon_as_answer = app_info.get('use_icon_as_answer_icon') or False

    db = get_db()
    try:
        cur = db.cursor()
        # 1. 写入 dify_workflows
        cur.execute(r'''
            INSERT INTO dify_workflows
            (id, tenant_id, app_id, type, version, graph, features, created_by, updated_by,
             created_at, updated_at, environment_variables, conversation_variables,
             marked_name, marked_comment, rag_pipeline_variables, kind, version_number)
            VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s, %s, %s, '', '', %s, 'standard', NULL)
        ''', (
            wf_id, tenant_id, app_id, wf_type,
            json.dumps(wf_info.get('graph') or {}, ensure_ascii=False),
            json.dumps(wf_info.get('features') or {}, ensure_ascii=False),
            account_id, account_id, ts, ts,
            json.dumps(wf_info.get('environment_variables') or {}, ensure_ascii=False),
            json.dumps(wf_info.get('conversation_variables') or {}, ensure_ascii=False),
            json.dumps(wf_info.get('rag_pipeline_variables') or {}, ensure_ascii=False)
        ))

        # 2. 可选：写入 dify_app_model_configs（携带 DSL 中的模型配置）
        if cfg_id:
            model_cfg = _extract_model_from_dsl(dsl) or {}
            provider = model_cfg.get('provider') or None
            model_id = model_cfg.get('name') or None
            model_json = json.dumps(model_cfg, ensure_ascii=False) if model_cfg.get('provider') else '{}'
            cur.execute(r'''
                INSERT INTO dify_app_model_configs
                (id, app_id, provider, model_id, configs, model, created_at, updated_at, created_by, updated_by,
                 opening_statement, suggested_questions, pre_prompt, prompt_type)
                VALUES (%s, %s, %s, %s, '{}', %s, %s, %s, %s, %s, '', '', '', 'simple')
            ''', (cfg_id, app_id, provider, model_id, model_json, ts, ts, account_id, account_id))

        # 3. 可选：写入 dify_sites
        if site_id:
            cur.execute(r'''
                INSERT INTO dify_sites
                (id, app_id, title, icon, icon_background, description, default_language,
                 customize_token_strategy, prompt_public, status, created_at, updated_at,
                 custom_disclaimer, show_workflow_steps, created_by, updated_by,
                 use_icon_as_answer_icon, code)
                VALUES (%s, %s, %s, %s, %s, %s, 'zh-Hans', 'not_allowed', false, 'normal',
                        %s, %s, '', true, %s, %s, %s, %s)
            ''', (
                site_id, app_id, app_name, icon, icon_bg, app_desc,
                ts, ts, account_id, account_id, use_icon_as_answer,
                uuid.uuid4().hex[:16]
            ))

        # 4. 写入 dify_apps
        cur.execute(r'''
            INSERT INTO dify_apps
            (id, tenant_id, name, mode, icon, icon_background, app_model_config_id, status,
             enable_site, enable_api, api_rpm, api_rph, is_demo, is_public, created_at, updated_at,
             is_universal, workflow_id, description, created_by, updated_by, use_icon_as_answer_icon,
             icon_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'normal', %s, true, 0, 0, false, false, %s, %s,
                    false, %s, %s, %s, %s, %s, 'emoji')
        ''', (
            app_id, tenant_id, app_name, app_mode, icon, icon_bg, cfg_id,
            bool(site_id), ts, ts, wf_id, app_desc,
            account_id, account_id, use_icon_as_answer
        ))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {'id': app_id, 'name': app_name, 'mode': app_mode}


def register_app_template_routes(app):
    """注册应用模板相关路由"""

    @app.route('/api/app-templates', methods=['GET'])
    def list_app_templates():
        _ensure_app_templates_table()
        q = (request.args.get('q') or '').strip().lower()
        category = (request.args.get('category') or '').strip()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM app_templates WHERE status = "active" ORDER BY synced_at DESC')
            rows = cur.fetchall()
        finally:
            db.close()
        items = []
        for r in rows:
            cats = []
            tags = []
            try:
                cats = json.loads(r['categories_json'] or '[]')
                tags = json.loads(r['tags_json'] or '[]')
            except Exception:
                pass
            if category and category != 'all':
                # 优先按中文展示分类筛选
                if (r['display_category'] or '') != category:
                    continue
            if q:
                text = ' '.join([r['name'] or '', r['description'] or '', ' '.join(cats), ' '.join(tags), r['display_category'] or '']).lower()
                if q not in text:
                    continue
            items.append({
                'id': r['marketplace_id'],
                'name': r['name'],
                'description': r['description'],
                'overview': r['overview'],
                'kind': r['kind'],
                'icon': r['icon'] or '',
                'categories': cats,
                'display_category': r['display_category'] or '',
                'tags': tags,
                'icon_url': r['icon_url'],
                'icon_background': r['icon_background'],
                'deps': json.loads(r['deps_json'] or '[]'),
                'source': r['source'],
                'synced_at': r['synced_at'].strftime('%Y-%m-%d %H:%M:%S') if r['synced_at'] else ''
            })
        return jsonify(code=200, data=items)

    @app.route('/api/app-templates/<tid>', methods=['GET'])
    def get_app_template(tid):
        _ensure_app_templates_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM app_templates WHERE marketplace_id = %s', (tid,))
            r = cur.fetchone()
        finally:
            db.close()
        if not r:
            return jsonify(code=404, msg='模板不存在')
        return jsonify(code=200, data={
            'id': r['marketplace_id'],
            'name': r['name'],
            'description': r['description'],
            'overview': r['overview'],
            'kind': r['kind'],
            'icon': r['icon'] or '',
            'categories': json.loads(r['categories_json'] or '[]'),
            'display_category': r['display_category'] or '',
            'tags': json.loads(r['tags_json'] or '[]'),
            'icon_url': r['icon_url'],
            'icon_background': r['icon_background'],
            'dsl_yaml': r['dsl_yaml'] or '',
            'deps': json.loads(r['deps_json'] or '[]'),
            'source': r['source']
        })

    @app.route('/api/app-templates/sync', methods=['POST'])
    def sync_app_templates():
        _ensure_app_templates_table()
        ids = request.json.get('ids') if request.is_json else None
        use_all = MARKETPLACE_SYNC_ALL and not ids
        template_items = []
        if use_all:
            template_items = _fetch_marketplace_templates_list()
            if not template_items:
                return jsonify(code=500, msg='从 Marketplace 获取模板列表失败')
        else:
            template_ids = ids or MARKETPLACE_TEMPLATE_IDS
            if not template_ids:
                return jsonify(code=400, msg='没有配置模板 ID')
            for tid in template_ids:
                detail = _fetch_marketplace_template(tid)
                if detail:
                    template_items.append(detail)
        success = 0
        failed = []
        dsl_failed = []
        synced_ids = []
        for detail in template_items:
            tid = detail.get('id')
            if not tid:
                continue
            synced_ids.append(tid)
            categories = detail.get('categories') or []
            display_category = _resolve_display_category(categories)
            # 先保存元数据（含中文分类），再下载 DSL
            row = _parse_template_detail(detail, '', display_category=display_category)
            _save_template_metadata(row)
            try:
                dsl = _download_dsl(tid)
                if dsl:
                    _save_dsl_file(tid, dsl)
                    # 用 DSL 重新解析，回填 kind/icon 等字段
                    full_row = _parse_template_detail(detail, dsl, display_category=display_category)
                    _save_template_to_db(full_row)
                else:
                    dsl_failed.append(tid)
            except Exception:
                dsl_failed.append(tid)
            success += 1
        # 清理已不在当前清单中的旧模板
        if synced_ids:
            db = get_db()
            try:
                cur = db.cursor()
                placeholders = ','.join(['%s'] * len(synced_ids))
                cur.execute(r'UPDATE app_templates SET status = "inactive" WHERE marketplace_id NOT IN (%s)' % placeholders, tuple(synced_ids))
                db.commit()
            finally:
                db.close()
        return jsonify(code=200, data={'success': success, 'failed': failed, 'dsl_failed': dsl_failed, 'total': len(template_items)})

    @app.route('/api/app-templates/<tid>/create', methods=['POST'])
    def create_from_template(tid):
        _ensure_app_templates_table()
        _ensure_dify_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM app_templates WHERE marketplace_id = %s', (tid,))
            r = cur.fetchone()
        finally:
            db.close()
        if not r:
            return jsonify(code=404, msg='模板不存在')
        # 数据库副本可能因历史字符集问题被破坏成 '?'（图标 emoji），
        # 依次回退本地缓存/重新下载，取第一份能解析的 DSL，并自愈回写。
        dsl_yaml, dsl_source = _load_valid_dsl(tid, r['dsl_yaml'])
        if not dsl_yaml:
            return jsonify(code=400, msg='模板 DSL 缺失或解析失败，请重新同步模板后重试')
        if dsl_source != 'db':
            try:
                _update_template_dsl(tid, dsl_yaml)
                _save_dsl_file(tid, dsl_yaml)
            except Exception:
                pass
        body = request.json or {}
        name = (body.get('name') or r['name'] or '未命名应用').strip()
        description = (body.get('description') or r['description'] or '').strip()
        uid = str(request.args.get('uid') or body.get('uid') or '').strip()
        owner = _resolve_dify_owner(uid)
        if not owner:
            return jsonify(code=500, msg='无法解析创建者，请确认数据库可访问')
        try:
            app = _create_app_from_dsl(dsl_yaml, name, description, owner)
        except Exception as e:
            return jsonify(code=500, msg='创建工作流应用失败: %s' % e)
        return jsonify(code=200, data=app)

    @app.route('/api/app-templates/categories', methods=['GET'])
    def list_template_categories():
        _ensure_app_templates_table()
        # 返回配置的中文展示分类顺序
        cats = ['新手入门', '客户服务', '知识检索', '办公提效', '市场营销', '销售拓客']
        return jsonify(code=200, data=cats)

    # ============================================================
    # 已安装应用管理 API（P1: 模板安装追踪）
    # ============================================================

    def _ensure_installed_apps_table():
        """确保已安装应用表存在"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(INSTALLED_APPS_TABLE_SQL)
            db.commit()
        finally:
            db.close()

    @app.route('/api/installed-apps', methods=['GET'])
    def list_installed_apps():
        """列出已安装的应用"""
        _ensure_installed_apps_table()
        tenant_id = request.args.get('tenant_id', 'system')
        status = request.args.get('status', '')
        source_type = request.args.get('source_type', '')

        where = ['tenant_id = %s']
        params = [tenant_id]
        if status:
            where.append('status = %s')
            params.append(status)
        if source_type:
            where.append('source_type = %s')
            params.append(source_type)

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM installed_apps
                           WHERE ''' + ' AND '.join(where) + r'''
                           ORDER BY installed_at DESC''', params)
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'tenant_id': r['tenant_id'],
                    'app_id': r['app_id'], 'source_type': r['source_type'],
                    'source_id': r['source_id'], 'source_name': r['source_name'],
                    'app_name': r['app_name'], 'app_mode': r['app_mode'],
                    'app_icon': r['app_icon'], 'app_description': r['app_description'],
                    'install_type': r['install_type'],
                    'installed_version': r['installed_version'],
                    'current_version': r['current_version'],
                    'status': r['status'],
                    'installed_by': r['installed_by'],
                    'installed_at': str(r['installed_at'] or ''),
                    'updated_at': str(r['updated_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/installed-apps', methods=['POST'])
    def record_installed_app():
        """记录新安装的应用"""
        _ensure_installed_apps_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        app_name = (body.get('app_name') or '').strip()
        if not app_name:
            return jsonify(code=400, msg='应用名称必填')

        install_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO installed_apps
                           (id, tenant_id, app_id, source_type, source_id, source_name,
                            app_name, app_mode, app_icon, app_description, install_type,
                            installed_version, current_version, status, installed_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (install_id,
                         body.get('tenant_id', 'system'),
                         body.get('app_id', ''),
                         body.get('source_type', 'template'),
                         body.get('source_id', ''),
                         body.get('source_name', ''),
                         app_name,
                         body.get('app_mode', 'workflow'),
                         body.get('app_icon', '🤖'),
                         body.get('app_description', ''),
                         body.get('install_type', 'new'),
                         body.get('installed_version', '1.0.0'),
                         body.get('current_version', '1.0.0'),
                         body.get('status', 'installed'),
                         body.get('installed_by', '')))
            db.commit()
            return jsonify(code=200, msg='记录成功', data={'id': install_id})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='记录失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/installed-apps/<install_id>', methods=['PUT'])
    def update_installed_app(install_id):
        """更新已安装应用状态"""
        _ensure_installed_apps_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            fields = []
            params = []
            for field in ['status', 'current_version', 'app_name', 'app_description']:
                if field in body:
                    fields.append(f'{field} = %s')
                    params.append(body[field])
            if not fields:
                return jsonify(code=400, msg='无更新字段')
            params.append(install_id)
            cur.execute(f'''UPDATE installed_apps SET {', '.join(fields)}
                           WHERE id = %s''', params)
            db.commit()
            return jsonify(code=200, msg='更新成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/installed-apps/<install_id>', methods=['DELETE'])
    def delete_installed_app(install_id):
        """删除已安装应用记录"""
        _ensure_installed_apps_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM installed_apps WHERE id = %s', (install_id,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

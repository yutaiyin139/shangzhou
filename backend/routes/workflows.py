# -*- coding: utf-8 -*-
"""工作流编排页后端 API：为原生 Vue Flow 编辑器提供数据与执行能力（MySQL 版，脱离 Dify）"""

import json
import re
import secrets
import string
import uuid
from datetime import datetime
from flask import jsonify, request, Response
import yaml

from config import get_db
from models.tables import (
    WORKFLOW_VERSIONS_TABLE_SQL,
    WORKFLOW_TEST_RUNS_TABLE_SQL,
    DIFY_APPS_TABLE_SQL,
    DIFY_WORKFLOWS_TABLE_SQL,
    DIFY_WORKFLOW_RUNS_TABLE_SQL,
    DIFY_WORKFLOW_NODE_EXECUTIONS_TABLE_SQL,
    DIFY_WORKFLOW_VERSION_COUNTERS_TABLE_SQL,
    DIFY_APP_MODEL_CONFIGS_TABLE_SQL,
    DIFY_SITES_TABLE_SQL,
    DIFY_API_TOKENS_TABLE_SQL,
    DIFY_PROVIDERS_TABLE_SQL,
    DIFY_PROVIDER_MODELS_TABLE_SQL,
    HUMAN_INPUT_FORMS_TABLE_SQL,
    WORKFLOW_PAUSES_TABLE_SQL,
    WORKFLOW_CONVERSATION_VARIABLES_TABLE_SQL,
    WORKFLOW_DRAFT_VARIABLES_TABLE_SQL,
)
from engine.workflow_runner import run_workflow, run_workflow_stream
from routes.audit import log_audit_event


def _ensure_dify_tables():
    """确保所有 Dify 兼容表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOWS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_RUNS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_NODE_EXECUTIONS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOW_VERSION_COUNTERS_TABLE_SQL)
        cur.execute(DIFY_APP_MODEL_CONFIGS_TABLE_SQL)
        cur.execute(DIFY_SITES_TABLE_SQL)
        cur.execute(DIFY_API_TOKENS_TABLE_SQL)
        cur.execute(DIFY_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_PROVIDER_MODELS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_workflow_versions_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_VERSIONS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _ensure_workflow_test_runs_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_TEST_RUNS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _is_uuid(value):
    return bool(re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', value or ''))


def _get_app(app_id):
    """从 MySQL dify_apps 表读取应用信息"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT id, tenant_id, name, mode, icon, icon_background, description, status, created_by, updated_by
            FROM dify_apps WHERE id = %s LIMIT 1
        ''', (app_id,))
        r = cur.fetchone()
    finally:
        db.close()
    if not r:
        return None
    return {
        'id': str(r['id']),
        'tenant_id': str(r['tenant_id']),
        'name': r['name'],
        'mode': r['mode'],
        'icon': r['icon'] or '🤖',
        'icon_background': r['icon_background'] or '#FFEAD5',
        'description': r['description'] or '',
        'status': r['status'],
        'created_by': str(r['created_by']) if r['created_by'] else '',
        'updated_by': str(r['updated_by']) if r['updated_by'] else ''
    }


def _get_workflow(app_id):
    """从 MySQL dify_workflows 表读取工作流"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT id, app_id, tenant_id, type, version, graph, features,
                   environment_variables, conversation_variables, rag_pipeline_variables,
                   created_by, updated_by, version_number
            FROM dify_workflows WHERE app_id = %s LIMIT 1
        ''', (app_id,))
        r = cur.fetchone()
    finally:
        db.close()
    if not r:
        return None
    def load_json(field):
        try:
            return json.loads(field or '{}')
        except Exception:
            return {}
    return {
        'id': str(r['id']),
        'app_id': str(r['app_id']),
        'tenant_id': str(r['tenant_id']),
        'type': r['type'],
        'version': r['version'],
        'graph': load_json(r['graph']),
        'features': load_json(r['features']),
        'environment_variables': load_json(r['environment_variables']),
        'conversation_variables': load_json(r['conversation_variables']),
        'rag_pipeline_variables': load_json(r['rag_pipeline_variables']),
        'created_by': str(r['created_by']) if r['created_by'] else '',
        'updated_by': str(r['updated_by']) if r['updated_by'] else '',
        'version_number': r['version_number'] or 1
    }


def _get_owner(uid):
    """解析创建者，非 UUID 当成本地用户 ID"""
    from routes.app_templates import _resolve_dify_owner
    return _resolve_dify_owner(uid)


def _build_blank_graph(mode='workflow', model=None):
    """构造空白工作流/对话流的初始 graph；workflow 默认带一个 LLM 节点并使用选定模型"""
    start_id = 'start-' + str(uuid.uuid4())[:8]
    model_data = model or {
        'provider': 'langgenius/openai/openai',
        'name': 'gpt-4o-mini',
        'mode': 'chat',
        'completion_params': {'temperature': 0.7}
    }
    if mode == 'workflow':
        llm_id = 'llm-' + str(uuid.uuid4())[:8]
        end_id = 'end-' + str(uuid.uuid4())[:8]
        nodes = [
            {
                'id': start_id, 'type': 'custom',
                'position': {'x': 80, 'y': 200}, 'width': 240, 'height': 90,
                'data': {'type': 'start', 'title': '开始', 'variables': []}
            },
            {
                'id': llm_id, 'type': 'custom',
                'position': {'x': 360, 'y': 200}, 'width': 240, 'height': 90,
                'data': {
                    'type': 'llm', 'title': 'LLM',
                    'model': model_data,
                    'prompt_template': [],
                    'context': {'enabled': False, 'variable_selector': []},
                    'vision': {'enabled': False}
                }
            },
            {
                'id': end_id, 'type': 'custom',
                'position': {'x': 640, 'y': 200}, 'width': 240, 'height': 90,
                'data': {'type': 'end', 'title': '结束', 'outputs': []}
            }
        ]
        edges = [
            {'id': '%s-%s' % (start_id, llm_id), 'source': start_id, 'target': llm_id, 'type': 'custom'},
            {'id': '%s-%s' % (llm_id, end_id), 'source': llm_id, 'target': end_id, 'type': 'custom'}
        ]
    else:
        answer_id = 'answer-' + str(uuid.uuid4())[:8]
        nodes = [
            {
                'id': start_id, 'type': 'custom',
                'position': {'x': 80, 'y': 200}, 'width': 240, 'height': 90,
                'data': {'type': 'start', 'title': '开始', 'variables': []}
            },
            {
                'id': answer_id, 'type': 'custom',
                'position': {'x': 400, 'y': 200}, 'width': 240, 'height': 90,
                'data': {'type': 'answer', 'title': '直接回复', 'answer': ''}
            }
        ]
        edges = [{'id': '%s-%s' % (start_id, answer_id), 'source': start_id, 'target': answer_id, 'type': 'custom'}]
    return {'nodes': nodes, 'edges': edges, 'viewport': {'x': 0, 'y': 0, 'zoom': 1}}


def _canonical_app_mode(mode):
    """将前端/DSL 中的模式名称映射为 Dify apps.mode 合法值"""
    return {
        'workflow': 'workflow',
        'completion': 'workflow',
        'chatflow': 'chat',
        'chat': 'chat',
        'advanced-chat': 'advanced-chat',
        'agent-chat': 'agent-chat',
        'agent': 'agent'
    }.get((mode or '').strip().lower(), mode or 'workflow')


def _create_blank_dify_app(name, description, mode, owner, model=None):
    """在 MySQL 中创建一个空白工作流/对话流应用，并绑定用户选择的模型"""
    wf_type_map = {'advanced-chat': 'chat', 'agent-chat': 'chat', 'chat': 'chat',
                   'workflow': 'workflow', 'completion': 'workflow', 'chatflow': 'chat'}
    wf_type = wf_type_map.get(mode) or mode
    app_mode = _canonical_app_mode(mode)
    app_id = str(uuid.uuid4())
    wf_id = str(uuid.uuid4())
    cfg_id = str(uuid.uuid4()) if mode in ('advanced-chat', 'agent', 'chat', 'chatflow', 'agent-chat') else None
    site_id = str(uuid.uuid4()) if mode in ('advanced-chat', 'agent', 'chat', 'chatflow', 'agent-chat') else None
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    tenant_id = owner['tenant_id']
    account_id = owner['account_id']

    app_name = name or '未命名应用'
    app_desc = description or ''
    icon = '🤖'
    icon_bg = '#FFEAD5'
    graph = _build_blank_graph(mode, model)

    db = get_db()
    try:
        cur = db.cursor()
        # 1. workflows
        cur.execute(r'''
            INSERT INTO dify_workflows
            (id, tenant_id, app_id, type, version, graph, features, created_by, updated_by,
             created_at, updated_at, environment_variables, conversation_variables,
             marked_name, marked_comment, rag_pipeline_variables, kind, version_number)
            VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s, %s, %s, '', '', %s, 'standard', NULL)
        ''', (
            wf_id, tenant_id, app_id, wf_type,
            json.dumps(graph, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
            account_id, account_id, ts, ts,
            json.dumps({}, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False)
        ))

        # 2. app_model_configs（对话类应用写入默认模型）
        provider = model['provider'] if model else None
        model_id = model['name'] if model else None
        if cfg_id:
            model_json = json.dumps(model, ensure_ascii=False) if model else '{}'
            cur.execute(r'''
                INSERT INTO dify_app_model_configs
                (id, app_id, provider, model_id, configs, model, created_at, updated_at, created_by, updated_by,
                 opening_statement, suggested_questions, pre_prompt, prompt_type)
                VALUES (%s, %s, %s, %s, '{}', %s, %s, %s, %s, %s, '', '', '', 'simple')
            ''', (cfg_id, app_id, provider, model_id, model_json, ts, ts, account_id, account_id))

        # 3. sites
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
                ts, ts, account_id, account_id, False,
                uuid.uuid4().hex[:16]
            ))

        # 4. apps
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
            account_id, account_id, False
        ))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {'id': app_id, 'name': app_name, 'mode': app_mode}


def _get_or_create_api_token(app_id, tenant_id):
    """获取应用的 Service API token，不存在则生成一条写入 dify_api_tokens 表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT id, token FROM dify_api_tokens WHERE app_id = %s AND type = %s LIMIT 1', (app_id, 'app'))
        row = cur.fetchone()
        if row:
            return str(row['token'])
    finally:
        db.close()

    token = 'app-' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    token_id = str(uuid.uuid4())
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            INSERT INTO dify_api_tokens (id, app_id, tenant_id, type, token, created_at)
            VALUES (%s, %s, %s, 'app', %s, %s)
        ''', (token_id, app_id, tenant_id, token, ts))
        db.commit()
    finally:
        db.close()
    return token


def _extract_start_inputs(graph, mode='workflow'):
    """从 graph 中提取 Start 节点的输入变量，用于构造运行输入表单"""
    inputs = []
    # 对话类应用：先加入「用户消息」输入
    if mode != 'workflow':
        inputs.append({
            'variable': 'query',
            'label': '用户消息',
            'type': 'paragraph',
            'required': True,
            'options': [],
            'max_length': None
        })
    for n in (graph or {}).get('nodes', []):
        data = n.get('data') or {}
        if data.get('type') == 'start':
            for v in (data.get('variables') or []):
                inputs.append({
                    'variable': v.get('variable', ''),
                    'label': v.get('label', v.get('variable', '')),
                    'type': v.get('type', 'text-input'),
                    'required': bool(v.get('required', False)),
                    'options': v.get('options') or [],
                    'max_length': v.get('max_length')
                })
            break
    return inputs


def _publish_dify_workflow(app_id, wf):
    """在 MySQL 中发布当前草稿：分配版本号并新增一条 published 工作流记录"""
    new_wf_id = str(uuid.uuid4())
    version_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        # 获取并递增版本号
        cur.execute(r'''
            INSERT INTO dify_workflow_version_counters (app_id, last_version_number)
            VALUES (%s, 1)
            ON DUPLICATE KEY UPDATE last_version_number = last_version_number + 1
        ''', (app_id,))
        cur.execute(r'SELECT last_version_number FROM dify_workflow_version_counters WHERE app_id = %s', (app_id,))
        version_number = cur.fetchone()['last_version_number']

        # 插入新版本的工作流记录
        cur.execute(r'''
            INSERT INTO dify_workflows
            (id, tenant_id, app_id, type, version, graph, features, created_by,
             created_at, updated_at, environment_variables, conversation_variables,
             marked_name, marked_comment, rag_pipeline_variables, kind, version_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'standard', %s)
        ''', (
            new_wf_id, wf['tenant_id'], app_id, wf['type'], version_str,
            json.dumps(wf['graph'], ensure_ascii=False),
            json.dumps(wf['features'], ensure_ascii=False),
            wf['created_by'] or wf['updated_by'], ts, ts,
            json.dumps(wf['environment_variables'], ensure_ascii=False),
            json.dumps(wf['conversation_variables'], ensure_ascii=False),
            wf.get('marked_name', ''),
            wf.get('marked_comment', ''),
            json.dumps(wf['rag_pipeline_variables'], ensure_ascii=False),
            version_number
        ))
        db.commit()
        return version_number
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_run_detail(app_id, run_id):
    """读取单次运行结果与节点 trace"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT id, status, inputs, outputs, error, elapsed_time, total_tokens, total_steps, created_at, finished_at
            FROM dify_workflow_runs WHERE id = %s AND app_id = %s LIMIT 1
        ''', (run_id, app_id))
        r = cur.fetchone()
    finally:
        db.close()
    if not r:
        return None
    def load(field):
        try:
            return json.loads(field or '{}')
        except Exception:
            return {}
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''
            SELECT node_id, node_type, title, inputs, outputs, status, error, elapsed_time, finished_at
            FROM dify_workflow_node_executions WHERE workflow_run_id = %s ORDER BY created_at ASC
        ''', (run_id,))
        node_rows = cur.fetchall()
    finally:
        db.close()
    return {
        'id': str(r['id']),
        'status': r['status'],
        'inputs': load(r['inputs']),
        'outputs': load(r['outputs']),
        'error': r['error'],
        'elapsed_time': r['elapsed_time'],
        'total_tokens': r['total_tokens'],
        'total_steps': r['total_steps'],
        'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else '',
        'finished_at': r['finished_at'].strftime('%Y-%m-%d %H:%M:%S') if r['finished_at'] else '',
        'nodes': [{
            'node_id': str(nr['node_id']),
            'node_type': nr['node_type'],
            'title': nr['title'],
            'inputs': load(nr['inputs']),
            'outputs': load(nr['outputs']),
            'status': nr['status'],
            'error': nr['error'],
            'elapsed_time': nr['elapsed_time']
        } for nr in node_rows]
    }


def register_workflow_routes(app):
    """注册工作流编排相关路由"""

    @app.route('/api/workflows/<app_id>', methods=['GET'])
    def get_workflow(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        _ensure_workflow_versions_table()
        app_info = _get_app(app_id)
        if not app_info:
            return jsonify(code=404, msg='应用不存在')
        wf = _get_workflow(app_id)
        if not wf:
            return jsonify(code=404, msg='工作流不存在')
        return jsonify(code=200, data={'app': app_info, 'workflow': wf})

    @app.route('/api/workflows/create', methods=['POST'])
    def create_blank_workflow_app():
        """创建空白工作流/对话流应用"""
        _ensure_dify_tables()
        body = request.json or {}
        name = (body.get('name') or '').strip()
        description = (body.get('description') or '').strip()
        mode = (body.get('mode') or 'workflow').strip().lower()
        model = body.get('model') or None
        uid = str(request.args.get('uid') or body.get('uid') or '').strip()
        if not name:
            return jsonify(code=400, msg='应用名称不能为空')
        if mode not in ('workflow', 'chatflow', 'advanced-chat', 'chat', 'agent-chat'):
            return jsonify(code=400, msg='不支持的应用模式')
        owner = _get_owner(uid)
        if not owner:
            return jsonify(code=500, msg='无法解析创建者，请确认数据库可访问')
        try:
            app = _create_blank_dify_app(name, description, mode, owner, model)
        except Exception as e:
            return jsonify(code=500, msg='创建应用失败: %s' % e)
        return jsonify(code=200, data=app)

    @app.route('/api/workflows/<app_id>/graph', methods=['PUT'])
    def save_workflow_graph(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        body = request.json or {}
        graph = body.get('graph')
        if not isinstance(graph, dict):
            return jsonify(code=400, msg='graph 格式错误')
        features = body.get('features')
        env_vars = body.get('environment_variables')
        conv_vars = body.get('conversation_variables')
        uid = str(request.args.get('uid') or body.get('uid') or '').strip()
        owner = _get_owner(uid)
        account_id = owner['account_id'] if owner else None
        ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        updates = [r"graph = %s", r"updated_at = %s"]
        params = [json.dumps(graph, ensure_ascii=False), ts]
        if isinstance(features, dict):
            updates.append(r"features = %s")
            params.append(json.dumps(features, ensure_ascii=False))
        if isinstance(env_vars, dict):
            updates.append(r"environment_variables = %s")
            params.append(json.dumps(env_vars, ensure_ascii=False))
        if isinstance(conv_vars, dict):
            updates.append(r"conversation_variables = %s")
            params.append(json.dumps(conv_vars, ensure_ascii=False))
        if account_id:
            updates.append(r"updated_by = %s")
            params.append(account_id)
        params.append(app_id)
        sql = r"UPDATE dify_workflows SET " + ", ".join(updates) + r" WHERE app_id = %s"
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(sql, tuple(params))
                db.commit()
                affected = cur.rowcount
            finally:
                db.close()
            if not affected:
                return jsonify(code=404, msg='工作流不存在')
        except Exception as e:
            return jsonify(code=500, msg='保存失败: %s' % e)

        # 同步画布中的触发节点（trigger-schedule / trigger-webhook）为可执行计划
        try:
            from engine.trigger_engine import sync_trigger_plans
            wf = _get_workflow(app_id) or {}
            sync_trigger_plans(
                app_id, graph,
                tenant_id=wf.get('tenant_id'),
                account_id=account_id,
            )
        except Exception:
            pass  # 触发计划同步失败不阻塞保存

        return jsonify(code=200, msg='保存成功')

    @app.route('/api/workflows/<app_id>', methods=['PUT'])
    def update_app_info(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        body = request.json or {}
        name = (body.get('name') or '').strip()
        description = (body.get('description') or '').strip()
        icon = body.get('icon')
        icon_bg = body.get('icon_background')
        if not name:
            return jsonify(code=400, msg='应用名称不能为空')
        updates = [r"name = %s", r"description = %s", r"updated_at = %s"]
        params = [name, description, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')]
        if icon is not None:
            updates.append(r"icon = %s")
            params.append(icon)
        if icon_bg is not None:
            updates.append(r"icon_background = %s")
            params.append(icon_bg)
        params.append(app_id)
        sql = r"UPDATE dify_apps SET " + ", ".join(updates) + r" WHERE id = %s"
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(sql, tuple(params))
                db.commit()
                affected = cur.rowcount
            finally:
                db.close()
            if not affected:
                return jsonify(code=404, msg='应用不存在')
        except Exception as e:
            return jsonify(code=500, msg='更新失败: %s' % e)
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/workflows/<app_id>/versions', methods=['GET'])
    def list_workflow_versions(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_workflow_versions_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_versions WHERE app_id = %s ORDER BY version_number DESC', (app_id,))
            rows = cur.fetchall()
        finally:
            db.close()
        items = []
        for r in rows:
            items.append({
                'id': r['id'],
                'app_id': r['app_id'],
                'version_number': r['version_number'],
                'name': r['name'],
                'comment': r['comment'],
                'created_by': r['created_by'],
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else ''
            })
        return jsonify(code=200, data=items)

    @app.route('/api/workflows/<app_id>/publish', methods=['POST'])
    def publish_workflow(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        _ensure_workflow_versions_table()
        wf = _get_workflow(app_id)
        if not wf:
            return jsonify(code=404, msg='工作流不存在')
        body = request.json or {}
        name = (body.get('name') or 'v%s' % (wf['version_number'] + 1)).strip()
        comment = (body.get('comment') or '').strip()
        uid = str(request.args.get('uid') or body.get('uid') or '').strip()
        # 在 MySQL 中发布：分配版本号并新增一条 published 工作流
        try:
            next_ver = _publish_dify_workflow(app_id, wf)
        except Exception as e:
            return jsonify(code=500, msg='发布失败: %s' % e)
        # 同时写入本地 MySQL 快照（版本历史）
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                INSERT INTO workflow_versions
                (app_id, version_number, name, comment, graph_json, features_json, env_vars_json, conv_vars_json, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                app_id, next_ver, name, comment,
                json.dumps(wf['graph'], ensure_ascii=False),
                json.dumps(wf['features'], ensure_ascii=False),
                json.dumps(wf['environment_variables'], ensure_ascii=False),
                json.dumps(wf['conversation_variables'], ensure_ascii=False),
                uid, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            ))
            db.commit()
        finally:
            db.close()
        # 同步更新 dify_apps.updated_at，让工作流应用列表显示最新时间
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE dify_apps SET updated_at = %s WHERE id = %s',
                        (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), app_id))
            db.commit()
        finally:
            db.close()
        return jsonify(code=200, data={'version_number': next_ver, 'name': name})

    @app.route('/api/workflows/<app_id>/versions/<int:vid>/restore', methods=['POST'])
    def restore_workflow_version(app_id, vid):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        _ensure_workflow_versions_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_versions WHERE app_id = %s AND version_number = %s LIMIT 1', (app_id, vid))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return jsonify(code=404, msg='版本不存在')
        def load_json(field):
            try:
                return json.loads(field or '{}')
            except Exception:
                return {}
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    UPDATE dify_workflows
                    SET graph = %s, features = %s, environment_variables = %s, conversation_variables = %s, updated_at = %s
                    WHERE app_id = %s
                ''', (
                    json.dumps(load_json(row['graph_json']), ensure_ascii=False),
                    json.dumps(load_json(row['features_json']), ensure_ascii=False),
                    json.dumps(load_json(row['env_vars_json']), ensure_ascii=False),
                    json.dumps(load_json(row['conv_vars_json']), ensure_ascii=False),
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), app_id
                ))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='恢复失败: %s' % e)
        return jsonify(code=200, msg='恢复成功')

    @app.route('/api/workflows/<app_id>/versions/<int:vid>', methods=['GET'])
    def get_workflow_version_detail(app_id, vid):
        """获取版本详情（含完整 graph_json，用于预览/diff）"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_workflow_versions_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_versions WHERE app_id = %s AND version_number = %s LIMIT 1', (app_id, vid))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return jsonify(code=404, msg='版本不存在')
        def parse_json(field):
            try:
                return json.loads(field or '{}')
            except Exception:
                return {}
        return jsonify(code=200, data={
            'id': row['id'],
            'app_id': row['app_id'],
            'version_number': row['version_number'],
            'name': row['name'],
            'comment': row['comment'],
            'graph': parse_json(row['graph_json']),
            'features': parse_json(row['features_json']),
            'environment_variables': parse_json(row['env_vars_json']),
            'conversation_variables': parse_json(row['conv_vars_json']),
            'created_by': row['created_by'],
            'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else ''
        })

    @app.route('/api/workflows/<app_id>/versions/diff', methods=['POST'])
    def diff_workflow_versions(app_id):
        """对比两个工作流版本，返回节点/边的增删改"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        body = request.json or {}
        vid_a = body.get('vid_a')
        vid_b = body.get('vid_b')
        if not vid_a or not vid_b:
            return jsonify(code=400, msg='需要提供 vid_a 和 vid_b')

        _ensure_workflow_versions_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT version_number, graph_json FROM workflow_versions WHERE app_id = %s AND version_number IN (%s, %s)',
                (app_id, vid_a, vid_b)
            )
            rows = {r['version_number']: r['graph_json'] for r in cur.fetchall()}
        finally:
            db.close()

        if vid_a not in rows:
            return jsonify(code=404, msg='版本 %s 不存在' % vid_a)
        if vid_b not in rows:
            return jsonify(code=404, msg='版本 %s 不存在' % vid_b)

        try:
            graph_a = json.loads(rows[vid_a] or '{}')
            graph_b = json.loads(rows[vid_b] or '{}')
        except Exception as e:
            return jsonify(code=500, msg='解析 graph 失败: %s' % e)

        diff_result = _diff_workflow_graphs(graph_a, graph_b)
        return jsonify(code=200, data=diff_result)

    def _diff_workflow_graphs(graph_a, graph_b):
        """对比两个工作流 graph，返回结构化 diff"""
        nodes_a = {n.get('id'): n for n in (graph_a.get('nodes') or [])}
        nodes_b = {n.get('id'): n for n in (graph_b.get('nodes') or [])}
        edges_a = {(e.get('source'), e.get('target')): e for e in (graph_a.get('edges') or [])}
        edges_b = {(e.get('source'), e.get('target')): e for e in (graph_b.get('edges') or [])}

        # 节点 diff
        added_nodes = [nodes_b[nid] for nid in nodes_b if nid not in nodes_a]
        removed_nodes = [nodes_a[nid] for nid in nodes_a if nid not in nodes_b]
        changed_nodes = []
        for nid in nodes_a:
            if nid in nodes_b:
                na, nb = nodes_a[nid], nodes_b[nid]
                changes = {}
                for key in ('position', 'data', 'title', 'type'):
                    if na.get(key) != nb.get(key):
                        changes[key] = {'old': na.get(key), 'new': nb.get(key)}
                if changes:
                    changed_nodes.append({'id': nid, 'changes': changes})

        # 边 diff
        added_edges = [edges_b[eid] for eid in edges_b if eid not in edges_a]
        removed_edges = [edges_a[eid] for eid in edges_a if eid not in edges_b]

        return {
            'summary': {
                'nodes_added': len(added_nodes),
                'nodes_removed': len(removed_nodes),
                'nodes_changed': len(changed_nodes),
                'edges_added': len(added_edges),
                'edges_removed': len(removed_edges),
            },
            'nodes': {
                'added': [{'id': n.get('id'), 'title': (n.get('data') or {}).get('title', n.get('id'))} for n in added_nodes],
                'removed': [{'id': n.get('id'), 'title': (n.get('data') or {}).get('title', n.get('id'))} for n in removed_nodes],
                'changed': [{'id': c['id'], 'title': (nodes_a[c['id']].get('data') or {}).get('title', c['id']), 'changes': c['changes']} for c in changed_nodes],
            },
            'edges': {
                'added': [{'source': e.get('source'), 'target': e.get('target')} for e in added_edges],
                'removed': [{'source': e.get('source'), 'target': e.get('target')} for e in removed_edges],
            }
        }

    @app.route('/api/workflows/<app_id>/variables', methods=['GET'])
    def get_workflow_variables(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        wf = _get_workflow(app_id)
        if not wf:
            return jsonify(code=404, msg='工作流不存在')
        return jsonify(code=200, data={
            'environment_variables': wf['environment_variables'],
            'conversation_variables': wf['conversation_variables']
        })

    @app.route('/api/workflows/<app_id>/variables', methods=['PUT'])
    def save_workflow_variables(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        body = request.json or {}
        env_vars = body.get('environment_variables')
        conv_vars = body.get('conversation_variables')
        if not isinstance(env_vars, dict) or not isinstance(conv_vars, dict):
            return jsonify(code=400, msg='变量必须为对象')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    UPDATE dify_workflows
                    SET environment_variables = %s, conversation_variables = %s, updated_at = %s
                    WHERE app_id = %s
                ''', (
                    json.dumps(env_vars, ensure_ascii=False),
                    json.dumps(conv_vars, ensure_ascii=False),
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), app_id
                ))
                db.commit()
                affected = cur.rowcount
            finally:
                db.close()
            if not affected:
                return jsonify(code=404, msg='工作流不存在')
        except Exception as e:
            return jsonify(code=500, msg='保存失败: %s' % e)
        return jsonify(code=200, msg='保存成功')

    @app.route('/api/workflows/<app_id>/runs', methods=['GET'])
    def list_workflow_runs(app_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()

        # 分页和筛选参数
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(1, int(request.args.get('page_size', 20))))
        status_filter = request.args.get('status', '').strip()
        offset = (page - 1) * page_size

        db = get_db()
        try:
            cur = db.cursor()
            # 构建查询条件
            where_clause = 'WHERE app_id = %s'
            params = [app_id]
            if status_filter:
                where_clause += ' AND status = %s'
                params.append(status_filter)

            # 获取总数
            cur.execute(f'SELECT COUNT(*) as cnt FROM dify_workflow_runs {where_clause}', params)
            total = cur.fetchone()['cnt']
            total_pages = max(1, (total + page_size - 1) // page_size)

            # 获取分页数据
            cur.execute(f'''
                SELECT id, status, inputs, outputs, error, elapsed_time, total_tokens, total_steps, created_at, finished_at
                FROM dify_workflow_runs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', params + [page_size, offset])
            rows = cur.fetchall()
        finally:
            db.close()

        items = []
        for r in rows:
            def load(field):
                try:
                    return json.loads(field or '{}')
                except Exception:
                    return {}
            items.append({
                'id': str(r['id']),
                'status': r['status'],
                'inputs': load(r['inputs']),
                'outputs': load(r['outputs']),
                'error': r['error'],
                'elapsed_time': r['elapsed_time'],
                'total_tokens': r['total_tokens'],
                'total_steps': r['total_steps'],
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else '',
                'finished_at': r['finished_at'].strftime('%Y-%m-%d %H:%M:%S') if r['finished_at'] else ''
            })
        return jsonify(code=200, data={
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages
        })

    @app.route('/api/workflows/<app_id>/dsl', methods=['GET'])
    def export_workflow_dsl(app_id):
        """导出当前工作流为 DSL YAML"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        app_info = _get_app(app_id)
        wf = _get_workflow(app_id)
        if not app_info or not wf:
            return jsonify(code=404, msg='应用或工作流不存在')
        dsl = {
            'app': {
                'name': app_info['name'],
                'mode': app_info['mode'],
                'icon': app_info['icon'],
                'icon_background': app_info['icon_background'],
                'description': app_info['description'],
            },
            'workflow': {
                'graph': wf['graph'],
                'features': wf['features'],
                'environment_variables': wf['environment_variables'],
                'conversation_variables': wf['conversation_variables'],
                'rag_pipeline_variables': wf['rag_pipeline_variables'],
            },
            'kind': 'app',
            'version': '0.1.0',
        }
        try:
            content = yaml.safe_dump(dsl, allow_unicode=True, sort_keys=False, default_flow_style=False)
        except Exception as e:
            return jsonify(code=500, msg='导出失败: %s' % e)
        return jsonify(code=200, data={'dsl': content, 'name': app_info['name']})

    @app.route('/api/workflows/<app_id>/inputs', methods=['GET'])
    def get_workflow_inputs(app_id):
        """返回 Start 节点定义的输入变量，供运行面板构造表单"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        app_info = _get_app(app_id)
        wf = _get_workflow(app_id)
        if not wf:
            return jsonify(code=404, msg='工作流不存在')
        mode = app_info.get('mode', 'workflow') if app_info else 'workflow'
        return jsonify(code=200, data=_extract_start_inputs(wf['graph'], mode))

    @app.route('/api/workflows/<app_id>/run', methods=['POST'])
    def run_workflow_view(app_id):
        """触发工作流运行，返回单次运行结果（使用本地引擎）"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        app_info = _get_app(app_id)
        if not app_info:
            return jsonify(code=404, msg='应用不存在')
        if not app_info.get('tenant_id'):
            return jsonify(code=500, msg='应用缺少租户信息')
        body = request.json or {}
        inputs = body.get('inputs') or {}
        user = str(body.get('user') or request.args.get('uid') or 'szagent-user')
        # 支持前端传入图数据，优先使用（解决未保存就运行的问题）
        graph = body.get('graph')
        mode = body.get('mode')
        # 使用本地工作流引擎执行
        status, data = run_workflow(app_id, inputs, user, graph=graph, mode=mode)
        if status not in (200, 201):
            msg = (data or {}).get('message') or (data or {}).get('code') or '运行失败'
            # 记录运行失败
            log_audit_event(
                action='run_workflow_failed',
                resource_type='workflow',
                resource_id=app_id,
                resource_name=app_info.get('name', ''),
                description=f'工作流运行失败: {msg}',
                status='failed',
                error_message=str(msg)[:500],
                user_id=user,
                request_obj=request,
                response_code=status or 500,
            )
            return jsonify(code=status or 500, msg='运行失败: %s' % msg, data=data)
        # 统一把结果归一化，方便前端展示
        if app_info['mode'] not in ('workflow', 'completion'):
            data = {
                'status': 'succeeded',
                'outputs': {'answer': (data or {}).get('outputs', {}).get('answer', '')},
                'answer': (data or {}).get('outputs', {}).get('answer', ''),
                'elapsed_time': data.get('elapsed_time'),
                'total_tokens': data.get('total_tokens', 0),
                'total_steps': 0,
                'nodes': []
            }
        # 记录运行成功
        log_audit_event(
            action='run_workflow',
            resource_type='workflow',
            resource_id=app_id,
            resource_name=app_info.get('name', ''),
            description=f'工作流运行成功: {app_info.get("name", "")}',
            status='success',
            user_id=user,
            request_obj=request,
            response_code=200,
        )
        return jsonify(code=200, data=data)

    @app.route('/api/workflows/<app_id>/stream', methods=['POST'])
    def stream_workflow_view(app_id):
        """流式执行工作流，通过 SSE 推送实时进度"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        app_info = _get_app(app_id)
        if not app_info:
            return jsonify(code=404, msg='应用不存在')
        body = request.json or {}
        inputs = body.get('inputs') or {}
        user = str(body.get('user') or request.args.get('uid') or 'szagent-user')
        # 支持前端传入图数据，优先使用（解决未保存就运行的问题）
        graph = body.get('graph')
        mode = body.get('mode')

        def generate():
            """SSE 事件生成器"""
            try:
                for evt in run_workflow_stream(app_id, inputs, user, graph=graph, mode=mode):
                    event_name = evt.get('event', 'message')
                    event_data = json.dumps(evt.get('data', {}), ensure_ascii=False)
                    yield f'event: {event_name}\ndata: {event_data}\n\n'
            except Exception as e:
                # 推送错误事件
                error_data = json.dumps({'message': str(e)}, ensure_ascii=False)
                yield f'event: error\ndata: {error_data}\n\n'

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    @app.route('/api/workflows/runs/<run_id>/stop', methods=['POST'])
    def stop_workflow_run(run_id):
        """
        停止正在运行的工作流

        参数:
            run_id: 运行 ID（从 SSE 事件的 workflow_start 中获取）

        响应: { code: 200, msg: '已停止' } 或 { code: 404, msg: '任务不存在或已结束' }
        """
        if not _is_uuid(run_id):
            return jsonify(code=400, msg='非法的运行 ID')
        from engine.workflow_runner import _cancel_workflow_task
        success = _cancel_workflow_task(run_id)
        if success:
            return jsonify(code=200, msg='已停止工作流运行')
        return jsonify(code=404, msg='任务不存在或已结束')

    @app.route('/api/workflows/<app_id>/runs/<run_id>', methods=['GET'])
    def get_workflow_run(app_id, run_id):
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        detail = _get_run_detail(app_id, run_id)
        if not detail:
            return jsonify(code=404, msg='运行记录不存在')
        return jsonify(code=200, data=detail)

    @app.route('/api/workflows/<app_id>/test-runs', methods=['GET'])
    def list_workflow_test_runs(app_id):
        """返回当前用户保存的测试运行记录"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_workflow_test_runs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT * FROM workflow_test_runs WHERE app_id = %s ORDER BY created_at DESC LIMIT 100',
                (app_id,)
            )
            rows = cur.fetchall()
        finally:
            db.close()

        def load_json(field):
            try:
                return json.loads(field or '{}')
            except Exception:
                return {}

        items = []
        for r in rows:
            items.append({
                'id': r['id'],
                'app_id': r['app_id'],
                'run_name': r['run_name'] or '',
                'inputs': load_json(r['inputs_json']),
                'outputs': load_json(r['outputs_json']),
                'status': r['status'] or '',
                'error': r['error'] or '',
                'elapsed_time': r['elapsed_time'],
                'total_tokens': r['total_tokens'] or 0,
                'total_steps': r['total_steps'] or 0,
                'nodes': load_json(r['nodes_json']),
                'created_by': r['created_by'] or '',
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else ''
            })
        return jsonify(code=200, data=items)

    @app.route('/api/workflows/<app_id>/test-runs', methods=['POST'])
    def save_workflow_test_run(app_id):
        """保存一次测试运行结果"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_workflow_test_runs_table()
        body = request.json or {}
        run_name = (body.get('run_name') or '').strip()
        result = body.get('result') or {}
        if not isinstance(result, dict):
            return jsonify(code=400, msg='result 格式错误')
        uid = str(request.args.get('uid') or body.get('uid') or '').strip()
        if not run_name:
            run_name = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''
                INSERT INTO workflow_test_runs
                (app_id, run_name, inputs_json, outputs_json, status, error, elapsed_time,
                 total_tokens, total_steps, nodes_json, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                app_id, run_name,
                json.dumps(body.get('inputs') or {}, ensure_ascii=False),
                json.dumps(result.get('outputs') or {}, ensure_ascii=False),
                result.get('status') or '',
                result.get('error') or '',
                result.get('elapsed_time'),
                result.get('total_tokens') or 0,
                result.get('total_steps') or 0,
                json.dumps(result.get('nodes') or [], ensure_ascii=False),
                uid, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            ))
            db.commit()
            return jsonify(code=200, data={'id': cur.lastrowid, 'run_name': run_name})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='保存失败: %s' % e)
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>', methods=['DELETE'])
    def delete_workflow_app(app_id):
        """从 MySQL 中删除工作流应用及其关联数据"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        # 先检查应用是否存在
        app_info = _get_app(app_id)
        if not app_info:
            return jsonify(code=404, msg='应用不存在')
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 删除关联表（按外键依赖顺序）
                cur.execute(r'DELETE FROM dify_workflow_node_executions WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_workflow_runs WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_workflows WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_app_model_configs WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_sites WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_api_tokens WHERE app_id = %s', (app_id,))
                cur.execute(r'DELETE FROM dify_apps WHERE id = %s', (app_id,))
                db.commit()
            finally:
                db.close()
            # 记录删除操作
            log_audit_event(
                action='delete_workflow',
                resource_type='workflow',
                resource_id=app_id,
                resource_name=app_info.get('name', ''),
                description=f'删除工作流: {app_info.get("name", "")}',
                status='success',
                request_obj=request,
                response_code=200,
            )
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            # 记录删除失败
            log_audit_event(
                action='delete_workflow_failed',
                resource_type='workflow',
                resource_id=app_id,
                resource_name=app_info.get('name', ''),
                description=f'删除工作流失败: {str(e)}',
                status='failed',
                error_message=str(e)[:500],
                request_obj=request,
                response_code=500,
            )
            return jsonify(code=500, msg='删除失败: %s' % e)

    @app.route('/api/workflows/<app_id>/test-runs/<int:tid>', methods=['DELETE'])
    def delete_workflow_test_run(app_id, tid):
        """删除一条保存的测试运行记录"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_workflow_test_runs_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM workflow_test_runs WHERE id = %s AND app_id = %s', (tid, app_id))
            db.commit()
            if not cur.rowcount:
                return jsonify(code=404, msg='记录不存在')
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: %s' % e)
        finally:
            db.close()

    # ==================== Human Input API ====================

    # ==================== SMTP 配置 API ====================
    # 注意：SMTP 路由已在 auth.py 中定义（带认证），此处不再重复注册

    # ==================== Human Input 邮件投递 API（3.6） ====================

    @app.route('/api/human-input/deliveries', methods=['GET'])
    def list_human_input_deliveries():
        """获取投递记录列表"""
        try:
            from engine.human_input_delivery import get_deliveries
            run_id = request.args.get('run_id', '').strip() or None
            app_id = request.args.get('app_id', '').strip() or None
            status = request.args.get('status', '').strip() or None
            limit = int(request.args.get('limit', 50))
            deliveries = get_deliveries(run_id=run_id, app_id=app_id, status=status, limit=limit)
            return jsonify(code=200, data=deliveries)
        except Exception as e:
            return jsonify(code=500, msg='获取投递记录失败: ' + str(e))

    @app.route('/api/workflows/<app_id>/human-input/pending', methods=['GET'])
    def get_pending_human_input(app_id):
        """获取当前待处理的 Human Input（用于前端轮询）"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        db = get_db()
        try:
            cur = db.cursor()
            # 查找最近一个暂停在 Human Input 的工作流运行
            cur.execute(r'''
                SELECT * FROM dify_workflow_runs
                WHERE app_id = %s AND status = 'waiting'
                ORDER BY created_at DESC LIMIT 1
            ''', (app_id,))
            run = cur.fetchone()
            if not run:
                return jsonify(code=200, data={'pending': False})
            # 解析 outputs 获取 Human Input 配置
            outputs = json.loads(run['outputs'] or '{}')
            config = outputs.get('__human_input_config__', {})
            return jsonify(code=200, data={
                'pending': True,
                'run_id': run['id'],
                'node_id': outputs.get('__human_input_node_id__', ''),
                'config': config,
            })
        except Exception as e:
            return jsonify(code=500, msg='获取待处理输入失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/human-input/submit', methods=['POST'])
    def submit_human_input(app_id):
        """提交 Human Input，恢复工作流执行"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        body = request.json or {}
        run_id = body.get('run_id', '').strip()
        user_input = body.get('input') or {}
        if not run_id:
            return jsonify(code=400, msg='run_id 不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            # 获取运行记录
            cur.execute(r'SELECT * FROM dify_workflow_runs WHERE id = %s AND app_id = %s', (run_id, app_id))
            run = cur.fetchone()
            if not run:
                return jsonify(code=404, msg='运行记录不存在')

            # 解析保存的上下文（_pause_payload 写入 dify_workflow_runs.outputs）
            outputs = json.loads(run['outputs'] or '{}')
            context = outputs.get('__context__', {})
            output_var = outputs.get('__human_input_output_var__', 'human_input')
            human_node_id = outputs.get('__human_input_node_id__', '')
            executed_nodes = list(outputs.get('__executed_nodes__', []))
            branch_map = dict(outputs.get('__branch_map__', {}))

            # 将用户输入注入上下文：写入人工介入节点的 node 命名空间 + 扁平别名（extra 覆盖）
            from engine.workflow_runner import apply_node_outputs
            if isinstance(user_input, dict):
                injected = dict(user_input)
                injected[output_var] = user_input
            else:
                injected = {output_var: user_input}
            if human_node_id:
                apply_node_outputs(context, human_node_id, injected, extra=True)
            else:
                context.update(injected)

            # 更新运行状态为运行中
            cur.execute(r"UPDATE dify_workflow_runs SET status = 'running' WHERE id = %s", (run_id,))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='恢复执行失败: ' + str(e))
        finally:
            db.close()

        # 3.6: 标记邮件投递为已提交
        try:
            from engine.human_input_delivery import mark_delivery_submitted
            mark_delivery_submitted(run_id)
        except Exception:
            pass

        # 从暂停处继续执行后续节点（经调度器恢复：与首次执行共用同一套就绪/剪枝逻辑）
        try:
            from engine.workflow_runner import _execute_workflow_graph
            # 获取工作流图
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
                wf_row = cur.fetchone()
                cur.execute(r'SELECT * FROM dify_app_model_configs WHERE app_id = %s LIMIT 1', (app_id,))
                model_cfg_row = cur.fetchone()
            finally:
                db.close()

            graph = json.loads(wf_row['graph'] or '{}')

            # 人工介入节点视为已完成：加入 executed 以触发其出边、避免重复执行/再次暂停
            resume_executed = list(dict.fromkeys(
                executed_nodes + ([human_node_id] if human_node_id else [])))
            result = _execute_workflow_graph(
                graph, {}, model_cfg_row, app_id, run_id,
                resume={'executed': resume_executed, 'branches': branch_map, 'context': context},
            )

            # 多个 Human Input：仍可能再次暂停
            if isinstance(result, dict) and result.get('__human_input_pause__'):
                db = get_db()
                try:
                    cur = db.cursor()
                    cur.execute(r"UPDATE dify_workflow_runs SET status='waiting', outputs=%s WHERE id=%s",
                                (json.dumps(result, ensure_ascii=False), run_id))
                    db.commit()
                finally:
                    db.close()
                return jsonify(code=200, data={
                    'status': 'waiting',
                    'message': '等待用户输入',
                    'human_input': {
                        'config': result.get('__human_input_config__', {}),
                        'node_id': result.get('__human_input_node_id__', ''),
                        'output_var': result.get('__human_input_output_var__', 'human_input'),
                    },
                })

            # 更新运行记录为成功
            ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''
                    UPDATE dify_workflow_runs
                    SET status = 'succeeded', outputs = %s, finished_at = %s
                    WHERE id = %s
                ''', (json.dumps(result, ensure_ascii=False), ts, run_id))
                db.commit()
            finally:
                db.close()

            return jsonify(code=200, data={
                'status': 'succeeded',
                'outputs': {k: v for k, v in result.items() if not k.startswith('__')},
            })
        except Exception as e:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r"UPDATE dify_workflow_runs SET status = 'failed', error = %s WHERE id = %s", (str(e)[:500], run_id))
                db.commit()
            finally:
                db.close()
            return jsonify(code=500, msg='恢复执行失败: ' + str(e))

    # ==================== 异步工作流 API ====================
    # 注意：/api/model-providers 已在 models.py 中定义，此处不再重复注册

    @app.route('/api/workflows/<app_id>/run-async', methods=['POST'])
    def run_workflow_async_view(app_id):
        """
        异步触发工作流运行，立即返回任务 ID

        请求体: {inputs: {}, user: 'xxx'}
        响应: {code: 202, data: {task_id, run_id, status: 'pending'}}

        使用方式:
            1. 调用此接口获取 task_id
            2. 通过 GET /api/workflows/tasks/<task_id> 轮询任务状态
            3. 或通过 WebSocket 订阅实时进度
        """
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        _ensure_dify_tables()
        app_info = _get_app(app_id)
        if not app_info:
            return jsonify(code=404, msg='应用不存在')

        body = request.json or {}
        inputs = body.get('inputs') or {}
        user = str(body.get('user') or request.args.get('uid') or 'szagent-user')
        stream = bool(body.get('stream', False))

        try:
            if stream:
                from tasks.workflow_tasks import run_workflow_stream_async
                task = run_workflow_stream_async.delay(app_id, inputs, user)
            else:
                from tasks.workflow_tasks import run_workflow_async
                task = run_workflow_async.delay(app_id, inputs, user)

            # 记录审计日志
            log_audit_event(
                action='run_workflow_async',
                resource_type='workflow',
                resource_id=app_id,
                resource_name=app_info.get('name', ''),
                description=f'异步触发工作流: {app_info.get("name", "")}',
                status='success',
                user_id=user,
                request_obj=request,
                response_code=202,
            )

            return jsonify(code=202, data={
                'task_id': task.id,
                'status': 'pending',
                'message': '工作流已加入执行队列',
                'poll_url': f'/api/workflows/tasks/{task.id}',
                'ws_room': f'wf:{app_id}',
            })
        except Exception as e:
            log_audit_event(
                action='run_workflow_async_failed',
                resource_type='workflow',
                resource_id=app_id,
                resource_name=app_info.get('name', ''),
                description=f'异步触发工作流失败: {str(e)}',
                status='failed',
                error_message=str(e)[:500],
                user_id=user,
                request_obj=request,
                response_code=500,
            )
            return jsonify(code=500, msg='异步启动失败: %s' % str(e))

    @app.route('/api/workflows/tasks/<task_id>', methods=['GET'])
    def get_async_task_status(task_id):
        """
        查询异步任务状态

        响应:
            进行中: {code: 200, data: {task_id, state: 'RUNNING', status: 'running', meta: {...}}}
            成功:   {code: 200, data: {task_id, state: 'SUCCESS', status: 'succeeded', result: {...}}}
            失败:   {code: 200, data: {task_id, state: 'FAILURE', status: 'failed', error: '...'}}
        """
        from tasks.workflow_tasks import get_workflow_task_status
        status = get_workflow_task_status(task_id)
        return jsonify(code=200, data=status)

    @app.route('/api/workflows/tasks/<task_id>/cancel', methods=['POST'])
    def cancel_async_task(task_id):
        """
        取消异步任务

        响应: {code: 200, msg: '已发送取消信号'} 或 {code: 400, msg: '任务已完成或不存在'}
        """
        from tasks.workflow_tasks import revoke_workflow_task
        try:
            revoke_workflow_task(task_id, terminate=True)
            return jsonify(code=200, msg='已发送取消信号')
        except Exception as e:
            return jsonify(code=400, msg='取消失败: %s' % str(e))

    @app.route('/api/workflows/<app_id>/run-sync', methods=['POST'])
    def run_workflow_sync_view(app_id):
        """
        同步执行工作流（保留原有行为，供小型工作流快速执行）

        与 /api/workflows/<app_id>/run 的区别:
            - 增加了 mode 参数支持（sync/async）
            - 默认为同步模式，保持向后兼容
        """
        # 复用原有的 run_workflow_view 逻辑
        return run_workflow_view(app_id)

    # ============================================================
    # Human Input 表单 API（P1: 工作流暂停交互）
    # ============================================================

    def _ensure_human_input_forms_table():
        """确保 Human Input 表单表存在"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(HUMAN_INPUT_FORMS_TABLE_SQL)
            db.commit()
        finally:
            db.close()

    @app.route('/api/workflows/human-input-forms', methods=['GET'])
    def list_human_input_forms():
        """列出 Human Input 表单"""
        _ensure_human_input_forms_table()
        tenant_id = request.args.get('tenant_id', 'system')
        status = request.args.get('status', '')
        workflow_run_id = request.args.get('workflow_run_id', '')

        where = ['tenant_id = %s']
        params = [tenant_id]
        if status:
            where.append('status = %s')
            params.append(status)
        if workflow_run_id:
            where.append('workflow_run_id = %s')
            params.append(workflow_run_id)

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM human_input_forms
                           WHERE ''' + ' AND '.join(where) + r'''
                           ORDER BY created_at DESC''', params)
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'tenant_id': r['tenant_id'],
                    'app_id': r['app_id'], 'workflow_run_id': r['workflow_run_id'],
                    'node_id': r['node_id'], 'form_key': r['form_key'],
                    'title': r['title'], 'description': r['description'],
                    'input_fields': json.loads(r['input_fields_json'] or '[]'),
                    'submit_url': r['submit_url'],
                    'status': r['status'],
                    'submitted_by': r['submitted_by'],
                    'submitted_data': json.loads(r['submitted_data_json'] or '{}') if r['submitted_data_json'] else {},
                    'submitted_at': str(r['submitted_at'] or ''),
                    'expired_at': str(r['expired_at'] or ''),
                    'created_at': str(r['created_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/workflows/human-input-forms', methods=['POST'])
    def create_human_input_form():
        """创建 Human Input 表单"""
        _ensure_human_input_forms_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        title = (body.get('title') or '').strip()
        if not title:
            return jsonify(code=400, msg='表单标题必填')

        import secrets
        form_id = str(uuid.uuid4())
        form_key = 'hf-' + secrets.token_hex(16)
        submit_token = secrets.token_hex(32)

        # 构建提交 URL
        base_url = request.host_url.rstrip('/')
        submit_url = f"{base_url}/api/workflows/human-input-forms/{form_key}/submit"

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO human_input_forms
                           (id, tenant_id, app_id, workflow_run_id, node_id, form_key,
                            title, description, input_fields_json, submit_url, submit_token,
                            status, expired_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting', %s)''',
                        (form_id,
                         body.get('tenant_id', 'system'),
                         body.get('app_id', ''),
                         body.get('workflow_run_id', ''),
                         body.get('node_id', ''),
                         form_key,
                         title,
                         body.get('description', ''),
                         json.dumps(body.get('input_fields', []), ensure_ascii=False),
                         submit_url,
                         submit_token,
                         body.get('expired_at', None)))
            db.commit()
            return jsonify(code=200, msg='创建成功', data={
                'id': form_id, 'form_key': form_key,
                'submit_url': submit_url, 'status': 'waiting'
            })
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='创建失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/human-input-forms/<form_key>/submit', methods=['POST'])
    def submit_human_input_form(form_key):
        """提交 Human Input 表单"""
        _ensure_human_input_forms_table()
        body = request.get_json() or {}
        submit_token = body.get('submit_token', '')
        submitted_data = body.get('data', {})

        db = get_db()
        try:
            cur = db.cursor()
            # 验证表单
            cur.execute(r'''SELECT * FROM human_input_forms
                           WHERE form_key = %s AND status = 'waiting'
                           AND (expired_at IS NULL OR expired_at > NOW())''', (form_key,))
            form = cur.fetchone()
            if not form:
                return jsonify(code=404, msg='表单不存在或已过期')

            if submit_token and submit_token != form['submit_token']:
                return jsonify(code=403, msg='提交令牌无效')

            # 更新表单状态
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(r'''UPDATE human_input_forms
                           SET status = 'submitted',
                               submitted_data_json = %s,
                               submitted_by = %s,
                               submitted_at = %s
                           WHERE form_key = %s''',
                        (json.dumps(submitted_data, ensure_ascii=False),
                         body.get('submitted_by', ''),
                         now_str,
                         form_key))
            db.commit()
            return jsonify(code=200, msg='提交成功', data={
                'form_key': form_key,
                'workflow_run_id': form['workflow_run_id'],
                'submitted_at': now_str
            })
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='提交失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/human-input-forms/<form_key>', methods=['GET'])
    def get_human_input_form(form_key):
        """获取单个 Human Input 表单（用于表单页面渲染）"""
        _ensure_human_input_forms_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM human_input_forms WHERE form_key = %s''', (form_key,))
            form = cur.fetchone()
            if not form:
                return jsonify(code=404, msg='表单不存在')
            return jsonify(code=200, data={
                'id': form['id'],
                'form_key': form['form_key'],
                'app_id': form['app_id'],
                'app_name': form['title'],
                'workflow_run_id': form['workflow_run_id'],
                'node_id': form['node_id'],
                'title': form['title'],
                'message': form['description'],
                'fields': json.loads(form['input_fields_json'] or '[]'),
                'status': form['status'],
                'submitted_data': json.loads(form['submitted_data_json'] or '{}') if form['submitted_data_json'] else {},
                'expired_at': str(form['expired_at'] or ''),
                'created_at': str(form['created_at'] or ''),
            })
        finally:
            db.close()

    # ============================================================
    # 工作流暂停/恢复 API（P1: 工作流控制）
    # ============================================================

    def _ensure_workflow_pauses_table():
        """确保工作流暂停状态表存在"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(WORKFLOW_PAUSES_TABLE_SQL)
            db.commit()
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/pause', methods=['POST'])
    def pause_workflow(app_id):
        """暂停工作流"""
        _ensure_workflow_pauses_table()
        body = request.get_json() or {}
        workflow_run_id = body.get('workflow_run_id', '')
        node_id = body.get('node_id', '')
        pause_reason = body.get('pause_reason', 'human_input')

        if not workflow_run_id or not node_id:
            return jsonify(code=400, msg='workflow_run_id 和 node_id 必填')

        pause_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_pauses
                           (id, tenant_id, app_id, workflow_id, workflow_run_id,
                            node_id, node_type, pause_reason, pause_context_json,
                            resume_strategy, timeout_seconds, paused_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (pause_id,
                         body.get('tenant_id', 'system'),
                         app_id,
                         body.get('workflow_id', ''),
                         workflow_run_id,
                         node_id,
                         body.get('node_type', 'human-input'),
                         pause_reason,
                         json.dumps(body.get('context', {}), ensure_ascii=False),
                         body.get('resume_strategy', 'manual'),
                         body.get('timeout_seconds', 86400),
                         body.get('paused_by', '')))
            db.commit()
            return jsonify(code=200, msg='已暂停', data={'pause_id': pause_id})
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='暂停失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/resume', methods=['POST'])
    def resume_workflow(app_id):
        """恢复工作流"""
        _ensure_workflow_pauses_table()
        body = request.get_json() or {}
        pause_id = body.get('pause_id', '')
        workflow_run_id = body.get('workflow_run_id', '')

        if not pause_id and not workflow_run_id:
            return jsonify(code=400, msg='pause_id 或 workflow_run_id 必填')

        db = get_db()
        try:
            cur = db.cursor()
            if pause_id:
                cur.execute(r'''UPDATE workflow_pauses
                               SET status = 'resumed',
                                   resumed_by = %s,
                                   resumed_at = NOW()
                               WHERE id = %s AND status = 'paused' ''',
                            (body.get('resumed_by', ''), pause_id))
            else:
                cur.execute(r'''UPDATE workflow_pauses
                               SET status = 'resumed',
                                   resumed_by = %s,
                                   resumed_at = NOW()
                               WHERE workflow_run_id = %s AND status = 'paused' ''',
                            (body.get('resumed_by', ''), workflow_run_id))
            db.commit()
            return jsonify(code=200, msg='已恢复')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='恢复失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/pauses', methods=['GET'])
    def list_workflow_pauses(app_id):
        """列出工作流暂停记录"""
        _ensure_workflow_pauses_table()
        tenant_id = request.args.get('tenant_id', 'system')
        status = request.args.get('status', '')

        where = ['tenant_id = %s AND app_id = %s']
        params = [tenant_id, app_id]
        if status:
            where.append('status = %s')
            params.append(status)

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM workflow_pauses
                           WHERE ''' + ' AND '.join(where) + r'''
                           ORDER BY paused_at DESC''', params)
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'app_id': r['app_id'],
                    'workflow_run_id': r['workflow_run_id'],
                    'node_id': r['node_id'], 'node_type': r['node_type'],
                    'pause_reason': r['pause_reason'],
                    'resume_strategy': r['resume_strategy'],
                    'status': r['status'],
                    'paused_by': r['paused_by'],
                    'paused_at': str(r['paused_at'] or ''),
                    'resumed_by': r['resumed_by'],
                    'resumed_at': str(r['resumed_at'] or ''),
                    'timeout_seconds': r['timeout_seconds'],
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    # ============================================================
    # 工作流变量 API（P1: 对话变量/草稿变量管理）
    # ============================================================

    def _ensure_workflow_conversation_variables_table():
        """确保工作流对话变量表存在"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(WORKFLOW_CONVERSATION_VARIABLES_TABLE_SQL)
            db.commit()
        finally:
            db.close()

    def _ensure_workflow_draft_variables_table():
        """确保工作流草稿变量表存在"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(WORKFLOW_DRAFT_VARIABLES_TABLE_SQL)
            db.commit()
        finally:
            db.close()

    @app.route('/api/workflows/conversation-variables', methods=['GET'])
    def list_conversation_variables():
        """列出对话变量"""
        _ensure_workflow_conversation_variables_table()
        conversation_id = request.args.get('conversation_id', '')
        if not conversation_id:
            return jsonify(code=400, msg='conversation_id 必填')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM workflow_conversation_variables
                           WHERE conversation_id = %s
                           ORDER BY variable_name''', (conversation_id,))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'conversation_id': r['conversation_id'],
                    'variable_name': r['variable_name'],
                    'variable_type': r['variable_type'],
                    'variable_value': json.loads(r['variable_value'] or 'null') if r['variable_value'] else None,
                    'variable_scope': r['variable_scope'],
                    'is_persistent': bool(r['is_persistent']),
                    'expires_at': str(r['expires_at'] or ''),
                    'created_at': str(r['created_at'] or ''),
                    'updated_at': str(r['updated_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/workflows/conversation-variables', methods=['POST'])
    def set_conversation_variable():
        """设置对话变量"""
        _ensure_workflow_conversation_variables_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        conversation_id = body.get('conversation_id', '')
        variable_name = body.get('variable_name', '')
        if not conversation_id or not variable_name:
            return jsonify(code=400, msg='conversation_id 和 variable_name 必填')

        var_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_conversation_variables
                           (id, tenant_id, app_id, conversation_id, workflow_run_id,
                            variable_name, variable_type, variable_value, variable_scope,
                            source_node_id, is_persistent, expires_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                            variable_type = VALUES(variable_type),
                            variable_value = VALUES(variable_value),
                            variable_scope = VALUES(variable_scope),
                            source_node_id = VALUES(source_node_id),
                            is_persistent = VALUES(is_persistent),
                            expires_at = VALUES(expires_at)''',
                        (var_id,
                         body.get('tenant_id', 'system'),
                         body.get('app_id', ''),
                         conversation_id,
                         body.get('workflow_run_id', ''),
                         variable_name,
                         body.get('variable_type', 'string'),
                         json.dumps(body.get('variable_value'), ensure_ascii=False),
                         body.get('variable_scope', 'conversation'),
                         body.get('source_node_id', ''),
                         1 if body.get('is_persistent', True) else 0,
                         body.get('expires_at', None)))
            db.commit()
            return jsonify(code=200, msg='设置成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='设置失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/conversation-variables/<var_id>', methods=['DELETE'])
    def delete_conversation_variable(var_id):
        """删除对话变量"""
        _ensure_workflow_conversation_variables_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM workflow_conversation_variables WHERE id = %s', (var_id,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/draft-variables', methods=['GET'])
    def list_draft_variables(app_id):
        """列出工作流草稿变量"""
        _ensure_workflow_draft_variables_table()
        draft_key = request.args.get('draft_key', 'default')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''SELECT * FROM workflow_draft_variables
                           WHERE app_id = %s AND draft_key = %s
                           ORDER BY variable_name''', (app_id, draft_key))
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'], 'app_id': r['app_id'],
                    'draft_key': r['draft_key'],
                    'variable_name': r['variable_name'],
                    'variable_type': r['variable_type'],
                    'variable_value': json.loads(r['variable_value'] or 'null') if r['variable_value'] else None,
                    'default_value': json.loads(r['default_value'] or 'null') if r['default_value'] else None,
                    'description': r['description'],
                    'is_required': bool(r['is_required']),
                    'validation_rule': json.loads(r['validation_rule'] or '{}') if r['validation_rule'] else {},
                    'ui_config': json.loads(r['ui_config_json'] or '{}') if r['ui_config_json'] else {},
                    'created_by': r['created_by'],
                    'created_at': str(r['created_at'] or ''),
                    'updated_at': str(r['updated_at'] or ''),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/draft-variables', methods=['POST'])
    def set_draft_variable():
        """设置工作流草稿变量"""
        _ensure_workflow_draft_variables_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        app_id = body.get('app_id', app_id)
        variable_name = body.get('variable_name', '')
        if not variable_name:
            return jsonify(code=400, msg='variable_name 必填')

        var_id = str(uuid.uuid4())
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_draft_variables
                           (id, tenant_id, app_id, workflow_id, draft_key,
                            variable_name, variable_type, variable_value, default_value,
                            description, is_required, validation_rule, ui_config_json, created_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                            variable_type = VALUES(variable_type),
                            variable_value = VALUES(variable_value),
                            default_value = VALUES(default_value),
                            description = VALUES(description),
                            is_required = VALUES(is_required),
                            validation_rule = VALUES(validation_rule),
                            ui_config_json = VALUES(ui_config_json)''',
                        (var_id,
                         body.get('tenant_id', 'system'),
                         app_id,
                         body.get('workflow_id', ''),
                         body.get('draft_key', 'default'),
                         variable_name,
                         body.get('variable_type', 'string'),
                         json.dumps(body.get('variable_value'), ensure_ascii=False) if body.get('variable_value') is not None else None,
                         json.dumps(body.get('default_value'), ensure_ascii=False) if body.get('default_value') is not None else None,
                         body.get('description', ''),
                         1 if body.get('is_required', False) else 0,
                         json.dumps(body.get('validation_rule', {}), ensure_ascii=False),
                         json.dumps(body.get('ui_config', {}), ensure_ascii=False),
                         body.get('created_by', '')))
            db.commit()
            return jsonify(code=200, msg='设置成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='设置失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/draft-variables/<var_id>', methods=['DELETE'])
    def delete_draft_variable(app_id, var_id):
        """删除工作流草稿变量"""
        _ensure_workflow_draft_variables_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM workflow_draft_variables WHERE id = %s AND app_id = %s',
                        (var_id, app_id))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

    # ============================================================
    # 触发器管理（定时计划 / 触发日志）—— 对应 Dify trigger_schedule
    # ============================================================

    @app.route('/api/workflows/<app_id>/schedules', methods=['GET'])
    def list_workflow_schedules(app_id):
        """列出应用的定时触发计划"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        from engine.trigger_engine import list_schedule_plans
        try:
            plans = list_schedule_plans(app_id)
        except Exception as e:
            return jsonify(code=500, msg='查询失败: ' + str(e))
        return jsonify(code=200, data=[dict(p) for p in plans])

    @app.route('/api/workflows/schedules/<plan_id>', methods=['PUT'])
    def update_workflow_schedule(plan_id):
        """更新定时计划（修改 cron / 启用 / 停用）"""
        body = request.json or {}
        cron_expr = body.get('cron_expr')
        enabled = body.get('enabled')
        if cron_expr is None and enabled is None:
            return jsonify(code=400, msg='无可更新字段（cron_expr / enabled）')
        from engine.trigger_engine import update_schedule_plan
        try:
            ok, message = update_schedule_plan(plan_id, cron_expr=cron_expr, enabled=enabled)
        except Exception as e:
            return jsonify(code=500, msg='更新失败: ' + str(e))
        if not ok:
            return jsonify(code=400, msg=message)
        return jsonify(code=200, msg=message)

    @app.route('/api/workflows/schedules/<plan_id>', methods=['DELETE'])
    def delete_workflow_schedule(plan_id):
        """删除定时计划"""
        from engine.trigger_engine import delete_schedule_plan
        try:
            deleted = delete_schedule_plan(plan_id)
        except Exception as e:
            return jsonify(code=500, msg='删除失败: ' + str(e))
        if not deleted:
            return jsonify(code=404, msg='计划不存在')
        return jsonify(code=200, msg='删除成功')

    @app.route('/api/workflows/<app_id>/trigger-logs', methods=['GET'])
    def list_workflow_trigger_logs(app_id):
        """分页查询触发日志（schedule / webhook / plugin）"""
        if not _is_uuid(app_id):
            return jsonify(code=400, msg='非法的应用 ID')
        trigger_type = request.args.get('trigger_type') or None
        page = max(int(request.args.get('page', 1) or 1), 1)
        page_size = min(int(request.args.get('page_size', 20) or 20), 100)
        from engine.trigger_engine import list_trigger_logs
        try:
            data = list_trigger_logs(app_id, trigger_type=trigger_type, page=page, page_size=page_size)
        except Exception as e:
            return jsonify(code=500, msg='查询失败: ' + str(e))
        return jsonify(code=200, data={'items': [dict(r) for r in data['items']],
                                       'total': data['total'], 'page': page, 'page_size': page_size})

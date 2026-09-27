# -*- coding: utf-8 -*-
"""
YAML DSL 导出/导入 —— 对齐 Dify DSL 格式，支持应用完整配置的可移植性

支持:
- Agent 导出/导入（单智能体配置 + 绑定技能 + 模型配置）
- Workflow 导出/导入（graph JSON + 节点配置 + 变量）
"""

import json
import uuid
from datetime import datetime
from flask import jsonify, request

import yaml

from config import get_db
from models.tables import (
    AGENTS_TABLE_SQL,
    AGENT_SKILL_BINDINGS_TABLE_SQL,
    DIFY_APPS_TABLE_SQL,
    DIFY_WORKFLOWS_TABLE_SQL,
    DIFY_APP_MODEL_CONFIGS_TABLE_SQL,
    DIFY_API_TOKENS_TABLE_SQL,
)
from utils.helpers import now


def _ensure_tables():
    """确保所有依赖表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(AGENTS_TABLE_SQL)
        cur.execute(AGENT_SKILL_BINDINGS_TABLE_SQL)
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_WORKFLOWS_TABLE_SQL)
        cur.execute(DIFY_APP_MODEL_CONFIGS_TABLE_SQL)
        cur.execute(DIFY_API_TOKENS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


# ============================================================
# Agent DSL 导出/导入
# ============================================================

def _export_agent_dsl(aid):
    """导出单智能体为 YAML DSL"""
    db = get_db()
    try:
        cur = db.cursor()
        # 获取 Agent 信息
        cur.execute(
            r'SELECT id, name, role, description, icon, status, config FROM agents WHERE id = %s',
            (aid,))
        agent = cur.fetchone()
        if not agent:
            return None, '智能体不存在'

        # 解析 config
        config = {}
        if agent.get('config'):
            try:
                config = json.loads(agent['config'])
            except Exception:
                config = {}

        # 获取绑定技能
        cur.execute(
            r'SELECT skill_key, skill_name, skill_icon, skill_kind FROM agent_skill_bindings WHERE agent_id = %s',
            (aid,))
        skills = cur.fetchall()

        # 构建 DSL
        dsl = {
            'kind': 'agent',
            'version': '0.1.0',
            'app': {
                'name': agent['name'] or '',
                'mode': 'agent',
                'icon': agent.get('icon') or '🤖',
                'description': agent.get('description') or '',
            },
            'agent': {
                'role': agent.get('role') or '',
                'prompt': config.get('prompt', ''),
                'strategy': config.get('strategy', 'react'),
                'max_iterations': config.get('max_iterations', 5),
                'output_format': config.get('output_format', 'text'),
                'fallback_model': config.get('fallback_model', ''),
                'memory_enabled': config.get('memory_enabled', True),
                'temperature': config.get('temperature', 0.7),
                'max_tokens': config.get('max_tokens', 4096),
            },
            'skills': [{
                'key': s['skill_key'],
                'name': s['skill_name'],
                'icon': s['skill_icon'],
                'kind': s['skill_kind'],
            } for s in skills],
            'model_config': {
                'provider': config.get('model_provider', ''),
                'model': agent.get('model_name', ''),
                'temperature': config.get('temperature', 0.7),
                'max_tokens': config.get('max_tokens', 4096),
            },
            'exported_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        content = yaml.safe_dump(dsl, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return {'dsl': content, 'name': agent['name'], 'kind': 'agent'}, None
    finally:
        db.close()


def _import_agent_dsl(dsl_data, owner_id=None):
    """从 YAML DSL 创建/更新单智能体。

    owner_id 缺省不再用 1：那列已改成存 dify_accounts.id（UUID），
    写进去一个 '1' 会让导入的智能体对任何登录账号都不可见（列表按 owner 过滤）。
    没传时回退到当前登录身份，拿不到真实账号就拒绝导入，不造无主数据。
    """
    owner_id = str(owner_id or '').strip()
    if not owner_id:
        from utils.helpers import _safe_uid
        owner_id = _safe_uid(None)
    if not owner_id or owner_id.isdigit():
        # 空串 = 无登录态（_safe_uid 现在不再伪造身份）；纯数字 = 已废弃的旧 users.id 残留。
        # 这两种值写进 owner 只会造出对任何账号都不可见、又不报错的无主数据。
        return None, '无法确定导入归属（缺少登录态），请在页面登录后重试'
    app_section = dsl_data.get('app', {})
    agent_section = dsl_data.get('agent', {})
    skills_section = dsl_data.get('skills', [])

    name = (app_section.get('name') or '').strip()
    if not name:
        return None, '应用名称不能为空'

    db = get_db()
    try:
        cur = db.cursor()

        # 检查同名应用是否已存在
        cur.execute(
            r"SELECT id FROM agents WHERE name = %s AND type = 'single' AND owner = %s",
            (name, owner_id))
        existing = cur.fetchone()

        # 构建 config JSON
        config = {
            'prompt': agent_section.get('prompt', ''),
            'strategy': agent_section.get('strategy', 'react'),
            'max_iterations': agent_section.get('max_iterations', 5),
            'output_format': agent_section.get('output_format', 'text'),
            'fallback_model': agent_section.get('fallback_model', ''),
            'memory_enabled': agent_section.get('memory_enabled', True),
            'temperature': agent_section.get('temperature', 0.7),
            'max_tokens': agent_section.get('max_tokens', 4096),
            'model_provider': dsl_data.get('model_config', {}).get('provider', ''),
        }

        if existing:
            # 更新现有应用
            aid = existing['id']
            cur.execute(
                r'''UPDATE agents SET
                    name = %s, role = %s, description = %s, icon = %s,
                    config = %s, updated_at = %s
                    WHERE id = %s''',
                (name,
                 agent_section.get('role', ''),
                 app_section.get('description', ''),
                 app_section.get('icon', '🤖'),
                 json.dumps(config, ensure_ascii=False),
                 now(),
                 aid))
            # 清除旧技能绑定
            cur.execute(r'DELETE FROM agent_skill_bindings WHERE agent_id = %s', (aid,))
        else:
            # 创建新应用
            cur.execute(
                r'''INSERT INTO agents (name, role, description, icon, type, status, owner, config, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'single', 'draft', %s, %s, %s, %s)''',
                (name,
                 agent_section.get('role', ''),
                 app_section.get('description', ''),
                 app_section.get('icon', '🤖'),
                 owner_id,
                 json.dumps(config, ensure_ascii=False),
                 now(),
                 now()))
            aid = cur.lastrowid

        # 导入技能绑定
        for skill in skills_section:
            skill_key = skill.get('key', '')
            if skill_key:
                cur.execute(
                    r'''INSERT INTO agent_skill_bindings (agent_id, skill_key, skill_name, skill_icon, skill_kind)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            skill_name = VALUES(skill_name),
                            skill_icon = VALUES(skill_icon),
                            skill_kind = VALUES(skill_kind)''',
                    (aid, skill_key, skill.get('name', skill_key),
                     skill.get('icon', '✨'), skill.get('kind', 'builtin')))

        db.commit()
        return {'id': aid, 'name': name, 'imported': True, 'updated': bool(existing)}, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()


# ============================================================
# Workflow DSL 导入（导出已在 workflows.py 中实现）
# ============================================================

def _import_workflow_dsl(dsl_data, owner_tenant='system', owner_account='system'):
    """从 YAML DSL 创建工作流应用"""
    app_section = dsl_data.get('app', {})
    workflow_section = dsl_data.get('workflow', {})

    name = (app_section.get('name') or '').strip()
    if not name:
        return None, '应用名称不能为空'

    mode = app_section.get('mode', 'workflow')
    graph = workflow_section.get('graph', {'nodes': [], 'edges': [], 'viewport': {'x': 0, 'y': 0, 'zoom': 1}})
    features = workflow_section.get('features', {})
    env_vars = workflow_section.get('environment_variables', {})
    conv_vars = workflow_section.get('conversation_variables', {})

    app_id = str(uuid.uuid4())
    wf_id = str(uuid.uuid4())
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()

        # 检查同名应用
        cur.execute(
            r'SELECT id FROM dify_apps WHERE name = %s AND tenant_id = %s',
            (name, owner_tenant))
        existing = cur.fetchone()

        if existing:
            # 更新现有应用
            app_id = existing['id']
            # 更新 apps 表
            cur.execute(
                r'''UPDATE dify_apps SET
                    name = %s, mode = %s, icon = %s, icon_background = %s,
                    description = %s, updated_at = %s, updated_by = %s
                    WHERE id = %s''',
                (name, mode, app_section.get('icon', '🤖'),
                 app_section.get('icon_background', '#FFEAD5'),
                 app_section.get('description', ''),
                 ts, owner_account, app_id))
            # 更新 workflows 表
            cur.execute(
                r'''UPDATE dify_workflows SET
                    graph = %s, features = %s, environment_variables = %s,
                    conversation_variables = %s, updated_at = %s, updated_by = %s
                    WHERE app_id = %s''',
                (json.dumps(graph, ensure_ascii=False),
                 json.dumps(features, ensure_ascii=False),
                 json.dumps(env_vars, ensure_ascii=False),
                 json.dumps(conv_vars, ensure_ascii=False),
                 ts, owner_account, app_id))
            updated = True
        else:
            # 创建新应用
            cur.execute(
                r'''INSERT INTO dify_apps
                    (id, tenant_id, name, mode, icon, icon_background, status,
                     enable_site, enable_api, api_rpm, api_rph, is_demo, is_public,
                     created_at, updated_at, is_universal, workflow_id, description,
                     created_by, updated_by, use_icon_as_answer_icon, icon_type)
                    VALUES (%s, %s, %s, %s, %s, %s, 'normal', true, true, 0, 0, false, false,
                            %s, %s, false, %s, %s, %s, %s, false, 'emoji')''',
                (app_id, owner_tenant, name, mode,
                 app_section.get('icon', '🤖'),
                 app_section.get('icon_background', '#FFEAD5'),
                 ts, ts, wf_id, app_section.get('description', ''),
                 owner_account, owner_account))

            cur.execute(
                r'''INSERT INTO dify_workflows
                    (id, tenant_id, app_id, type, version, graph, features,
                     created_by, updated_by, created_at, updated_at,
                     environment_variables, conversation_variables,
                     marked_name, marked_comment, rag_pipeline_variables, kind, version_number)
                    VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s, %s, %s, '', '', %s, 'standard', NULL)''',
                (wf_id, owner_tenant, app_id, mode,
                 json.dumps(graph, ensure_ascii=False),
                 json.dumps(features, ensure_ascii=False),
                 owner_account, owner_account, ts, ts,
                 json.dumps(env_vars, ensure_ascii=False),
                 json.dumps(conv_vars, ensure_ascii=False),
                 json.dumps({}, ensure_ascii=False)))
            updated = False

        db.commit()
        return {'id': app_id, 'name': name, 'imported': True, 'updated': updated}, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()


# ============================================================
# 路由注册
# ============================================================

def register_dsl_routes(app):
    """注册 DSL 导出/导入路由"""

    # ── Agent DSL ──

    @app.route('/api/agents/<int:aid>/export', methods=['GET'])
    def export_agent(aid):
        """导出单智能体为 YAML DSL"""
        _ensure_tables()
        result, err = _export_agent_dsl(aid)
        if err:
            return jsonify(code=404, msg=err)
        return jsonify(code=200, data=result)

    @app.route('/api/agents/import', methods=['POST'])
    def import_agent():
        """从 YAML DSL 导入单智能体"""
        _ensure_tables()
        body = request.get_json() or {}
        dsl_text = body.get('dsl', '')
        # 归属由登录身份决定，不接受客户端传入：旧写法 body.get('owner_id', 1) 既能伪造
        # 他人归属，也会在列改成 UUID 后把导入的智能体写成谁也看不见的 '1'
        from utils.helpers import _safe_uid
        owner_id = _safe_uid(None)
        overwrite = body.get('overwrite', False)

        if not dsl_text:
            return jsonify(code=400, msg='DSL 内容不能为空')

        try:
            dsl_data = yaml.safe_load(dsl_text)
        except yaml.YAMLError as e:
            return jsonify(code=400, msg=f'YAML 解析失败: {e}')

        if not isinstance(dsl_data, dict):
            return jsonify(code=400, msg='无效的 DSL 格式')

        result, err = _import_agent_dsl(dsl_data, owner_id)
        if err:
            return jsonify(code=500, msg=err)

        # 如果不覆盖且已存在，给出提示
        if result.get('updated') and not overwrite:
            return jsonify(code=200, data={
                **result,
                'warning': f'已存在同名应用 "{result["name"]}"，已更新配置。如需新建，请先修改应用名称。'
            })

        return jsonify(code=200, data=result)

    # ── Workflow DSL ──

    @app.route('/api/workflows/import', methods=['POST'])
    def import_workflow():
        """从 YAML DSL 导入工作流"""
        _ensure_tables()
        body = request.get_json() or {}
        dsl_text = body.get('dsl', '')
        tenant_id = body.get('tenant_id', 'system')
        account_id = body.get('account_id', 'system')
        overwrite = body.get('overwrite', False)

        if not dsl_text:
            return jsonify(code=400, msg='DSL 内容不能为空')

        try:
            dsl_data = yaml.safe_load(dsl_text)
        except yaml.YAMLError as e:
            return jsonify(code=400, msg=f'YAML 解析失败: {e}')

        if not isinstance(dsl_data, dict):
            return jsonify(code=400, msg='无效的 DSL 格式')

        result, err = _import_workflow_dsl(dsl_data, tenant_id, account_id)
        if err:
            return jsonify(code=500, msg=err)

        if result.get('updated') and not overwrite:
            return jsonify(code=200, data={
                **result,
                'warning': f'已存在同名应用 "{result["name"]}"，已更新配置。如需新建，请先修改应用名称。'
            })

        return jsonify(code=200, data=result)

    # ── 通用 DSL 导入（自动识别类型） ──

    @app.route('/api/dsl/import', methods=['POST'])
    def import_dsl_auto():
        """自动识别 DSL 类型并导入"""
        _ensure_tables()
        body = request.get_json() or {}
        dsl_text = body.get('dsl', '')

        if not dsl_text:
            return jsonify(code=400, msg='DSL 内容不能为空')

        try:
            dsl_data = yaml.safe_load(dsl_text)
        except yaml.YAMLError as e:
            return jsonify(code=400, msg=f'YAML 解析失败: {e}')

        if not isinstance(dsl_data, dict):
            return jsonify(code=400, msg='无效的 DSL 格式')

        kind = dsl_data.get('kind', '')
        if kind == 'agent':
            return import_agent()
        elif kind == 'workflow' or 'workflow' in dsl_data:
            return import_workflow()
        else:
            # 尝试根据结构推断
            if 'agent' in dsl_data:
                return import_agent()
            elif 'graph' in str(dsl_data):
                return import_workflow()
            return jsonify(code=400, msg='无法识别 DSL 类型，请确保 DSL 包含 kind 字段（agent/workflow）')

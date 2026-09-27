# -*- coding: utf-8 -*-
"""多智能体应用路由（MySQL 版，脱离 Dify）"""

import json
import re
from flask import jsonify, request
from config import get_db
from utils.helpers import now, _gen_appkey, _safe_uid
from utils.llm import _call_llm, _call_llm_with_config
from routes.agents import _load_agent_config, _save_agent_config
from models.tables import (
    DIFY_APPS_TABLE_SQL,
    DIFY_TOOL_PROVIDERS_TABLE_SQL,
    DIFY_DATASOURCE_PROVIDERS_TABLE_SQL,
    DIFY_PROVIDERS_TABLE_SQL,
    DIFY_PROVIDER_MODELS_TABLE_SQL,
)


def _load_multi_agent_config(aid):
    return _load_agent_config(aid, 'multi')


def _save_multi_agent_config(aid, config):
    return _save_agent_config(aid, config, 'multi')


def _ensure_multi_agent_tables():
    """确保多智能体相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_APPS_TABLE_SQL)
        cur.execute(DIFY_TOOL_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_DATASOURCE_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_PROVIDERS_TABLE_SQL)
        cur.execute(DIFY_PROVIDER_MODELS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _load_sub_agent_configs(sub_agent_ids):
    """批量加载子智能体配置，返回 {id: {name, config, model_cfg}}"""
    if not sub_agent_ids:
        return {}
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ','.join(['%s'] * len(sub_agent_ids))
        cur.execute(
            r"SELECT id, name, role, description, config FROM agents WHERE id IN (%s) AND type = 'single'" % placeholders,
            sub_agent_ids
        )
        rows = cur.fetchall()
    finally:
        db.close()
    result = {}
    for row in rows:
        cfg = {}
        if row.get('config'):
            try:
                cfg = json.loads(row['config'])
            except Exception:
                pass
        # 加载子智能体指定的模型配置
        model_cfg = None
        model_name = cfg.get('model', '')
        if model_name:
            db2 = get_db()
            try:
                cur2 = db2.cursor()
                cur2.execute(
                    r'SELECT * FROM model_configs WHERE (credential_name = %s OR model_name = %s OR provider = %s) AND status = 1 LIMIT 1',
                    (model_name, model_name, model_name)
                )
                model_cfg = cur2.fetchone()
            finally:
                db2.close()
        result[row['id']] = {
            'name': row['name'],
            'role': row['role'] or '',
            'description': row['description'] or '',
            'config': cfg,
            'model_cfg': model_cfg
        }
    return result


def _route_to_sub_agent(message, sub_agents_info, main_model_cfg=None):
    """LLM 路由：判断用户消息应由哪个子智能体处理，返回 (agent_id, reason)"""
    if not sub_agents_info:
        return 0, '无子智能体'
    agent_list = []
    for aid, info in sub_agents_info.items():
        desc = info['description'] or info['role'] or info['name']
        prompt_hint = info['config'].get('prompt', '')[:120] if info.get('config') else ''
        line = '- id=%s, name=%s, 描述=%s' % (aid, info['name'], desc)
        if prompt_hint:
            line += ', 能力摘要=%s' % prompt_hint.replace('\n', ' ')
        agent_list.append(line)
    router_prompt = (
        '你是多智能体调度器。根据用户消息和可用子智能体列表，判断应由哪个子智能体处理。\n'
        '如果消息明确属于某个子智能体的职责范围，返回该子智能体的 id；'
        '如果消息是通用问题或需要多个智能体协作，返回 id=0 表示由主 Agent 直接回答。\n\n'
        '可用子智能体：\n' + '\n'.join(agent_list) + '\n\n'
        '请返回 JSON 格式：{"agent_id": <id 或 0>, "reason": "选择原因"}'
    )
    content, err = _call_llm_with_config(router_prompt, message, main_model_cfg, temperature=0.1)
    if err:
        return 0, '路由失败: ' + err
    # 解析 JSON
    try:
        m = re.search(r'\{[^}]+\}', content)
        if m:
            obj = json.loads(m.group())
            return int(obj.get('agent_id', 0)), obj.get('reason', '')
    except Exception:
        pass
    return 0, '路由解析失败'


def _multi_agent_dispatch(aid, cfg, message):
    """多智能体调度核心逻辑：路由 → 调用子智能体 → 返回结果"""
    sub_agent_ids = [s.get('id') for s in (cfg.get('agents') or []) if isinstance(s, dict) and s.get('id')]
    sub_agents_info = _load_sub_agent_configs(sub_agent_ids)

    # 构建主 Agent system prompt
    parts = []
    if cfg.get('prompt'):
        parts.append(cfg['prompt'].strip())
    if cfg.get('handoff'):
        parts.append('转交规则：' + cfg['handoff'].strip())
    main_prompt = '\n'.join(parts) or '你是多智能体工作台助手，请帮助用户解决问题。'

    # 加载主 Agent 模型配置
    main_model_cfg = None
    main_model_name = cfg.get('model', '')
    if main_model_name:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'SELECT * FROM model_configs WHERE (credential_name = %s OR model_name = %s OR provider = %s) AND status = 1 LIMIT 1',
                (main_model_name, main_model_name, main_model_name)
            )
            main_model_cfg = cur.fetchone()
        finally:
            db.close()

    # 路由决策
    target_id, reason = _route_to_sub_agent(message, sub_agents_info, main_model_cfg)

    if target_id and target_id in sub_agents_info:
        # 调用子智能体
        sub = sub_agents_info[target_id]
        sub_cfg = sub['config']
        sub_prompt = sub_cfg.get('prompt', '')
        if not sub_prompt:
            p = []
            if sub['role']:
                p.append('你的角色：' + sub['role'])
            if sub['description']:
                p.append(sub['description'])
            sub_prompt = '\n'.join(p) or '你是智能助手，请帮助用户解决问题。'
        content, err = _call_llm_with_config(sub_prompt, message, sub['model_cfg'])
        if err:
            return None, err, None
        return content, None, sub['name']
    else:
        # 主 Agent 直接回答
        content, err = _call_llm_with_config(main_prompt, message, main_model_cfg)
        if err:
            return None, err, None
        return content, None, None


def register_multi_agent_routes(app):
    """注册多智能体相关路由"""

    @app.route('/api/multi-agents', methods=['GET'])
    def get_multi_agents():
        """多智能体应用列表（只看本人创建的）"""
        from routes.agents import _ensure_agents_table
        _ensure_agents_table()
        uid = _safe_uid(None)
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, role, description, icon, status, created_at, updated_at FROM agents WHERE type = 'multi' AND owner = %s ORDER BY updated_at DESC", (uid,))
            rows = cur.fetchall()
            for r in rows:
                if r['created_at']:
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if r['updated_at']:
                    r['updated_at'] = r['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/multi-agents/<int:aid>', methods=['GET'])
    def get_multi_agent(aid):
        """多智能体应用详情"""
        from routes.agents import _ensure_agents_table
        _ensure_agents_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, role, description, icon, status, config, created_at, updated_at FROM agents WHERE id = %s AND type = 'multi'", (aid,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='智能体不存在')
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else ''
            row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else ''
            if row.get('config'):
                try:
                    row['config'] = json.loads(row['config'])
                except Exception:
                    row['config'] = None
            return jsonify(code=200, data=row)
        finally:
            db.close()

    @app.route('/api/multi-agents', methods=['POST'])
    def create_multi_agent():
        """创建多智能体应用"""
        d = request.get_json()
        name = d.get('name', '').strip()
        if not name:
            return jsonify(code=400, msg='请输入应用名称')
        uid = _safe_uid(None)
        if not uid:
            return jsonify(code=401, msg='请先登录再创建智能体')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO agents (name, role, description, icon, status, type, owner, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'draft', 'multi', %s, %s, %s)''',
                (name, d.get('role', '').strip(), d.get('description', '').strip(),
                 d.get('icon') or '🤖', uid, now(), now())
            )
            db.commit()
            cur.execute(r"SELECT id, name, role, description, icon, status, created_at, updated_at FROM agents WHERE id = %s", (cur.lastrowid,))
            row = cur.fetchone()
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, msg='创建成功', data=row)
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/multi-agents/<int:aid>', methods=['PUT'])
    def update_multi_agent(aid):
        """更新多智能体应用信息"""
        d = request.get_json()
        db = get_db()
        try:
            cur = db.cursor()
            fields = []
            vals = []
            for key in ('name', 'role', 'description', 'icon', 'status', 'config'):
                if key in d:
                    fields.append(f'{key} = %s')
                    val = d[key]
                    if key == 'config' and not isinstance(val, str):
                        val = json.dumps(val, ensure_ascii=False)
                    vals.append(val)
            if not fields:
                return jsonify(code=400, msg='没有可更新的字段')
            fields.append('updated_at = %s')
            vals.append(now())
            vals.append(aid)
            cur.execute(f'UPDATE agents SET {", ".join(fields)} WHERE id = %s AND type = %s', vals + ['multi'])
            db.commit()
            cur.execute(r'SELECT id, name, role, description, icon, status, updated_at FROM agents WHERE id = %s', (aid,))
            row = cur.fetchone()
            if row['updated_at']:
                row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, msg='保存成功', data=row)
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/multi-agents/<int:aid>', methods=['DELETE'])
    def delete_multi_agent(aid):
        """删除多智能体应用"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"DELETE FROM agents WHERE id = %s AND type = 'multi'", (aid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  MULTI-AGENT AppKey
    # ═══════════════════════════════════════════

    @app.route('/api/multi-agents/<int:aid>/appkeys', methods=['GET'])
    def list_multi_agent_appkeys(aid):
        """多智能体 AppKey 列表"""
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        return jsonify(code=200, data=cfg.get('app_keys') or [])

    @app.route('/api/multi-agents/<int:aid>/appkeys', methods=['POST'])
    def create_multi_agent_appkey(aid):
        """生成新 AppKey"""
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        keys = cfg.get('app_keys') or []
        if len(keys) >= 20:
            return jsonify(code=400, msg='AppKey 数量已达上限（20）')
        item = {'key': _gen_appkey(), 'created_at': now(), 'enabled': True}
        keys.append(item)
        cfg['app_keys'] = keys
        _save_multi_agent_config(aid, cfg)
        return jsonify(code=200, msg='生成成功', data=item)

    @app.route('/api/multi-agents/<int:aid>/appkeys/<key>', methods=['PUT'])
    def toggle_multi_agent_appkey(aid, key):
        """启用/禁用 AppKey"""
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        d = request.get_json() or {}
        for k in cfg.get('app_keys') or []:
            if k['key'] == key:
                k['enabled'] = bool(d.get('enabled', not k.get('enabled', True)))
                _save_multi_agent_config(aid, cfg)
                return jsonify(code=200, msg='已更新')
        return jsonify(code=404, msg='AppKey 不存在')

    @app.route('/api/multi-agents/<int:aid>/appkeys/<key>', methods=['DELETE'])
    def delete_multi_agent_appkey(aid, key):
        """删除 AppKey"""
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        cfg['app_keys'] = [k for k in (cfg.get('app_keys') or []) if k['key'] != key]
        _save_multi_agent_config(aid, cfg)
        return jsonify(code=200, msg='删除成功')

    # ═══════════════════════════════════════════
    #  MULTI-AGENT 调试 / API 对话
    # ═══════════════════════════════════════════

    @app.route('/api/multi-agents/<int:aid>/debug', methods=['POST'])
    def debug_multi_agent(aid):
        """调试调用多智能体"""
        d = request.get_json()
        message = (d.get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入调试消息')
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        content, err, handled_by = _multi_agent_dispatch(aid, cfg, message)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'reply': content, 'handled_by': handled_by or '主 Agent'})

    @app.route('/api/multi-agents/<int:aid>/chat', methods=['POST'])
    def multi_agent_api_chat(aid):
        """多智能体 API 对话"""
        cfg = _load_multi_agent_config(aid)
        if cfg is None:
            return jsonify(code=404, msg='多智能体不存在')
        api = (cfg.get('access_points') or {}).get('api') or {}
        if not api.get('enabled'):
            return jsonify(code=403, msg='API 访问点已停用，请先在访问点页面启用')
        auth = request.headers.get('Authorization', '')
        key = auth[7:].strip() if auth.startswith('Bearer ') else ''
        ok = any(k.get('key') == key and k.get('enabled', True) for k in cfg.get('app_keys') or [])
        if not ok:
            return jsonify(code=401, msg='AppKey 无效或已禁用')
        message = ((request.get_json() or {}).get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入消息')
        content, err, handled_by = _multi_agent_dispatch(aid, cfg, message)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'reply': content, 'handled_by': handled_by or '主 Agent'})

    # ═══════════════════════════════════════════
    #  MULTI-AGENT CONFIG（工具/连接器/AI 生成/记忆）
    # ═══════════════════════════════════════════

    @app.route('/api/multi-agent/tools', methods=['GET'])
    def multi_agent_tools():
        """从 MySQL 列出可用工具"""
        _ensure_multi_agent_tables()
        from models.builtin_tools import BUILTIN_TOOLS
        tools = []
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # dify 应用
                cur.execute(r'''SELECT id, name, mode, icon, description FROM dify_apps
                                   WHERE status = 'normal' AND enable_api = true ORDER BY updated_at DESC''')
                apps = cur.fetchall()
                for a in apps:
                    tools.append({'key': 'app_' + str(a['id']), 'name': a['name'], 'icon': a['icon'] or '🤖',
                                  'source': '应用', 'mode': a['mode'], 'desc': a['description'] or ''})
                # 自定义工具
                cur.execute(r'SELECT id, tool_name, tool_type FROM dify_tool_providers ORDER BY created_at DESC')
                for r in cur.fetchall():
                    tools.append({'key': 'tool_%s' % r['id'], 'name': r['tool_name'], 'icon': '🔧',
                                  'source': '工具', 'mode': '', 'desc': ''})
            finally:
                db.close()
            # 已安装的内置工具
            from routes.tools import _installed_tool_ids
            for t in BUILTIN_TOOLS:
                if t['id'] in _installed_tool_ids():
                    tools.append({'key': 'builtin_' + t['id'], 'name': t['name'],
                                  'icon': t['icon'].replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&') or '🔧',
                                  'source': '内置工具', 'mode': '', 'desc': t['description'] or ''})
        except Exception as e:
            return jsonify(code=500, msg='查询工具失败: ' + str(e))
        return jsonify(code=200, data=tools)

    @app.route('/api/multi-agent/connectors', methods=['GET'])
    def multi_agent_connectors():
        """从 MySQL 列出可用连接器"""
        _ensure_multi_agent_tables()
        conns = []
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # MCP 服务器（从本地 mcp_servers 表）
                cur.execute(r'SELECT id, name, url FROM mcp_servers ORDER BY created_at DESC')
                for m in cur.fetchall():
                    conns.append({'key': 'mcp_' + str(m['id']), 'name': m['name'], 'icon': '🔌',
                                  'source': 'MCP 服务器', 'desc': m['url'] or ''})
                # 数据源
                cur.execute(r'SELECT id, name, datasource_type FROM dify_datasource_providers ORDER BY created_at DESC')
                for d in cur.fetchall():
                    conns.append({'key': 'ds_' + str(d['id']), 'name': d['name'], 'icon': '🔗',
                                  'source': '数据源', 'desc': d['datasource_type'] or ''})
                # 模型供应商
                cur.execute(r'''SELECT provider_name, provider_type FROM dify_providers
                                WHERE is_valid = true ORDER BY updated_at DESC''')
                seen = set()
                for p in cur.fetchall():
                    nm = p['provider_name'].split('/')[-1]
                    if nm in seen:
                        continue
                    seen.add(nm)
                    conns.append({'key': 'prov_' + nm, 'name': nm, 'icon': '🌐',
                                  'source': '模型供应商', 'desc': p['provider_type']})
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='查询连接器失败: ' + str(e))
        return jsonify(code=200, data=conns)

    @app.route('/api/multi-agent/gen-desc', methods=['POST'])
    def multi_agent_gen_desc():
        """AI 一键生成转交描述"""
        d = request.get_json()
        name = d.get('name', '').strip() or '多智能体'
        role = d.get('role', '').strip()
        agents = d.get('agents') or []
        base = '智能体名称：%s' % name
        if role:
            base += '\n角色定位：%s' % role
        if agents:
            base += '\n包含子智能体：' + '、'.join(str(x) for x in agents)
        content, err = _call_llm(
            '你是智能体协作编排专家。根据用户提供的多智能体信息，生成一段简洁的"转交描述"（150 字以内）：'
            '说明该多智能体负责什么、在什么情况下适合把任务转交给它、它能产出什么。直接输出描述文本，不要 JSON 和多余格式。',
            base, temperature=0.6)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'desc': content})

    @app.route('/api/multi-agent/optimize-prompt', methods=['POST'])
    def multi_agent_optimize_prompt():
        """AI 一键优化提示词"""
        d = request.get_json()
        prompt = d.get('prompt', '').strip()
        if not prompt:
            return jsonify(code=400, msg='请先填写提示词')
        content, err = _call_llm(
            '你是提示词工程专家。请优化用户提供的提示词：保持原有意图不变，使结构更清晰、指令更明确、边界更完整。'
            '可使用 # 标题与 * 列表组织。直接输出优化后的提示词全文，不要解释、不要 JSON。',
            prompt, temperature=0.4)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'prompt': content})

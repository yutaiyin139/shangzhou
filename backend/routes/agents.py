# -*- coding: utf-8 -*-
"""单智能体路由"""

from flask import jsonify, request
import json
import re
from config import get_db
from utils.helpers import now, _gen_appkey, _gen_web_token, _safe_uid
from utils.llm import _call_llm
from models.tables import AGENTS_TABLE_SQL, AGENT_SKILL_BINDINGS_TABLE_SQL, AGENT_CONFIG_REVISIONS_TABLE_SQL


def _ensure_agents_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(AGENTS_TABLE_SQL)
        # 兼容旧表：补 config 列
        cur.execute(r"SELECT COUNT(*) AS n FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'agents' AND column_name = 'config'")
        if cur.fetchone()['n'] == 0:
            cur.execute(r'ALTER TABLE agents ADD COLUMN config TEXT')
        # 兼容旧表：补 type 列
        cur.execute(r"SELECT COUNT(*) AS n FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'agents' AND column_name = 'type'")
        if cur.fetchone()['n'] == 0:
            cur.execute(r"ALTER TABLE agents ADD COLUMN type VARCHAR(10) NOT NULL DEFAULT 'single'")
        cur.execute(r"UPDATE agents SET type = 'single' WHERE type IS NULL OR type = ''")
        # 兼容旧表：补 owner 列
        cur.execute(r"SELECT COUNT(*) AS n FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'agents' AND column_name = 'owner'")
        if cur.fetchone()['n'] == 0:
            cur.execute(r'ALTER TABLE agents ADD COLUMN owner INT DEFAULT 1')
        cur.execute(r'UPDATE agents SET owner = 1 WHERE owner IS NULL')
        # 确保技能绑定表存在
        cur.execute(AGENT_SKILL_BINDINGS_TABLE_SQL)
        # 确保配置版本表存在
        cur.execute(AGENT_CONFIG_REVISIONS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _load_agent_config(aid, atype):
    """读取指定类型智能体 config"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r"SELECT config FROM agents WHERE id = %s AND type = %s", (aid, atype))
        row = cur.fetchone()
    finally:
        db.close()
    if not row:
        return None
    try:
        return json.loads(row['config']) if row['config'] else {}
    except Exception:
        return {}


def _save_agent_config(aid, config, atype):
    """写回指定类型智能体 config"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r"UPDATE agents SET config = %s, updated_at = %s WHERE id = %s AND type = %s",
                    (json.dumps(config, ensure_ascii=False), now(), aid, atype))
        db.commit()
    finally:
        db.close()


def _default_access_points():
    return {
        'web': {'enabled': True, 'token': _gen_web_token(), 'updated_at': now(), 'name': '', 'color': '#2E63F0'},
        'api': {'enabled': False}
    }


def _find_agent_by_web_token(token):
    """按 web token 查找单智能体"""
    if not token:
        return None
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r"SELECT id, name, icon, description, config FROM agents WHERE type = 'single' AND config LIKE %s",
                    ('%' + token + '%',))
        rows = cur.fetchall()
    finally:
        db.close()
    for row in rows:
        try:
            cfg = json.loads(row['config']) if row['config'] else {}
        except Exception:
            continue
        web = (cfg.get('access_points') or {}).get('web') or {}
        if web.get('token') == token and web.get('enabled'):
            return {'id': row['id'], 'name': row['name'], 'icon': row['icon'],
                    'description': row['description'], 'config': cfg}
    return None


def _agent_system_prompt(aid, cfg, query: str = '', conversation_id: str = ''):
    """
    单智能体 system prompt。
    - 当 query 非空时，检索 agent 长期记忆并注入 prompt 末尾。
    - 当 conversation_id 非空时，注入对话历史摘要（摘要记忆）。
    - 注入已绑定技能的说明到 prompt。
    """
    parts = []
    if cfg.get('prompt'):
        parts.append(cfg['prompt'].strip())
    else:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT role, description FROM agents WHERE id = %s AND type = %s', (aid, 'single'))
            row = cur.fetchone()
        finally:
            db.close()
        if row:
            if row['role']:
                parts.append('你的角色：' + row['role'].strip())
            if row['description']:
                parts.append(row['description'].strip())
    base = '\n'.join(p for p in parts if p) or '你是智能体工作台助手，请帮助用户解决问题。'

    # 技能注入：将绑定技能的使用说明注入 prompt
    try:
        skill_ctx = _build_skill_context(aid)
        if skill_ctx:
            base = base + '\n\n' + skill_ctx
    except Exception:
        pass

    # 记忆注入：仅当有 query 且 agent 启用记忆时
    if query and cfg.get('memory_enabled', True):
        try:
            from engine.agent_memory import build_memory_context
            mem_ctx = build_memory_context(aid, query, limit=5, min_score=0.35)
            if mem_ctx:
                base = base + '\n\n' + mem_ctx
        except Exception:
            pass

    # 摘要记忆注入：当有 conversation_id 时，注入历史对话摘要
    if conversation_id:
        try:
            summary_ctx = _build_summary_context(conversation_id)
            if summary_ctx:
                base = base + '\n\n' + summary_ctx
        except Exception:
            pass

    return base


def _build_skill_context(aid) -> str:
    """
    构建技能上下文：读取 agent 已绑定的技能，格式化为 LLM 可理解的上下文。

    返回格式:
        ## 可用技能
        你已绑定以下技能，请根据用户需求主动调用：

        ### 技能名称
        技能描述和使用说明...
    """
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'''SELECT skill_key, skill_name, skill_icon, skill_kind
                FROM agent_skill_bindings
                WHERE agent_id = %s
                ORDER BY created_at ASC''',
            (aid,))
        rows = cur.fetchall()
    finally:
        db.close()

    if not rows:
        return ''

    # 加载技能详情
    skill_details = _load_skill_details()
    parts = ['## 可用技能', '你已绑定以下技能，请根据用户需求主动调用：']

    for row in rows:
        key = row['skill_key']
        name = row['skill_name'] or key
        icon = row['skill_icon'] or '✨'
        detail = skill_details.get(key, {})
        desc = detail.get('description', '')
        content = detail.get('content', '')  # SKILL.md 内容

        skill_section = f'### {icon} {name}'
        if desc:
            skill_section += f'\n{desc}'
        if content:
            # 截取 SKILL.md 的前 500 字符作为使用说明
            brief = content[:500] + ('...' if len(content) > 500 else '')
            skill_section += f'\n使用说明：\n{brief}'
        parts.append(skill_section)

    return '\n\n'.join(parts)


def _load_skill_details() -> dict:
    """加载所有已安装技能的详情（builtin + custom）"""
    details = {}
    # 加载内置技能
    try:
        from models.builtin_skills import BUILTIN_SKILLS
        for skill in BUILTIN_SKILLS:
            details[skill['key']] = {
                'name': skill.get('name', ''),
                'description': skill.get('description', ''),
                'content': skill.get('content', ''),
                'icon': skill.get('icon', '✨'),
                'kind': 'builtin'
            }
    except Exception:
        pass

    # 加载自定义技能
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT name, description, icon, category, content FROM skills')
        for row in cur.fetchall():
            # 自定义技能用 name 作为 key
            details[row['name']] = {
                'name': row['name'],
                'description': row.get('description', ''),
                'content': row.get('content', ''),
                'icon': row.get('icon', '🔧'),
                'kind': 'custom'
            }
    except Exception:
        pass
    finally:
        db.close()

    return details


def _build_summary_context(conversation_id: str) -> str:
    """
    构建对话摘要上下文。
    从 conversation_summaries 表获取最新摘要，格式化为 LLM 可理解的上下文。

    返回格式:
        ## 历史对话摘要
        以下是之前对话的摘要：
        <summary_text>

        请基于以上摘要理解对话上下文，继续回答用户的问题。
    """
    if not conversation_id:
        return ''
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            r'''SELECT summary_text, message_count, created_at
                FROM conversation_summaries
                WHERE conversation_id = %s
                ORDER BY created_at DESC LIMIT 1''',
            (conversation_id,))
        row = cur.fetchone()
        if not row or not row.get('summary_text'):
            return ''
        summary_text = row['summary_text'].strip()
        if not summary_text:
            return ''
        return (
            '## 历史对话摘要\n'
            '以下是之前对话的摘要：\n'
            f'{summary_text}\n\n'
            '请基于以上摘要理解对话上下文，继续回答用户的问题。'
        )
    finally:
        db.close()


def register_agent_routes(app):
    """注册单智能体相关路由"""

    @app.route('/api/agents', methods=['GET'])
    def get_agents():
        """单智能体应用列表"""
        _ensure_agents_table()
        uid = _safe_uid(request.args.get('uid'))
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, role, description, icon, status, created_at, updated_at FROM agents WHERE type = 'single' AND owner = %s ORDER BY updated_at DESC", (uid,))
            rows = cur.fetchall()
            for r in rows:
                if r['created_at']:
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if r['updated_at']:
                    r['updated_at'] = r['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/agents/accessible', methods=['GET'])
    def get_accessible_agents():
        """当前用户有权访问的单智能体列表"""
        _ensure_agents_table()
        uid = _safe_uid(request.args.get('uid'))
        db = get_db()
        try:
            cur = db.cursor()
            # 直接查询，不 JOIN 用户表（owner 为 int，dify_accounts.id 为 UUID，无法关联）
            cur.execute(r"""
                SELECT a.id, a.name, a.role, a.description, a.icon, a.status, a.owner,
                       a.created_at, a.updated_at
                FROM agents a
                WHERE a.type = 'single' AND (a.owner = %s OR a.status = 'published')
                ORDER BY a.updated_at DESC
            """, (uid,))
            rows = cur.fetchall()
            for r in rows:
                if r['created_at']:
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if r['updated_at']:
                    r['updated_at'] = r['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                r['is_mine'] = (r['owner'] == uid)
                r['owner_name'] = '用户' + str(r['owner'])  # 简化显示
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/agents/<int:aid>', methods=['GET'])
    def get_agent(aid):
        """单智能体应用详情"""
        _ensure_agents_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT id, name, role, description, icon, status, config, created_at, updated_at FROM agents WHERE id = %s', (aid,))
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

    @app.route('/api/agents', methods=['POST'])
    def create_agent():
        """创建单智能体应用"""
        d = request.get_json()
        name = d.get('name', '').strip()
        if not name:
            return jsonify(code=400, msg='请输入应用名称')
        uid = _safe_uid(d.get('uid'))
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO agents (name, role, description, icon, status, owner, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s)''',
                (name, d.get('role', '').strip(), d.get('description', '').strip(),
                 d.get('icon') or '🤖', uid, now(), now())
            )
            db.commit()
            cur.execute(r'SELECT id, name, role, description, icon, status, created_at, updated_at FROM agents WHERE id = %s', (cur.lastrowid,))
            row = cur.fetchone()
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, msg='创建成功', data=row)
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/agents/<int:aid>', methods=['PUT'])
    def update_agent(aid):
        """更新单智能体应用信息"""
        d = request.get_json()
        db = get_db()
        try:
            cur = db.cursor()
            fields = []
            vals = []
            config = None
            for key in ('name', 'role', 'description', 'icon', 'status', 'config'):
                if key in d:
                    fields.append(f'{key} = %s')
                    val = d[key]
                    if key == 'config':
                        config = val if not isinstance(val, str) else json.loads(val)
                        val = json.dumps(config, ensure_ascii=False) if not isinstance(val, str) else val
                    vals.append(val)
            if not fields:
                return jsonify(code=400, msg='没有可更新的字段')
            fields.append('updated_at = %s')
            vals.append(now())
            vals.append(aid)
            cur.execute(f'UPDATE agents SET {", ".join(fields)} WHERE id = %s', vals)
            db.commit()

            # 配置变更时自动保存版本快照
            if config is not None:
                try:
                    from engine.agent_strategies import ConfigRevisionManager
                    strategy = (config.get('strategy') or 'react') if isinstance(config, dict) else 'react'
                    ConfigRevisionManager.save_revision(aid, config, strategy, change_note='配置更新自动保存')
                except Exception:
                    pass

            return jsonify(code=200, msg='保存成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/agents/<int:aid>', methods=['DELETE'])
    def delete_agent(aid):
        """删除单智能体应用"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM agents WHERE id = %s', (aid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  AppKey 管理
    # ═══════════════════════════════════════════

    @app.route('/api/agents/<int:aid>/appkeys', methods=['GET'])
    def list_agent_appkeys(aid):
        """单智能体 AppKey 列表"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        return jsonify(code=200, data=cfg.get('app_keys') or [])

    @app.route('/api/agents/<int:aid>/appkeys', methods=['POST'])
    def create_agent_appkey(aid):
        """生成新 AppKey"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        keys = cfg.get('app_keys') or []
        if len(keys) >= 20:
            return jsonify(code=400, msg='AppKey 数量已达上限（20）')
        item = {'key': _gen_appkey(), 'created_at': now(), 'enabled': True}
        keys.append(item)
        cfg['app_keys'] = keys
        _save_agent_config(aid, cfg, 'single')
        return jsonify(code=200, msg='生成成功', data=item)

    @app.route('/api/agents/<int:aid>/appkeys/<key>', methods=['PUT'])
    def toggle_agent_appkey(aid, key):
        """启用/禁用 AppKey"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        d = request.get_json() or {}
        for k in cfg.get('app_keys') or []:
            if k['key'] == key:
                k['enabled'] = bool(d.get('enabled', not k.get('enabled', True)))
                _save_agent_config(aid, cfg, 'single')
                return jsonify(code=200, msg='已更新')
        return jsonify(code=404, msg='AppKey 不存在')

    @app.route('/api/agents/<int:aid>/appkeys/<key>', methods=['DELETE'])
    def delete_agent_appkey(aid, key):
        """删除 AppKey"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        cfg['app_keys'] = [k for k in (cfg.get('app_keys') or []) if k['key'] != key]
        _save_agent_config(aid, cfg, 'single')
        return jsonify(code=200, msg='删除成功')

    # ═══════════════════════════════════════════
    #  访问点管理
    # ═══════════════════════════════════════════

    @app.route('/api/agents/<int:aid>/access-points', methods=['GET'])
    def get_agent_access_points(aid):
        """访问点状态"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        if not cfg.get('access_points'):
            cfg['access_points'] = _default_access_points()
            _save_agent_config(aid, cfg, 'single')
        ap = cfg['access_points']
        web = ap.get('web') or {}
        api = ap.get('api') or {}
        return jsonify(code=200, data={
            'web_enabled': bool(web.get('enabled')),
            'web_token': web.get('token') or '',
            'web_updated_at': web.get('updated_at') or '',
            'web_name': web.get('name') or '',
            'web_color': web.get('color') or '#2E63F0',
            'api_enabled': bool(api.get('enabled')),
            'api_key_count': len(cfg.get('app_keys') or [])
        })

    @app.route('/api/agents/<int:aid>/access-points', methods=['PUT'])
    def update_agent_access_points(aid):
        """开关 Web/API 访问点"""
        d = request.get_json() or {}
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        ap = cfg.setdefault('access_points', _default_access_points())
        web = ap.setdefault('web', {'enabled': True, 'token': _gen_web_token(), 'updated_at': now()})
        api = ap.setdefault('api', {'enabled': False})
        if 'web_enabled' in d:
            web['enabled'] = bool(d['web_enabled'])
            if web['enabled'] and not web.get('token'):
                web['token'] = _gen_web_token()
                web['updated_at'] = now()
        if 'api_enabled' in d:
            api['enabled'] = bool(d['api_enabled'])
        if 'web_name' in d:
            web['name'] = str(d['web_name']).strip()
        if 'web_color' in d:
            web['color'] = str(d['web_color']).strip()
        _save_agent_config(aid, cfg, 'single')
        return jsonify(code=200, msg='已更新')

    @app.route('/api/agents/<int:aid>/access-points/refresh', methods=['POST'])
    def refresh_agent_web_token(aid):
        """刷新 Web app 访问 token"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        ap = cfg.setdefault('access_points', _default_access_points())
        web = ap.setdefault('web', {})
        web['token'] = _gen_web_token()
        web['updated_at'] = now()
        _save_agent_config(aid, cfg, 'single')
        return jsonify(code=200, msg='已刷新', data={'web_token': web['token'], 'web_updated_at': web['updated_at']})

    # ═══════════════════════════════════════════
    #  Web App 公开访问
    # ═══════════════════════════════════════════

    @app.route('/api/web-agent/<token>', methods=['GET'])
    def get_web_agent(token):
        """Web app 公开入口"""
        hit = _find_agent_by_web_token(token)
        if not hit:
            return jsonify(code=404, msg='访问点不存在或已停用')
        web = (hit['config'].get('access_points') or {}).get('web') or {}
        return jsonify(code=200, data={
            'name': web.get('name') or hit['name'],
            'icon': hit['icon'],
            'description': hit['description'],
            'color': web.get('color') or '#2E63F0'
        })

    @app.route('/api/web-agent/<token>/chat', methods=['POST'])
    def web_agent_chat(token):
        """Web app 公开对话"""
        hit = _find_agent_by_web_token(token)
        if not hit:
            return jsonify(code=404, msg='访问点不存在或已停用')
        body = request.get_json() or {}
        message = (body.get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入消息')
        conversation_id = body.get('conversation_id', '')
        # 自动摘要：当消息数超过阈值时压缩历史
        if conversation_id:
            try:
                from routes.conversation_summaries import auto_summarize_if_needed
                auto_summarize_if_needed(conversation_id, app_id=hit['id'])
            except Exception:
                pass
        system_prompt = _agent_system_prompt(hit['id'], hit['config'], message,
                                             conversation_id=conversation_id)
        content, err = _call_llm(system_prompt, message)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'reply': content})

    # ═══════════════════════════════════════════
    #  API 对话
    # ═══════════════════════════════════════════

    @app.route('/api/agents/<int:aid>/chat', methods=['POST'])
    def agent_api_chat(aid):
        """后端服务 API 对话"""
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        api = (cfg.get('access_points') or {}).get('api') or {}
        if not api.get('enabled'):
            return jsonify(code=403, msg='API 访问点已停用，请先在访问点页面启用')
        auth = request.headers.get('Authorization', '')
        key = auth[7:].strip() if auth.startswith('Bearer ') else ''
        ok = any(k.get('key') == key and k.get('enabled', True) for k in cfg.get('app_keys') or [])
        if not ok:
            return jsonify(code=401, msg='AppKey 无效或已禁用')
        body = request.get_json() or {}
        message = (body.get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入消息')
        conversation_id = body.get('conversation_id', '')
        # 自动摘要：当消息数超过阈值时压缩历史
        if conversation_id:
            try:
                from routes.conversation_summaries import auto_summarize_if_needed
                auto_summarize_if_needed(conversation_id, app_id=str(aid))
            except Exception:
                pass
        system_prompt = _agent_system_prompt(aid, cfg, message,
                                             conversation_id=conversation_id)
        content, err = _call_llm(system_prompt, message)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'reply': content})

    @app.route('/api/agents/<int:aid>/debug', methods=['POST'])
    def debug_agent(aid):
        """调试调用单智能体"""
        d = request.get_json()
        message = (d.get('message') or '').strip()
        if not message:
            return jsonify(code=400, msg='请输入调试消息')
        cfg = _load_agent_config(aid, 'single')
        if cfg is None:
            return jsonify(code=404, msg='智能体不存在')
        content, err = _call_llm(_agent_system_prompt(aid, cfg), message)
        if err:
            return jsonify(code=500, msg=err)
        return jsonify(code=200, data={'reply': content})

    @app.route('/api/agents/<int:aid>/workflow-refs', methods=['GET'])
    def agent_workflow_refs(aid):
        """工作流访问：引用了该智能体的多智能体应用列表"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"SELECT id, name, status, config, updated_at FROM agents WHERE type = 'multi'")
            rows = cur.fetchall()
        finally:
            db.close()
        refs = []
        for row in rows:
            try:
                cfg = json.loads(row['config']) if row['config'] else {}
            except Exception:
                continue
            subs = cfg.get('agents') or []
            if any(s.get('id') == aid for s in subs):
                refs.append({
                    'id': row['id'], 'name': row['name'], 'node': 'Agent 节点',
                    'version': 'v1', 'status': row['status'],
                    'updated_at': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else ''
                })
        return jsonify(code=200, data=refs)

    # ═══════════════════════════════════════════
    #  技能绑定管理
    # ═══════════════════════════════════════════

    @app.route('/api/agents/<int:aid>/skills', methods=['GET'])
    def get_agent_skills(aid):
        """获取智能体已绑定的技能列表"""
        _ensure_agents_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT id, agent_id, skill_key, skill_name, skill_icon, skill_kind, created_at
                    FROM agent_skill_bindings
                    WHERE agent_id = %s
                    ORDER BY created_at ASC''',
                (aid,))
            rows = cur.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/agents/<int:aid>/skills', methods=['POST'])
    def bind_agent_skill(aid):
        """为智能体绑定技能"""
        _ensure_agents_table()
        d = request.get_json() or {}
        skill_key = (d.get('skill_key') or '').strip()
        if not skill_key:
            return jsonify(code=400, msg='请指定技能标识')

        # 获取技能详情
        skill_name = d.get('skill_name', skill_key)
        skill_icon = d.get('skill_icon', '✨')
        skill_kind = d.get('skill_kind', 'builtin')

        # 如果前端没传详情，从内置技能表自动补全
        if not d.get('skill_name'):
            try:
                from models.builtin_skills import BUILTIN_SKILLS
                for skill in BUILTIN_SKILLS:
                    if skill['key'] == skill_key:
                        skill_name = skill.get('name', skill_key)
                        skill_icon = skill.get('icon', '✨')
                        skill_kind = 'builtin'
                        break
            except Exception:
                pass

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''INSERT INTO agent_skill_bindings (agent_id, skill_key, skill_name, skill_icon, skill_kind)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        skill_name = VALUES(skill_name),
                        skill_icon = VALUES(skill_icon),
                        skill_kind = VALUES(skill_kind)''',
                (aid, skill_key, skill_name, skill_icon, skill_kind))
            db.commit()
            return jsonify(code=200, msg='技能绑定成功', data={
                'skill_key': skill_key,
                'skill_name': skill_name,
                'skill_icon': skill_icon
            })
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/agents/<int:aid>/skills/<skill_key>', methods=['DELETE'])
    def unbind_agent_skill(aid, skill_key):
        """解除智能体的技能绑定"""
        _ensure_agents_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'DELETE FROM agent_skill_bindings WHERE agent_id = %s AND skill_key = %s',
                (aid, skill_key))
            db.commit()
            return jsonify(code=200, msg='已解除绑定')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    # ═══════════════════════════════════════════
    #  配置版本管理
    # ═══════════════════════════════════════════

    @app.route('/api/agents/<int:aid>/config-revisions', methods=['GET'])
    def get_config_revisions(aid):
        """获取智能体配置版本列表"""
        _ensure_agents_table()
        try:
            from engine.agent_strategies import ConfigRevisionManager
            revisions = ConfigRevisionManager.list_revisions(aid)
            return jsonify(code=200, data=revisions)
        except Exception as e:
            return jsonify(code=500, msg=str(e))

    @app.route('/api/agents/<int:aid>/config-revisions', methods=['POST'])
    def save_config_revision(aid):
        """保存当前配置为新版本"""
        _ensure_agents_table()
        d = request.get_json() or {}
        config = d.get('config', {})
        strategy = d.get('strategy', 'react')
        change_note = d.get('change_note', '')

        try:
            from engine.agent_strategies import ConfigRevisionManager
            revision_id = ConfigRevisionManager.save_revision(aid, config, strategy, change_note)
            return jsonify(code=200, msg='已保存版本', data={'revision_id': revision_id})
        except Exception as e:
            return jsonify(code=500, msg=str(e))

    @app.route('/api/agents/<int:aid>/config-revisions/<int:rid>', methods=['GET'])
    def get_config_revision(aid, rid):
        """获取指定版本的配置"""
        _ensure_agents_table()
        try:
            from engine.agent_strategies import ConfigRevisionManager
            revision = ConfigRevisionManager.get_revision(rid)
            if not revision or revision.get('agent_id') != aid:
                return jsonify(code=404, msg='版本不存在')
            return jsonify(code=200, data=revision)
        except Exception as e:
            return jsonify(code=500, msg=str(e))

    @app.route('/api/agents/<int:aid>/config-revisions/<int:rid>/rollback', methods=['POST'])
    def rollback_config_revision(aid, rid):
        """回滚到指定版本"""
        _ensure_agents_table()
        try:
            from engine.agent_strategies import ConfigRevisionManager
            config = ConfigRevisionManager.rollback_to_revision(aid, rid)
            if config is None:
                return jsonify(code=404, msg='版本不存在或不属于该智能体')
            # 更新智能体配置
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    r'UPDATE agents SET config = %s, updated_at = %s WHERE id = %s',
                    (json.dumps(config, ensure_ascii=False), now(), aid))
                db.commit()
            finally:
                db.close()
            return jsonify(code=200, msg='已回滚到指定版本', data=config)
        except Exception as e:
            return jsonify(code=500, msg=str(e))

    # ═══════════════════════════════════════════
    #  策略管理
    # ═══════════════════════════════════════════

    @app.route('/api/agent/strategies', methods=['GET'])
    def list_agent_strategies():
        """列出所有可用策略"""
        try:
            from engine.agent_strategies import list_strategies
            return jsonify(code=200, data=list_strategies())
        except Exception as e:
            return jsonify(code=500, msg=str(e))

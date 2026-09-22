# -*- coding: utf-8 -*-
"""Agent 模板路由 —— 预配置 Agent 模板的 CRUD 管理"""
import json
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from models.tables import (
    AGENT_TEMPLATES_TABLE_SQL,
    CONVERSATION_SUMMARIES_TABLE_SQL,
)
from config import get_db
from utils.auth import login_required

bp = Blueprint('agent_templates', __name__)

# ============================================================
# 初始化表
# ============================================================

def init_tables():
    """初始化 Agent 模板相关表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(AGENT_TEMPLATES_TABLE_SQL)
        cur.execute(CONVERSATION_SUMMARIES_TABLE_SQL)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

init_tables()

# ============================================================
# 辅助函数
# ============================================================

def _row_to_template(row):
    """数据库行转模板字典"""
    return {
        'id': row['id'],
        'name': row['name'],
        'description': row['description'] or '',
        'icon': row['icon'] or '🤖',
        'icon_background': row['icon_background'] or '#E8F3FF',
        'category': row['category'] or 'general',
        'tags': json.loads(row['tags_json'] or '[]'),
        'model_provider': row['model_provider'] or '',
        'model_name': row['model_name'] or '',
        'system_prompt': row['system_prompt'] or '',
        'user_prompt_template': row['user_prompt_template'] or '',
        'tools': json.loads(row['tools_json'] or '[]'),
        'mcp_servers': json.loads(row['mcp_servers_json'] or '[]'),
        'knowledge_ids': json.loads(row['knowledge_ids_json'] or '[]'),
        'max_iterations': row['max_iterations'] or 5,
        'temperature': float(row['temperature'] or 0.7),
        'is_public': bool(row['is_public']),
        'is_official': bool(row['is_official']),
        'author_id': row['author_id'] or '',
        'author_name': row['author_name'] or '',
        'usage_count': row['usage_count'] or 0,
        'rating': float(row['rating'] or 0),
        'rating_count': row['rating_count'] or 0,
        'status': row['status'] or 'active',
        'created_at': str(row['created_at']),
        'updated_at': str(row['updated_at']),
    }

def _get_template_by_id(template_id):
    """根据 ID 获取模板"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM agent_templates WHERE id = %s', (template_id,))
        return cur.fetchone()
    finally:
        db.close()

# ============================================================
# 模板 CRUD
# ============================================================

@bp.route('/api/agent-templates', methods=['GET'])
@login_required
def list_templates():
    """列出 Agent 模板（支持搜索/分类/分页/排序）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 12)), 50)
    category = request.args.get('category', '')
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    is_official = request.args.get('is_official', '')

    where = [r'status = "active"']
    params = []

    # 公开模板或自己的模板
    where.append(r'(is_public = 1 OR author_id = %s)')
    params.append(request.user_id or '')

    if category and category != 'all':
        where.append(r'category = %s')
        params.append(category)

    if q:
        where.append(r'(name LIKE %s OR description LIKE %s)')
        params.append(f'%{q}%')
        params.append(f'%{q}%')

    if is_official in ('1', 'true'):
        where.append(r'is_official = 1')

    where_sql = 'WHERE ' + ' AND '.join(where)
    offset = (page - 1) * page_size

    # 排序
    order_map = {
        'created_at': 'created_at DESC',
        'usage_count': 'usage_count DESC',
        'rating': 'rating DESC',
        'name': 'name ASC',
    }
    order_sql = order_map.get(sort_by, 'created_at DESC')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM agent_templates ' + where_sql, params)
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM agent_templates ' + where_sql +
            r' ORDER BY ' + order_sql + r' LIMIT %s OFFSET %s',
            params + [page_size, offset]
        )
        items = [_row_to_template(r) for r in cur.fetchall()]
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


@bp.route('/api/agent-templates/<template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """获取单个模板详情"""
    row = _get_template_by_id(template_id)
    if not row:
        return jsonify(code=404, msg='模板不存在')
    return jsonify(code=200, data=_row_to_template(row))


@bp.route('/api/agent-templates', methods=['POST'])
@login_required
def create_template():
    """创建新模板"""
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    if not name:
        return jsonify(code=400, msg='模板名称不能为空')

    template_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO agent_templates
                       (id, name, description, icon, icon_background, category, tags_json,
                        model_provider, model_name, system_prompt, user_prompt_template,
                        tools_json, mcp_servers_json, knowledge_ids_json,
                        max_iterations, temperature, is_public, is_official,
                        author_id, author_name, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        template_id,
                        name,
                        body.get('description', ''),
                        body.get('icon', '🤖'),
                        body.get('icon_background', '#E8F3FF'),
                        body.get('category', 'general'),
                        json.dumps(body.get('tags', []), ensure_ascii=False),
                        body.get('model_provider', ''),
                        body.get('model_name', ''),
                        body.get('system_prompt', ''),
                        body.get('user_prompt_template', ''),
                        json.dumps(body.get('tools', []), ensure_ascii=False),
                        json.dumps(body.get('mcp_servers', []), ensure_ascii=False),
                        json.dumps(body.get('knowledge_ids', []), ensure_ascii=False),
                        body.get('max_iterations', 5),
                        body.get('temperature', 0.7),
                        1 if body.get('is_public', True) else 0,
                        1 if body.get('is_official', False) else 0,
                        request.user_id or '',
                        body.get('author_name', ''),
                        'active',
                        now, now,
                    ))
        db.commit()
        return jsonify(code=200, msg='创建成功', data={'id': template_id, 'name': name})
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/agent-templates/<template_id>', methods=['PUT'])
@login_required
def update_template(template_id):
    """更新模板"""
    row = _get_template_by_id(template_id)
    if not row:
        return jsonify(code=404, msg='模板不存在')

    body = request.get_json() or {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE agent_templates SET
                       name = %s, description = %s, icon = %s, icon_background = %s,
                       category = %s, tags_json = %s, model_provider = %s, model_name = %s,
                       system_prompt = %s, user_prompt_template = %s, tools_json = %s,
                       mcp_servers_json = %s, knowledge_ids_json = %s,
                       max_iterations = %s, temperature = %s,
                       is_public = %s, is_official = %s, updated_at = %s
                       WHERE id = %s''',
                    (
                        body.get('name', row['name']),
                        body.get('description', row['description'] or ''),
                        body.get('icon', row['icon'] or '🤖'),
                        body.get('icon_background', row['icon_background'] or '#E8F3FF'),
                        body.get('category', row['category'] or 'general'),
                        json.dumps(body.get('tags', json.loads(row['tags_json'] or '[]')), ensure_ascii=False),
                        body.get('model_provider', row['model_provider'] or ''),
                        body.get('model_name', row['model_name'] or ''),
                        body.get('system_prompt', row['system_prompt'] or ''),
                        body.get('user_prompt_template', row['user_prompt_template'] or ''),
                        json.dumps(body.get('tools', json.loads(row['tools_json'] or '[]')), ensure_ascii=False),
                        json.dumps(body.get('mcp_servers', json.loads(row['mcp_servers_json'] or '[]')), ensure_ascii=False),
                        json.dumps(body.get('knowledge_ids', json.loads(row['knowledge_ids_json'] or '[]')), ensure_ascii=False),
                        body.get('max_iterations', row['max_iterations'] or 5),
                        body.get('temperature', float(row['temperature'] or 0.7)),
                        1 if body.get('is_public', bool(row['is_public'])) else 0,
                        1 if body.get('is_official', bool(row['is_official'])) else 0,
                        now,
                        template_id,
                    ))
        db.commit()
        return jsonify(code=200, msg='更新成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/agent-templates/<template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """删除模板（软删除）"""
    row = _get_template_by_id(template_id)
    if not row:
        return jsonify(code=404, msg='模板不存在')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE agent_templates SET status = "inactive" WHERE id = %s', (template_id,))
        db.commit()
        return jsonify(code=200, msg='删除成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


# ============================================================
# 模板操作
# ============================================================

@bp.route('/api/agent-templates/<template_id>/use', methods=['POST'])
@login_required
def use_template(template_id):
    """使用模板创建 Agent"""
    row = _get_template_by_id(template_id)
    if not row:
        return jsonify(code=404, msg='模板不存在')

    body = request.get_json() or {}
    app_name = (body.get('name') or row['name'] + ' (副本)').strip()

    # 构建 Agent 配置
    agent_config = {
        'name': app_name,
        'description': body.get('description', row['description'] or ''),
        'mode': 'agent',
        'model_provider': body.get('model_provider', row['model_provider'] or ''),
        'model_name': body.get('model_name', row['model_name'] or ''),
        'system_prompt': body.get('system_prompt', row['system_prompt'] or ''),
        'user_prompt_template': body.get('user_prompt_template', row['user_prompt_template'] or ''),
        'tools': body.get('tools', json.loads(row['tools_json'] or '[]')),
        'mcp_servers': body.get('mcp_servers', json.loads(row['mcp_servers_json'] or '[]')),
        'knowledge_ids': body.get('knowledge_ids', json.loads(row['knowledge_ids_json'] or '[]')),
        'max_iterations': body.get('max_iterations', row['max_iterations'] or 5),
        'temperature': body.get('temperature', float(row['temperature'] or 0.7)),
    }

    # 增加使用计数
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE agent_templates SET usage_count = usage_count + 1 WHERE id = %s', (template_id,))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

    return jsonify(code=200, msg='模板应用成功', data=agent_config)


@bp.route('/api/agent-templates/<template_id>/rate', methods=['POST'])
@login_required
def rate_template(template_id):
    """为模板评分"""
    row = _get_template_by_id(template_id)
    if not row:
        return jsonify(code=404, msg='模板不存在')

    body = request.get_json() or {}
    score = float(body.get('score', 0))
    if not (0 <= score <= 5):
        return jsonify(code=400, msg='评分必须在 0-5 之间')

    db = get_db()
    try:
        cur = db.cursor()
        # 加权平均更新评分
        cur.execute(r'''UPDATE agent_templates SET
                       rating = (rating * rating_count + %s) / (rating_count + 1),
                       rating_count = rating_count + 1
                       WHERE id = %s''', (score, template_id))
        db.commit()
        return jsonify(code=200, msg='评分成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/agent-templates/categories', methods=['GET'])
def list_categories():
    """获取模板分类列表"""
    categories = [
        {'key': 'all', 'label': '全部分类', 'icon': '📋'},
        {'key': 'general', 'label': '通用助手', 'icon': '🤖'},
        {'key': 'customer', 'label': '客服支持', 'icon': '💬'},
        {'key': 'analysis', 'label': '数据分析', 'icon': '📊'},
        {'key': 'creative', 'label': '创意写作', 'icon': '✍️'},
        {'key': 'code', 'label': '代码助手', 'icon': '💻'},
        {'key': 'education', 'label': '教育培训', 'icon': '📚'},
        {'key': 'marketing', 'label': '营销推广', 'icon': '📣'},
    ]
    return jsonify(code=200, data=categories)


# ============================================================
# 注册路由
# ============================================================

def register_agent_template_routes(app):
    """注册 Agent 模板路由"""
    app.register_blueprint(bp)

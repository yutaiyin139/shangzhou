# -*- coding: utf-8 -*-
"""工作流模板库路由（P4: 保存/复用/分类/搜索）"""

import json
import uuid
from datetime import datetime

from flask import jsonify, request
from config import get_db
from models.tables import WORKFLOW_TEMPLATES_TABLE_SQL
from utils.helpers import now


def _ensure_workflow_templates_table():
    """确保工作流模板表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_TEMPLATES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _serialize_template(row):
    """将数据库行序列化为 API 响应格式"""
    if not row:
        return None
    tags = []
    try:
        tags = json.loads(row['tags_json'] or '[]')
    except Exception:
        pass
    inputs = []
    try:
        inputs = json.loads(row['inputs_json'] or '[]')
    except Exception:
        pass
    outputs = []
    try:
        outputs = json.loads(row['outputs_json'] or '[]')
    except Exception:
        pass
    return {
        'id': row['id'],
        'name': row['name'],
        'description': row['description'] or '',
        'category': row['category'] or 'general',
        'tags': tags,
        'icon': row['icon'] or '📋',
        'icon_background': row['icon_background'] or '#EAF1FE',
        'graph': json.loads(row['graph_json'] or '{}'),
        'inputs': inputs,
        'outputs': outputs,
        'version': row['version'] or '1.0.0',
        'author_id': row['author_id'] or '',
        'author_name': row['author_name'] or '',
        'is_public': bool(row['is_public']),
        'is_official': bool(row['is_official']),
        'usage_count': row['usage_count'] or 0,
        'rating': float(row['rating'] or 0),
        'rating_count': row['rating_count'] or 0,
        'status': row['status'] or 'active',
        'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '',
        'updated_at': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else '',
    }


def register_workflow_template_routes(app):
    """注册工作流模板相关路由"""

    @app.route('/api/workflow-templates', methods=['GET'])
    def list_workflow_templates():
        """列出工作流模板（支持搜索、分类、分页）"""
        _ensure_workflow_templates_table()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        category = (request.args.get('category') or '').strip()
        q = (request.args.get('q') or '').strip().lower()
        tag = (request.args.get('tag') or '').strip()
        is_official = request.args.get('is_official', '')
        sort_by = request.args.get('sort_by', 'created_at')  # created_at/usage_count/rating

        where = [r'status = "active"', r'is_public = 1']
        params = []

        if category and category != 'all':
            where.append(r'category = %s')
            params.append(category)

        if is_official in ('0', '1'):
            where.append(r'is_official = %s')
            params.append(int(is_official))

        if q:
            where.append(r'(LOWER(name) LIKE %s OR LOWER(description) LIKE %s)')
            params.append(f'%{q}%')
            params.append(f'%{q}%')

        if tag:
            where.append(r'JSON_CONTAINS(tags_json, %s)')
            params.append(json.dumps(tag))

        # 排序
        sort_map = {
            'created_at': 'created_at DESC',
            'usage_count': 'usage_count DESC',
            'rating': 'rating DESC, rating_count DESC',
            'name': 'name ASC',
        }
        order_by = sort_map.get(sort_by, 'created_at DESC')

        where_sql = 'WHERE ' + ' AND '.join(where)
        offset = (page - 1) * page_size

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT COUNT(*) as total FROM workflow_templates ' + where_sql, params)
            total = cur.fetchone()['total']
            cur.execute(
                r'SELECT * FROM workflow_templates ' + where_sql +
                r' ORDER BY ' + order_by + r' LIMIT %s OFFSET %s',
                params + [page_size, offset]
            )
            items = [_serialize_template(r) for r in cur.fetchall()]
        finally:
            db.close()

        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    @app.route('/api/workflow-templates/<template_id>', methods=['GET'])
    def get_workflow_template(template_id):
        """获取单个模板详情"""
        _ensure_workflow_templates_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_templates WHERE id = %s', (template_id,))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return jsonify(code=404, msg='模板不存在')
        return jsonify(code=200, data=_serialize_template(row))

    @app.route('/api/workflow-templates', methods=['POST'])
    def create_workflow_template():
        """创建新模板（从现有工作流保存）"""
        _ensure_workflow_templates_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        name = (body.get('name') or '').strip()
        if not name:
            return jsonify(code=400, msg='模板名称不能为空')

        graph = body.get('graph')
        if not graph:
            return jsonify(code=400, msg='工作流图不能为空')

        template_id = str(uuid.uuid4())
        tags = body.get('tags', [])
        inputs = body.get('inputs', [])
        outputs = body.get('outputs', [])

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_templates
                           (id, name, description, category, tags_json, icon, icon_background,
                            graph_json, inputs_json, outputs_json, version, author_id, author_name,
                            is_public, is_official, status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
                template_id,
                name,
                body.get('description', ''),
                body.get('category', 'general'),
                json.dumps(tags, ensure_ascii=False),
                body.get('icon', '📋'),
                body.get('icon_background', '#EAF1FE'),
                json.dumps(graph, ensure_ascii=False),
                json.dumps(inputs, ensure_ascii=False),
                json.dumps(outputs, ensure_ascii=False),
                body.get('version', '1.0.0'),
                body.get('author_id'),
                body.get('author_name', ''),
                1 if body.get('is_public', True) else 0,
                1 if body.get('is_official', False) else 0,
                'active',
                now(),
                now(),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'创建失败: {e}')
        finally:
            db.close()

        return jsonify(code=200, msg='创建成功', data={'id': template_id, 'name': name})

    @app.route('/api/workflow-templates/<template_id>', methods=['PUT'])
    def update_workflow_template(template_id):
        """更新模板"""
        _ensure_workflow_templates_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_templates WHERE id = %s', (template_id,))
            if not cur.fetchone():
                return jsonify(code=404, msg='模板不存在')

            # 动态构建更新字段
            fields = []
            params = []
            if 'name' in body:
                fields.append(r'name = %s')
                params.append(body['name'].strip())
            if 'description' in body:
                fields.append(r'description = %s')
                params.append(body['description'])
            if 'category' in body:
                fields.append(r'category = %s')
                params.append(body['category'])
            if 'tags' in body:
                fields.append(r'tags_json = %s')
                params.append(json.dumps(body['tags'], ensure_ascii=False))
            if 'icon' in body:
                fields.append(r'icon = %s')
                params.append(body['icon'])
            if 'icon_background' in body:
                fields.append(r'icon_background = %s')
                params.append(body['icon_background'])
            if 'graph' in body:
                fields.append(r'graph_json = %s')
                params.append(json.dumps(body['graph'], ensure_ascii=False))
            if 'inputs' in body:
                fields.append(r'inputs_json = %s')
                params.append(json.dumps(body['inputs'], ensure_ascii=False))
            if 'outputs' in body:
                fields.append(r'outputs_json = %s')
                params.append(json.dumps(body['outputs'], ensure_ascii=False))
            if 'is_public' in body:
                fields.append(r'is_public = %s')
                params.append(1 if body['is_public'] else 0)

            if not fields:
                return jsonify(code=400, msg='没有要更新的字段')

            fields.append(r'updated_at = %s')
            params.append(now())
            params.append(template_id)

            cur.execute(
                r'UPDATE workflow_templates SET ' + ', '.join(fields) + r' WHERE id = %s',
                params
            )
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'更新失败: {e}')
        finally:
            db.close()

        return jsonify(code=200, msg='更新成功')

    @app.route('/api/workflow-templates/<template_id>', methods=['DELETE'])
    def delete_workflow_template(template_id):
        """删除模板（软删除）"""
        _ensure_workflow_templates_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE workflow_templates SET status = "inactive", updated_at = %s WHERE id = %s',
                        (now(), template_id))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'删除失败: {e}')
        finally:
            db.close()

    @app.route('/api/workflow-templates/<template_id>/use', methods=['POST'])
    def use_workflow_template(template_id):
        """使用模板创建工作流（增加使用计数）"""
        _ensure_workflow_templates_table()
        body = request.get_json() or {}

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM workflow_templates WHERE id = %s AND status = "active"', (template_id,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='模板不存在')

            # 增加使用计数
            cur.execute(r'UPDATE workflow_templates SET usage_count = usage_count + 1 WHERE id = %s', (template_id,))
            db.commit()

            # 返回模板数据供前端创建应用
            template = _serialize_template(row)
            template['suggested_name'] = body.get('name', row['name'] + ' (副本)')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'使用模板失败: {e}')
        finally:
            db.close()

        return jsonify(code=200, data=template)

    @app.route('/api/workflow-templates/<template_id>/rate', methods=['POST'])
    def rate_workflow_template(template_id):
        """为模板评分"""
        _ensure_workflow_templates_table()
        body = request.get_json()
        score = body.get('score') if body else None
        if score is None or not (0 <= float(score) <= 5):
            return jsonify(code=400, msg='评分必须在 0-5 之间')

        db = get_db()
        try:
            cur = db.cursor()
            # 使用增量平均计算
            cur.execute(r'''UPDATE workflow_templates
                           SET rating = (rating * rating_count + %s) / (rating_count + 1),
                               rating_count = rating_count + 1
                           WHERE id = %s AND status = "active"''',
                        (float(score), template_id))
            db.commit()
            return jsonify(code=200, msg='评分成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'评分失败: {e}')
        finally:
            db.close()

    @app.route('/api/workflow-templates/categories', methods=['GET'])
    def list_workflow_template_categories():
        """获取工作流模板分类列表"""
        categories = [
            {'key': 'all', label: '全部', icon: '📁'},
            {'key': 'general', label: '通用', icon: '📋'},
            {'key': 'analysis', label: '数据分析', icon: '📊'},
            {'key': 'automation', label: '自动化', icon: '⚙️'},
            {'key': 'integration', label: '集成', icon: '🔗'},
            {'key': 'data', label: '数据处理', icon: '🗃️'},
            {'key': 'content', label: '内容创作', icon: '✍️'},
            {'key': 'customer', label: '客户服务', icon: '💬'},
        ]
        return jsonify(code=200, data=categories)

    @app.route('/api/workflow-templates/save-from-workflow', methods=['POST'])
    def save_workflow_as_template():
        """将当前工作流保存为模板"""
        _ensure_workflow_templates_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        app_id = body.get('app_id')
        if not app_id:
            return jsonify(code=400, msg='缺少应用 ID')

        # 获取工作流图
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM dify_workflows WHERE app_id = %s LIMIT 1', (app_id,))
            wf_row = cur.fetchone()
            if not wf_row:
                return jsonify(code=404, msg='工作流不存在')

            graph = json.loads(wf_row['graph'] or '{}')
            graph_json = wf_row['graph']
        except Exception as e:
            return jsonify(code=500, msg=f'获取工作流失败: {e}')
        finally:
            db.close()

        # 创建模板
        template_id = str(uuid.uuid4())
        name = (body.get('name') or '').strip()
        if not name:
            return jsonify(code=400, msg='模板名称不能为空')

        inputs = body.get('inputs', [])
        outputs = body.get('outputs', [])

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_templates
                           (id, name, description, category, tags_json, icon, icon_background,
                            graph_json, inputs_json, outputs_json, version, author_id, author_name,
                            is_public, status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
                template_id,
                name,
                body.get('description', ''),
                body.get('category', 'general'),
                json.dumps(body.get('tags', []), ensure_ascii=False),
                body.get('icon', '📋'),
                body.get('icon_background', '#EAF1FE'),
                graph_json,
                json.dumps(inputs, ensure_ascii=False),
                json.dumps(outputs, ensure_ascii=False),
                body.get('version', '1.0.0'),
                body.get('author_id'),
                body.get('author_name', ''),
                1 if body.get('is_public', True) else 0,
                'active',
                now(),
                now(),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'保存失败: {e}')
        finally:
            db.close()

        return jsonify(code=200, msg='保存成功', data={'id': template_id, 'name': name})

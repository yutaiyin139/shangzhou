# -*- coding: utf-8 -*-
"""
工作流评论协作 API（P2 #15）

功能:
    - 在画布上添加/查看/回复/解决评论
    - 支持节点级评论和全局评论
    - 评论位置（x, y）持久化
"""

import uuid
from datetime import datetime
from flask import jsonify, request

from config import get_db
from models.tables import WORKFLOW_COMMENTS_TABLE_SQL
from utils.auth import login_required
from routes.audit import log_audit_event


def _ensure_comments_table():
    """确保评论表已创建"""
    try:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(WORKFLOW_COMMENTS_TABLE_SQL)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def register_workflow_comments_routes(app):
    """注册工作流评论路由"""

    # ═══════════════════════════════════════════
    #  评论 CRUD
    # ═══════════════════════════════════════════

    @app.route('/api/workflows/<app_id>/comments', methods=['GET'])
    @login_required
    def list_workflow_comments(app_id):
        """
        获取工作流评论列表

        查询参数:
            node_id: 按节点过滤（可选）
            include_resolved: 是否包含已解决评论（默认 false）

        响应: [{ id, user_name, content, node_id, position, created_at, replies }]
        """
        _ensure_comments_table()
        node_id = request.args.get('node_id', '')
        include_resolved = request.args.get('include_resolved', '0') == '1'

        db = get_db()
        try:
            cur = db.cursor()
            sql = r'''SELECT c.id, c.user_id, c.user_name, c.content, c.node_id,
                        c.position_x, c.position_y, c.parent_id, c.resolved, c.created_at
                FROM workflow_comments c
                WHERE c.app_id = %1s'''
            params = [app_id]
            if node_id:
                sql += r' AND c.node_id = %s'
                params.append(node_id)
            if not include_resolved:
                sql += r' AND c.resolved = 0'
            sql += r' ORDER BY c.created_at ASC'
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            # 构建评论树
            comments = {}
            for row in rows:
                comment = {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'] or '匿名',
                    'content': row['content'],
                    'node_id': row['node_id'] or '',
                    'position_x': row['position_x'] or 0,
                    'position_y': row['position_y'] or 0,
                    'parent_id': row['parent_id'],
                    'resolved': bool(row['resolved']),
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '',
                    'replies': [],
                }
                if not row['parent_id']:
                    comments[row['id']] = comment

            # 挂载回复
            for row in rows:
                if row['parent_id'] and row['parent_id'] in comments:
                    reply = {
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'user_name': row['user_name'] or '匿名',
                        'content': row['content'],
                        'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '',
                    }
                    comments[row['parent_id']]['replies'].append(reply)

            return jsonify(code=200, data=list(comments.values()))
        except Exception as e:
            return jsonify(code=500, msg='获取评论失败: %s' % e)
        finally:
            db.close()

    @app.route('/api/workflows/<app_id>/comments', methods=['POST'])
    @login_required
    def add_workflow_comment(app_id):
        """
        添加评论

        请求体:
            {
                content: 评论内容,
                node_id: 节点 ID（可选）,
                position_x: X 坐标（可选）,
                position_y: Y 坐标（可选）,
                parent_id: 回复的评论 ID（可选）
            }
        """
        _ensure_comments_table()
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        content = d.get('content', '').strip()
        if not content:
            return jsonify(code=400, msg='评论内容不能为空')
        if len(content) > 2000:
            return jsonify(code=400, msg='评论内容不能超过 2000 字')

        user = request.user
        comment_id = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO workflow_comments
                    (id, app_id, node_id, user_id, user_name, content, parent_id, position_x, position_y, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (comment_id, app_id,
                 d.get('node_id', '') or '',
                 user.get('user_id', ''),
                 user.get('username', '匿名'),
                 content,
                 d.get('parent_id') or None,
                 d.get('position_x', 0),
                 d.get('position_y', 0),
                 ts, ts))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='添加评论失败: %s' % e)
        finally:
            db.close()

        log_audit_event(
            action='add_workflow_comment',
            resource_type='workflow',
            resource_id=app_id,
            description=f'添加评论: {content[:50]}',
            status='success',
            request_obj=request,
            response_code=200,
        )
        return jsonify(code=200, msg='评论添加成功', data={'id': comment_id})

    @app.route('/api/workflows/<app_id>/comments/<comment_id>', methods=['PUT'])
    @login_required
    def update_workflow_comment(app_id, comment_id):
        """
        更新评论（仅评论作者可修改）

        请求体: { content: 新内容 }
        """
        _ensure_comments_table()
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        content = d.get('content', '').strip()
        if not content:
            return jsonify(code=400, msg='评论内容不能为空')

        user = request.user
        db = get_db()
        try:
            cur = db.cursor()
            # 检查权限（仅作者可修改）
            cur.execute(r'SELECT user_id FROM workflow_comments WHERE id = %s', (comment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='评论不存在')
            if row['user_id'] != user.get('user_id'):
                return jsonify(code=403, msg='无权修改他人评论')

            cur.execute(r'UPDATE workflow_comments SET content = %s, updated_at = NOW() WHERE id = %s',
                        (content, comment_id))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='更新评论失败: %s' % e)
        finally:
            db.close()

        return jsonify(code=200, msg='评论更新成功')

    @app.route('/api/workflows/<app_id>/comments/<comment_id>/resolve', methods=['POST'])
    @login_required
    def resolve_workflow_comment(app_id, comment_id):
        """
        标记评论为已解决

        请求体: { resolved: true/false }
        """
        _ensure_comments_table()
        d = request.get_json() or {}
        resolved = 1 if d.get('resolved', True) else 0

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'UPDATE workflow_comments SET resolved = %s WHERE id = %s AND app_id = %s',
                        (resolved, comment_id, app_id))
            db.commit()
            if cur.rowcount == 0:
                return jsonify(code=404, msg='评论不存在')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='操作失败: %s' % e)
        finally:
            db.close()

        return jsonify(code=200, msg='操作成功')

    @app.route('/api/workflows/<app_id>/comments/<comment_id>', methods=['DELETE'])
    @login_required
    def delete_workflow_comment(app_id, comment_id):
        """
        删除评论（仅评论作者可删除）
        """
        _ensure_comments_table()
        user = request.user

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT user_id FROM workflow_comments WHERE id = %s AND app_id = %s',
                        (comment_id, app_id))
            row = cur.fetchone()
            if not row:
                return jsonify(code=404, msg='评论不存在')
            if row['user_id'] != user.get('user_id'):
                return jsonify(code=403, msg='无权删除他人评论')

            # 级联删除回复
            cur.execute(r'DELETE FROM workflow_comments WHERE parent_id = %s', (comment_id,))
            cur.execute(r'DELETE FROM workflow_comments WHERE id = %s', (comment_id,))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg='删除评论失败: %s' % e)
        finally:
            db.close()

        return jsonify(code=200, msg='评论已删除')

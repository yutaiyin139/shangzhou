# -*- coding: utf-8 -*-
"""对话历史管理路由（MySQL 版，脱离 Dify）"""

import uuid
from datetime import datetime
from flask import jsonify, request
from config import get_db
from models.tables import (
    DIFY_CONVERSATIONS_TABLE_SQL,
    DIFY_MESSAGES_TABLE_SQL,
)


def _ensure_conversation_tables():
    """确保对话相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_CONVERSATIONS_TABLE_SQL)
        cur.execute(DIFY_MESSAGES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _generate_title(message):
    """根据首条消息自动生成会话标题"""
    title = (message or '').strip()
    if len(title) > 30:
        title = title[:30] + '...'
    return title or '新对话'


def register_conversation_routes(app):
    """注册对话历史相关路由"""

    @app.route('/api/conversations', methods=['GET'])
    def list_conversations():
        """获取会话列表（按最后消息时间倒序）"""
        _ensure_conversation_tables()
        agent_id = request.args.get('agent_id')
        app_id = request.args.get('app_id')
        keyword = request.args.get('keyword', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
        offset = (page - 1) * page_size

        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 构建查询条件
                where = ["status = 'active'"]
                params = []
                if agent_id:
                    where.append('agent_id = %s')
                    params.append(agent_id)
                if app_id:
                    where.append('app_id = %s')
                    params.append(app_id)
                if keyword:
                    where.append('title LIKE %s')
                    params.append('%' + keyword + '%')

                where_sql = ' AND '.join(where)

                # 查询总数
                cur.execute(
                    f'SELECT COUNT(*) AS total FROM dify_conversations WHERE {where_sql}',
                    params
                )
                total = cur.fetchone()['total']

                # 查询列表
                cur.execute(
                    f'''SELECT id, app_id, agent_id, title, summary, model_name,
                        message_count, total_tokens, is_pinned, last_message_at, created_at
                        FROM dify_conversations
                        WHERE {where_sql}
                        ORDER BY is_pinned DESC, last_message_at DESC, created_at DESC
                        LIMIT %s OFFSET %s''',
                    params + [page_size, offset]
                )
                items = cur.fetchall()
            finally:
                db.close()

            return jsonify(code=200, data={
                'items': [{
                    'id': c['id'],
                    'app_id': c['app_id'],
                    'agent_id': c['agent_id'],
                    'title': c['title'],
                    'summary': c['summary'] or '',
                    'model_name': c['model_name'] or '',
                    'message_count': c['message_count'] or 0,
                    'total_tokens': c['total_tokens'] or 0,
                    'is_pinned': bool(c['is_pinned']),
                    'last_message_at': (c['last_message_at'].isoformat() + 'Z') if c['last_message_at'] else '',
                    'created_at': (c['created_at'].isoformat() + 'Z') if c['created_at'] else '',
                } for c in items],
                'total': total,
                'page': page,
                'page_size': page_size,
            })
        except Exception as e:
            return jsonify(code=500, msg='获取会话列表失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>', methods=['GET'])
    def get_conversation(conv_id):
        """获取会话详情（含消息列表）"""
        _ensure_conversation_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    'SELECT * FROM dify_conversations WHERE id = %s',
                    (conv_id,)
                )
                conv = cur.fetchone()
                if not conv:
                    return jsonify(code=404, msg='会话不存在')

                cur.execute(
                    '''SELECT id, role, content, tokens, model_provider, model_name,
                       feedback, feedback_reason, metadata, created_at
                       FROM dify_messages
                       WHERE conversation_id = %s
                       ORDER BY created_at ASC''',
                    (conv_id,)
                )
                messages = cur.fetchall()
            finally:
                db.close()

            return jsonify(code=200, data={
                'id': conv['id'],
                'app_id': conv['app_id'],
                'agent_id': conv['agent_id'],
                'title': conv['title'],
                'summary': conv['summary'] or '',
                'model_provider': conv['model_provider'] or '',
                'model_name': conv['model_name'] or '',
                'system_prompt': conv['system_prompt'] or '',
                'knowledge_ids': conv['knowledge_ids'] or '',
                'message_count': conv['message_count'] or 0,
                'total_tokens': conv['total_tokens'] or 0,
                'is_pinned': bool(conv['is_pinned']),
                'status': conv['status'],
                'last_message_at': (conv['last_message_at'].isoformat() + 'Z') if conv['last_message_at'] else '',
                'created_at': (conv['created_at'].isoformat() + 'Z') if conv['created_at'] else '',
                'messages': [{
                    'id': m['id'],
                    'role': m['role'],
                    'content': m['content'] or '',
                    'tokens': m['tokens'] or 0,
                    'model_provider': m['model_provider'] or '',
                    'model_name': m['model_name'] or '',
                    'feedback': m['feedback'] or 0,
                    'feedback_reason': m['feedback_reason'] or '',
                    'metadata': m['metadata'] or '',
                    'created_at': (m['created_at'].isoformat() + 'Z') if m['created_at'] else '',
                } for m in messages],
            })
        except Exception as e:
            return jsonify(code=500, msg='获取会话详情失败: ' + str(e))

    @app.route('/api/conversations', methods=['POST'])
    def create_conversation():
        """创建新会话"""
        _ensure_conversation_tables()
        body = request.get_json(silent=True) or {}
        title = (body.get('title') or '').strip() or '新对话'
        agent_id = body.get('agent_id')
        app_id = body.get('app_id')
        system_prompt = (body.get('system_prompt') or '').strip()
        knowledge_ids = body.get('knowledge_ids') or []

        conv_id = str(uuid.uuid4())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    '''INSERT INTO dify_conversations
                       (id, app_id, agent_id, title, system_prompt, knowledge_ids,
                        model_provider, model_name, created_at, updated_at, last_message_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (conv_id, app_id, agent_id, title, system_prompt,
                     ','.join(knowledge_ids) if knowledge_ids else '',
                     body.get('model_provider', ''), body.get('model_name', ''),
                     ts, ts, ts)
                )
                db.commit()
            finally:
                db.close()
            return jsonify(code=200, data={'id': conv_id, 'title': title}, msg='创建成功')
        except Exception as e:
            return jsonify(code=500, msg='创建会话失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>', methods=['PUT'])
    def update_conversation(conv_id):
        """更新会话（重命名、置顶、设置摘要等）"""
        _ensure_conversation_tables()
        body = request.get_json(silent=True) or {}
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 动态构建更新字段
                fields = []
                params = []
                if 'title' in body:
                    fields.append('title = %s')
                    params.append((body['title'] or '').strip() or '新对话')
                if 'summary' in body:
                    fields.append('summary = %s')
                    params.append(body['summary'])
                if 'is_pinned' in body:
                    fields.append('is_pinned = %s')
                    params.append(1 if body['is_pinned'] else 0)
                if 'status' in body:
                    fields.append('status = %s')
                    params.append(body['status'])

                if not fields:
                    return jsonify(code=400, msg='没有要更新的字段')

                params.append(conv_id)
                cur.execute(
                    f"UPDATE dify_conversations SET {', '.join(fields)} WHERE id = %s",
                    params
                )
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='会话不存在')
                return jsonify(code=200, msg='更新成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='更新会话失败: ' + str(e))
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='更新会话失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>', methods=['DELETE'])
    def delete_conversation(conv_id):
        """删除会话（级联删除消息）"""
        _ensure_conversation_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute('DELETE FROM dify_messages WHERE conversation_id = %s', (conv_id,))
                cur.execute('DELETE FROM dify_conversations WHERE id = %s', (conv_id,))
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='会话不存在')
                return jsonify(code=200, msg='删除成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='删除会话失败: ' + str(e))
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='删除会话失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>/messages', methods=['GET'])
    def get_messages(conv_id):
        """获取会话的消息列表（分页）"""
        _ensure_conversation_tables()
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(200, max(1, request.args.get('page_size', 50, type=int)))
        offset = (page - 1) * page_size

        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    'SELECT COUNT(*) AS total FROM dify_messages WHERE conversation_id = %s',
                    (conv_id,)
                )
                total = cur.fetchone()['total']

                cur.execute(
                    '''SELECT id, role, content, tokens, model_provider, model_name,
                       feedback, feedback_reason, created_at
                       FROM dify_messages
                       WHERE conversation_id = %s
                       ORDER BY created_at ASC
                       LIMIT %s OFFSET %s''',
                    (conv_id, page_size, offset)
                )
                messages = cur.fetchall()
            finally:
                db.close()

            return jsonify(code=200, data={
                'items': [{
                    'id': m['id'],
                    'role': m['role'],
                    'content': m['content'] or '',
                    'tokens': m['tokens'] or 0,
                    'model_provider': m['model_provider'] or '',
                    'model_name': m['model_name'] or '',
                    'feedback': m['feedback'] or 0,
                    'feedback_reason': m['feedback_reason'] or '',
                    'created_at': (m['created_at'].isoformat() + 'Z') if m['created_at'] else '',
                } for m in messages],
                'total': total,
                'page': page,
                'page_size': page_size,
            })
        except Exception as e:
            return jsonify(code=500, msg='获取消息列表失败: ' + str(e))

    @app.route('/api/messages/<message_id>/thoughts', methods=['GET'])
    def get_message_thoughts(message_id):
        """获取消息的 Agent 思考链（ReAct 推理过程）"""
        try:
            from engine.thought_chain import get_thought_chain
            thoughts = get_thought_chain(message_id)
            return jsonify(code=200, data={
                'items': thoughts,
                'total': len(thoughts),
            })
        except Exception as e:
            return jsonify(code=500, msg='获取思考链失败: ' + str(e))

    @app.route('/api/messages/<message_id>/retriever-resources', methods=['GET'])
    def get_message_retriever_resources(message_id):
        """获取消息的检索引用（知识库来源追踪）"""
        try:
            from engine.retrieval_resources import get_retriever_resources
            resources = get_retriever_resources(message_id)
            return jsonify(code=200, data={
                'items': resources,
                'total': len(resources),
            })
        except Exception as e:
            return jsonify(code=500, msg='获取引用失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>/messages/<msg_id>/feedback', methods=['POST'])
    def message_feedback(conv_id, msg_id):
        """消息反馈（赞/踩）"""
        _ensure_conversation_tables()
        body = request.get_json(silent=True) or {}
        feedback = body.get('feedback', 0)
        feedback_reason = (body.get('feedback_reason') or '').strip()

        try:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(
                    '''UPDATE dify_messages
                       SET feedback = %s, feedback_reason = %s
                       WHERE id = %s AND conversation_id = %s''',
                    (feedback, feedback_reason, msg_id, conv_id)
                )
                db.commit()
                if not cur.rowcount:
                    return jsonify(code=404, msg='消息不存在')
                return jsonify(code=200, msg='反馈成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='反馈失败: ' + str(e))
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='反馈失败: ' + str(e))

    @app.route('/api/conversations/<conv_id>/clear', methods=['POST'])
    def clear_messages(conv_id):
        """清空会话消息（保留会话本身）"""
        _ensure_conversation_tables()
        try:
            db = get_db()
            try:
                cur = db.cursor()
                # 级联删除思考链和引用
                try:
                    cur.execute(
                        'DELETE t FROM message_agent_thoughts t '
                        'JOIN dify_messages m ON t.message_id = m.id '
                        'WHERE m.conversation_id = %s', (conv_id,))
                    cur.execute(
                        'DELETE rr FROM dataset_retriever_resources rr '
                        'JOIN dify_messages m ON rr.message_id = m.id '
                        'WHERE m.conversation_id = %s', (conv_id,))
                except Exception:
                    pass  # 表可能不存在
                cur.execute('DELETE FROM dify_messages WHERE conversation_id = %s', (conv_id,))
                cur.execute(
                    '''UPDATE dify_conversations
                       SET message_count = 0, total_tokens = 0, updated_at = %s
                       WHERE id = %s''',
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), conv_id)
                )
                db.commit()
                return jsonify(code=200, msg='清空成功')
            except Exception as e:
                db.rollback()
                return jsonify(code=500, msg='清空失败: ' + str(e))
            finally:
                db.close()
        except Exception as e:
            return jsonify(code=500, msg='清空失败: ' + str(e))

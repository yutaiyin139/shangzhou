# -*- coding: utf-8 -*-
"""消息反馈路由（点赞/踩、反馈管理）"""

import uuid
from datetime import datetime
from flask import jsonify, request
from config import get_db
from models.tables import DIFY_MESSAGE_FEEDBACKS_TABLE_SQL


def _ensure_feedback_tables():
    """确保反馈相关表已创建"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DIFY_MESSAGE_FEEDBACKS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def register_feedback_routes(app):
    """注册反馈相关路由"""

    @app.route('/api/feedback', methods=['POST'])
    def submit_feedback():
        """提交消息反馈（点赞/踩）"""
        _ensure_feedback_tables()
        d = request.get_json()
        message_id = d.get('message_id', '').strip()
        rating = d.get('rating', 1)
        reason = d.get('reason', '').strip()
        user_id = d.get('user_id', '').strip() or None
        conversation_id = d.get('conversation_id', '').strip()

        if not message_id:
            return jsonify(code=400, msg='缺少消息ID')

        # 验证 rating 值
        if rating not in (1, -1):
            return jsonify(code=400, msg='无效的反馈值')

        db = get_db()
        try:
            cur = db.cursor()
            # 检查消息是否存在
            cur.execute(r'SELECT id FROM dify_messages WHERE id = %s', (message_id,))
            if not cur.fetchone():
                return jsonify(code=404, msg='消息不存在')

            # 检查是否已有反馈，有则更新
            cur.execute(
                r'SELECT id FROM dify_message_feedbacks WHERE message_id = %s AND (user_id = %s OR (user_id IS NULL AND %s IS NULL))',
                (message_id, user_id, user_id)
            )
            existing = cur.fetchone()

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if existing:
                # 更新现有反馈
                cur.execute(
                    r'''UPDATE dify_message_feedbacks
                        SET rating = %s, reason = %s, updated_at = %s
                        WHERE id = %s''',
                    (rating, reason, ts, existing['id'])
                )
            else:
                # 新建反馈
                feedback_id = str(uuid.uuid4())
                cur.execute(
                    r'''INSERT INTO dify_message_feedbacks
                        (id, message_id, conversation_id, user_id, rating, reason, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (feedback_id, message_id, conversation_id, user_id, rating, reason, ts, ts)
                )
            db.commit()

            # 更新消息的 feedback 字段
            cur.execute(
                r'UPDATE dify_messages SET feedback = %s WHERE id = %s',
                (rating, message_id)
            )
            db.commit()

            return jsonify(code=200, msg='反馈已提交', data={'rating': rating})
        except Exception as e:
            return jsonify(code=500, msg='提交失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/feedback/<message_id>', methods=['GET'])
    def get_feedback(message_id):
        """获取消息的反馈信息"""
        _ensure_feedback_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT f.*, da.name AS username
                    FROM dify_message_feedbacks f
                    LEFT JOIN dify_accounts da ON da.id = f.user_id
                    WHERE f.message_id = %s
                    ORDER BY f.created_at DESC''',
                (message_id,)
            )
            items = []
            for r in cur.fetchall():
                items.append({
                    'id': r['id'],
                    'message_id': r['message_id'],
                    'user_id': r['user_id'],
                    'username': r['username'] or '匿名',
                    'rating': r['rating'],
                    'reason': r['reason'],
                    'created_at': str(r['created_at']),
                })
            return jsonify(code=200, data=items)
        finally:
            db.close()

    @app.route('/api/feedback/conversation/<conversation_id>', methods=['GET'])
    def get_conversation_feedback(conversation_id):
        """获取会话的所有反馈统计"""
        _ensure_feedback_tables()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'''SELECT
                        COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) AS likes,
                        COALESCE(SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END), 0) AS dislikes,
                        COUNT(*) AS total
                    FROM dify_message_feedbacks
                    WHERE conversation_id = %s''',
                (conversation_id,)
            )
            row = cur.fetchone()
            return jsonify(code=200, data={
                'likes': int(row['likes']),
                'dislikes': int(row['dislikes']),
                'total': int(row['total']),
            })
        finally:
            db.close()

    @app.route('/api/feedback/<message_id>', methods=['DELETE'])
    def delete_feedback(message_id):
        """删除反馈（取消点赞/踩）"""
        _ensure_feedback_tables()
        user_id = request.args.get('user_id', '').strip() or None

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                r'DELETE FROM dify_message_feedbacks WHERE message_id = %s AND (user_id = %s OR (user_id IS NULL AND %s IS NULL))',
                (message_id, user_id, user_id)
            )
            # 重置消息的 feedback 字段
            cur.execute(
                r'UPDATE dify_messages SET feedback = 0 WHERE id = %s',
                (message_id,)
            )
            db.commit()
            return jsonify(code=200, msg='反馈已删除')
        except Exception as e:
            return jsonify(code=500, msg='删除失败: ' + str(e))
        finally:
            db.close()

    @app.route('/api/feedback/stats', methods=['GET'])
    def get_feedback_stats():
        """获取反馈统计数据（管理用）"""
        _ensure_feedback_tables()
        db = get_db()
        try:
            cur = db.cursor()

            # 总体统计
            cur.execute(r'''
                SELECT
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) AS total_likes,
                    COALESCE(SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END), 0) AS total_dislikes,
                    COUNT(*) AS total_feedbacks,
                    COUNT(DISTINCT message_id) AS messages_with_feedback
                FROM dify_message_feedbacks
            ''')
            overall = cur.fetchone()

            # 最近 7 天趋势
            cur.execute(r'''
                SELECT
                    DATE(created_at) AS date,
                    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS likes,
                    SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS dislikes
                FROM dify_message_feedbacks
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            trend = []
            for r in cur.fetchall():
                trend.append({
                    'date': str(r['date']),
                    'likes': int(r['likes']),
                    'dislikes': int(r['dislikes']),
                })

            # 反馈最多的消息（Top 10）
            cur.execute(r'''
                SELECT f.message_id, m.content, m.role,
                       SUM(CASE WHEN f.rating = 1 THEN 1 ELSE 0 END) AS likes,
                       SUM(CASE WHEN f.rating = -1 THEN 1 ELSE 0 END) AS dislikes
                FROM dify_message_feedbacks f
                JOIN dify_messages m ON m.id = f.message_id
                GROUP BY f.message_id
                ORDER BY likes + dislikes DESC
                LIMIT 10
            ''')
            top_messages = []
            for r in cur.fetchall():
                top_messages.append({
                    'message_id': r['message_id'],
                    'content': (r['content'] or '')[:100],
                    'role': r['role'],
                    'likes': int(r['likes']),
                    'dislikes': int(r['dislikes']),
                })

            return jsonify(code=200, data={
                'overall': {
                    'total_likes': int(overall['total_likes']),
                    'total_dislikes': int(overall['total_dislikes']),
                    'total_feedbacks': int(overall['total_feedbacks']),
                    'messages_with_feedback': int(overall['messages_with_feedback']),
                },
                'trend': trend,
                'top_messages': top_messages,
            })
        finally:
            db.close()

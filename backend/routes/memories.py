# -*- coding: utf-8 -*-
"""记忆管理路由"""

from flask import jsonify, request
from config import get_db
from utils.helpers import now
from models.tables import MEMORIES_TABLE_SQL


def _ensure_memories_table():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(MEMORIES_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def register_memory_routes(app):
    """注册记忆相关路由"""

    @app.route('/api/memories', methods=['GET'])
    def get_memories():
        """按 agent_id 查记忆列表"""
        _ensure_memories_table()
        agent_id = request.args.get('agent_id', type=int)
        db = get_db()
        try:
            cur = db.cursor()
            if agent_id:
                cur.execute(r'SELECT id, agent_id, content, created_at, updated_at FROM memories WHERE agent_id = %s ORDER BY updated_at DESC', (agent_id,))
            else:
                cur.execute(r'SELECT id, agent_id, content, created_at, updated_at FROM memories ORDER BY updated_at DESC')
            rows = cur.fetchall()
            for r in rows:
                r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else ''
                r['updated_at'] = r['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if r['updated_at'] else ''
            return jsonify(code=200, data=rows)
        finally:
            db.close()

    @app.route('/api/memories', methods=['POST'])
    def create_memory():
        """新增一条记忆"""
        _ensure_memories_table()
        d = request.get_json()
        agent_id = d.get('agent_id')
        content = d.get('content', '').strip()
        if not agent_id:
            return jsonify(code=400, msg='缺少 agent_id')
        if not content:
            return jsonify(code=400, msg='请输入记忆内容')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'INSERT INTO memories (agent_id, content, created_at, updated_at) VALUES (%s, %s, %s, %s)',
                        (agent_id, content, now(), now()))
            db.commit()
            return jsonify(code=200, msg='添加成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

    @app.route('/api/memories/<int:mid>', methods=['DELETE'])
    def delete_memory(mid):
        """删除一条记忆"""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM memories WHERE id = %s', (mid,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=str(e))
        finally:
            db.close()

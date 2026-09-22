# -*- coding: utf-8 -*-
"""Agent 记忆管理 API —— CRUD + 语义检索 + 向量化状态"""
import re
from flask import jsonify, request

from config import get_db
from engine.agent_memory import (
    add_memory, add_memories_bulk, search_memories, list_memories,
    get_memory, update_memory, delete_memory, delete_all_memories,
    build_memory_context, ensure_memories_schema,
)


def _is_int_id(s):
    return bool(re.match(r'^\d+$', s or ''))


def register_agent_memory_routes(app):
    """注册 Agent 记忆路由"""
    # 确保 memories 表包含向量化字段（兼容旧表自动升级）
    ensure_memories_schema()

    @app.route('/api/agents/<agent_id>/memories', methods=['GET'])
    def list_agent_memories(agent_id):
        """分页列出 agent 的记忆"""
        if not _is_int_id(agent_id):
            return jsonify(code=400, msg='非法的 agent ID')
        page = max(int(request.args.get('page', 1)), 1)
        page_size = min(int(request.args.get('page_size', 20)), 100)
        status = request.args.get('status', '')
        data = list_memories(int(agent_id), page=page, page_size=page_size, status=status)
        return jsonify(code=200, data=data)

    @app.route('/api/agents/<agent_id>/memories', methods=['POST'])
    def create_agent_memory(agent_id):
        """写入一条记忆"""
        if not _is_int_id(agent_id):
            return jsonify(code=400, msg='非法的 agent ID')
        body = request.json or {}
        content = (body.get('content') or '').strip()
        if not content:
            return jsonify(code=400, msg='content 不能为空')
        if len(content) > 5000:
            return jsonify(code=400, msg='content 长度不能超过 5000')

        # 批量模式
        if isinstance(content, list):
            contents = [c.strip() for c in content if isinstance(c, str) and c.strip()]
            n = add_memories_bulk(int(agent_id), contents)
            return jsonify(code=200, data={'added': n})

        row = add_memory(int(agent_id), content)
        if not row:
            return jsonify(code=500, msg='写入失败')
        return jsonify(code=200, data=row)

    @app.route('/api/agents/<agent_id>/memories/search', methods=['GET'])
    def search_agent_memories(agent_id):
        """语义检索记忆"""
        if not _is_int_id(agent_id):
            return jsonify(code=400, msg='非法的 agent ID')
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify(code=400, msg='q 不能为空')
        limit = min(int(request.args.get('limit', 5)), 20)
        min_score = float(request.args.get('min_score', 0.0))
        hits = search_memories(int(agent_id), query, limit=limit, min_score=min_score)
        return jsonify(code=200, data={'items': hits, 'query': query})

    @app.route('/api/agents/<agent_id>/memories/context', methods=['GET'])
    def agent_memory_context(agent_id):
        """检索记忆并返回拼接好的 system-prompt 片段（供前端预览）"""
        if not _is_int_id(agent_id):
            return jsonify(code=400, msg='非法的 agent ID')
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify(code=400, msg='q 不能为空')
        limit = min(int(request.args.get('limit', 5)), 10)
        min_score = float(request.args.get('min_score', 0.5))
        ctx = build_memory_context(int(agent_id), query, limit=limit, min_score=min_score)
        return jsonify(code=200, data={'context': ctx})

    @app.route('/api/agents/<agent_id>/memories/<memory_id>', methods=['GET'])
    def get_agent_memory(agent_id, memory_id):
        if not _is_int_id(agent_id) or not _is_int_id(memory_id):
            return jsonify(code=400, msg='非法的 ID')
        row = get_memory(int(memory_id), int(agent_id))
        if not row:
            return jsonify(code=404, msg='记忆不存在')
        return jsonify(code=200, data=row)

    @app.route('/api/agents/<agent_id>/memories/<memory_id>', methods=['PUT'])
    def update_agent_memory(agent_id, memory_id):
        if not _is_int_id(agent_id) or not _is_int_id(memory_id):
            return jsonify(code=400, msg='非法的 ID')
        body = request.json or {}
        content = (body.get('content') or '').strip()
        if not content:
            return jsonify(code=400, msg='content 不能为空')
        ok = update_memory(int(memory_id), int(agent_id), content)
        if not ok:
            return jsonify(code=404, msg='记忆不存在或更新失败')
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/agents/<agent_id>/memories/<memory_id>', methods=['DELETE'])
    def delete_agent_memory(agent_id, memory_id):
        if not _is_int_id(agent_id) or not _is_int_id(memory_id):
            return jsonify(code=400, msg='非法的 ID')
        ok = delete_memory(int(memory_id), int(agent_id))
        if not ok:
            return jsonify(code=404, msg='记忆不存在')
        return jsonify(code=200, msg='删除成功')

    @app.route('/api/agents/<agent_id>/memories', methods=['DELETE'])
    def delete_all_agent_memories(agent_id):
        """清空 agent 全部记忆"""
        if not _is_int_id(agent_id):
            return jsonify(code=400, msg='非法的 agent ID')
        n = delete_all_memories(int(agent_id))
        return jsonify(code=200, data={'deleted': n})

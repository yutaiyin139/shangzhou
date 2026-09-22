# -*- coding: utf-8 -*-
"""
知识 Pipeline API（P2 #13）

功能:
    - Pipeline CRUD（创建/读取/更新/删除）
    - 执行 Pipeline（手动触发/定时调度）
    - 执行日志查询
    - 文档管理（添加待处理文档）
"""

import json
from flask import jsonify, request

from utils.auth import login_required, role_required
from engine.knowledge_pipeline import (
    create_pipeline, update_pipeline, delete_pipeline,
    get_pipeline, list_pipelines,
    run_pipeline, get_execution_log, list_execution_logs,
)


def register_knowledge_pipeline_routes(app):
    """注册知识 Pipeline 路由"""

    # ═══════════════════════════════════════════
    #  Pipeline CRUD
    # ═══════════════════════════════════════════

    @app.route('/api/knowledge/pipelines', methods=['GET'])
    @login_required
    def list_pipelines_view():
        """
        列出 Pipeline

        查询参数:
            dataset_id: 按知识库过滤
            status: 按状态过滤
            page: 页码
            limit: 每页数量
        """
        dataset_id = request.args.get('dataset_id')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        pipelines = list_pipelines(dataset_id=dataset_id, status=status, page=page, limit=limit)
        return jsonify(code=200, data=pipelines)

    @app.route('/api/knowledge/pipelines/<pipeline_id>', methods=['GET'])
    @login_required
    def get_pipeline_view(pipeline_id):
        """获取 Pipeline 详情"""
        pipeline = get_pipeline(pipeline_id)
        if not pipeline:
            return jsonify(code=404, msg='Pipeline 不存在'), 404
        return jsonify(code=200, data=pipeline)

    @app.route('/api/knowledge/pipelines', methods=['POST'])
    @login_required
    def create_pipeline_view():
        """
        创建 Pipeline

        请求体:
            {
                name: Pipeline 名称,
                description: 描述（可选）,
                dataset_id: 关联知识库 ID（可选）,
                stages: [{type, config, order}],  // 阶段配置
                schedule: cron 表达式（可选）
            }

        stage type: fetch, parse, clean, segment, transform, embed, index
        """
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        name = d.get('name', '').strip()
        if not name:
            return jsonify(code=400, msg='Pipeline 名称为必填项')

        stages = d.get('stages', [])
        if not stages:
            return jsonify(code=400, msg='至少配置一个阶段')

        # 验证阶段类型
        valid_types = {'fetch', 'parse', 'clean', 'segment', 'transform', 'embed', 'index'}
        for stage in stages:
            if stage.get('type') not in valid_types:
                return jsonify(code=400, msg=f'无效的阶段类型: {stage.get("type")}')

        user = request.user
        pipeline_id = create_pipeline(
            name=name,
            description=d.get('description', ''),
            stages=stages,
            dataset_id=d.get('dataset_id'),
            schedule=d.get('schedule'),
            created_by=user.get('user_id', ''),
        )
        return jsonify(code=200, msg='创建成功', data={'id': pipeline_id})

    @app.route('/api/knowledge/pipelines/<pipeline_id>', methods=['PUT'])
    @login_required
    def update_pipeline_view(pipeline_id):
        """更新 Pipeline"""
        d = request.get_json()
        if not d:
            return jsonify(code=400, msg='请求体不能为空')

        # 验证阶段类型
        if 'stages' in d:
            valid_types = {'fetch', 'parse', 'clean', 'segment', 'transform', 'embed', 'index'}
            for stage in d['stages']:
                if stage.get('type') not in valid_types:
                    return jsonify(code=400, msg=f'无效的阶段类型: {stage.get("type")}')

        success = update_pipeline(pipeline_id, **d)
        if not success:
            return jsonify(code=404, msg='Pipeline 不存在')
        return jsonify(code=200, msg='更新成功')

    @app.route('/api/knowledge/pipelines/<pipeline_id>', methods=['DELETE'])
    @login_required
    def delete_pipeline_view(pipeline_id):
        """删除 Pipeline"""
        delete_pipeline(pipeline_id)
        return jsonify(code=200, msg='删除成功')

    # ═══════════════════════════════════════════
    #  执行控制
    # ═══════════════════════════════════════════

    @app.route('/api/knowledge/pipelines/<pipeline_id>/run', methods=['POST'])
    @login_required
    def run_pipeline_view(pipeline_id):
        """
        执行 Pipeline

        请求体: { trigger_type: 'manual' (可选) }
        """
        d = request.get_json() or {}
        trigger_type = d.get('trigger_type', 'manual')
        try:
            execution_id = run_pipeline(pipeline_id, trigger_type=trigger_type)
            return jsonify(code=200, msg='Pipeline 已开始执行', data={'execution_id': execution_id})
        except ValueError as e:
            return jsonify(code=400, msg=str(e))
        except Exception as e:
            return jsonify(code=500, msg=f'执行失败: {e}')

    @app.route('/api/knowledge/pipelines/<pipeline_id>/pause', methods=['POST'])
    @login_required
    def pause_pipeline_view(pipeline_id):
        """暂停 Pipeline"""
        success = update_pipeline(pipeline_id, status='paused')
        if not success:
            return jsonify(code=404, msg='Pipeline 不存在')
        return jsonify(code=200, msg='Pipeline 已暂停')

    @app.route('/api/knowledge/pipelines/<pipeline_id>/resume', methods=['POST'])
    @login_required
    def resume_pipeline_view(pipeline_id):
        """恢复 Pipeline"""
        success = update_pipeline(pipeline_id, status='draft')
        if not success:
            return jsonify(code=404, msg='Pipeline 不存在')
        return jsonify(code=200, msg='Pipeline 已恢复')

    # ═══════════════════════════════════════════
    #  执行日志
    # ═══════════════════════════════════════════

    @app.route('/api/knowledge/pipelines/<pipeline_id>/logs', methods=['GET'])
    @login_required
    def list_execution_logs_view(pipeline_id):
        """
        列出执行日志

        查询参数:
            page: 页码
            limit: 每页数量
        """
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        logs = list_execution_logs(pipeline_id, page=page, limit=limit)
        return jsonify(code=200, data=logs)

    @app.route('/api/knowledge/pipelines/logs/<execution_id>', methods=['GET'])
    @login_required
    def get_execution_log_view(execution_id):
        """获取执行日志详情"""
        log = get_execution_log(execution_id)
        if not log:
            return jsonify(code=404, msg='执行日志不存在'), 404
        return jsonify(code=200, data=log)

    # ═══════════════════════════════════════════
    #  阶段类型说明
    # ═══════════════════════════════════════════

    @app.route('/api/knowledge/pipelines/stage-types', methods=['GET'])
    def get_stage_types():
        """获取支持的阶段类型说明"""
        stage_types = [
            {
                'type': 'fetch',
                'name': '获取文档',
                'description': '从各种来源获取文档内容',
                'config': {
                    'source_type': 'text|file|url|api',
                    'texts': ['直接输入的文本'],
                    'file_paths': ['文件路径列表'],
                    'urls': ['URL 列表'],
                },
            },
            {
                'type': 'parse',
                'name': '解析内容',
                'description': '解析文档内容，去除 HTML 标签等',
                'config': {
                    'strip_html': True,
                    'strip_whitespace': True,
                },
            },
            {
                'type': 'clean',
                'name': '清洗文本',
                'description': '清洗和标准化文本内容',
                'config': {
                    'remove_special_chars': False,
                    'normalize_whitespace': True,
                    'remove_duplicates': False,
                },
            },
            {
                'type': 'segment',
                'name': '文档分段',
                'description': '将文档切分为分段',
                'config': {
                    'mode': 'general|paragraph',
                    'max_tokens': 500,
                    'overlap': 50,
                },
            },
            {
                'type': 'transform',
                'name': '内容转换',
                'description': '对内容进行转换（摘要、关键词等）',
                'config': {
                    'transform_type': 'none|keywords',
                },
            },
            {
                'type': 'embed',
                'name': '向量化',
                'description': '生成分段的向量嵌入',
                'config': {
                    'model': 'text-embedding-ada-002',
                    'batch_size': 10,
                },
            },
            {
                'type': 'index',
                'name': '写入知识库',
                'description': '将分段写入知识库',
                'config': {},
            },
        ]
        return jsonify(code=200, data=stage_types)

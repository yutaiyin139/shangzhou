# -*- coding: utf-8 -*-
"""Agent 评估系统路由（P4: 自动评测/指标）"""

import json
import uuid
import time
from datetime import datetime

from flask import jsonify, request
from config import get_db
from models.tables import AGENT_EVALUATIONS_TABLE_SQL
from utils.helpers import now


def _ensure_evaluations_table():
    """确保评估表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(AGENT_EVALUATIONS_TABLE_SQL)
        db.commit()
    finally:
        db.close()


def _serialize_evaluation(row):
    """将数据库行序列化为 API 响应格式"""
    if not row:
        return None
    dataset = []
    try:
        dataset = json.loads(row['dataset_json'] or '[]')
    except Exception:
        pass
    metrics = {}
    try:
        metrics = json.loads(row['metrics_json'] or '{}')
    except Exception:
        pass
    result = {}
    try:
        result = json.loads(row['result_json'] or '{}')
    except Exception:
        pass
    return {
        'id': row['id'],
        'app_id': row['app_id'],
        'name': row['name'],
        'description': row['description'] or '',
        'dataset': dataset,
        'metrics': metrics,
        'status': row['status'] or 'pending',
        'total_cases': row['total_cases'] or 0,
        'completed_cases': row['completed_cases'] or 0,
        'passed_cases': row['passed_cases'] or 0,
        'avg_score': float(row['avg_score'] or 0),
        'avg_latency_ms': row['avg_latency_ms'] or 0,
        'total_tokens': row['total_tokens'] or 0,
        'result': result,
        'started_at': row['started_at'].strftime('%Y-%m-%d %H:%M:%S') if row['started_at'] else None,
        'completed_at': row['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if row['completed_at'] else None,
        'created_by': row['created_by'] or '',
        'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '',
        'updated_at': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else '',
    }


def register_evaluation_routes(app):
    """注册 Agent 评估相关路由"""

    @app.route('/api/evaluations', methods=['GET'])
    def list_evaluations():
        """列出评估任务"""
        _ensure_evaluations_table()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        app_id = (request.args.get('app_id') or '').strip()
        status = (request.args.get('status') or '').strip()

        where = []
        params = []
        if app_id:
            where.append(r'app_id = %s')
            params.append(app_id)
        if status:
            where.append(r'status = %s')
            params.append(status)

        where_sql = 'WHERE ' + ' AND '.join(where) if where else ''
        offset = (page - 1) * page_size

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT COUNT(*) as total FROM agent_evaluations ' + where_sql, params)
            total = cur.fetchone()['total']
            cur.execute(
                r'SELECT * FROM agent_evaluations ' + where_sql +
                r' ORDER BY created_at DESC LIMIT %s OFFSET %s',
                params + [page_size, offset]
            )
            items = [_serialize_evaluation(r) for r in cur.fetchall()]
        finally:
            db.close()

        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    @app.route('/api/evaluations/<eval_id>', methods=['GET'])
    def get_evaluation(eval_id):
        """获取单个评估详情"""
        _ensure_evaluations_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM agent_evaluations WHERE id = %s', (eval_id,))
            row = cur.fetchone()
        finally:
            db.close()
        if not row:
            return jsonify(code=404, msg='评估不存在')
        return jsonify(code=200, data=_serialize_evaluation(row))

    @app.route('/api/evaluations', methods=['POST'])
    def create_evaluation():
        """创建评估任务"""
        _ensure_evaluations_table()
        body = request.get_json()
        if not body:
            return jsonify(code=400, msg='请求体不能为空')

        app_id = body.get('app_id')
        if not app_id:
            return jsonify(code=400, msg='缺少应用 ID')

        name = (body.get('name') or '').strip()
        if not name:
            return jsonify(code=400, msg='评估名称不能为空')

        dataset = body.get('dataset', [])
        if not dataset:
            return jsonify(code=400, msg='评估数据集不能为空')

        eval_id = str(uuid.uuid4())

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''INSERT INTO agent_evaluations
                           (id, app_id, name, description, dataset_json, metrics_json,
                            status, total_cases, created_by, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)''', (
                eval_id,
                app_id,
                name,
                body.get('description', ''),
                json.dumps(dataset, ensure_ascii=False),
                json.dumps(body.get('metrics', {}), ensure_ascii=False),
                len(dataset),
                body.get('created_by'),
                now(),
                now(),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'创建失败: {e}')
        finally:
            db.close()

        return jsonify(code=200, msg='创建成功', data={'id': eval_id, 'name': name})

    @app.route('/api/evaluations/<eval_id>/run', methods=['POST'])
    def run_evaluation(eval_id):
        """运行评估任务"""
        _ensure_evaluations_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'SELECT * FROM agent_evaluations WHERE id = %s', (eval_id,))
            row = cur.fetchone()
        finally:
            db.close()

        if not row:
            return jsonify(code=404, msg='评估不存在')

        if row['status'] == 'running':
            return jsonify(code=400, msg='评估已在运行中')

        # 更新状态为运行中
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"UPDATE agent_evaluations SET status = 'running', started_at = %s WHERE id = %s",
                        (now(), eval_id))
            db.commit()
        finally:
            db.close()

        # 异步执行评估（简化版：同步执行）
        try:
            _execute_evaluation(eval_id)
        except Exception as e:
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r"UPDATE agent_evaluations SET status = 'failed' WHERE id = %s", (eval_id,))
                db.commit()
            finally:
                db.close()
            return jsonify(code=500, msg=f'评估执行失败: {e}')

        return jsonify(code=200, msg='评估完成')

    @app.route('/api/evaluations/<eval_id>', methods=['DELETE'])
    def delete_evaluation(eval_id):
        """删除评估任务"""
        _ensure_evaluations_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'DELETE FROM agent_evaluations WHERE id = %s', (eval_id,))
            db.commit()
            return jsonify(code=200, msg='删除成功')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'删除失败: {e}')
        finally:
            db.close()

    @app.route('/api/evaluations/<eval_id>/stop', methods=['POST'])
    def stop_evaluation(eval_id):
        """停止评估任务"""
        _ensure_evaluations_table()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r"UPDATE agent_evaluations SET status = 'completed', completed_at = %s WHERE id = %s AND status = 'running'",
                        (now(), eval_id))
            db.commit()
            return jsonify(code=200, msg='已停止')
        except Exception as e:
            db.rollback()
            return jsonify(code=500, msg=f'停止失败: {e}')
        finally:
            db.close()

    @app.route('/api/evaluations/stats', methods=['GET'])
    def get_evaluation_stats():
        """获取评估统计"""
        _ensure_evaluations_table()
        app_id = (request.args.get('app_id') or '').strip()

        db = get_db()
        try:
            cur = db.cursor()
            if app_id:
                cur.execute(r'''SELECT
                                   COUNT(*) as total,
                                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                                   SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                                   AVG(avg_score) as avg_score,
                                   AVG(avg_latency_ms) as avg_latency
                               FROM agent_evaluations WHERE app_id = %s''', (app_id,))
            else:
                cur.execute(r'''SELECT
                                   COUNT(*) as total,
                                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                                   SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                                   AVG(avg_score) as avg_score,
                                   AVG(avg_latency_ms) as avg_latency
                               FROM agent_evaluations''')
            row = cur.fetchone()
        finally:
            db.close()

        return jsonify(code=200, data={
            'total': row['total'] or 0,
            'completed': row['completed'] or 0,
            'running': row['running'] or 0,
            'avg_score': float(row['avg_score'] or 0),
            'avg_latency_ms': int(row['avg_latency'] or 0),
        })


def _execute_evaluation(eval_id):
    """执行评估任务"""
    from engine.workflow_runner import run_workflow
    from utils.llm import chat_completion

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM agent_evaluations WHERE id = %s', (eval_id,))
        eval_row = cur.fetchone()
    finally:
        db.close()

    if not eval_row:
        return

    dataset = json.loads(eval_row['dataset_json'] or '[]')
    app_id = eval_row['app_id']

    results = []
    total_score = 0
    total_latency = 0
    total_tokens = 0
    passed = 0

    for i, case in enumerate(dataset):
        input_text = case.get('input', '')
        expected = case.get('expected', '')

        start_time = time.time()
        try:
            # 调用 LLM 获取实际输出
            response = chat_completion(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': input_text}],
                temperature=0.7,
                max_tokens=1000
            )
            actual_output = response.get('content', '')
            tokens_used = response.get('usage', {}).get('total_tokens', 0)
        except Exception as e:
            actual_output = f'错误: {str(e)}'
            tokens_used = 0

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 计算得分（简化：基于关键词匹配）
        score = _calculate_score(actual_output, expected)
        total_score += score
        total_latency += elapsed_ms
        total_tokens += tokens_used

        if score >= 0.7:
            passed += 1

        results.append({
            'input': input_text,
            'expected': expected,
            'actual': actual_output,
            'score': score,
            'latency_ms': elapsed_ms,
            'tokens': tokens_used,
            'passed': score >= 0.7,
        })

        # 更新进度
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE agent_evaluations
                           SET completed_cases = %s, passed_cases = %s
                           WHERE id = %s''', (i + 1, passed, eval_id))
            db.commit()
        finally:
            db.close()

    # 计算最终统计
    avg_score = total_score / len(dataset) if dataset else 0
    avg_latency = total_latency / len(dataset) if dataset else 0

    # 保存结果
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE agent_evaluations
                       SET status = 'completed',
                           result_json = %s,
                           avg_score = %s,
                           avg_latency_ms = %s,
                           total_tokens = %s,
                           completed_cases = %s,
                           passed_cases = %s,
                           completed_at = %s
                       WHERE id = %s''', (
            json.dumps(results, ensure_ascii=False),
            avg_score,
            avg_latency,
            total_tokens,
            len(dataset),
            passed,
            now(),
            eval_id,
        ))
        db.commit()
    finally:
        db.close()


def _calculate_score(actual: str, expected: str) -> float:
    """计算单个测试用例得分（简化版）"""
    if not actual or not expected:
        return 0.0

    actual_lower = actual.lower()
    expected_lower = expected.lower()

    # 完全匹配
    if actual_lower.strip() == expected_lower.strip():
        return 1.0

    # 关键词匹配
    expected_words = set(expected_lower.split())
    actual_words = set(actual_lower.split())
    if not expected_words:
        return 0.0

    common = expected_words & actual_words
    score = len(common) / len(expected_words)

    # 包含期望输出的主要部分
    if expected_lower in actual_lower:
        score = max(score, 0.9)

    return min(score, 1.0)

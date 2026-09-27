# -*- coding: utf-8 -*-
"""工作流调试路由 —— 断点调试、单步执行、变量查看"""
import json
import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime

from utils.helpers import _safe_uid

from models.tables import (
    WORKFLOW_DEBUG_SESSIONS_TABLE_SQL,
    WORKFLOW_BATCH_RUNS_TABLE_SQL,
)
from config import get_db
from utils.auth import login_required

bp = Blueprint('workflow_debug', __name__)

# ============================================================
# 初始化表
# ============================================================

def init_tables():
    """初始化和批量运行相关表"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(WORKFLOW_DEBUG_SESSIONS_TABLE_SQL)
        cur.execute(WORKFLOW_BATCH_RUNS_TABLE_SQL)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

init_tables()

# ============================================================
# 辅助函数
# ============================================================

def _row_to_debug_session(row):
    """数据库行转调试会话字典"""
    return {
        'id': row['id'],
        'app_id': row['app_id'],
        'account_id': row['account_id'],
        'inputs': json.loads(row['inputs_json'] or '{}'),
        'current_node_id': row['current_node_id'] or '',
        'status': row['status'] or 'running',
        'context': json.loads(row['context_json'] or '{}'),
        'breakpoints': json.loads(row['breakpoints_json'] or '[]'),
        'node_results': json.loads(row['node_results_json'] or '{}'),
        'current_node_result': row['current_node_result'] or '',
        'error_message': row['error_message'] or '',
        'created_at': str(row['created_at']),
        'updated_at': str(row['updated_at']),
    }

def _get_debug_session(session_id):
    """获取调试会话"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM workflow_debug_sessions WHERE id = %s', (session_id,))
        return cur.fetchone()
    finally:
        db.close()

# ============================================================
# 调试会话管理
# ============================================================

@bp.route('/api/workflows/<app_id>/debug/start', methods=['POST'])
@login_required
def start_debug_session(app_id):
    """启动调试会话"""
    body = request.get_json() or {}
    inputs = body.get('inputs', {})
    breakpoints = body.get('breakpoints', [])

    session_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO workflow_debug_sessions
                       (id, app_id, account_id, inputs_json, breakpoints_json,
                        status, context_json, node_results_json, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, 'running', '{}', '{}', %s, %s)''',
                    (
                        session_id, app_id, _safe_uid(None),
                        json.dumps(inputs, ensure_ascii=False),
                        json.dumps(breakpoints, ensure_ascii=False),
                        now, now,
                    ))
        db.commit()
        return jsonify(code=200, msg='调试会话已启动', data={
            'session_id': session_id,
            'status': 'running',
            'inputs': inputs,
            'breakpoints': breakpoints,
        })
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/workflows/debug/<session_id>', methods=['GET'])
@login_required
def get_debug_session(session_id):
    """获取调试会话状态"""
    row = _get_debug_session(session_id)
    if not row:
        return jsonify(code=404, msg='调试会话不存在')
    return jsonify(code=200, data=_row_to_debug_session(row))


@bp.route('/api/workflows/debug/<session_id>/step', methods=['POST'])
@login_required
def step_debug(session_id):
    """
    单步执行：执行当前节点并暂停
    返回执行结果和下一个节点信息
    """
    row = _get_debug_session(session_id)
    if not row:
        return jsonify(code=404, msg='调试会话不存在')

    if row['status'] == 'completed':
        return jsonify(code=200, msg='调试已完成', data={'status': 'completed'})

    body = request.get_json() or {}
    # 获取当前上下文和节点结果
    context = json.loads(row['context_json'] or '{}')
    node_results = json.loads(row['node_results_json'] or '{}')
    breakpoints = json.loads(row['breakpoints_json'] or '[]')
    inputs = json.loads(row['inputs_json'] or '{}')

    # 获取工作流图
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT graph FROM dify_workflows WHERE app_id = %s ORDER BY created_at DESC LIMIT 1', (row['app_id'],))
        wf_row = cur.fetchone()
        if not wf_row:
            return jsonify(code=404, msg='工作流不存在')
        graph = json.loads(wf_row['graph'] or '{}')
    finally:
        db.close()

    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    # 确定下一个要执行的节点
    current_node_id = row['current_node_id'] or ''
    next_node_id = body.get('next_node_id', '')

    if not next_node_id:
        # 自动查找下一个节点
        if not current_node_id:
            # 从 start 节点开始
            start_node = next((n for n in nodes if n.get('data', {}).get('type') == 'start'), None)
            next_node_id = start_node['id'] if start_node else ''
        else:
            # 查找当前节点的输出连接的下一个节点
            for edge in edges:
                if edge.get('source') == current_node_id:
                    next_node_id = edge.get('target', '')
                    break

    if not next_node_id:
        # 没有下一个节点，调试完成
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(r'''UPDATE workflow_debug_sessions SET
                           status = 'completed', current_node_id = '',
                           context_json = %s, updated_at = %s
                           WHERE id = %s''',
                        (json.dumps(context, ensure_ascii=False), now, session_id))
            db.commit()
        except Exception:
            pass
        finally:
            db.close()
        return jsonify(code=200, msg='调试完成', data={'status': 'completed'})

    # 执行节点
    next_node = next((n for n in nodes if n['id'] == next_node_id), None)
    if not next_node:
        return jsonify(code=404, msg=f'节点 {next_node_id} 不存在')

    node_data = next_node.get('data', {})
    node_type = node_data.get('type', '')

    # 执行节点
    try:
        # 单步调试要的就是"只跑这一个节点"，入口是 _execute_node（旧的 _execute_single_node 并不存在）
        from engine.workflow_runner import _execute_node
        result = _execute_node(node_type, node_data, context, {})
        if isinstance(result, dict):
            context.update(result)
            node_results[next_node_id] = result
    except Exception as e:
        return jsonify(code=500, msg=f'节点执行错误: {str(e)}')

    # 检查是否是断点
    is_breakpoint = next_node_id in breakpoints
    status = 'paused' if is_breakpoint else 'running'

    # 更新会话
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''UPDATE workflow_debug_sessions SET
                       current_node_id = %s, status = %s,
                       context_json = %s, node_results_json = %s,
                       current_node_result = %s, updated_at = %s
                       WHERE id = %s''',
                    (
                        next_node_id, status,
                        json.dumps(context, ensure_ascii=False),
                        json.dumps(node_results, ensure_ascii=False),
                        json.dumps(node_results.get(next_node_id, {}), ensure_ascii=False),
                        now, session_id,
                    ))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

    return jsonify(code=200, msg='执行成功', data={
        'status': status,
        'current_node_id': next_node_id,
        'node_type': node_type,
        'node_result': node_results.get(next_node_id, {}),
        'context': context,
        'is_breakpoint': is_breakpoint,
    })


@bp.route('/api/workflows/debug/<session_id>/continue', methods=['POST'])
@login_required
def continue_debug(session_id):
    """继续执行：从当前断点继续执行到下一个断点或结束"""
    row = _get_debug_session(session_id)
    if not row:
        return jsonify(code=404, msg='调试会话不存在')

    if row['status'] == 'completed':
        return jsonify(code=200, msg='调试已完成', data={'status': 'completed'})

    breakpoints = json.loads(row['breakpoints_json'] or '[]')
    context = json.loads(row['context_json'] or '{}')
    node_results = json.loads(row['node_results_json'] or '{}')

    # 获取工作流图
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT graph FROM dify_workflows WHERE app_id = %s ORDER BY created_at DESC LIMIT 1', (row['app_id'],))
        wf_row = cur.fetchone()
        if not wf_row:
            return jsonify(code=404, msg='工作流不存在')
        graph = json.loads(wf_row['graph'] or '{}')
    finally:
        db.close()

    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    current_node_id = row['current_node_id'] or ''

    # 循环执行直到遇到断点或结束
    max_steps = 100  # 安全限制
    step_count = 0
    last_node_id = current_node_id
    last_result = {}

    while step_count < max_steps:
        step_count += 1

        # 查找下一个节点
        next_node_id = ''
        if not current_node_id:
            start_node = next((n for n in nodes if n.get('data', {}).get('type') == 'start'), None)
            next_node_id = start_node['id'] if start_node else ''
        else:
            for edge in edges:
                if edge.get('source') == current_node_id:
                    next_node_id = edge.get('target', '')
                    break

        if not next_node_id:
            # 执行完成
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''UPDATE workflow_debug_sessions SET
                               status = 'completed', current_node_id = '',
                               context_json = %s, updated_at = %s
                               WHERE id = %s''',
                            (json.dumps(context, ensure_ascii=False), now, session_id))
                db.commit()
            except Exception:
                pass
            finally:
                db.close()
            return jsonify(code=200, msg='调试完成', data={
                'status': 'completed',
                'steps': step_count,
            })

        # 执行节点
        next_node = next((n for n in nodes if n['id'] == next_node_id), None)
        if not next_node:
            break

        node_data = next_node.get('data', {})
        node_type = node_data.get('type', '')

        try:
            from engine.workflow_runner import _execute_node
            result = _execute_node(node_type, node_data, context, {})
            if isinstance(result, dict):
                context.update(result)
                node_results[next_node_id] = result
                last_result = result
        except Exception as e:
            return jsonify(code=500, msg=f'节点执行错误: {str(e)}')

        last_node_id = next_node_id

        # 检查是否是断点
        if next_node_id in breakpoints:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db = get_db()
            try:
                cur = db.cursor()
                cur.execute(r'''UPDATE workflow_debug_sessions SET
                               current_node_id = %s, status = 'paused',
                               context_json = %s, node_results_json = %s,
                               current_node_result = %s, updated_at = %s
                               WHERE id = %s''',
                            (
                                next_node_id,
                                json.dumps(context, ensure_ascii=False),
                                json.dumps(node_results, ensure_ascii=False),
                                json.dumps(last_result, ensure_ascii=False),
                                now, session_id,
                            ))
                db.commit()
            except Exception:
                pass
            finally:
                db.close()
            return jsonify(code=200, msg='已暂停在断点', data={
                'status': 'paused',
                'current_node_id': next_node_id,
                'node_type': node_type,
                'node_result': last_result,
                'context': context,
                'steps': step_count,
            })

        current_node_id = next_node_id

    # 达到最大步数
    return jsonify(code=200, msg='达到最大步数限制', data={
        'status': 'paused',
        'current_node_id': last_node_id,
        'context': context,
        'steps': step_count,
    })


@bp.route('/api/workflows/debug/<session_id>/stop', methods=['POST'])
@login_required
def stop_debug(session_id):
    """停止调试会话"""
    row = _get_debug_session(session_id)
    if not row:
        return jsonify(code=404, msg='调试会话不存在')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'UPDATE workflow_debug_sessions SET status = "completed", updated_at = %s WHERE id = %s',
                    (now, session_id))
        db.commit()
        return jsonify(code=200, msg='调试已停止')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/workflows/debug/<session_id>/variables', methods=['GET'])
@login_required
def get_debug_variables(session_id):
    """获取当前调试上下文变量"""
    row = _get_debug_session(session_id)
    if not row:
        return jsonify(code=404, msg='调试会话不存在')

    context = json.loads(row['context_json'] or '{}')
    return jsonify(code=200, data={
        'context': context,
        'current_node_id': row['current_node_id'],
        'node_results': json.loads(row['node_results_json'] or '{}'),
    })


# ============================================================
# 批量运行
# ============================================================

@bp.route('/api/workflows/<app_id>/batch-run', methods=['POST'])
@login_required
def create_batch_run(app_id):
    """创建批量运行任务"""
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    input_data = body.get('input_data', [])

    if not name:
        return jsonify(code=400, msg='任务名称不能为空')
    if not input_data or not isinstance(input_data, list):
        return jsonify(code=400, msg='输入数据不能为空')

    batch_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'''INSERT INTO workflow_batch_runs
                       (id, app_id, account_id, name, status, total_count,
                        input_data_json, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s, %s)''',
                    (
                        batch_id, app_id, _safe_uid(None), name,
                        len(input_data),
                        json.dumps(input_data, ensure_ascii=False),
                        now, now,
                    ))
        db.commit()
        return jsonify(code=200, msg='批量任务已创建', data={
            'id': batch_id,
            'name': name,
            'total_count': len(input_data),
            'status': 'pending',
        })
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


@bp.route('/api/workflows/<app_id>/batch-run/<batch_id>/start', methods=['POST'])
@login_required
def start_batch_run(app_id, batch_id):
    """启动批量运行任务"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM workflow_batch_runs WHERE id = %s AND app_id = %s', (batch_id, app_id))
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='批量任务不存在')

        if row['status'] == 'running':
            return jsonify(code=400, msg='任务已在运行中')

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(r'UPDATE workflow_batch_runs SET status = "running", updated_at = %s WHERE id = %s',
                    (now, batch_id))
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()

    # 异步执行批量任务
    try:
        from tasks.workflow_tasks import execute_batch_run
        execute_batch_run.delay(batch_id)
    except Exception as e:
        # 以前这里 except: pass —— 批次会被标成 running 但永无人执行，前端只看到"已启动"
        err_msg = '无法排入后台队列: %s' % str(e)
        db2 = get_db()
        try:
            cur2 = db2.cursor()
            cur2.execute(r'UPDATE workflow_batch_runs SET status = "error", error_message = %s, updated_at = %s WHERE id = %s',
                         (err_msg[:500], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), batch_id))
            db2.commit()
        finally:
            db2.close()
        return jsonify(code=500, msg='批量任务启动失败: ' + str(e))

    return jsonify(code=200, msg='批量任务已启动')


@bp.route('/api/workflows/<app_id>/batch-runs', methods=['GET'])
@login_required
def list_batch_runs(app_id):
    """列出批量运行任务"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT COUNT(*) as total FROM workflow_batch_runs WHERE app_id = %s', (app_id,))
        total = cur.fetchone()['total']

        cur.execute(
            r'SELECT * FROM workflow_batch_runs WHERE app_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s',
            (app_id, page_size, offset)
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'id': r['id'],
                'name': r['name'],
                'status': r['status'],
                'total_count': r['total_count'],
                'success_count': r['success_count'],
                'fail_count': r['fail_count'],
                'created_at': str(r['created_at']),
                'updated_at': str(r['updated_at']),
            })
        return jsonify(code=200, data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    finally:
        db.close()


@bp.route('/api/workflows/<app_id>/batch-run/<batch_id>', methods=['GET'])
@login_required
def get_batch_run(app_id, batch_id):
    """获取批量任务详情"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'SELECT * FROM workflow_batch_runs WHERE id = %s AND app_id = %s', (batch_id, app_id))
        row = cur.fetchone()
        if not row:
            return jsonify(code=404, msg='批量任务不存在')

        return jsonify(code=200, data={
            'id': row['id'],
            'name': row['name'],
            'status': row['status'],
            'total_count': row['total_count'],
            'success_count': row['success_count'],
            'fail_count': row['fail_count'],
            'input_data': json.loads(row['input_data_json'] or '[]'),
            'output_data': json.loads(row['output_data_json'] or '[]'),
            'error_message': row['error_message'] or '',
            'created_at': str(row['created_at']),
            'updated_at': str(row['updated_at']),
        })
    finally:
        db.close()


@bp.route('/api/workflows/<app_id>/batch-run/<batch_id>', methods=['DELETE'])
@login_required
def delete_batch_run(app_id, batch_id):
    """删除批量任务"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(r'DELETE FROM workflow_batch_runs WHERE id = %s AND app_id = %s', (batch_id, app_id))
        db.commit()
        return jsonify(code=200, msg='删除成功')
    except Exception as e:
        db.rollback()
        return jsonify(code=500, msg=str(e))
    finally:
        db.close()


# ============================================================
# 注册路由
# ============================================================

def register_workflow_debug_routes(app):
    """注册工作流调试路由"""
    app.register_blueprint(bp)

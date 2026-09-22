# -*- coding: utf-8 -*-
"""阶段 2（P1）Agent 增强 + RAG 元数据 —— 确定性功能测试

覆盖（不依赖真实 embedding 模型 / LLM / 外网）：
  2.3 策略注册表 + ReAct 响应解析（纯逻辑）
  2.1 记忆向量回路：MySQL + Qdrant 真实双写 + 语义排序 + context 注入（get_embedding 桩化，去 Celery 竞态）
  2.4 元数据：字段 CRUD / 分段绑定 / JSON 同步 / SQL 过滤 / 负例 / 解绑 / 级联删除

运行：cd backend && python tests/e2e_phase2_agent_rag_check.py
前置：MySQL + Qdrant 可达（后端进程非必需，直接用 engine）。
"""
import sys
import os
import json
import math
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_db  # noqa: E402

PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f'  [PASS] {name}')
    except Exception as e:
        FAIL += 1
        print(f'  [FAIL] {name}: {type(e).__name__}: {e}')


# ============================================================
# 2.3 Agent 策略注册表 + ReAct 解析（纯逻辑）
# ============================================================
def t_strategy_registry():
    from engine.agent_strategies import (
        list_strategies, get_strategy, ReActStrategy,
        FunctionCallStrategy, PlanExecuteStrategy)
    names = set(list_strategies())
    assert {'react', 'function_call', 'plan_execute'} <= names, f'缺少策略: {names}'
    assert isinstance(get_strategy('react'), ReActStrategy)
    assert isinstance(get_strategy('function_call'), FunctionCallStrategy)
    assert isinstance(get_strategy('plan_execute'), PlanExecuteStrategy)
    try:
        get_strategy('__no_such_strategy__')
        raise AssertionError('未知策略应抛 ValueError')
    except ValueError:
        pass


def _react():
    from engine.agent_strategies import get_strategy
    return get_strategy('react')


def t_react_parse_json_action():
    r = _react()._parse_response('{"action": "search", "action_input": {"q": "x"}}')
    assert r['type'] == 'action' and r['action'] == 'search' and r['action_input'] == {'q': 'x'}, r


def t_react_parse_final_answer():
    r = _react()._parse_response('Final Answer: 天空是蓝色的')
    assert r['type'] == 'final_answer' and '蓝色' in r['content'], r


def t_react_parse_text_action():
    r = _react()._parse_response('Thought: 需要查天气\nAction: get_weather\nAction Input: {"city": "北京"}')
    assert r['type'] == 'action' and r['action'] == 'get_weather' and r['action_input'] == {'city': '北京'}, r


def t_react_parse_unknown():
    r = _react()._parse_response('这是一段没有任何格式的自由文本')
    assert r['type'] == 'unknown', r


# ============================================================
# 2.1 记忆向量回路（fake embedding + 真实 MySQL/Qdrant）
# ============================================================
DIMS = 512
TMP_AGENT = 990001  # 一次性 agent_id，测后清空


def _fake_embed(text):
    """字符袋 -> 归一化向量（确定性，无需模型）。共享字符越多，cosine 越高。"""
    v = [0.0] * DIMS
    for ch in text:
        v[hash(ch) % DIMS] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _clear_mem(agent_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM memories WHERE agent_id = %s', (agent_id,))
        db.commit()
    finally:
        db.close()
    try:
        from utils.vector_store import get_vector_store
        from engine.agent_memory import _collection_name
        get_vector_store().delete_collection(_collection_name(agent_id))
    except Exception:
        pass


def _insert_memory(agent_id, content):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            'INSERT INTO memories (agent_id, content, embedding_status, created_at, updated_at)'
            ' VALUES (%s, %s, %s, %s, %s)', (agent_id, content, 'pending', now, now))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def t_memory_vector_loop():
    import engine.embedding_service as es
    from engine import agent_memory as am
    am.ensure_memories_schema()
    _clear_mem(TMP_AGENT)

    orig = es.get_embedding
    es.get_embedding = _fake_embed  # 桩化：写入/检索同进程用同一确定性向量
    try:
        contents = [
            '张三是一名高级后端工程师，擅长 Python 和分布式系统。',
            '李四是产品经理，负责 AI 平台条线。',
            '公司每周三下午有技术分享会，在报告厅举行。',
        ]
        ids = []
        for c in contents:
            mid = _insert_memory(TMP_AGENT, c)
            am._persist_embedding(mid, TMP_AGENT, _fake_embed(c), c)  # 双写 MySQL(completed)+Qdrant
            ids.append(mid)
        # 校验落库状态
        db = get_db(); cur = db.cursor()
        cur.execute("SELECT COUNT(*) c FROM memories WHERE agent_id=%s AND embedding_status='completed'", (TMP_AGENT,))
        assert cur.fetchone()['c'] == 3, '双写后应有 3 条 completed'
        db.close()
        # 语义检索：后端工程师 -> 张三第一
        hits = am.search_memories(TMP_AGENT, '后端工程师', limit=3)
        assert hits, '检索无结果'
        assert '张三' in hits[0]['content'], f'张三应排第一: {hits[0]}'
        assert hits[0]['score'] > 0, hits[0]
        # context 注入：技术分享 -> 含分享会
        ctx = am.build_memory_context(TMP_AGENT, '技术分享会', limit=3, min_score=0.0)
        assert '技术分享会' in ctx, ctx
        assert ctx.startswith('# 用户长期记忆'), ctx
    finally:
        es.get_embedding = orig
        _clear_mem(TMP_AGENT)


# ============================================================
# 2.4 元数据：字段 / 绑定 / JSON 同步 / 过滤 / 级联
# ============================================================
def _pick_dataset_segment():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT dataset_id, COUNT(*) n FROM dify_document_segments'
                    ' GROUP BY dataset_id ORDER BY n DESC LIMIT 1')
        row = cur.fetchone()
        if not row:
            return None, []
        ds = row['dataset_id']
        cur.execute('SELECT id, metadata FROM dify_document_segments WHERE dataset_id=%s ORDER BY id LIMIT 1', (ds,))
        seg = cur.fetchone()
        return ds, (seg['id'] if seg else None), (seg['metadata'] if seg else None)
    finally:
        db.close()


def t_metadata_crud():
    from engine import metadata_engine as me
    me.ensure_metadata_tables()
    ds, seg, seg_meta_orig = _pick_dataset_segment()
    assert ds and seg, '环境中无含分段的数据集，无法验证绑定'
    fld_name = 'zz_阶段2测试部门'
    fld = me.create_metadata_field(ds, fld_name, 'string', 'phase2 e2e')
    assert fld and fld.get('id'), fld
    try:
        # 绑定
        b = me.bind_segment_metadata(ds, fld['id'], seg, '法务')
        assert b and b.get('id'), b
        md = me.get_segment_metadata(seg)
        assert md.get(fld_name) == '法务', md
        # JSON 冗余同步
        db = get_db(); cur = db.cursor()
        cur.execute('SELECT metadata FROM dify_document_segments WHERE id=%s', (seg,))
        jso = json.loads(cur.fetchone()['metadata'] or '{}')
        db.close()
        assert jso.get(fld_name) == '法务', f'JSON 同步失败: {jso}'
        # 过滤 SQL 构造
        where, params = me.build_metadata_filter_sql(
            ds, [{'name': fld_name, 'value': '法务', 'operator': 'eq'}])
        assert 'dataset_metadata_bindings' in where and '法务' in params, (where, params)
        # 正例命中
        passed = me.filter_segments_by_metadata(ds, [seg], [{'name': fld_name, 'value': '法务', 'operator': 'eq'}])
        assert seg in passed, passed
        # 负例排除
        blocked = me.filter_segments_by_metadata(ds, [seg], [{'name': fld_name, 'value': '财务部', 'operator': 'eq'}])
        assert seg not in blocked, blocked
        # 解绑
        assert me.unbind_segment_metadata(ds, fld['id'], seg) is True
        assert fld_name not in me.get_segment_metadata(seg), '解绑后仍残留'
    finally:
        me.delete_metadata_field(fld['id'], ds)
        # 级联：字段删除后绑定应清空
        assert fld_name not in me.get_segment_metadata(seg), '级联删除失败'
        # 还原分段原始 metadata JSON（避免污染真实数据）
        db = get_db(); cur = db.cursor()
        cur.execute('UPDATE dify_document_segments SET metadata=%s WHERE id=%s', (seg_meta_orig, seg))
        db.commit(); db.close()


def t_metadata_field_validation():
    from engine import metadata_engine as me
    me.ensure_metadata_tables()
    assert me.create_metadata_field('nonexistent-ds', '   ') is None, '空字段名应拒绝'


if __name__ == '__main__':
    print('===== 阶段 2 确定性功能测试 =====')
    print('[2.3] Agent 策略注册表 + ReAct 解析')
    check('strategy_registry', t_strategy_registry)
    check('react_parse_json_action', t_react_parse_json_action)
    check('react_parse_final_answer', t_react_parse_final_answer)
    check('react_parse_text_action', t_react_parse_text_action)
    check('react_parse_unknown', t_react_parse_unknown)
    print('[2.1] Agent 记忆向量化回路 (MySQL + Qdrant, embedding 桩化)')
    check('memory_vector_loop', t_memory_vector_loop)
    print('[2.4] 知识库元数据系统')
    check('metadata_crud', t_metadata_crud)
    check('metadata_field_validation', t_metadata_field_validation)
    print(f'\n结果: {PASS} PASS / {FAIL} FAIL')
    sys.exit(1 if FAIL else 0)

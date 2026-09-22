# -*- coding: utf-8 -*-
"""
知识库关键词表引擎 —— jieba 分词索引 + 混合检索（向量+关键词加权）

职责:
    1. 为数据集分段建立关键词索引（dataset_keyword_tables 表）
    2. 提供基于关键词的检索（含词频加权）
    3. 与向量检索结合形成混合检索

设计要点:
    - jieba 分词（中文），英文按空格/标点切分
    - 索引按 (dataset_id, keyword, segment_id) 唯一存储，含词频
    - 检索时用 OR 匹配关键词，按匹配度和词频加权打分
    - 可选：jieba 不可用时回退到 2-gram 分词
"""
import re
import uuid
from datetime import datetime
from typing import List, Dict, Set
from collections import Counter

from config import get_db
from models.tables import DATASET_KEYWORD_TABLES_TABLE_SQL

# jieba 可选依赖
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

# 停用词（常见无意义词）
_STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也',
    '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '他',
    '她', '们', '那', '它', '什么', '怎么', '如何', '可以', '可能', '因为', '所以', '但是',
    '如果', '虽然', '而且', '或者', '我们', '你们', '他们', '它们', '这个', '那个', '这些',
    '那些', '以及', '等等', '之一', '对于', '关于', '通过', '进行', '使用', '已经', '正在',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'shall', 'can',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'is', 'it', 'this', 'that',
    'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'which', 'who', 'whom', 'whose',
    'what', 'how', 'why', 'not', 'no', 'yes', 'all', 'each', 'every', 'both', 'few', 'more',
    'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
    'also', 'there', 'here', 'out', 'up', 'down', 'over', 'under', 'again', 'once', 'about',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among',
}


def ensure_keyword_table():
    """确保关键词表存在"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(DATASET_KEYWORD_TABLES_TABLE_SQL)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _tokenize(text: str) -> List[str]:
    """
    分词：优先 jieba，回退到 2-gram。
    返回过滤后的关键词列表。
    """
    if not text:
        return []

    text = text.strip()
    if not text:
        return []

    tokens = []
    if JIEBA_AVAILABLE:
        tokens = list(jieba.cut(text))
    else:
        # 回退：英文按空格/标点切分，中文 2-gram
        # 英文部分
        en_parts = re.findall(r'[a-zA-Z][a-zA-Z0-9._\-]{1,}', text)
        tokens.extend(en_parts)
        # 中文部分
        zh_parts = re.findall(r'[一-龥]+', text)
        for part in zh_parts:
            if len(part) == 1:
                tokens.append(part)
            else:
                # 2-gram + 完整词
                tokens.append(part)
                for i in range(len(part) - 1):
                    tokens.append(part[i:i + 2])

    # 过滤：去空白、去停用词、去单字（保留有意义的单字）
    result = []
    for t in tokens:
        t = t.strip().lower()
        if not t or len(t) < 1:
            continue
        if t in _STOPWORDS:
            continue
        # 去掉纯标点
        if re.match(r'^[\W_]+$', t):
            continue
        result.append(t)

    return result


def _extract_keywords(text: str, max_keywords: int = 50) -> List[str]:
    """提取关键词（去重，按词频降序，限制数量）"""
    tokens = _tokenize(text)
    freq = Counter(tokens)
    # 按词频降序
    sorted_kw = sorted(freq.items(), key=lambda x: -x[1])
    return [kw for kw, _ in sorted_kw[:max_keywords]]


def build_keyword_index_for_segment(dataset_id: str, segment_id: str, content: str) -> int:
    """
    为单个分段建立关键词索引。

    参数:
        dataset_id: 数据集 ID
        segment_id: 分段 ID
        content: 分段内容

    返回:
        索引的关键词数量
    """
    keywords = _extract_keywords(content)
    if not keywords:
        return 0

    ensure_keyword_table()

    # 先删除旧的索引
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM dataset_keyword_tables WHERE segment_id = %s', (segment_id,))

        # 批量插入
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        n = 0
        for kw in keywords:
            cur.execute(
                'INSERT INTO dataset_keyword_tables (dataset_id, keyword, segment_id, term_frequency, created_at)'
                ' VALUES (%s, %s, %s, %s, %s)'
                ' ON DUPLICATE KEY UPDATE term_frequency = term_frequency + 1',
                (dataset_id, kw[:200], segment_id, 1, now))
            n += 1
        db.commit()
        return n
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


def build_keyword_index_for_dataset(dataset_id: str, batch_size: int = 100) -> int:
    """
    为整个数据集建立关键词索引。

    参数:
        dataset_id: 数据集 ID
        batch_size: 每批处理的分段数

    返回:
        索引的分段数量
    """
    ensure_keyword_table()

    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''
            SELECT id, content FROM dify_document_segments
            WHERE dataset_id = %s AND enabled = 1 AND status = 'completed'
        ''', (dataset_id,))
        segments = cur.fetchall()
    finally:
        db.close()

    # 先清除旧索引
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM dataset_keyword_tables WHERE dataset_id = %s', (dataset_id,))
        db.commit()
    finally:
        db.close()

    n = 0
    for seg in segments:
        count = build_keyword_index_for_segment(dataset_id, seg['id'], seg['content'] or '')
        if count > 0:
            n += 1

    return n


def keyword_search(dataset_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """
    基于关键词表的检索。

    参数:
        dataset_id: 数据集 ID
        query: 查询文本
        top_k: 返回结果数

    返回:
        [{segment_id, score, matched_keywords}, ...] 按分数降序
    """
    if not query:
        return []

    query_keywords = _extract_keywords(query, max_keywords=20)
    if not query_keywords:
        return []

    ensure_keyword_table()

    db = get_db()
    try:
        cur = db.cursor()
        # 使用 IN 查询匹配关键词
        fmt = ','.join(['%s'] * len(query_keywords))
        cur.execute(f'''
            SELECT segment_id, keyword, term_frequency
            FROM dataset_keyword_tables
            WHERE dataset_id = %s AND keyword IN ({fmt})
        ''', [dataset_id] + query_keywords)
        rows = cur.fetchall()
    finally:
        db.close()

    if not rows:
        return []

    # 按 segment 聚合得分
    seg_scores = {}
    seg_keywords = {}
    for r in rows:
        seg_id = r['segment_id']
        tf = r['term_frequency'] or 1
        # 得分：词频加权 + 匹配关键词数量加权
        score = tf * 1.0 + (1.0 if r['keyword'] in query_keywords else 0.5)
        seg_scores[seg_id] = seg_scores.get(seg_id, 0) + score
        if seg_id not in seg_keywords:
            seg_keywords[seg_id] = []
        seg_keywords[seg_id].append(r['keyword'])

    # 归一化并排序
    max_score = max(seg_scores.values()) if seg_scores else 1
    results = []
    for seg_id, score in sorted(seg_scores.items(), key=lambda x: -x[1])[:top_k]:
        results.append({
            'segment_id': seg_id,
            'score': score / max_score,  # 归一化到 0-1
            'matched_keywords': seg_keywords.get(seg_id, []),
        })

    return results


def hybrid_search(dataset_id: str, query: str, vector_results: List[Dict],
                  top_k: int = 5, vector_weight: float = 0.7) -> List[Dict]:
    """
    混合检索：向量结果 + 关键词结果加权合并。

    参数:
        dataset_id: 数据集 ID
        query: 查询文本
        vector_results: 向量搜索结果 [{id, content, score, ...}]
        top_k: 返回结果数
        vector_weight: 向量权重（0-1，默认 0.7）

    返回:
        合并后的结果列表（含混合分数）
    """
    kw_results = keyword_search(dataset_id, query, top_k=top_k * 2)
    kw_weight = 1.0 - vector_weight

    # 合并分数
    merged = {}

    # 向量结果
    for idx, r in enumerate(vector_results):
        seg_id = r.get('id', '')
        if not seg_id:
            continue
        vec_score = r.get('score', 0)
        # 位置加权（越靠前越高）
        position_boost = 1.0 - (idx / max(len(vector_results), 1)) * 0.2
        merged[seg_id] = {
            'id': seg_id,
            'content': r.get('content', ''),
            'score': vec_score,
            'vector_score': vec_score,
            'keyword_score': 0,
            'hybrid_score': vec_score * vector_weight * position_boost,
            'dataset_id': r.get('dataset_id', ''),
            'document_id': r.get('document_id', ''),
        }

    # 关键词结果
    for r in kw_results:
        seg_id = r['segment_id']
        kw_score = r['score']
        if seg_id in merged:
            merged[seg_id]['keyword_score'] = kw_score
            merged[seg_id]['hybrid_score'] += kw_score * kw_weight
        else:
            merged[seg_id] = {
                'id': seg_id,
                'content': '',
                'score': 0,
                'vector_score': 0,
                'keyword_score': kw_score,
                'hybrid_score': kw_score * kw_weight,
                'dataset_id': '',
                'document_id': '',
            }

    # 补充 content
    seg_ids = [r['id'] for r in merged.values() if not r['content']]
    if seg_ids:
        db = get_db()
        try:
            cur = db.cursor()
            fmt = ','.join(['%s'] * len(seg_ids))
            # MySQLdb 需要元组参数（列表会被当作单个值进行 % 格式化）
            cur.execute(f'SELECT id, content, dataset_id, document_id FROM dify_document_segments WHERE id IN ({fmt})', tuple(seg_ids))
            info = {r['id']: r for r in cur.fetchall()}
            for r in merged.values():
                if not r['content'] and r['id'] in info:
                    r['content'] = info[r['id']]['content']
                    r['dataset_id'] = info[r['id']]['dataset_id']
                    r['document_id'] = info[r['id']]['document_id']
        finally:
            db.close()

    # 按混合分数排序
    results = sorted(merged.values(), key=lambda x: -x['hybrid_score'])[:top_k]
    # 用混合分数替代原分数
    for r in results:
        r['score'] = r['hybrid_score']
    return results


def get_keyword_stats(dataset_id: str) -> Dict:
    """获取数据集关键词统计"""
    ensure_keyword_table()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT COUNT(DISTINCT keyword) AS kw_count, COUNT(DISTINCT segment_id) AS seg_count FROM dataset_keyword_tables WHERE dataset_id = %s', (dataset_id,))
        row = cur.fetchone()
        return {
            'keyword_count': row['kw_count'] if row else 0,
            'indexed_segments': row['seg_count'] if row else 0,
        }
    finally:
        db.close()

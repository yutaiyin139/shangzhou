# -*- coding: utf-8 -*-
"""
向量存储模块 —— 基于 Qdrant 的高性能向量检索

功能：
1. 向量 CRUD（插入/更新/删除/查询）
2. 相似度搜索（Cosine/Dot/Euclidean）
3. 批量操作
4. 混合检索（向量 + 关键词）
5. 集合管理

依赖：qdrant-client（可选，未安装时回退到 MySQL 实现）
"""

import json
import uuid
import time
import math
from typing import List, Dict, Optional, Tuple, Any

# 尝试导入 qdrant_client，未安装时使用回退方案
_QDRANT_AVAILABLE = False
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchText, MatchValue,
        ScoredPoint, UpdateStatus,
        PointIdsList,
    )
    _QDRANT_AVAILABLE = True
except ImportError:
    QdrantClient = None
    Distance = VectorParams = PointStruct = None
    Filter = FieldCondition = MatchText = MatchValue = None

from config import get_db


class VectorStore:
    """
    向量存储类 —— 封装 Qdrant 操作，提供统一的向量检索接口。

    使用方式：
        store = VectorStore()
        store.create_collection("my_collection", vector_size=1536)
        store.upsert("my_collection", vectors=[[0.1, 0.2, ...]], payloads=[{"text": "..."}])
        results = store.search("my_collection", query_vector=[0.1, 0.2, ...], limit=5)
    """

    def __init__(self, host: str = 'localhost', port: int = 6333, use_qdrant: bool = True):
        """
        初始化向量存储。

        参数:
        - host: Qdrant 服务地址
        - port: Qdrant HTTP 端口
        - use_qdrant: 是否使用 Qdrant（False 则使用 MySQL 回退）
        """
        self._client = None
        self._use_qdrant = use_qdrant and _QDRANT_AVAILABLE
        self._host = host
        self._port = port

        if self._use_qdrant:
            try:
                self._client = QdrantClient(host=host, port=port, timeout=10)
                # 测试连接
                self._client.get_collections()
            except Exception as e:
                print(f'[VectorStore] Qdrant 连接失败 ({e})，回退到 MySQL 模式')
                self._client = None
                self._use_qdrant = False

    @property
    def backend(self) -> str:
        """返回当前使用的后端名称"""
        return 'qdrant' if self._use_qdrant else 'mysql'

    @property
    def is_available(self) -> bool:
        """检查向量存储是否可用"""
        if self._use_qdrant and self._client:
            try:
                self._client.get_collections()
                return True
            except Exception:
                return False
        return True  # MySQL 总是可用

    def create_collection(
        self,
        name: str,
        vector_size: int = 1536,
        distance: str = 'cosine',
        on_disk: bool = False
    ) -> bool:
        """
        创建向量集合。

        参数:
        - name: 集合名称
        - vector_size: 向量维度
        - distance: 距离度量（cosine/dot/euclidean）
        - on_disk: 是否存储在磁盘（大数据集时推荐）

        返回:
        - bool: 是否创建成功
        """
        if self._use_qdrant and self._client:
            return self._create_collection_qdrant(name, vector_size, distance, on_disk)
        return self._create_collection_mysql(name, vector_size, distance)

    def get_declared_dim(self, name: str) -> Optional[int]:
        """对外接口：读取集合已声明的向量维度（非 Qdrant 后端或读不到返回 None）"""
        if not (self._use_qdrant and self._client):
            return None
        return self._collection_dim(name)

    def _collection_dim(self, name: str) -> Optional[int]:
        """读取 Qdrant 集合已声明的向量维度（读不到返回 None）"""
        try:
            info = self._client.get_collection(collection_name=name)
            size = getattr(getattr(info.config.params, 'vectors', None), 'size', None)
            return int(size) if size else None
        except Exception:
            return None

    def _create_collection_qdrant(self, name, vector_size, distance, on_disk):
        """Qdrant: 创建集合（已存在且维度不符时重建，否则旧集合无法写入新向量）"""
        try:
            # 检查集合是否已存在
            collections = self._client.get_collections().collections
            if any(c.name == name for c in collections):
                existing_dim = self._collection_dim(name)
                if existing_dim is not None and existing_dim != int(vector_size):
                    # 维度漂移（如 embedding 模型从本地 384 维切换到通义 1024 维），
                    # 旧集合继续写入会持续 400，只能重建（旧向量本身已不可用）
                    print(f'[VectorStore] 集合 {name} 维度 {existing_dim} != {vector_size}，重建集合')
                    self._client.delete_collection(collection_name=name)
                else:
                    return True

            # 距离度量映射
            distance_map = {
                'cosine': Distance.COSINE,
                'dot': Distance.DOT,
                'euclidean': Distance.EUCLID,
            }
            dist = distance_map.get(distance.lower(), Distance.COSINE)

            # 创建集合
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=dist,
                    on_disk=on_disk
                )
            )
            return True
        except Exception as e:
            print(f'[VectorStore] 创建集合失败: {e}')
            return False

    def _create_collection_mysql(self, name, vector_size, distance):
        """MySQL: 创建集合元数据记录"""
        db = get_db()
        try:
            cur = db.cursor()
            # 使用 vector_collections 表记录集合元数据
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vector_collections (
                    name VARCHAR(255) PRIMARY KEY,
                    vector_size INT NOT NULL DEFAULT 1536,
                    distance VARCHAR(20) DEFAULT 'cosine',
                    point_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cur.execute('''
                INSERT IGNORE INTO vector_collections (name, vector_size, distance)
                VALUES (%s, %s, %s)
            ''', (name, vector_size, distance))
            db.commit()
            return True
        except Exception as e:
            print(f'[VectorStore] 创建集合元数据失败: {e}')
            return False
        finally:
            db.close()

    def upsert(
        self,
        collection: str,
        vectors: List[List[float]],
        payloads: List[Dict] = None,
        ids: List[str] = None
    ) -> bool:
        """
        插入或更新向量。

        参数:
        - collection: 集合名称
        - vectors: 向量列表
        - payloads: 关联数据列表（与 vectors 一一对应）
        - ids: 自定义 ID 列表（可选，默认自动生成 UUID）

        返回:
        - bool: 是否成功
        """
        if not vectors:
            return True

        if self._use_qdrant and self._client:
            return self._upsert_qdrant(collection, vectors, payloads, ids)
        return self._upsert_mysql(collection, vectors, payloads, ids)

    def _upsert_qdrant(self, collection, vectors, payloads, ids):
        """Qdrant: 插入/更新向量（兼容新版 qdrant-client）"""
        try:
            points = []
            for i, vector in enumerate(vectors):
                point_id = ids[i] if ids and i < len(ids) else str(uuid.uuid4())
                payload = payloads[i] if payloads and i < len(payloads) else {}
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                ))

            result = self._client.upsert(
                collection_name=collection,
                points=points,
                wait=True
            )
            # 兼容新旧版本返回结构
            status = getattr(result, 'status', None)
            return status == UpdateStatus.COMPLETED or status is None
        except Exception as e:
            print(f'[VectorStore] upsert 失败: {e}')
            return False

    def _upsert_mysql(self, collection, vectors, payloads, ids):
        """MySQL: 存储向量到 document_segments 表"""
        db = get_db()
        try:
            cur = db.cursor()
            for i, vector in enumerate(vectors):
                segment_id = ids[i] if ids and i < len(ids) else str(uuid.uuid4())
                payload = payloads[i] if payloads and i < len(payloads) else {}

                # 获取 dataset_id 和 content
                dataset_id = payload.get('dataset_id', '')
                content = payload.get('content', '')

                # 检查是否已存在
                cur.execute(
                    'SELECT id FROM dify_document_segments WHERE id = %s',
                    (segment_id,)
                )
                if cur.fetchone():
                    # 更新
                    cur.execute('''
                        UPDATE dify_document_segments
                        SET embedding = %s,
                            embedding_model = %s,
                            embedding_status = 'completed',
                            content = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    ''', (
                        json.dumps(vector),
                        payload.get('embedding_model', 'unknown'),
                        content,
                        segment_id
                    ))
                else:
                    # 插入
                    cur.execute('''
                        INSERT INTO dify_document_segments
                        (id, tenant_id, dataset_id, document_id, position,
                         content, embedding, embedding_model, embedding_status,
                         word_count, tokens, hit_count, status, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'completed',
                                %s, %s, 0, 'completed', %s)
                    ''', (
                        segment_id,
                        payload.get('tenant_id', ''),
                        dataset_id,
                        payload.get('document_id', ''),
                        payload.get('position', 0),
                        content,
                        json.dumps(vector),
                        payload.get('embedding_model', 'unknown'),
                        len(content.replace(' ', '')),
                        max(1, int(len(content) / 3)),
                        payload.get('created_by', '')
                    ))

            db.commit()
            return True
        except Exception as e:
            print(f'[VectorStore] MySQL upsert 失败: {e}')
            db.rollback()
            return False
        finally:
            db.close()

    def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 5,
        min_score: float = 0.0,
        filter_conditions: Dict = None
    ) -> List[Dict]:
        """
        向量相似度搜索。

        参数:
        - collection: 集合名称
        - query_vector: 查询向量
        - limit: 返回结果数量
        - min_score: 最低相似度阈值
        - filter_conditions: 过滤条件（如 {"dataset_id": "xxx"}）

        返回:
        - list: 搜索结果列表 [{id, score, payload}]
        """
        if not query_vector:
            return []

        if self._use_qdrant and self._client:
            return self._search_qdrant(collection, query_vector, limit, min_score, filter_conditions)
        return self._search_mysql(collection, query_vector, limit, min_score, filter_conditions)

    def _search_qdrant(self, collection, query_vector, limit, min_score, filter_conditions):
        """Qdrant: 向量搜索（兼容新版 qdrant-client: query_points）"""
        try:
            # 构建过滤条件
            qdrant_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    if isinstance(value, list):
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value[0]) if len(value) == 1
                            else FieldCondition(key=key, match=MatchText(any=[str(v) for v in value])))
                        )
                    else:
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            # 新版 qdrant-client 用 query_points 替代 search
            if hasattr(self._client, 'query_points'):
                result = self._client.query_points(
                    collection_name=collection,
                    query=query_vector,
                    query_filter=qdrant_filter,
                    limit=limit,
                    score_threshold=min_score,
                    with_payload=True,
                    with_vectors=False,
                )
                # query_points 返回 (points, next_page_offset)
                points = result[0] if isinstance(result, tuple) else result.points
            else:
                # 旧版兼容
                points = self._client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    query_filter=qdrant_filter,
                    limit=limit,
                    score_threshold=min_score,
                    with_payload=True,
                    with_vectors=False,
                )

            return [
                {
                    'id': str(hit.id),
                    'score': hit.score,
                    'payload': hit.payload or {},
                }
                for hit in points
            ]
        except Exception as e:
            print(f'[VectorStore] Qdrant 搜索失败: {e}')
            return []

    def _search_mysql(self, collection, query_vector, limit, min_score, filter_conditions):
        """MySQL: 内存余弦相似度搜索"""
        db = get_db()
        try:
            cur = db.cursor()

            # 构建查询条件
            where_clauses = ["embedding IS NOT NULL", "embedding_status = 'completed'", "enabled = 1"]
            params = []

            if filter_conditions:
                if 'dataset_id' in filter_conditions:
                    dataset_id = filter_conditions['dataset_id']
                    if isinstance(dataset_id, list):
                        placeholders = ','.join(['%s'] * len(dataset_id))
                        where_clauses.append(f'dataset_id IN ({placeholders})')
                        params.extend(dataset_id)
                    else:
                        where_clauses.append('dataset_id = %s')
                        params.append(dataset_id)

            sql = f'''
                SELECT id, content, embedding
                FROM dify_document_segments
                WHERE {' AND '.join(where_clauses)}
                LIMIT 500
            '''
            cur.execute(sql, params)
            rows = cur.fetchall()
        finally:
            db.close()

        # 计算余弦相似度
        results = []
        dim = len(query_vector)
        for row in rows:
            try:
                emb = json.loads(row['embedding']) if row['embedding'] else []
            except (json.JSONDecodeError, TypeError):
                continue

            if len(emb) != dim:
                continue

            score = self._cosine_similarity(query_vector, emb)
            if score >= min_score:
                results.append({
                    'id': row['id'],
                    'score': score,
                    'payload': {'content': row['content']},
                    'content': row['content'],
                })

        # 按相似度降序排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    def delete_collection(self, collection: str) -> bool:
        """删除集合"""
        if self._use_qdrant and self._client:
            try:
                self._client.delete_collection(collection_name=collection)
                return True
            except Exception:
                return False
        return True

    def get_collection_info(self, collection: str) -> Optional[Dict]:
        """获取集合信息"""
        if self._use_qdrant and self._client:
            try:
                info = self._client.get_collection(collection_name=collection)
                return {
                    'name': collection,
                    'points_count': info.points_count,
                    'vectors_config': str(info.config.params.vectors),
                    'backend': 'qdrant',
                }
            except Exception:
                return None
        return None

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        if self._use_qdrant and self._client:
            try:
                collections = self._client.get_collections().collections
                return [c.name for c in collections]
            except Exception:
                return []
        return []

    def delete_points(self, collection: str, point_ids: List[str]) -> bool:
        """删除指定点（按 ID）"""
        if self._use_qdrant and self._client:
            try:
                from qdrant_client.models import PointIdsList
                self._client.delete(
                    collection_name=collection,
                    points_selector=PointIdsList(points=point_ids),
                    wait=True
                )
                return True
            except Exception:
                return False
        return True

    def delete_points_by_filter(self, collection: str, qdrant_filter) -> bool:
        """按过滤条件删除点（新版 API 推荐方式）"""
        if self._use_qdrant and self._client:
            try:
                self._client.delete(
                    collection_name=collection,
                    points_selector=qdrant_filter,
                    wait=True
                )
                return True
            except Exception:
                return False
        return True

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# ============================================================
# 全局单例
# ============================================================

_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """获取向量存储全局单例"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance

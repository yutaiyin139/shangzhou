# -*- coding: utf-8 -*-
"""
图调度器 —— Dify 式「动态就绪调度」

取代旧的「一次性静态拓扑排序 + 事后删边重算」方案。旧方案有两个致命问题：
1. 分支命中后重算拓扑时，被剪掉的分支节点入度归零，被当成根节点重新执行
   （实测：IF/ELSE 的两条分支都会被执行）；
2. 分支过滤依赖 sourceHandle == 'case-{branch}'，与前端画布实际产生的句柄完全脱节。

新模型的三个要点：
- 就绪判定：节点仅在「所有入边的来源都已落定（执行完成 / 已失活）」且「至少一条入边
  被真正激活（信号到达）」时才就绪；无入边的根节点直接就绪。
- 可达性剪枝：路由节点（if-else / 问题分类）命中某分支后，未命中句柄的出边标记为失活，
  失活信号沿下游传播；全部入边都失活的节点整体失活，永不执行，也不会被当成根节点。
- 生命周期不可逆：已执行 / 已失活的节点不会因后续路由重新评估而回到可执行集合。
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================
# 句柄（handle）命名契约
# ============================================================
# 前端 WfNode.vue 为条件分支节点的每个 case 渲染 <Handle :id="case.id">，
# 因此画布产生的边满足 sourceHandle == case.id（默认 case id 为 'true' / 'false'）。
#
# 兼容以下历史写法：
#   - 'case-{branch_id}'：Dify DSL / 早期熵舟引擎约定
#   - 'yes' / 'no'      ：早期熵舟前端硬编码句柄（yes→首个分支，no→末个分支）
#   - null / ''         ：未标注句柄的边，视为普通边（不参与分支过滤）

HANDLE_CASE_PREFIX = 'case-'

# 兜底句柄：始终视为命中（用于未做分支标注的历史图）
HANDLE_ALWAYS_ACTIVE = (None, '', 'source', 'default')

# 旧版前端硬编码句柄 → 分支位置别名
LEGACY_HANDLE_ALIAS = {'yes': 'first', 'no': 'last'}


def branch_ids_of(node_data):
    """返回路由节点的可路由句柄集合（分支 id 列表，按声明顺序）。非路由节点返回 []。"""
    node_type = (node_data or {}).get('type', '')
    if node_type == 'if-else':
        cases = node_data.get('cases') or []
        ids = [str(c.get('id')) for c in cases if c.get('id') is not None]
        if not ids:
            ids = [str(i) for i in range(len(cases))]
        return ids
    if node_type == 'question-classifier':
        classes = node_data.get('classes') or []
        return [str(c.get('id')) for c in classes if c.get('id') is not None]
    return []


def normalize_handle(source_handle, ordered_branch_ids):
    """把边的 sourceHandle 归一化为分支 id；无法归一化时返回 None（表示普通边）。"""
    if source_handle in HANDLE_ALWAYS_ACTIVE:
        return None
    handle = str(source_handle)
    if handle.startswith(HANDLE_CASE_PREFIX):
        return handle[len(HANDLE_CASE_PREFIX):]
    if handle in ordered_branch_ids:
        return handle
    # 旧版前端 yes/no 句柄：按分支声明顺序映射
    if ordered_branch_ids:
        alias = LEGACY_HANDLE_ALIAS.get(handle)
        if alias == 'first':
            return ordered_branch_ids[0]
        if alias == 'last':
            return ordered_branch_ids[-1]
    return None


def build_routing_map(main_nodes):
    """按节点收集路由信息：{node_id: {'branch_ids': [...]}}。"""
    routing_map = {}
    for node in main_nodes:
        branch_ids = branch_ids_of(node.get('data', {}))
        if branch_ids:
            routing_map[node['id']] = {'branch_ids': branch_ids}
    return routing_map


class GraphScheduler:
    """动态就绪调度器（详见模块文档）。"""

    def __init__(self, node_map, edges, routing_map=None, executed=None, branches=None):
        self.node_ids = list(node_map.keys())
        self.node_map = node_map
        self.routing_map = routing_map or {}

        self.out_edges = {nid: [] for nid in self.node_ids}
        self.in_edges = {nid: [] for nid in self.node_ids}
        self.edge_handle = {}
        for idx, edge in enumerate(edges):
            src = edge.get('source')
            tgt = edge.get('target')
            if src not in self.out_edges or tgt not in self.in_edges:
                continue
            key = (src, tgt, idx)
            self.out_edges[src].append(key)
            self.in_edges[tgt].append(key)
            self.edge_handle[key] = edge.get('sourceHandle')

        # 边状态：句柄归一化结果 + 是否已激活 / 已失活
        self.edge_branch = {key: normalize_handle(self.edge_handle[key],
                                                  self._ordered_branch_ids(key[0]))
                            for key in self.edge_handle}
        self.edge_fired = {key: False for key in self.edge_handle}
        self.edge_dead = {key: False for key in self.edge_handle}

        self.executed = set(executed or [])
        self.branches = dict(branches or {})
        self.dead = set()

        # 恢复历史执行状态：已执行节点的出边按已记录的分支决策重新落定
        # （不重复执行、不重新决策，保证暂停/恢复与首次执行的路由结果一致）
        for nid in self.node_ids:
            if nid in self.executed:
                self.on_executed(nid, self.branches.get(nid), replay=True)

    # ---------------- 查询 ----------------

    def _ordered_branch_ids(self, src):
        return (self.routing_map.get(src) or {}).get('branch_ids') or []

    def is_routing(self, node_id):
        return bool(self._ordered_branch_ids(node_id))

    def next_ready(self):
        """返回下一个就绪节点（按图内声明顺序，保证执行序稳定）；无则返回 None。"""
        for nid in self.node_ids:
            if nid in self.executed or nid in self.dead:
                continue
            if self._is_ready(nid):
                return nid
        return None

    def remaining(self):
        """既未执行也未失活的节点（调度正常结束后即为成环/死锁节点）。"""
        return [nid for nid in self.node_ids
                if nid not in self.executed and nid not in self.dead]

    def skipped_nodes(self):
        """被可达性剪枝掉的节点。"""
        return [nid for nid in self.node_ids if nid in self.dead]

    def decide_branch(self, node_id, outputs):
        """从节点输出解析本次命中的分支句柄（无分支决策时返回 None）。"""
        if not self.is_routing(node_id) or not isinstance(outputs, dict):
            return None
        branch = outputs.get('__branch__')
        if branch is None:
            branch = outputs.get('__if_else_branch__')
        if branch is None:
            branch = outputs.get('class_id')
        return None if branch is None else str(branch)

    # ---------------- 状态迁移 ----------------

    def on_executed(self, node_id, branch=None, replay=False):
        """节点执行完成：命中分支的出边激活，未命中的出边失活并向下游传播。"""
        if node_id not in self.executed:
            self.executed.add(node_id)
        if branch is not None:
            self.branches[node_id] = branch
        elif replay:
            branch = self.branches.get(node_id)

        keys = self.out_edges.get(node_id, [])
        routed_keys = [k for k in keys if self.edge_branch[k] is not None]

        if self.is_routing(node_id) and routed_keys:
            matched = [k for k in routed_keys if self.edge_branch[k] == branch]
            if not matched:
                # 图中没有与命中分支对应的句柄（历史数据缺标注）→ 全分支放行，
                # 保持旧行为，避免把整个下游剪成空图。
                logger.warning('路由节点 %s 命中分支 %r，但未找到匹配句柄的出边，按全分支放行',
                               node_id, branch)
                matched = routed_keys
            dead_keys = [k for k in routed_keys if k not in matched]
        else:
            dead_keys, matched = [], keys

        for key in matched:
            self._fire_edge(key)
        for key in dead_keys:
            self._kill_edge(key)

    def on_failed(self, node_id):
        """节点执行失败：出边全部失活，下游不再执行。"""
        if node_id not in self.executed:
            self.executed.add(node_id)
        for key in self.out_edges.get(node_id, []):
            self._kill_edge(key)

    def _fire_edge(self, key):
        if self.edge_fired[key] or self.edge_dead[key]:
            return
        self.edge_fired[key] = True

    def _kill_edge(self, key):
        if self.edge_dead[key] or self.edge_fired[key]:
            return
        self.edge_dead[key] = True
        target = key[1]
        if target in self.executed or target in self.dead:
            return
        if not self._has_live_pending_in(target):
            self._kill_node(target)

    def _kill_node(self, node_id):
        """节点整体不可达：沿其出边继续传播失活（可达性剪枝）。"""
        if node_id in self.dead or node_id in self.executed:
            return
        self.dead.add(node_id)
        for key in self.out_edges.get(node_id, []):
            self._kill_edge(key)

    def _has_live_pending_in(self, node_id):
        """是否存在仍可能激活的入边（来源尚未落定）。"""
        for key in self.in_edges.get(node_id, []):
            if self.edge_fired[key] or self.edge_dead[key]:
                continue
            if key[0] not in self.executed and key[0] not in self.dead:
                return True
        return False

    def _is_ready(self, node_id):
        incoming = self.in_edges.get(node_id, [])
        if not incoming:
            return True
        fired = 0
        for key in incoming:
            src = key[0]
            if self.edge_dead[key]:
                continue
            if self.edge_fired[key]:
                fired += 1
                continue
            # 来源尚未落定 → 还需等待
            if src not in self.executed and src not in self.dead:
                return False
        # 所有入边都落定，但没有任何一条被激活 → 不可达
        return fired > 0


def build_scheduler(node_map, main_nodes, main_edges, executed=None, branches=None):
    """构造调度器（集中处理句柄归一化所需的分支声明顺序）。"""
    return GraphScheduler(node_map, main_edges, build_routing_map(main_nodes),
                          executed=executed, branches=branches)

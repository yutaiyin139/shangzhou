import { getNodeType } from './nodeRegistry'

/** 位置坐标 */
interface Position {
  x: number
  y: number
}

/** 原始节点 */
interface RawNode {
  id: string
  type?: string
  position?: Position
  width?: number
  height?: number
  sourcePosition?: string
  targetPosition?: string
  data?: Record<string, unknown>
  [key: string]: unknown
}

/** 原始边 */
interface RawEdge {
  id?: string
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  data?: Record<string, unknown>
  [key: string]: unknown
}

/** 原始图 */
interface RawGraph {
  nodes?: RawNode[]
  edges?: RawEdge[]
  viewport?: { x?: number; y?: number; zoom?: number }
}

/** Vue Flow 节点 */
interface VueFlowNode {
  id: string
  type: string
  position: Position
  width?: number
  height?: number
  sourcePosition?: string
  targetPosition?: string
  data: Record<string, unknown>
}

/** Vue Flow 边 */
interface VueFlowEdge {
  id: string
  source: string
  target: string
  sourceHandle: string | null
  targetHandle: string | null
  type: string
  animated: boolean
  data: Record<string, unknown>
}

/** 转换后的元素 */
interface FlowElements {
  nodes: VueFlowNode[]
  edges: VueFlowEdge[]
}

/**
 * 把平台 workflows.graph JSON 转换成 Vue Flow 可用的 elements
 */
export function graphToElements(graph: RawGraph = {}): FlowElements {
  const rawNodes = graph.nodes || []
  const rawEdges = graph.edges || []

  const nodes: VueFlowNode[] = rawNodes.map(n => {
    const data = (n.data || {}) as Record<string, unknown>
    const nodeType = (data.type as string) || n.type || 'custom'
    const meta = getNodeType(nodeType)
    return {
      id: n.id,
      type: 'wf-node',
      position: n.position || { x: 0, y: 0 },
      width: n.width || 240,
      height: n.height || (meta.outputs === 0 ? 70 : 90),
      sourcePosition: n.sourcePosition || 'right',
      targetPosition: n.targetPosition || 'left',
      data: {
        ...data,
        _type: nodeType,
        _title: (data.title as string) || meta.title,
        _icon: meta.icon,
        _color: meta.color
      }
    }
  })

  const edges: VueFlowEdge[] = rawEdges.map(e => ({
    id: e.id || `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle || null,
    targetHandle: e.targetHandle || null,
    type: 'default',
    animated: false,
    data: e.data || {}
  }))

  return { nodes, edges }
}

/**
 * 把 Vue Flow 的 nodes/edges 转回平台 graph JSON
 */
export function elementsToGraph(
  nodes: VueFlowNode[],
  edges: VueFlowEdge[],
  viewport: { x?: number; y?: number; zoom?: number } = {}
): RawGraph {
  const rawNodes: RawNode[] = nodes.map(n => {
    const { _type, _title, _icon, _color, ...data } = n.data
    return {
      id: n.id,
      type: 'custom',
      position: n.position,
      width: n.width || 240,
      height: n.height || 90,
      positionAbsolute: n.position,
      selected: false,
      sourcePosition: n.sourcePosition || 'right',
      targetPosition: n.targetPosition || 'left',
      data: {
        ...data,
        type: _type,
        title: (data.title as string) || _title
      }
    }
  })

  const rawEdges: RawEdge[] = edges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
    type: 'custom',
    zIndex: 0,
    data: e.data || {}
  }))

  return {
    nodes: rawNodes,
    edges: rawEdges,
    viewport: { x: viewport.x ?? 0, y: viewport.y ?? 0, zoom: viewport.zoom ?? 1 }
  }
}

/**
 * 生成一个新的节点 ID（时间戳 + 随机数）
 */
export function newNodeId(): string {
  return Date.now().toString() + Math.floor(Math.random() * 1000).toString()
}

/**
 * 把 library 拖拽数据转成 Vue Flow node
 */
export function createVueFlowNode(type: string, position: Position): VueFlowNode {
  const meta = getNodeType(type)
  // 深拷贝 defaultData：meta 是模块级单例，浅拷贝会让同类型新建节点共享
  // 嵌套对象/数组（model、prompt_template、dataset_ids…），编辑一个会污染另一个。
  const defaults = JSON.parse(JSON.stringify(meta.defaultData || {}))
  return {
    id: newNodeId(),
    type: 'wf-node',
    position,
    data: {
      ...defaults,
      _type: type,
      _title: meta.title,
      _icon: meta.icon,
      _color: meta.color
    }
  }
}

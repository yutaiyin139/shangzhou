import * as dagre from 'dagre'

/** 节点接口 */
interface LayoutNode {
  id: string
  width?: number
  height?: number
  position?: { x: number; y: number }
  [key: string]: unknown
}

/** 边接口 */
interface LayoutEdge {
  source: string
  target: string
}

/** 布局选项 */
interface LayoutOptions {
  rankdir?: string
  nodesep?: number
  ranksep?: number
  marginx?: number
  marginy?: number
  nodeWidth?: number
  nodeHeight?: number
}

/**
 * 使用 dagre 对 nodes/edges 做自动布局，返回新的 nodes（带新 position）
 */
export function autoLayout(nodes: LayoutNode[], edges: LayoutEdge[], options: LayoutOptions = {}): LayoutNode[] {
  if (!nodes || nodes.length === 0) return nodes
  // dagre 类型复杂，使用 any 断言避免类型冲突
  const g = new dagre.graphlib.Graph() as any
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: options.rankdir || 'LR',
    nodesep: 40,
    ranksep: 80,
    marginx: 20,
    marginy: 20
  })

  const nodeWidth = options.nodeWidth || 240
  const nodeHeight = options.nodeHeight || 90

  nodes.forEach(n => {
    const id = n.id
    g.setNode(id, { width: n.width || nodeWidth, height: n.height || nodeHeight })
  })
  edges.forEach(e => {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target)
    }
  })

  dagre.layout(g)

  return nodes.map(n => {
    const pos = g.node(n.id)
    if (!pos) return n
    return {
      ...n,
      position: {
        x: pos.x - (n.width || nodeWidth) / 2,
        y: pos.y - (n.height || nodeHeight) / 2
      }
    }
  })
}

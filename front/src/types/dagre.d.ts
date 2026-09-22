/* ============ dagre 类型声明 ============
 * dagre 是一个 JavaScript 库，没有官方 @types 包
 * 提供完整的类型声明以支持 TypeScript 编译
 */

declare module 'dagre' {
  /** 图配置 */
  interface GraphLabel {
    rankdir?: string
    nodesep?: number
    ranksep?: number
    marginx?: number
    marginy?: number
    [key: string]: unknown
  }

  /** 节点配置 */
  interface NodeLabel {
    width?: number
    height?: number
    [key: string]: unknown
  }

  /** 边配置 */
  interface EdgeLabel {
    [key: string]: unknown
  }

  /** 节点位置 */
  interface NodePosition {
    x: number
    y: number
    width?: number
    height?: number
  }

  /** dagre 图实例 */
  interface DagreGraph {
    setNode(id: string, label?: NodeLabel): DagreGraph
    setEdge(source: string, target: string, label?: EdgeLabel): DagreGraph
    hasNode(id: string): boolean
    node(id: string): NodePosition | undefined
    setDefaultEdgeLabel(callback: () => EdgeLabel): DagreGraph
    setGraph(label: GraphLabel): DagreGraph
  }

  namespace graphlib {
    class Graph {
      constructor(options?: Record<string, unknown>)
    }
  }

  function layout(graph: DagreGraph): void
  function graphlib(): { Graph: new (options?: Record<string, unknown>) => unknown }

  export { layout, graphlib, GraphLabel, NodeLabel, EdgeLabel, DagreGraph }
}

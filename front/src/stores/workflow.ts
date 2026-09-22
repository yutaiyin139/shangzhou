/* ============ 工作流状态管理 ============
 *
 * 管理工作流编辑器的状态：节点、边、选中状态、历史记录
 */
import { defineStore } from 'pinia'
import { ref, computed, Ref } from 'vue'

/** 工作流节点接口 */
interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
  [key: string]: unknown
}

/** 工作流边接口 */
interface WorkflowEdge {
  id: string
  source: string
  target: string
  [key: string]: unknown
}

/** 工作流变量接口 */
interface WorkflowVariable {
  name: string
  type?: string
  default?: unknown
  [key: string]: unknown
}

/** 运行日志接口 */
interface RunLog {
  timestamp: string
  [key: string]: unknown
}

/** 历史记录接口 */
interface HistoryEntry {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export const useWorkflowStore = defineStore('workflow', () => {
  // ============ State ============

  // 工作流基本信息
  const workflowId = ref('')
  const workflowName = ref('')
  const workflowDescription = ref('')

  // 画布数据
  const nodes: Ref<WorkflowNode[]> = ref([])
  const edges: Ref<WorkflowEdge[]> = ref([])

  // 选中状态
  const selectedNodeId = ref<string | null>(null)
  const selectedEdgeId = ref<string | null>(null)

  // 历史记录（用于撤销/重做）
  const history: Ref<HistoryEntry[]> = ref([])
  const historyIndex = ref(-1)
  const maxHistorySize = 50

  // 运行状态
  const isRunning = ref(false)
  const runLogs: Ref<RunLog[]> = ref([])

  // 变量定义
  const variables: Ref<WorkflowVariable[]> = ref([])

  // 版本信息
  const versions: Ref<unknown[]> = ref([])
  const currentVersion = ref<unknown>(null)

  // 是否已保存
  const isDirty = ref(false)

  // ============ Getters ============

  const nodeCount = computed(() => nodes.value.length)
  const edgeCount = computed(() => edges.value.length)

  const selectedNode = computed(() => {
    if (!selectedNodeId.value) return null
    return nodes.value.find(n => n.id === selectedNodeId.value) || null
  })

  const selectedEdge = computed(() => {
    if (!selectedEdgeId.value) return null
    return edges.value.find(e => e.id === selectedEdgeId.value) || null
  })

  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value < history.value.length - 1)

  const nodeIds = computed(() => nodes.value.map(n => n.id))

  // ============ Actions ============

  /**
   * 设置工作流信息
   */
  function setWorkflow(id: string, name: string, description?: string): void {
    workflowId.value = id
    workflowName.value = name
    workflowDescription.value = description || ''
    isDirty.value = false
  }

  /**
   * 添加节点
   */
  function addNode(node: WorkflowNode): void {
    nodes.value.push(node)
    _saveHistory()
    isDirty.value = true
  }

  /**
   * 更新节点
   */
  function updateNode(id: string, data: Partial<WorkflowNode>): void {
    const idx = nodes.value.findIndex(n => n.id === id)
    if (idx > -1) {
      nodes.value[idx] = { ...nodes.value[idx], ...data }
      isDirty.value = true
    }
  }

  /**
   * 删除节点（同时删除关联的边）
   */
  function removeNode(id: string): void {
    nodes.value = nodes.value.filter(n => n.id !== id)
    edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
    if (selectedNodeId.value === id) selectedNodeId.value = null
    _saveHistory()
    isDirty.value = true
  }

  /**
   * 选择节点
   */
  function selectNode(id: string): void {
    selectedNodeId.value = id
    selectedEdgeId.value = null
  }

  /**
   * 添加边
   */
  function addEdge(edge: WorkflowEdge): void {
    edges.value.push(edge)
    isDirty.value = true
  }

  /**
   * 更新边
   */
  function updateEdge(id: string, data: Partial<WorkflowEdge>): void {
    const idx = edges.value.findIndex(e => e.id === id)
    if (idx > -1) {
      edges.value[idx] = { ...edges.value[idx], ...data }
      isDirty.value = true
    }
  }

  /**
   * 删除边
   */
  function removeEdge(id: string): void {
    edges.value = edges.value.filter(e => e.id !== id)
    if (selectedEdgeId.value === id) selectedEdgeId.value = null
    isDirty.value = true
  }

  /**
   * 选择边
   */
  function selectEdge(id: string): void {
    selectedEdgeId.value = id
    selectedNodeId.value = null
  }

  /**
   * 清除选中
   */
  function clearSelection(): void {
    selectedNodeId.value = null
    selectedEdgeId.value = null
  }

  /**
   * 加载工作流数据（替换全部节点和边）
   */
  function loadWorkflow(data: { nodes?: WorkflowNode[]; edges?: WorkflowEdge[]; variables?: WorkflowVariable[] }): void {
    nodes.value = data.nodes || []
    edges.value = data.edges || []
    variables.value = data.variables || []
    _saveHistory()
    isDirty.value = false
  }

  /**
   * 导出工作流数据
   */
  function exportWorkflow(): {
    id: string
    name: string
    description: string
    nodes: WorkflowNode[]
    edges: WorkflowEdge[]
    variables: WorkflowVariable[]
  } {
    return {
      id: workflowId.value,
      name: workflowName.value,
      description: workflowDescription.value,
      nodes: nodes.value,
      edges: edges.value,
      variables: variables.value,
    }
  }

  /**
   * 添加变量
   */
  function addVariable(variable: WorkflowVariable): void {
    variables.value.push(variable)
    isDirty.value = true
  }

  /**
   * 删除变量
   */
  function removeVariable(name: string): void {
    variables.value = variables.value.filter(v => v.name !== name)
    isDirty.value = true
  }

  /**
   * 开始运行
   */
  function startRunning(): void {
    isRunning.value = true
    runLogs.value = []
  }

  /**
   * 添加运行日志
   */
  function addRunLog(log: Record<string, unknown>): void {
    runLogs.value.push({
      timestamp: new Date().toISOString(),
      ...log,
    })
  }

  /**
   * 停止运行
   */
  function stopRunning(): void {
    isRunning.value = false
  }

  /**
   * 撤销
   */
  function undo(): void {
    if (canUndo.value) {
      historyIndex.value--
      _restoreFromHistory()
    }
  }

  /**
   * 重做
   */
  function redo(): void {
    if (canRedo.value) {
      historyIndex.value++
      _restoreFromHistory()
    }
  }

  /**
   * 标记为已保存
   */
  function markSaved(): void {
    isDirty.value = false
  }

  /**
   * 重置工作流状态
   */
  function reset(): void {
    workflowId.value = ''
    workflowName.value = ''
    workflowDescription.value = ''
    nodes.value = []
    edges.value = []
    selectedNodeId.value = null
    selectedEdgeId.value = null
    history.value = []
    historyIndex.value = -1
    isRunning.value = false
    runLogs.value = []
    variables.value = []
    versions.value = []
    currentVersion.value = null
    isDirty.value = false
  }

  // ============ 内部方法 ============

  /**
   * 保存历史记录
   */
  function _saveHistory(): void {
    // 移除当前位置之后的记录（重做历史）
    if (historyIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, historyIndex.value + 1)
    }

    // 添加新记录
    history.value.push({
      nodes: JSON.parse(JSON.stringify(nodes.value)),
      edges: JSON.parse(JSON.stringify(edges.value)),
    })

    // 限制历史记录大小
    if (history.value.length > maxHistorySize) {
      history.value.shift()
    } else {
      historyIndex.value++
    }
  }

  /**
   * 从历史记录恢复
   */
  function _restoreFromHistory(): void {
    const state = history.value[historyIndex.value]
    if (state) {
      nodes.value = JSON.parse(JSON.stringify(state.nodes))
      edges.value = JSON.parse(JSON.stringify(state.edges))
    }
  }

  return {
    // State
    workflowId,
    workflowName,
    workflowDescription,
    nodes,
    edges,
    selectedNodeId,
    selectedEdgeId,
    isRunning,
    runLogs,
    variables,
    versions,
    currentVersion,
    isDirty,

    // Getters
    nodeCount,
    edgeCount,
    selectedNode,
    selectedEdge,
    canUndo,
    canRedo,
    nodeIds,

    // Actions
    setWorkflow,
    addNode,
    updateNode,
    removeNode,
    selectNode,
    addEdge,
    updateEdge,
    removeEdge,
    selectEdge,
    clearSelection,
    loadWorkflow,
    exportWorkflow,
    addVariable,
    removeVariable,
    startRunning,
    addRunLog,
    stopRunning,
    undo,
    redo,
    markSaved,
    reset,
  }
})

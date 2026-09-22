<template>
  <div id="page-root" class="page-root workflow-studio-root">
    <div class="st-wrap">
      <!-- 左窄栏 -->
      <aside class="st-rail">
        <div class="rail-top">
          <a class="rail-back" href="#/workflow-app" title="返回">‹</a>
          <span class="rail-home">🏠</span>
          <span class="rail-sep">/</span>
          <span class="rail-title">工作室</span>
        </div>
        <div class="rail-card">
          <div class="rc-ico" :style="{ background: app.icon_background }">{{ app.icon || '🤖' }}</div>
          <div>
            <div class="rc-name">{{ app.name || '未命名应用' }}</div>
            <div class="rc-sub">{{ typeLabel }}</div>
          </div>
        </div>
        <nav class="rail-menu">
          <button class="rm-item" :class="{ active: activeTab === 'orchestration' }" @click="activeTab = 'orchestration'"><span class="rm-ico">🗂</span>编排</button>
          <button class="rm-item" :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'"><span class="rm-ico">📋</span>日志</button>
          <button class="rm-item" @click="exportDsl"><span class="rm-ico">⬇</span>导出 DSL</button>
        </nav>
      </aside>

      <!-- 主区 -->
      <div class="st-main">
        <!-- 顶栏 -->
        <header class="st-top">
          <span class="st-save">{{ saveStatus }}</span>
          <div class="st-top-right">
            <button class="t-ico-btn" title="撤销" @click="undo">↶</button>
            <button class="t-ico-btn" title="重做" @click="redo">↷</button>
            <button class="t-ico-btn" title="自动布局" @click="autoLayoutNodes">⇅</button>
            <button class="t-ico-btn" title="适应视图" @click="fitView">⊡</button>
            <button class="run-btn" @click="runWorkflow">▶ 测试运行</button>
            <button class="t-ico-btn" title="调试" @click="debugPanelOpen = !debugPanelOpen">🐛</button>
            <button class="t-ico-btn" title="环境变量" @click="openVariables">ENV</button>
            <button class="t-ico-btn" title="版本历史" @click="openVersions">⌚</button>
            <div class="pub-wrap">
              <button class="pub-btn" @click="publish">发布 ▾</button>
            </div>
            <button class="t-ico-btn" title="保存" @click="saveGraph">💾</button>
          </div>
        </header>

        <!-- 舞台 / 日志 -->
        <div class="st-stage" :class="{ 'logs-active': activeTab === 'logs' }">
          <template v-if="activeTab === 'orchestration'">
            <WfCanvas
              ref="canvasRef"
              :graph="graph"
              @select-node="onSelectNode"
              @deselect="selectedNode = null"
              @update:graph="onGraphChanged"
            />
            <PropertyPanel
              :node="selectedNode"
              @update="onUpdateNode"
              @close="selectedNode = null"
              @delete="onDeleteNode"
              @add-next="onAddNextNode"
            />
          </template>
          <WorkflowLogsTab v-else-if="activeTab === 'logs'" :app-id="appId" />
        </div>
      </div>

      <!-- 节点库悬浮 (仅编排模式显示) -->
      <NodeLibrary v-if="activeTab === 'orchestration'" class="floating-library" />

      <!-- 运行面板 -->
      <RunPanel v-if="runPanelOpen" :app-id="appId" :graph="graph" :mode="app.mode" @close="runPanelOpen = false" />

      <!-- 变量面板 -->
      <VariablePanel v-if="variablesOpen" :app-id="appId" @close="variablesOpen = false" @saved="onVariablesSaved" />

      <!-- 版本面板 -->
      <VersionPanel v-if="versionsOpen" :app-id="appId" @close="versionsOpen = false" @restored="onVersionRestored" />

      <!-- 调试面板 -->
      <DebugPanel v-if="debugPanelOpen" ref="debugPanelRef" :app-id="appId" :graph="graph" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from '../utils/global'
import WfCanvas from '../components/workflow/WfCanvas.vue'
import NodeLibrary from '../components/workflow/NodeLibrary.vue'
import PropertyPanel from '../components/workflow/PropertyPanel.vue'
import RunPanel from '../components/workflow/RunPanel.vue'
import VariablePanel from '../components/workflow/VariablePanel.vue'
import VersionPanel from '../components/workflow/VersionPanel.vue'
import WorkflowLogsTab from '../components/workflow/WorkflowLogsTab.vue'
import DebugPanel from '../components/workflow/DebugPanel.vue'

const route = useRoute()
const appId = computed(() => route.query.id || '')

const app = ref({})
const workflow = ref({})
const graph = ref({ nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } })
const selectedNode = ref(null)
const saveStatus = ref('未保存')
const canvasRef = ref(null)
const runPanelOpen = ref(false)
const activeTab = ref('orchestration')
const variablesOpen = ref(false)
const versionsOpen = ref(false)
const debugPanelOpen = ref(false)
const debugPanelRef = ref(null)

// 撤销/重做历史
const history = ref([])
const historyIndex = ref(-1)
let restoring = false

const typeLabel = computed(() => {
  const map = {
    workflow: '工作流',
    chat: 'Chatflow',
    chatflow: 'Chatflow',
    'advanced-chat': '对话流',
    agent: 'Agent',
    'agent-chat': 'Agent'
  }
  return map[app.value.mode] || (app.value.mode || '工作流')
})

async function loadWorkflow() {
  if (!appId.value) {
    toast('缺少应用 ID')
    return
  }
  try {
    const res = await apiGet('/api/workflows/' + encodeURIComponent(appId.value))
    if (res.code === 200) {
      app.value = res.data.app || {}
      workflow.value = res.data.workflow || {}
      graph.value = workflow.value.graph || { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } }
      // 初始化历史栈
      history.value = [JSON.parse(JSON.stringify(graph.value))]
      historyIndex.value = 0
      saveStatus.value = '已加载'
    } else {
      toast(res.msg || '加载失败')
    }
  } catch (e) {
    toast('加载工作流失败')
  }
}

function onGraphChanged(g) {
  graph.value = g
  saveStatus.value = '未保存'
  if (restoring) return
  // 记录历史（截断 redo 分支）
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(JSON.parse(JSON.stringify(g)))
  historyIndex.value = history.value.length - 1
}

async function saveGraph() {
  if (!appId.value) return
  const currentGraph = canvasRef.value ? canvasRef.value.getGraph() : graph.value
  try {
    const res = await apiPut('/api/workflows/' + encodeURIComponent(appId.value) + '/graph', {
      graph: currentGraph,
      features: workflow.value.features,
      environment_variables: workflow.value.environment_variables,
      conversation_variables: workflow.value.conversation_variables
    })
    if (res.code === 200) {
      saveStatus.value = '已保存'
      toast('保存成功')
    } else {
      toast(res.msg || '保存失败')
    }
  } catch (e) {
    toast('保存失败')
  }
}

async function publish() {
  if (!appId.value) return
  try {
    const res = await apiPost('/api/workflows/' + encodeURIComponent(appId.value) + '/publish', { name: '', comment: '' })
    if (res.code === 200) {
      toast('发布成功：' + res.data.name)
    } else {
      toast(res.msg || '发布失败')
    }
  } catch (e) {
    toast('发布失败')
  }
}

function onSelectNode(node) {
  selectedNode.value = node
}

function onUpdateNode(nodeId, patch) {
  canvasRef.value?.updateNodeData(nodeId, patch)
  // 同步更新 selectedNode，确保 PropertyPanel 获取最新数据
  if (selectedNode.value && selectedNode.value.id === nodeId) {
    selectedNode.value = { ...selectedNode.value, data: { ...selectedNode.value.data, ...patch } }
  }
  saveStatus.value = '未保存'
}

function onDeleteNode(nodeId) {
  canvasRef.value?.removeNode(nodeId)
  selectedNode.value = null
  saveStatus.value = '未保存'
}

function onAddNextNode(nodeId, nodeType) {
  const node = canvasRef.value?.addNode(nodeType, { x: 200, y: 200 })
  if (node) {
    // 自动连线
    const edge = {
      id: `edge-${nodeId}-${node.id}`,
      source: nodeId,
      target: node.id,
      type: 'default',
      data: {}
    }
    // 通过 canvasRef 的 addEdge 或直接操作 graph
    const { graph } = canvasRef.value?.getGraph() || {}
    if (graph) {
      graph.edges = [...(graph.edges || []), edge]
      canvasRef.value?.setGraph(graph)
    }
    selectedNode.value = node
    saveStatus.value = '未保存'
  }
}

function fitView() {
  canvasRef.value?.fitView()
}

function autoLayoutNodes() {
  canvasRef.value?.applyLayout()
  toast('已自动布局')
}

function undo() {
  if (historyIndex.value <= 0) { toast('没有更早的操作'); return }
  historyIndex.value--
  restoring = true
  const g = JSON.parse(JSON.stringify(history.value[historyIndex.value]))
  graph.value = g
  canvasRef.value?.setGraph(g)
  restoring = false
  saveStatus.value = '未保存'
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) { toast('没有可重做的操作'); return }
  historyIndex.value++
  restoring = true
  const g = JSON.parse(JSON.stringify(history.value[historyIndex.value]))
  graph.value = g
  canvasRef.value?.setGraph(g)
  restoring = false
  saveStatus.value = '未保存'
}

function openVariables() {
  variablesOpen.value = true
}

function openVersions() {
  versionsOpen.value = true
}

function openRunsPanel() {
  activeTab.value = activeTab.value === 'logs' ? 'orchestration' : 'logs'
}

function onVariablesSaved(vars) {
  workflow.value.environment_variables = vars.environment_variables
  workflow.value.conversation_variables = vars.conversation_variables
  saveStatus.value = '未保存'
  toast('变量已保存')
}

function onVersionRestored() {
  loadWorkflow()
}

async function exportDsl() {
  if (!appId.value) return
  try {
    const res = await apiGet('/api/workflows/' + encodeURIComponent(appId.value) + '/dsl')
    if (res.code === 200 && res.data) {
      const blob = new Blob([res.data.dsl], { type: 'text/yaml;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = (res.data.name || 'workflow').replace(/[^\w一-龥]/g, '_') + '.yml'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast('已导出 DSL')
    } else {
      toast(res.msg || '导出失败')
    }
  } catch (e) {
    toast('导出失败')
  }
}

function runWorkflow() {
  runPanelOpen.value = !runPanelOpen.value
}

function onKeydown(e) {
  const mod = e.ctrlKey || e.metaKey
  if (!mod) return
  const key = e.key.toLowerCase()
  if (key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }
  else if (key === 'y' || (key === 'z' && e.shiftKey)) { e.preventDefault(); redo() }
  else if (key === 's') { e.preventDefault(); saveGraph() }
}

onMounted(() => {
  loadWorkflow()
  window.addEventListener('keydown', onKeydown)
})

// 监听 appId 变化：当从编辑器 A 跳转到编辑器 B 时，重新加载工作流
watch(appId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    loadWorkflow()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style>
.workflow-studio-root{ height: 100vh; overflow: hidden; background: #fff; }
.st-wrap{ display: flex; height: 100vh; background: #fff; position: relative; }

/* ===== 左窄栏 ===== */
.st-rail{ width: 200px; background: #F7F8FA; border-right: 1px solid var(--border-light); display: flex; flex-direction: column; flex-shrink: 0; }
.rail-top{ display: flex; align-items: center; gap: 6px; padding: 12px 12px 10px; }
.rail-back{ border: none; background: none; font-size: 16px; color: var(--text-2); cursor: pointer; padding: 2px 4px; border-radius: 4px; line-height: 1; text-decoration: none; }
.rail-back:hover{ background: #ECEEF1; color: var(--text-1); }
.rail-home{ font-size: 15px; }
.rail-sep{ color: var(--text-4); font-size: 12px; }
.rail-title{ font-size: 14px; font-weight: 600; }
.rail-card{ display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid var(--border-light); border-radius: 10px; margin: 2px 10px 10px; padding: 10px 12px; }
.rc-ico{ width: 38px; height: 38px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 21px; flex-shrink: 0; }
.rc-name{ font-size: 15px; font-weight: 700; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px; }
.rc-sub{ font-size: 12px; color: var(--text-3); margin-top: 2px; }
.rail-menu{ padding: 0 10px; display: flex; flex-direction: column; gap: 2px; }
.rm-item{ display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 7px; font-size: 13.5px; color: var(--text-1); cursor: pointer; border: none; background: none; text-align: left; }
.rm-item .rm-ico{ font-size: 14px; width: 18px; text-align: center; color: var(--text-2); }
.rm-item:hover{ background: #EEF0F3; }
.rm-item.active{ background: var(--primary-light); color: var(--primary); font-weight: 500; }
.rm-item.active .rm-ico{ color: var(--primary); }

/* ===== 右侧主区 ===== */
.st-main{ flex: 1; display: flex; flex-direction: column; min-width: 0; }
.st-top{ height: 52px; background: #fff; display: flex; align-items: center; padding: 0 14px; gap: 10px; position: relative; z-index: 6; flex-shrink: 0; border-bottom: 1px solid var(--border-light); }
.st-save{ font-size: 13px; color: var(--text-3); }
.st-top-right{ margin-left: auto; display: flex; align-items: center; gap: 8px; }
.run-btn{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--primary); background: #fff; border-radius: 7px; padding: 6px 13px; font-size: 13px; color: var(--primary); cursor: pointer; }
.run-btn:hover{ background: var(--primary-light); }
.t-ico-btn{ position: relative; border: 1px solid var(--border); background: #fff; border-radius: 7px; height: 32px; min-width: 34px; padding: 0 8px; display: inline-flex; align-items: center; justify-content: center; color: var(--text-2); font-size: 13px; cursor: pointer; gap: 3px; }
.t-ico-btn:hover{ color: var(--primary); border-color: var(--primary); }
.pub-wrap{ position: relative; }
.pub-btn{ border: none; background: var(--primary); color: #fff; border-radius: 7px; padding: 7px 16px; font-size: 13.5px; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.pub-btn:hover{ background: var(--primary-hover); }

/* ===== 舞台 / 画布 ===== */
.st-stage{ flex: 1; display: flex; min-height: 0; background: #FCFCFD; overflow: hidden; }
.st-stage.logs-active{ background: #f8f9fb; }
.st-stage.logs-active > * { flex: 1; min-width: 0; min-height: 0; }

/* ===== 悬浮节点库 ===== */
.floating-library{ position: absolute; left: 200px; top: 52px; bottom: 0; z-index: 5; box-shadow: 2px 0 12px rgba(29,33,41,.08); }
</style>

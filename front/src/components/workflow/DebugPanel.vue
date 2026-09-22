<template>
  <div class="debug-panel" :class="{ collapsed: collapsed }">
    <!-- 面板头部 -->
    <div class="dp-header">
      <div class="dp-title">
        <span class="dp-icon">🐛</span>
        <span>调试器</span>
        <span v-if="sessionId" class="dp-session-id">#{{ sessionId.slice(0, 8) }}</span>
      </div>
      <div class="dp-header-actions">
        <button class="dp-btn-icon" @click="collapsed = !collapsed" :title="collapsed ? '展开' : '收起'">
          {{ collapsed ? '▼' : '▲' }}
        </button>
      </div>
    </div>

    <div v-if="!collapsed" class="dp-body">
      <!-- 未开始调试状态 -->
      <div v-if="!sessionId" class="dp-idle">
        <div class="dp-idle-icon">🔍</div>
        <div class="dp-idle-text">启动调试以检查工作流执行</div>
        <div class="dp-form">
          <label class="dp-label">输入变量 (JSON)</label>
          <textarea
            v-model="inputJson"
            class="dp-textarea"
            rows="4"
            placeholder='{"query": "你好"}'
          ></textarea>
          <label class="dp-label">断点节点 ID (逗号分隔)</label>
          <input
            v-model="breakpointsStr"
            class="dp-input"
            placeholder="node_1, node_2"
          />
        </div>
        <button class="dp-btn dp-btn-primary" @click="startDebug" :disabled="loading">
          {{ loading ? '启动中...' : '▶ 开始调试' }}
        </button>
      </div>

      <!-- 调试中状态 -->
      <div v-else class="dp-active">
        <!-- 状态栏 -->
        <div class="dp-status-bar">
          <span class="dp-status-badge" :class="statusClass">{{ statusText }}</span>
          <span class="dp-current-node" v-if="currentNodeId">
            当前: {{ currentNodeId }}
          </span>
        </div>

        <!-- 控制按钮 -->
        <div class="dp-controls">
          <button class="dp-btn dp-btn-sm" @click="stepOnce" :disabled="status === 'completed' || loading">
            ⏭ 单步
          </button>
          <button class="dp-btn dp-btn-sm" @click="continueRun" :disabled="status === 'completed' || loading">
            ⏩ 继续
          </button>
          <button class="dp-btn dp-btn-sm dp-btn-danger" @click="stopDebug" :disabled="status === 'completed'">
            ⏹ 停止
          </button>
          <button class="dp-btn dp-btn-sm" @click="loadVariables" :disabled="loading">
            🔄 刷新
          </button>
        </div>

        <!-- 节点执行结果 -->
        <div class="dp-section">
          <div class="dp-section-title" @click="showNodeResult = !showNodeResult">
            <span>{{ showNodeResult ? '▼' : '▶' }}</span>
            <span>节点结果</span>
            <span class="dp-count">{{ Object.keys(nodeResults).length }}</span>
          </div>
          <div v-if="showNodeResult" class="dp-section-body">
            <div v-if="Object.keys(nodeResults).length === 0" class="dp-empty">暂无执行结果</div>
            <div
              v-for="(result, nid) in nodeResults"
              :key="nid"
              class="dp-node-result"
              :class="{ active: nid === currentNodeId, breakpoint: breakpoints.includes(nid) }"
            >
              <div class="dp-node-result-header" @click="selectNodeResult(nid)">
                <span class="dp-node-type">{{ getNodeType(nid) }}</span>
                <span class="dp-node-id">{{ nid }}</span>
                <span v-if="breakpoints.includes(nid)" class="dp-breakpoint-mark">🔴</span>
              </div>
              <div v-if="selectedNodeResult === nid" class="dp-node-result-body">
                <pre>{{ JSON.stringify(result, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- 上下文变量 -->
        <div class="dp-section">
          <div class="dp-section-title" @click="showContext = !showContext">
            <span>{{ showContext ? '▼' : '▶' }}</span>
            <span>上下文变量</span>
            <span class="dp-count">{{ Object.keys(context).length }}</span>
          </div>
          <div v-if="showContext" class="dp-section-body">
            <div v-if="Object.keys(context).length === 0" class="dp-empty">暂无变量</div>
            <div v-for="(val, key) in context" :key="key" class="dp-var-row">
              <span class="dp-var-key">{{ key }}</span>
              <span class="dp-var-val">{{ formatVal(val) }}</span>
            </div>
          </div>
        </div>

        <!-- 执行日志 -->
        <div class="dp-section">
          <div class="dp-section-title" @click="showLogs = !showLogs">
            <span>{{ showLogs ? '▼' : '▶' }}</span>
            <span>执行日志</span>
            <span class="dp-count">{{ logs.length }}</span>
          </div>
          <div v-if="showLogs" class="dp-section-body dp-logs">
            <div v-if="logs.length === 0" class="dp-empty">暂无日志</div>
            <div
              v-for="(log, idx) in logs"
              :key="idx"
              class="dp-log-row"
              :class="'dp-log-' + log.level"
            >
              <span class="dp-log-time">{{ log.time }}</span>
              <span class="dp-log-msg">{{ log.msg }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { apiGet, apiPost } from '../../api/client'
import { toast } from '../../utils/global'

const props = defineProps({
  appId: { type: String, required: true },
  graph: { type: Object, default: () => ({ nodes: [], edges: [] }) },
})

const collapsed = ref(false)
const loading = ref(false)
const sessionId = ref('')
const status = ref('idle') // idle | running | paused | completed
const currentNodeId = ref('')
const context = ref({})
const nodeResults = ref({})
const breakpoints = ref([])
const logs = ref([])
const showNodeResult = ref(true)
const showContext = ref(true)
const showLogs = ref(true)
const selectedNodeResult = ref('')

const inputJson = ref('{"query": ""}')
const breakpointsStr = ref('')

const statusText = computed(() => {
  const map = { idle: '未开始', running: '运行中', paused: '已暂停', completed: '已完成' }
  return map[status.value] || status.value
})

const statusClass = computed(() => 'dp-status-' + status.value)

function getNodeType(nodeId) {
  const node = (props.graph.nodes || []).find(n => n.id === nodeId)
  if (!node) return 'unknown'
  return node.data?.type || node.type || 'unknown'
}

function formatVal(val) {
  if (val === null || val === undefined) return 'null'
  if (typeof val === 'object') {
    const s = JSON.stringify(val)
    return s.length > 80 ? s.slice(0, 80) + '...' : s
  }
  const s = String(val)
  return s.length > 80 ? s.slice(0, 80) + '...' : s
}

function addLog(level, msg) {
  const now = new Date()
  const time = now.toTimeString().slice(0, 8)
  logs.value.push({ level, msg, time })
  if (logs.value.length > 100) logs.value.shift()
}

function selectNodeResult(nid) {
  selectedNodeResult.value = selectedNodeResult.value === nid ? '' : nid
}

async function startDebug() {
  loading.value = true
  logs.value = []
  nodeResults.value = {}
  context.value = {}

  let inputs = {}
  try {
    inputs = inputJson.value.trim() ? JSON.parse(inputJson.value) : {}
  } catch (e) {
    toast('输入 JSON 格式错误')
    loading.value = false
    return
  }

  breakpoints.value = breakpointsStr.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)

  try {
    const res = await apiPost(`/api/workflows/${props.appId}/debug/start`, {
      inputs,
      breakpoints: breakpoints.value,
    })
    if (res.code === 200) {
      sessionId.value = res.data.id
      status.value = 'running'
      currentNodeId.value = res.data.current_node_id || ''
      addLog('info', `调试会话已启动: ${res.data.id}`)
      await loadVariables()
    } else {
      toast(res.msg || '启动调试失败')
    }
  } catch (e) {
    toast('启动调试失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function stepOnce() {
  if (!sessionId.value) return
  loading.value = true
  try {
    const res = await apiPost(`/api/workflows/debug/${sessionId.value}/step`)
    if (res.code === 200) {
      status.value = res.data.status
      currentNodeId.value = res.data.current_node_id || ''
      if (res.data.node_result) {
        nodeResults.value[res.data.current_node_id] = res.data.node_result
      }
      if (res.data.context) {
        context.value = res.data.context
      }
      if (res.data.is_breakpoint) {
        addLog('warn', `🔴 断点触发: ${res.data.current_node_id}`)
      } else {
        addLog('info', `单步执行: ${res.data.current_node_id} (${res.data.node_type})`)
      }
      if (res.data.status === 'completed') {
        addLog('info', '✅ 调试已完成')
      }
      await loadVariables()
    } else {
      toast(res.msg || '单步执行失败')
    }
  } catch (e) {
    toast('单步执行失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function continueRun() {
  if (!sessionId.value) return
  loading.value = true
  try {
    const res = await apiPost(`/api/workflows/debug/${sessionId.value}/continue`)
    if (res.code === 200) {
      status.value = res.data.status
      currentNodeId.value = res.data.current_node_id || ''
      if (res.data.node_result) {
        nodeResults.value[res.data.current_node_id] = res.data.node_result
      }
      if (res.data.context) {
        context.value = res.data.context
      }
      addLog('info', `继续执行 (${res.data.steps || 0} 步)`)
      if (res.data.status === 'paused') {
        addLog('warn', `🔴 暂停在: ${res.data.current_node_id}`)
      } else if (res.data.status === 'completed') {
        addLog('info', '✅ 调试已完成')
      }
      await loadVariables()
    } else {
      toast(res.msg || '继续执行失败')
    }
  } catch (e) {
    toast('继续执行失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function stopDebug() {
  if (!sessionId.value) return
  loading.value = true
  try {
    const res = await apiPost(`/api/workflows/debug/${sessionId.value}/stop`)
    if (res.code === 200) {
      status.value = 'completed'
      addLog('info', '⏹ 调试已停止')
      toast('调试已停止')
    }
  } catch (e) {
    toast('停止失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadVariables() {
  if (!sessionId.value) return
  try {
    const res = await apiGet(`/api/workflows/debug/${sessionId.value}/variables`)
    if (res.code === 200) {
      context.value = res.data.context || {}
      nodeResults.value = res.data.node_results || {}
      currentNodeId.value = res.data.current_node_id || currentNodeId.value
    }
  } catch (e) {
    // silent
  }
}

// 暴露方法给父组件
defineExpose({
  startDebug,
  stopDebug,
  loadSession: (sid) => {
    sessionId.value = sid
    status.value = 'running'
    loadVariables()
  },
})
</script>

<style scoped>
.debug-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 380px;
  background: var(--panel);
  border-left: 1px solid var(--border);
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.08);
  z-index: 200;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
}

.debug-panel.collapsed {
  width: 120px;
}

.dp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--panel-header);
}

.dp-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}

.dp-icon {
  font-size: 16px;
}

.dp-session-id {
  font-size: 11px;
  color: var(--text-3);
  font-family: monospace;
}

.dp-header-actions {
  display: flex;
  gap: 4px;
}

.dp-btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  color: var(--text-2);
  font-size: 12px;
}

.dp-btn-icon:hover {
  background: var(--bg-hover);
}

.dp-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.dp-idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px 0;
}

.dp-idle-icon {
  font-size: 36px;
}

.dp-idle-text {
  font-size: 13px;
  color: var(--text-3);
  text-align: center;
}

.dp-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dp-label {
  font-size: 12px;
  color: var(--text-2);
  font-weight: 500;
}

.dp-textarea,
.dp-input {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--input-bg);
  color: var(--text-1);
  font-size: 12px;
  font-family: monospace;
  resize: vertical;
}

.dp-textarea:focus,
.dp-input:focus {
  outline: none;
  border-color: var(--primary);
}

.dp-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.dp-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dp-btn-primary {
  background: var(--primary);
  color: white;
  width: 100%;
}

.dp-btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.dp-btn-sm {
  padding: 4px 10px;
  font-size: 12px;
  background: var(--bg-2);
  color: var(--text-1);
  border: 1px solid var(--border);
}

.dp-btn-sm:hover:not(:disabled) {
  background: var(--bg-hover);
}

.dp-btn-danger {
  color: var(--danger);
  border-color: var(--danger);
}

.dp-status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.dp-status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.dp-status-idle {
  background: var(--bg-2);
  color: var(--text-3);
}

.dp-status-running {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.dp-status-paused {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.dp-status-completed {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.dp-current-node {
  font-size: 11px;
  color: var(--text-3);
  font-family: monospace;
}

.dp-controls {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.dp-section {
  margin-bottom: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.dp-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--bg-2);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.dp-section-title:hover {
  background: var(--bg-hover);
}

.dp-count {
  margin-left: auto;
  background: var(--bg-3);
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
  color: var(--text-3);
}

.dp-section-body {
  padding: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.dp-empty {
  font-size: 12px;
  color: var(--text-4);
  text-align: center;
  padding: 12px;
}

.dp-node-result {
  margin-bottom: 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.dp-node-result.active {
  border-color: var(--primary);
}

.dp-node-result.breakpoint {
  border-color: var(--danger);
}

.dp-node-result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--bg-1);
  cursor: pointer;
  font-size: 11px;
}

.dp-node-result-header:hover {
  background: var(--bg-hover);
}

.dp-node-type {
  background: var(--bg-3);
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
}

.dp-node-id {
  font-family: monospace;
  color: var(--text-3);
}

.dp-breakpoint-mark {
  margin-left: auto;
}

.dp-node-result-body {
  padding: 6px 8px;
  background: var(--bg-1);
  border-top: 1px solid var(--border);
}

.dp-node-result-body pre {
  margin: 0;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-2);
}

.dp-var-row {
  display: flex;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px;
  border-bottom: 1px solid var(--border-light);
}

.dp-var-key {
  font-weight: 600;
  color: var(--text-1);
  min-width: 60px;
}

.dp-var-val {
  color: var(--text-3);
  font-family: monospace;
  word-break: break-all;
}

.dp-logs {
  font-family: monospace;
  font-size: 11px;
}

.dp-log-row {
  display: flex;
  gap: 6px;
  padding: 2px 0;
}

.dp-log-time {
  color: var(--text-4);
  flex-shrink: 0;
}

.dp-log-info .dp-log-msg {
  color: var(--text-2);
}

.dp-log-warn .dp-log-msg {
  color: #f59e0b;
}

.dp-log-error .dp-log-msg {
  color: var(--danger);
}
</style>

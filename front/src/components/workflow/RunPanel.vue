<template>
  <div class="run-panel">
    <div class="rp-head">
      <span class="rp-title">测试运行</span>
      <button class="rp-close" @click="$emit('close')">✕</button>
    </div>

    <div class="rp-body">
      <!-- 输入表单 -->
      <div v-if="!result && view !== 'history'" class="rp-inputs">
        <div v-if="inputs.length === 0" class="rp-empty">该工作流没有输入变量</div>
        <div v-for="inp in inputs" :key="inp.variable" class="rp-field">
          <label>{{ inp.label || inp.variable }} <span v-if="inp.required" class="rp-req">*</span></label>
          <textarea v-if="inp.type === 'paragraph'" v-model="form[inp.variable]" :placeholder="inp.label || inp.variable" rows="3"></textarea>
          <input v-else v-model="form[inp.variable]" :placeholder="inp.label || inp.variable" @keydown.enter="run">
        </div>
        <div class="rp-run-btns">
          <button class="rp-run-btn" :disabled="running" @click="run">
            {{ running && !streaming ? '运行中…' : '▶ 运行' }}
          </button>
          <button class="rp-stream-btn" :disabled="running" @click="runStream">
            {{ running && streaming ? '流式运行中…' : '⚡ 流式运行' }}
          </button>
          <button v-if="running" class="rp-stop-btn" @click="stopRun">
            <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            停止
          </button>
        </div>

        <div v-if="running && !streaming" class="rp-progress-wrap">
          <div class="rp-progress-bar">
            <div class="rp-progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <div class="rp-progress-text">{{ progressHint }}</div>
        </div>

        <!-- 流式执行追踪面板 -->
        <div v-if="running && streaming" class="rp-stream-trace">
          <div class="rp-stream-head">
            <span class="rp-stream-title">执行追踪</span>
            <span class="rp-stream-status" :class="streamStatus">{{ getStreamStatusLabel(streamStatus) }}</span>
          </div>
          <div class="rp-stream-nodes">
            <div v-for="node in streamNodes" :key="node.node_id" class="rp-stream-node" :class="node.status">
              <span class="rp-node-dot" :class="node.status"></span>
              <span class="rp-node-title">{{ node.title || node.node_type }}</span>
              <span class="rp-node-type">{{ node.node_type }}</span>
              <!-- LLM 流式输出预览 -->
              <div v-if="node.streaming && node.delta" class="rp-node-delta">{{ node.delta }}</div>
              <!-- Agent 思考链预览 -->
              <div v-if="node.node_type === 'agent' && agentThoughts[node.node_id] && agentThoughts[node.node_id].length" class="rp-agent-thoughts">
                <span class="rp-agent-thought-count">💭 {{ agentThoughts[node.node_id].length }} 步思考</span>
                <span v-if="agentThoughts[node.node_id].some(t => t.tool_name)" class="rp-agent-tool-count">🔧 {{ agentThoughts[node.node_id].filter(t => t.tool_name).length }} 次工具调用</span>
              </div>
              <div v-if="node.status === 'failed'" class="rp-node-error">{{ node.error }}</div>
            </div>
          </div>
          <div v-if="streamNodes.length === 0" class="rp-empty">等待节点开始…</div>
        </div>
      </div>

      <!-- 结果展示 -->
      <div v-else-if="result && view !== 'history'" class="rp-result">
        <div class="rp-status" :class="result.status">
          {{ statusLabel(result.status) }}
        </div>
        <div v-if="result.error" class="rp-error">{{ result.error }}</div>

        <div v-if="result.outputs && Object.keys(result.outputs).length" class="rp-sec">
          <div class="rp-sec-title">输出</div>
          <div v-for="(val, key) in result.outputs" :key="key" class="rp-out">
            <div class="rp-out-key">{{ key }}</div>
            <pre class="rp-out-val">{{ formatVal(val) }}</pre>
          </div>
        </div>

        <div class="rp-meta">
          <span>耗时 {{ result.elapsed_time != null ? result.elapsed_time + 's' : '-' }}</span>
          <span>Token {{ result.total_tokens }}</span>
          <span>步骤 {{ result.total_steps }}</span>
        </div>

        <div v-if="result.nodes && result.nodes.length" class="rp-sec">
          <div class="rp-sec-title">节点执行</div>
          <div v-for="n in result.nodes" :key="n.node_id" class="rp-node">
            <span class="rp-node-dot" :class="n.status"></span>
            <span class="rp-node-title">{{ n.title || n.node_type }}</span>
            <span class="rp-node-time">{{ n.elapsed_time != null ? n.elapsed_time + 's' : '' }}</span>
          </div>
        </div>

        <div class="rp-actions">
          <button class="rp-save-btn" @click="saveResult">💾 保存结果</button>
          <button class="rp-history-btn" @click="openHistory">📋 查看已保存结果</button>
          <button class="rp-again-btn" @click="result = null">再次运行</button>
        </div>
      </div>

      <!-- 历史记录 -->
      <div v-else-if="view === 'history'" class="rp-history">
        <div class="rp-history-head">
          <button class="rp-back" @click="view = ''">‹ 返回</button>
          <span class="rp-history-title">已保存的测试运行</span>
        </div>
        <div v-if="historyLoading" class="rp-empty">加载中…</div>
        <div v-else-if="history.length === 0" class="rp-empty">暂无保存的测试运行</div>
        <div v-else class="rp-history-list">
          <div
            v-for="h in history"
            :key="h.id"
            class="rp-history-item"
            :class="{ active: selectedHistory && selectedHistory.id === h.id }"
            @click="selectedHistory = h"
          >
            <div class="rp-history-name">{{ h.run_name }}</div>
            <div class="rp-history-meta">
              <span :class="['rp-history-status', h.status]">{{ statusLabel(h.status) }}</span>
              <span>{{ h.created_at }}</span>
            </div>
          </div>
        </div>

        <div v-if="selectedHistory" class="rp-history-detail">
          <div class="rp-status" :class="selectedHistory.status">
            {{ statusLabel(selectedHistory.status) }}
          </div>
          <div v-if="selectedHistory.error" class="rp-error">{{ selectedHistory.error }}</div>
          <div v-if="selectedHistory.inputs && Object.keys(selectedHistory.inputs).length" class="rp-sec">
            <div class="rp-sec-title">输入</div>
            <pre class="rp-out-val">{{ formatVal(selectedHistory.inputs) }}</pre>
          </div>
          <div v-if="selectedHistory.outputs && Object.keys(selectedHistory.outputs).length" class="rp-sec">
            <div class="rp-sec-title">输出</div>
            <div v-for="(val, key) in selectedHistory.outputs" :key="key" class="rp-out">
              <div class="rp-out-key">{{ key }}</div>
              <pre class="rp-out-val">{{ formatVal(val) }}</pre>
            </div>
          </div>
          <div class="rp-meta">
            <span>耗时 {{ selectedHistory.elapsed_time != null ? selectedHistory.elapsed_time + 's' : '-' }}</span>
            <span>Token {{ selectedHistory.total_tokens }}</span>
            <span>步骤 {{ selectedHistory.total_steps }}</span>
          </div>
          <button class="rp-danger-btn" @click="deleteHistory(selectedHistory.id)">删除此记录</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { toast } from '../../utils/global'

const props = defineProps({
  appId: { type: String, required: true },
  graph: { type: Object, default: null },
  mode: { type: String, default: null }
})

const emit = defineEmits(['close'])

const inputs = ref([])
const form = ref({})
const result = ref(null)
const running = ref(false)
const progress = ref(0)
const progressHint = ref('准备运行…')
let progressTimer = null
const view = ref('')
const history = ref([])
const historyLoading = ref(false)
const selectedHistory = ref(null)

// 流式执行状态
const streaming = ref(false)
const streamStatus = ref('connecting') // connecting | running | succeeded | failed | stopped
const streamNodes = ref([])
const agentThoughts = ref({}) // { node_id: [{type, content, tool_name, tool_input, tool_output, step_type}] }
let currentRunId = null  // 当前运行 ID（用于停止）
let streamReader = null  // 当前流的 reader

function statusLabel(s) {
  const map = { succeeded: '成功', failed: '失败', running: '运行中', partial_succeeded: '部分成功', stopped: '已停止' }
  return map[s] || s || '未知'
}

function getStreamStatusLabel(status) {
  const map = {
    connecting: '连接中…',
    running: '执行中',
    succeeded: '已完成',
    failed: '失败',
    stopped: '已停止',
    paused: '已暂停'
  }
  return map[status] || status || '未知'
}

// 停止运行
function stopRun() {
  if (!currentRunId) return
  const runId = currentRunId
  // 关闭流
  if (streamReader) {
    streamReader.cancel().catch(() => {})
    streamReader = null
  }
  // 通知后端停止
  fetch('/api/workflows/runs/' + runId + '/stop', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.code !== 200 && data.code !== 404) {
        console.warn('[stop workflow]', data.msg)
      }
    })
    .catch(() => {})
}

function formatVal(v) {
  if (v == null) return 'null'
  if (typeof v === 'string') return v
  return JSON.stringify(v, null, 2)
}

function startProgress() {
  progress.value = 5
  progressHint.value = '正在调用模型…'
  let step = 0
  progressTimer = setInterval(() => {
    step++
    if (progress.value < 85) {
      progress.value += Math.random() * 8
      if (step % 3 === 0) progressHint.value = progress.value < 30 ? '正在调用模型…' : progress.value < 60 ? '模型思考中…' : '正在生成回复…'
    }
  }, 600)
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  progress.value = 100
  progressHint.value = '运行完成'
}

async function loadInputs() {
  try {
    const r = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/inputs')
    const res = await r.json()
    if (res.code === 200) {
      inputs.value = res.data || []
      const f = {}
      inputs.value.forEach(i => { f[i.variable] = '' })
      form.value = f
    }
  } catch (e) {}
}

async function run() {
  if (running.value) return
  running.value = true
  startProgress()
  try {
    // 构建请求头（包含 JWT Token）
    const headers = { 'Content-Type': 'application/json' }
    try {
      const tokens = sessionStorage.getItem('auth_tokens')
      if (tokens) {
        const t = JSON.parse(tokens)
        if (t && t.access_token) {
          headers['Authorization'] = 'Bearer ' + t.access_token
        }
      }
    } catch (e) { /* ignore */ }
    const r = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/run', {
      method: 'POST',
      headers,
      body: JSON.stringify({ inputs: form.value, graph: props.graph, mode: props.mode })
    })
    const res = await r.json()
    if (res.code === 200 && res.data) {
      const d = res.data
      result.value = {
        status: d.status || d.data?.status || 'succeeded',
        outputs: d.outputs || d.data?.outputs || {},
        error: d.error || d.data?.error || d.message || '',
        elapsed_time: d.elapsed_time ?? d.data?.elapsed_time ?? null,
        total_tokens: d.total_tokens ?? d.data?.total_tokens ?? 0,
        total_steps: d.total_steps ?? d.data?.total_steps ?? 0,
        nodes: d.nodes || []
      }
    } else {
      result.value = { status: 'failed', outputs: {}, error: res.msg || '运行失败', elapsed_time: null, total_tokens: 0, total_steps: 0, nodes: [] }
    }
  } catch (e) {
    result.value = { status: 'failed', outputs: {}, error: e.message || '运行失败', elapsed_time: null, total_tokens: 0, total_steps: 0, nodes: [] }
  } finally {
    stopProgress()
    running.value = false
  }
}

async function runStream() {
  if (running.value) return
  running.value = true
  streaming.value = true
  streamStatus.value = 'connecting'
  streamNodes.value = []
  currentRunId = null
  streamReader = null
  progressHint.value = '正在连接…'

  try {
    // 构建请求头（包含 JWT Token）
    const headers = { 'Content-Type': 'application/json' }
    try {
      const tokens = sessionStorage.getItem('auth_tokens')
      if (tokens) {
        const t = JSON.parse(tokens)
        if (t && t.access_token) {
          headers['Authorization'] = 'Bearer ' + t.access_token
        }
      }
    } catch (e) { /* ignore */ }
    // 使用 fetch + ReadableStream 处理 SSE
    const response = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({ inputs: form.value, graph: props.graph, mode: props.mode })
    })

    if (!response.ok) {
      throw new Error('服务器返回错误: ' + response.status)
    }

    streamReader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await streamReader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''

      for (const chunk of chunks) {
        if (!chunk.trim()) continue
        let eventName = 'message'
        let dataStr = ''
        for (const line of chunk.split('\n')) {
          if (line.startsWith('event: ')) {
            eventName = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            dataStr = line.slice(6)
          }
        }
        if (dataStr) {
          try {
            const data = JSON.parse(dataStr)
            // 保存 run_id（用于停止）
            if (data.run_id && !currentRunId) {
              currentRunId = data.run_id
            }
            handleStreamEvent(eventName, data)
            // 如果已停止，跳出循环
            if (streamStatus.value === 'stopped') {
              break
            }
          } catch (e) {}
        }
      }
    }
  } catch (e) {
    streamStatus.value = 'failed'
    result.value = { status: 'failed', outputs: {}, error: e.message || '流式运行失败', elapsed_time: null, total_tokens: 0, total_steps: 0, nodes: streamNodes.value }
  } finally {
    running.value = false
    streaming.value = false
    progress.value = 100
  }
}

function handleStreamEvent(eventName, data) {
  switch (eventName) {
    case 'workflow_start':
      streamStatus.value = 'running'
      progressHint.value = '工作流执行中…'
      break

    case 'node_start': {
      // 添加或更新节点状态
      const idx = streamNodes.value.findIndex(n => n.node_id === data.node_id)
      const nodeInfo = {
        node_id: data.node_id,
        node_type: data.node_type,
        title: data.title,
        status: 'running',
        streaming: false,
        delta: '',
        error: ''
      }
      if (idx >= 0) {
        streamNodes.value[idx] = nodeInfo
      } else {
        streamNodes.value.push(nodeInfo)
      }
      break
    }

    case 'node_stream': {
      // LLM 节点流式输出
      const idx = streamNodes.value.findIndex(n => n.node_id === data.node_id)
      if (idx >= 0) {
        streamNodes.value[idx].streaming = true
        if (data.delta) {
          streamNodes.value[idx].delta = data.content || (streamNodes.value[idx].delta + data.delta)
        }
        if (data.done) {
          streamNodes.value[idx].streaming = false
        }
      }
      break
    }

    case 'node_complete': {
      const idx = streamNodes.value.findIndex(n => n.node_id === data.node_id)
      if (idx >= 0) {
        streamNodes.value[idx].status = data.status
        streamNodes.value[idx].streaming = false
        if (data.error) {
          streamNodes.value[idx].error = data.error
        }
      }
      break
    }

    case 'agent_thought_stream': {
      // Agent 节点实时思考链
      const nid = data.node_id
      if (!agentThoughts.value[nid]) {
        agentThoughts.value[nid] = []
      }
      agentThoughts.value[nid].push({
        type: data.type,
        content: data.content || '',
        tool_name: data.tool_name || '',
        tool_input: data.tool_input || '',
        tool_output: data.tool_output || '',
        step_type: data.step_type || '',
      })
      // 同步到 streamNodes 的 delta 中（实时展示）
      const idx = streamNodes.value.findIndex(n => n.node_id === nid)
      if (idx >= 0) {
        streamNodes.value[idx].streaming = true
        const lastThought = agentThoughts.value[nid][agentThoughts.value[nid].length - 1]
        if (lastThought.type === 'tool_call') {
          streamNodes.value[idx].delta = `🔧 ${lastThought.tool_name}(${JSON.stringify(lastThought.tool_input).slice(0, 100)})`
        } else if (lastThought.type === 'reasoning') {
          streamNodes.value[idx].delta = `💭 ${lastThought.content.slice(0, 150)}`
        } else if (lastThought.type === 'done') {
          streamNodes.value[idx].delta = `✅ ${lastThought.content.slice(0, 150)}`
        }
      }
      break
    }

    case 'workflow_complete':
      streamStatus.value = 'succeeded'
      progressHint.value = '运行完成'
      result.value = {
        status: 'succeeded',
        outputs: data.outputs || {},
        error: '',
        elapsed_time: data.elapsed_time,
        total_tokens: data.total_tokens || 0,
        total_steps: streamNodes.value.length,
        nodes: streamNodes.value.map(n => ({
          node_id: n.node_id,
          node_type: n.node_type,
          title: n.title,
          status: n.status
        }))
      }
      break

    case 'workflow_result':
      // 最终结果
      if (data.outputs) {
        if (!result.value) result.value = { status: 'succeeded', outputs: {}, error: '', elapsed_time: null, total_tokens: 0, total_steps: 0, nodes: [] }
        result.value.outputs = { ...result.value.outputs, ...data.outputs }
      }
      if (data.answer) {
        if (!result.value) result.value = { status: 'succeeded', outputs: {}, error: '', elapsed_time: null, total_tokens: 0, total_steps: 0, nodes: [] }
        result.value.outputs.answer = data.answer
      }
      break

    case 'workflow_pause':
      streamStatus.value = 'paused'
      progressHint.value = '等待用户输入…'
      break

    case 'workflow_stopped':
      streamStatus.value = 'stopped'
      progressHint.value = '已停止'
      result.value = {
        status: 'stopped',
        outputs: data.outputs || {},
        error: '用户主动停止',
        elapsed_time: data.elapsed_time,
        total_tokens: data.total_tokens || 0,
        total_steps: streamNodes.value.length,
        nodes: streamNodes.value.map(n => ({
          node_id: n.node_id,
          node_type: n.node_type,
          title: n.title,
          status: n.status
        }))
      }
      break

    case 'error':
      streamStatus.value = 'failed'
      progressHint.value = '运行失败'
      result.value = {
        status: 'failed',
        outputs: {},
        error: data.message || '运行失败',
        elapsed_time: data.elapsed_time,
        total_tokens: 0,
        total_steps: streamNodes.value.length,
        nodes: streamNodes.value.map(n => ({
          node_id: n.node_id,
          node_type: n.node_type,
          title: n.title,
          status: n.status
        }))
      }
      break
  }
}

async function saveResult() {
  if (!result.value) return
  const runName = prompt('请输入保存名称（可选）：')
  if (runName === null) return
  try {
    const r = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/test-runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_name: runName, result: result.value, inputs: form.value })
    })
    const res = await r.json()
    if (res.code === 200) {
      toast('保存成功')
    } else {
      toast(res.msg || '保存失败')
    }
  } catch (e) {
    toast('保存失败')
  }
}

async function openHistory() {
  view.value = 'history'
  selectedHistory.value = null
  historyLoading.value = true
  try {
    const r = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/test-runs')
    const res = await r.json()
    if (res.code === 200) {
      history.value = res.data || []
    } else {
      toast(res.msg || '加载历史失败')
    }
  } catch (e) {
    toast('加载历史失败')
  } finally {
    historyLoading.value = false
  }
}

async function deleteHistory(id) {
  if (!confirm('确定删除这条保存的记录吗？')) return
  try {
    const r = await fetch('/api/workflows/' + encodeURIComponent(props.appId) + '/test-runs/' + id, {
      method: 'DELETE'
    })
    const res = await r.json()
    if (res.code === 200) {
      history.value = history.value.filter(h => h.id !== id)
      selectedHistory.value = null
      toast('已删除')
    } else {
      toast(res.msg || '删除失败')
    }
  } catch (e) {
    toast('删除失败')
  }
}

onMounted(loadInputs)
onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style scoped>
.run-panel{ position: absolute; right: 0; top: 0; bottom: 0; width: 420px; background: #fff; border-left: 1px solid var(--border-light); display: flex; flex-direction: column; z-index: 20; box-shadow: -6px 0 24px rgba(29,33,41,.10); }
.rp-head{ display: flex; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border-light); }
.rp-title{ font-size: 15px; font-weight: 700; }
.rp-close{ margin-left: auto; border: none; background: none; color: var(--text-3); cursor: pointer; font-size: 16px; }
.rp-close:hover{ color: var(--text-1); }
.rp-body{ flex: 1; overflow-y: auto; padding: 16px; }
.rp-inputs{ display: flex; flex-direction: column; gap: 14px; }
.rp-empty{ color: var(--text-3); font-size: 13px; text-align: center; padding: 30px 0; }
.rp-field label{ display: block; font-size: 13px; font-weight: 600; color: var(--text-1); margin-bottom: 6px; }
.rp-field input, .rp-field textarea{ width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; font-size: 13px; outline: none; box-sizing: border-box; font-family: inherit; }
.rp-field input:focus, .rp-field textarea:focus{ border-color: var(--primary); }
.rp-field textarea{ resize: vertical; }
.rp-req{ color: var(--red); }
.rp-run-btn{ background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 10px; font-size: 14px; cursor: pointer; }
.rp-run-btn:disabled{ opacity: .6; cursor: not-allowed; }
.rp-run-btn:hover{ background: var(--primary-hover); }

.rp-progress-wrap{ margin-top: 4px; }
.rp-progress-bar{ height: 6px; background: #E8EAED; border-radius: 3px; overflow: hidden; }
.rp-progress-fill{ height: 100%; background: var(--primary); border-radius: 3px; transition: width .2s; }
.rp-progress-text{ font-size: 12px; color: var(--text-2); margin-top: 8px; }

.rp-result{ display: flex; flex-direction: column; gap: 14px; }
.rp-status{ font-size: 15px; font-weight: 700; }
.rp-status.succeeded{ color: var(--green); }
.rp-status.failed{ color: var(--red); }
.rp-status.running{ color: var(--primary); }
.rp-error{ background: var(--red-bg); color: var(--red); border-radius: 8px; padding: 10px 12px; font-size: 12.5px; word-break: break-all; }
.rp-sec-title{ font-size: 13px; font-weight: 700; color: var(--text-1); margin-bottom: 8px; }
.rp-out{ background: #F7F8FA; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
.rp-out-key{ font-size: 12px; color: var(--text-3); margin-bottom: 4px; }
.rp-out-val{ font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 240px; overflow-y: auto; color: var(--text-1); margin: 0; }
.rp-meta{ display: flex; gap: 16px; font-size: 12px; color: var(--text-3); }
.rp-node{ display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-light); font-size: 13px; }
.rp-node-dot{ width: 8px; height: 8px; border-radius: 50%; background: var(--text-4); }
.rp-node-dot.succeeded{ background: var(--green); }
.rp-node-dot.failed{ background: var(--red); }
.rp-node-title{ flex: 1; }
.rp-node-time{ color: var(--text-3); font-size: 12px; }

.rp-actions{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; }
.rp-actions button{ flex: 1; min-width: 90px; border-radius: 8px; padding: 8px; font-size: 13px; cursor: pointer; border: 1px solid var(--border); background: #fff; color: var(--text-1); }
.rp-actions button:hover{ border-color: var(--primary); color: var(--primary); }
.rp-save-btn{ background: var(--primary) !important; color: #fff !important; border-color: var(--primary) !important; }
.rp-save-btn:hover{ background: var(--primary-hover) !important; }

.rp-history{ display: flex; flex-direction: column; gap: 12px; }
.rp-history-head{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.rp-back{ border: none; background: none; color: var(--primary); font-size: 13px; cursor: pointer; padding: 0; }
.rp-history-title{ font-size: 15px; font-weight: 700; }
.rp-history-list{ display: flex; flex-direction: column; gap: 8px; }
.rp-history-item{ border: 1px solid var(--border-light); border-radius: 8px; padding: 10px 12px; cursor: pointer; }
.rp-history-item:hover, .rp-history-item.active{ border-color: var(--primary); background: var(--primary-light); }
.rp-history-name{ font-size: 13px; font-weight: 600; color: var(--text-1); }
.rp-history-meta{ display: flex; gap: 10px; font-size: 12px; color: var(--text-3); margin-top: 4px; }
.rp-history-status{ font-weight: 600; }
.rp-history-status.succeeded{ color: var(--green); }
.rp-history-status.failed{ color: var(--red); }
.rp-history-detail{ border-top: 1px solid var(--border-light); padding-top: 14px; margin-top: 4px; display: flex; flex-direction: column; gap: 12px; }
.rp-danger-btn{ background: var(--red-bg); color: var(--red); border: 1px solid var(--red); border-radius: 8px; padding: 8px; font-size: 13px; cursor: pointer; }
.rp-danger-btn:hover{ background: var(--red); color: #fff; }

/* 流式运行按钮 */
.rp-run-btns{ display: flex; gap: 10px; }
.rp-run-btn{ flex: 1; background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 10px; font-size: 14px; cursor: pointer; }
.rp-run-btn:disabled{ opacity: .6; cursor: not-allowed; }
.rp-run-btn:hover:not(:disabled){ background: var(--primary-hover); }
.rp-stream-btn{ flex: 1; background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #fff; border: none; border-radius: 8px; padding: 10px; font-size: 14px; cursor: pointer; transition: all .2s; }
.rp-stream-btn:disabled{ opacity: .6; cursor: not-allowed; }
.rp-stream-btn:hover:not(:disabled){ background: linear-gradient(135deg, #4F46E5, #7C3AED); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, .3); }
.rp-stop-btn{ display: flex; align-items: center; justify-content: center; gap: 5px; background: #F53F3F; color: #fff; border: none; border-radius: 8px; padding: 10px 14px; font-size: 14px; cursor: pointer; font-weight: 600; transition: all .15s; }
.rp-stop-btn:hover{ background: #E63535; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(245, 63, 63, .3); }

/* 流式执行追踪面板 */
.rp-stream-trace{ display: flex; flex-direction: column; gap: 10px; padding: 12px; background: #FAFBFC; border: 1px solid var(--border-light); border-radius: 10px; }
.rp-stream-head{ display: flex; align-items: center; justify-content: space-between; }
.rp-stream-title{ font-size: 13px; font-weight: 700; color: var(--text-1); }
.rp-stream-status{ font-size: 12px; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
.rp-stream-status.connecting{ background: #FEF3C7; color: #D97706; }
.rp-stream-status.running{ background: #DBEAFE; color: #2563EB; }
.rp-stream-status.succeeded{ background: #D1FAE5; color: #059669; }
.rp-stream-status.failed{ background: #FEE2E2; color: #DC2626; }
.rp-stream-status.paused{ background: #FEF3C7; color: #D97706; }
.rp-stream-nodes{ display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.rp-stream-node{ display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: #fff; border: 1px solid var(--border-light); border-radius: 8px; font-size: 12.5px; flex-wrap: wrap; }
.rp-stream-node.running{ border-color: #93C5FD; background: #EFF6FF; }
.rp-stream-node.succeeded{ border-color: #6EE7B7; background: #ECFDF5; }
.rp-stream-node.failed{ border-color: #FCA5A5; background: #FEF2F2; }
.rp-stream-node .rp-node-type{ font-size: 11px; color: var(--text-3); background: #F3F4F6; padding: 1px 6px; border-radius: 4px; }
.rp-node-delta{ width: 100%; font-size: 12px; color: var(--text-2); background: #F9FAFB; padding: 6px 8px; border-radius: 6px; margin-top: 4px; max-height: 80px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; border-left: 3px solid var(--primary); }
.rp-node-error{ width: 100%; font-size: 12px; color: var(--red); background: var(--red-bg); padding: 6px 8px; border-radius: 6px; margin-top: 4px; }
.rp-agent-thoughts{ width: 100%; display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.rp-agent-thought-count, .rp-agent-tool-count{ font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(46, 99, 240, 0.08); color: var(--primary); font-weight: 500; }
</style>

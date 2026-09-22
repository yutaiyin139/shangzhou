<template>
  <div class="logs-tab">
    <!-- 顶部筛选栏 -->
    <div class="logs-toolbar">
      <div class="logs-filter-group">
        <label class="logs-filter-label">状态</label>
        <select v-model="statusFilter" class="logs-filter-select" @change="loadRuns(1)">
          <option value="">全部</option>
          <option value="succeeded">成功</option>
          <option value="failed">失败</option>
          <option value="running">运行中</option>
        </select>
      </div>
      <div class="logs-filter-group">
        <label class="logs-filter-label">每页</label>
        <select v-model.number="pageSize" class="logs-filter-select logs-page-size" @change="loadRuns(1)">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </div>
      <button class="logs-refresh-btn" :disabled="loading" @click="loadRuns(1)">
        {{ loading ? '加载中…' : '↻ 刷新' }}
      </button>
    </div>

    <!-- 主内容区 -->
    <div class="logs-content">
      <!-- 运行列表 -->
      <div class="logs-list-panel" :class="{ 'with-detail': selectedRun }">
        <div v-if="loading && runs.length === 0" class="logs-empty">加载中…</div>
        <div v-else-if="runs.length === 0" class="logs-empty">
          <div class="logs-empty-icon">📋</div>
          <div class="logs-empty-text">暂无运行记录</div>
          <div class="logs-empty-hint">运行工作流后，执行记录将显示在这里</div>
        </div>
        <div v-else class="logs-run-list">
          <div
            v-for="run in runs"
            :key="run.id"
            class="logs-run-item"
            :class="{ active: selectedRun && selectedRun.id === run.id, [run.status]: true }"
            @click="selectRun(run)"
          >
            <div class="logs-run-header">
              <span class="logs-run-status" :class="run.status">{{ statusLabel(run.status) }}</span>
              <span class="logs-run-time">{{ formatTime(run.created_at) }}</span>
            </div>
            <div class="logs-run-inputs">
              <span v-for="(val, key) in run.inputs" :key="key" class="logs-run-input-tag">
                {{ key }}: {{ formatInputVal(val) }}
              </span>
            </div>
            <div class="logs-run-meta">
              <span v-if="run.elapsed_time" title="耗时">⏱ {{ typeof run.elapsed_time === 'number' ? run.elapsed_time.toFixed(2) + 's' : run.elapsed_time }}</span>
              <span v-if="run.total_tokens" title="Token">🔤 {{ run.total_tokens }}</span>
              <span v-if="run.total_steps" title="步骤">📶 {{ run.total_steps }}</span>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="logs-pagination">
          <button :disabled="currentPage <= 1" class="logs-page-btn" @click="loadRuns(currentPage - 1)">‹</button>
          <span class="logs-page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button :disabled="currentPage >= totalPages" class="logs-page-btn" @click="loadRuns(currentPage + 1)">›</button>
        </div>
      </div>

      <!-- 运行详情 -->
      <div v-if="selectedRun" class="logs-detail-panel">
        <div class="logs-detail-header">
          <button class="logs-detail-back" @click="selectedRun = null">‹ 返回</button>
          <span class="logs-detail-title">运行详情</span>
          <span class="logs-detail-status" :class="selectedRun.status">{{ statusLabel(selectedRun.status) }}</span>
        </div>

        <div class="logs-detail-body">
          <!-- 概览 -->
          <div class="logs-detail-section">
            <div class="logs-detail-section-title">概览</div>
            <div class="logs-detail-overview">
              <div class="logs-overview-item">
                <span class="logs-overview-label">开始时间</span>
                <span class="logs-overview-value">{{ selectedRun.created_at }}</span>
              </div>
              <div class="logs-overview-item">
                <span class="logs-overview-label">结束时间</span>
                <span class="logs-overview-value">{{ selectedRun.finished_at || '-' }}</span>
              </div>
              <div class="logs-overview-item">
                <span class="logs-overview-label">耗时</span>
                <span class="logs-overview-value">{{ selectedRun.elapsed_time ? (typeof selectedRun.elapsed_time === 'number' ? selectedRun.elapsed_time.toFixed(2) + 's' : selectedRun.elapsed_time) : '-' }}</span>
              </div>
              <div class="logs-overview-item">
                <span class="logs-overview-label">Token 消耗</span>
                <span class="logs-overview-value">{{ selectedRun.total_tokens || 0 }}</span>
              </div>
              <div class="logs-overview-item">
                <span class="logs-overview-label">执行步骤</span>
                <span class="logs-overview-value">{{ selectedRun.total_steps || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 错误信息 -->
          <div v-if="selectedRun.error" class="logs-detail-section">
            <div class="logs-detail-section-title">错误信息</div>
            <pre class="logs-detail-error">{{ selectedRun.error }}</pre>
          </div>

          <!-- 输入 -->
          <div v-if="selectedRun.inputs && Object.keys(selectedRun.inputs).length" class="logs-detail-section">
            <div class="logs-detail-section-title">输入</div>
            <pre class="logs-detail-json">{{ formatJson(selectedRun.inputs) }}</pre>
          </div>

          <!-- 输出 -->
          <div v-if="selectedRun.outputs && Object.keys(selectedRun.outputs).length" class="logs-detail-section">
            <div class="logs-detail-section-title">输出</div>
            <pre class="logs-detail-json">{{ formatJson(selectedRun.outputs) }}</pre>
          </div>

          <!-- 节点执行详情 -->
          <div v-if="selectedRun.nodes && selectedRun.nodes.length" class="logs-detail-section">
            <div class="logs-detail-section-title">节点执行 ({{ selectedRun.nodes.length }})</div>
            <div class="logs-node-list">
              <div
                v-for="node in selectedRun.nodes"
                :key="node.node_id"
                class="logs-node-item"
                :class="[node.status, { expanded: expandedNodes[node.node_id] }]"
              >
                <div class="logs-node-header" @click="toggleNode(node.node_id)">
                  <span class="logs-node-dot" :class="node.status"></span>
                  <span class="logs-node-title">{{ node.title || node.node_id }}</span>
                  <span class="logs-node-type">{{ node.node_type }}</span>
                  <span v-if="node.elapsed_time" class="logs-node-time">{{ typeof node.elapsed_time === 'number' ? node.elapsed_time.toFixed(2) + 's' : node.elapsed_time }}</span>
                  <span class="logs-node-toggle">{{ expandedNodes[node.node_id] ? '▼' : '▶' }}</span>
                </div>
                <div v-if="expandedNodes[node.node_id]" class="logs-node-detail">
                  <div v-if="node.error" class="logs-node-error">{{ node.error }}</div>
                  <div v-if="node.inputs && Object.keys(node.inputs).length" class="logs-node-section">
                    <div class="logs-node-section-title">输入</div>
                    <pre class="logs-node-json">{{ formatJson(node.inputs) }}</pre>
                  </div>
                  <div v-if="node.outputs && Object.keys(node.outputs).length" class="logs-node-section">
                    <div class="logs-node-section-title">输出</div>
                    <pre class="logs-node-json">{{ formatJson(node.outputs) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { toast } from '../../utils/global'

const props = defineProps({
  appId: { type: String, required: true }
})

const runs = ref([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const selectedRun = ref(null)
const expandedNodes = ref({})

function statusLabel(s) {
  const map = { succeeded: '成功', failed: '失败', running: '运行中', partial_succeeded: '部分成功', stopped: '已停止', waiting: '等待中' }
  return map[s] || s || '未知'
}

function formatTime(t) {
  if (!t) return ''
  // 格式: 2024-01-01 12:00:00
  const d = new Date(t.replace(' ', 'T'))
  if (isNaN(d.getTime())) return t

  const now = new Date()
  const diff = now - d

  // 1分钟内
  if (diff < 60000) return '刚刚'
  // 1小时内
  if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前'
  // 24小时内
  if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前'
  // 7天内
  if (diff < 604800000) return Math.floor(diff / 86400000) + ' 天前'

  // 超过7天显示完整日期
  return t
}

function formatInputVal(val) {
  if (val === null || val === undefined) return '-'
  const s = typeof val === 'string' ? val : JSON.stringify(val)
  return s.length > 30 ? s.substring(0, 30) + '…' : s
}

function formatJson(obj) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (e) {
    return String(obj)
  }
}

function toggleNode(nodeId) {
  expandedNodes.value[nodeId] = !expandedNodes.value[nodeId]
}

async function loadRuns(page = 1) {
  if (!props.appId) return
  loading.value = true
  try {
    let url = `/api/workflows/${encodeURIComponent(props.appId)}/runs?page=${page}&page_size=${pageSize.value}`
    if (statusFilter.value) url += `&status=${statusFilter.value}`

    const r = await fetch(url)
    const res = await r.json()
    if (res.code === 200) {
      const data = res.data || {}
      runs.value = data.items || []
      currentPage.value = data.page || page
      totalPages.value = data.total_pages || 1
    } else {
      toast(res.msg || '加载失败')
    }
  } catch (e) {
    toast('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function selectRun(run) {
  selectedRun.value = run
  expandedNodes.value = {}

  // 如果节点数据还未加载，获取详情
  if (!run.nodes || run.nodes.length === 0) {
    try {
      const r = await fetch(`/api/workflows/${encodeURIComponent(props.appId)}/runs/${run.id}`)
      const res = await r.json()
      if (res.code === 200 && res.data) {
        selectedRun.value = res.data
      }
    } catch (e) {
      // 忽略详情加载错误
    }
  }
}

onMounted(() => {
  loadRuns(1)
})
</script>

<style scoped>
.logs-tab {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #f8f9fb;
  overflow: hidden;
}

/* 工具栏 */
.logs-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.logs-filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.logs-filter-label {
  font-size: 13px;
  color: #6b7280;
}

.logs-filter-select {
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
  cursor: pointer;
}

.logs-filter-select:focus {
  outline: none;
  border-color: #4f8cff;
}

.logs-page-size {
  width: 60px;
}

.logs-refresh-btn {
  padding: 5px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.logs-refresh-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.logs-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 主内容区 */
.logs-content {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 运行列表面板 */
.logs-list-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  transition: width 0.2s;
}

.logs-list-panel.with-detail {
  width: 380px;
  min-width: 380px;
  max-width: 380px;
  border-right: 1px solid #e5e7eb;
}

.logs-run-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
}

.logs-run-item {
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
  min-width: 0;
  overflow: hidden;
}

.logs-run-item:hover {
  border-color: #4f8cff;
  box-shadow: 0 2px 8px rgba(79, 140, 255, 0.1);
}

.logs-run-item.active {
  border-color: #4f8cff;
  background: #f0f6ff;
}

.logs-run-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  min-width: 0;
  gap: 8px;
}

.logs-run-status {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.logs-run-status.succeeded { background: #ecfdf5; color: #059669; }
.logs-run-status.failed { background: #fef2f2; color: #dc2626; }
.logs-run-status.running { background: #eff6ff; color: #2563eb; }
.logs-run-status.stopped { background: #f3f4f6; color: #6b7280; }
.logs-run-status.waiting { background: #fffbeb; color: #d97706; }

.logs-run-time {
  font-size: 12px;
  color: #9ca3af;
  flex-shrink: 0;
}

.logs-run-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
  min-width: 0;
  overflow: hidden;
}

.logs-run-input-tag {
  font-size: 11px;
  padding: 2px 6px;
  background: #f3f4f6;
  border-radius: 3px;
  color: #4b5563;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logs-run-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #9ca3af;
}

/* 空状态 */
.logs-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.logs-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.4;
}

.logs-empty-text {
  font-size: 15px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 4px;
}

.logs-empty-hint {
  font-size: 13px;
  color: #9ca3af;
}

/* 分页 */
.logs-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.logs-page-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logs-page-btn:hover:not(:disabled) {
  background: #f3f4f6;
}

.logs-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.logs-page-info {
  font-size: 13px;
  color: #6b7280;
}

/* 详情面板 */
.logs-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

.logs-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.logs-detail-back {
  border: none;
  background: none;
  font-size: 14px;
  color: #4f8cff;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.logs-detail-back:hover {
  background: #eff6ff;
}

.logs-detail-title {
  font-size: 15px;
  font-weight: 600;
  flex: 1;
}

.logs-detail-status {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
}

.logs-detail-status.succeeded { background: #ecfdf5; color: #059669; }
.logs-detail-status.failed { background: #fef2f2; color: #dc2626; }
.logs-detail-status.running { background: #eff6ff; color: #2563eb; }

.logs-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.logs-detail-section {
  margin-bottom: 20px;
}

.logs-detail-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f3f4f6;
}

.logs-detail-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.logs-overview-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logs-overview-label {
  font-size: 12px;
  color: #9ca3af;
}

.logs-overview-value {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.logs-detail-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
  color: #991b1b;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

.logs-detail-json {
  background: #f8f9fb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

/* 节点列表 */
.logs-node-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.logs-node-item {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.logs-node-item.expanded {
  border-color: #d1d5db;
}

.logs-node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  background: #f9fafb;
  transition: background 0.1s;
}

.logs-node-header:hover {
  background: #f3f4f6;
}

.logs-node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.logs-node-dot.succeeded { background: #10b981; }
.logs-node-dot.failed { background: #ef4444; }
.logs-node-dot.running { background: #3b82f6; }
.logs-node-dot.stopped { background: #9ca3af; }

.logs-node-title {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logs-node-type {
  font-size: 11px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 3px;
}

.logs-node-time {
  font-size: 12px;
  color: #9ca3af;
}

.logs-node-toggle {
  font-size: 10px;
  color: #9ca3af;
  width: 16px;
  text-align: center;
}

.logs-node-detail {
  padding: 12px;
  border-top: 1px solid #f3f4f6;
  background: #fff;
}

.logs-node-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 12px;
  color: #991b1b;
  margin-bottom: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

.logs-node-section {
  margin-bottom: 8px;
}

.logs-node-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 4px;
}

.logs-node-json {
  background: #f8f9fb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 11px;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}
</style>

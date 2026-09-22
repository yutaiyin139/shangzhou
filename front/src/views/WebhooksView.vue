<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Webhook 管理</h1>
      <p class="page-desc">创建 Webhook 触发器，通过 HTTP 请求远程执行工作流</p>
    </div>

    <!-- 页签 -->
    <div class="tabs">
      <button class="tab-btn" :class="{ active: tab === 'schedule' }" @click="switchTab('schedule')">
        ⏰ 定时计划
      </button>
      <button class="tab-btn" :class="{ active: tab === 'webhook' }" @click="switchTab('webhook')">
        🔗 Webhook
      </button>
    </div>

    <!-- ============ 定时计划 ============ -->
    <template v-if="tab === 'schedule'">
      <div class="action-bar">
        <select v-model="scheduleApp" class="filter-select" @change="loadSchedules">
          <option value="">全部应用</option>
          <option v-for="app in apps" :key="app.id" :value="app.id">{{ app.name }}</option>
        </select>
        <span class="form-hint">定时计划由工作流画布中的「定时触发」节点自动生成，保存工作流后同步</span>
      </div>

      <div v-if="scheduleLoading" class="loading-state">加载中...</div>
      <div v-else-if="filteredSchedules.length === 0" class="empty-state">
        <div class="empty-icon">⏰</div>
        <p>暂无定时计划</p>
        <p class="form-hint">在工作流画布中拖入「定时触发」节点并保存，即自动生成定时计划</p>
      </div>
      <div v-else class="webhook-list">
        <div v-for="plan in filteredSchedules" :key="plan.id" class="webhook-card">
          <div class="wh-header">
            <h3 class="wh-name">{{ plan.node_title || '定时触发' }}</h3>
            <span class="wh-status" :class="plan.enabled ? 'active' : 'inactive'">
              {{ plan.enabled ? '运行中' : '已停用' }}
            </span>
          </div>
          <div class="wh-meta">
            <span class="meta-item">📅 {{ plan.cron_expr }}</span>
            <span class="meta-item">🌍 {{ plan.timezone }}</span>
            <span v-if="plan.next_run_at" class="meta-item">⏭ 下次: {{ formatTime(plan.next_run_at) }}</span>
            <span v-if="plan.last_run_at" class="meta-item">🕐 上次: {{ formatTime(plan.last_run_at) }}</span>
            <span class="meta-item">🔢 {{ plan.run_count }} 次</span>
          </div>
          <div class="wh-cron-edit">
            <input
              v-model="plan.cron_expr"
              type="text"
              class="form-input cron-input"
              placeholder="分 时 日 月 周"
              @keyup.enter="saveCron(plan)"
            />
            <button class="btn btn-sm" @click="saveCron(plan)">保存 Cron</button>
          </div>
          <div class="wh-actions">
            <button class="btn btn-sm" @click="toggleSchedule(plan)">
              {{ plan.enabled ? '停用' : '启用' }}
            </button>
            <button class="btn btn-sm btn-danger-outline" @click="deleteSchedule(plan)">删除</button>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ Webhook（原有功能） ============ -->
    <template v-else>
    <!-- 操作栏 -->
    <div class="action-bar">
      <button class="btn btn-primary" @click="showCreateModal = true">+ 新建 Webhook</button>
      <select v-model="filterApp" class="filter-select" @change="loadWebhooks">
        <option value="">全部应用</option>
        <option v-for="app in apps" :key="app.id" :value="app.id">{{ app.name }}</option>
      </select>
    </div>

    <!-- Webhook 列表 -->
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="webhooks.length === 0" class="empty-state">
      <div class="empty-icon">🔗</div>
      <p>暂无 Webhook</p>
      <button class="btn btn-primary" @click="showCreateModal = true">创建第一个 Webhook</button>
    </div>
    <div v-else class="webhook-list">
      <div v-for="wh in webhooks" :key="wh.id" class="webhook-card">
        <div class="wh-header">
          <h3 class="wh-name">{{ wh.name }}</h3>
          <span class="wh-status" :class="wh.is_active ? 'active' : 'inactive'">
            {{ wh.is_active ? '激活' : '停用' }}
          </span>
        </div>
        <p class="wh-desc">{{ wh.description || '暂无描述' }}</p>
        <div class="wh-url">
          <code>{{ wh.trigger_url }}</code>
          <button class="btn btn-sm" @click="copyUrl(wh.trigger_url)">复制</button>
        </div>
        <div class="wh-meta">
          <span class="meta-item">📊 {{ wh.call_count }} 次调用</span>
          <span v-if="wh.last_called_at" class="meta-item">🕐 最后: {{ formatTime(wh.last_called_at) }}</span>
          <span v-if="wh.last_status" class="meta-item" :class="wh.last_status">
            {{ wh.last_status === 'success' ? '✓ 成功' : '✗ 失败' }}
          </span>
        </div>
        <div class="wh-actions">
          <button class="btn btn-sm" @click="viewLogs(wh)">查看日志</button>
          <button class="btn btn-sm" @click="testWebhook(wh)">测试</button>
          <button class="btn btn-sm btn-danger-outline" @click="regenerateKey(wh)">重置密钥</button>
          <button class="btn btn-sm btn-danger-outline" @click="deleteWebhook(wh)">删除</button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="currentPage === 1" class="btn btn-sm" @click="changePage(currentPage - 1)">
        上一页
      </button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button :disabled="currentPage === totalPages" class="btn btn-sm" @click="changePage(currentPage + 1)">
        下一页
      </button>
    </div>

    <!-- 新建 Webhook 弹窗 -->
    <div v-if="showCreateModal" class="modal-mask show">
      <div class="modal-content">
        <div class="modal-header">
          <h2>新建 Webhook</h2>
          <button class="modal-close" @click="showCreateModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">关联应用 <span class="required">*</span></label>
            <select v-model="newWebhook.app_id" class="form-input">
              <option value="">选择工作流应用</option>
              <option v-for="app in apps" :key="app.id" :value="app.id">{{ app.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">名称 <span class="required">*</span></label>
            <input v-model="newWebhook.name" type="text" class="form-input" placeholder="输入 Webhook 名称" />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="newWebhook.description" class="form-input" rows="2" placeholder="描述（可选）" />
          </div>
          <div class="form-group">
            <label class="form-label">输入参数 Schema (JSON)</label>
            <textarea v-model="newWebhook.input_schema_text" class="form-input" rows="4" placeholder='{"type":"object","properties":{"query":{"type":"string"}}}' />
            <span class="form-hint">定义 Webhook 接收的输入参数格式</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createWebhook" :disabled="!canCreate">
            创建
          </button>
        </div>
      </div>
    </div>

    <!-- 日志弹窗 -->
    <div v-if="logModal" class="modal-mask show">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h2>调用日志 - {{ logWebhook?.name }}</h2>
          <button class="modal-close" @click="logModal = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="logs.length === 0" class="empty-state">
            <p>暂无调用记录</p>
          </div>
          <div v-else class="log-list">
            <div v-for="log in logs" :key="log.id" class="log-item" :class="log.status">
              <div class="log-header">
                <span class="log-status">{{ log.status === 'success' ? '✓' : '✗' }}</span>
                <span class="log-code">{{ log.response_code }}</span>
                <span class="log-ms">{{ log.elapsed_ms }}ms</span>
                <span class="log-time">{{ formatTime(log.created_at) }}</span>
              </div>
              <div v-if="log.error_message" class="log-error">{{ log.error_message }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="logModal = false">关闭</button>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

interface SchedulePlan {
  id: string
  app_id: string
  node_id: string
  node_title: string
  cron_expr: string
  timezone: string
  enabled: boolean | number
  last_run_at: string
  next_run_at: string
  run_count: number
  last_status: string
  last_error: string
  created_at: string
}

const tab = ref<'schedule' | 'webhook'>('schedule')
const schedules = ref<SchedulePlan[]>([])
const scheduleApp = ref('')
const scheduleLoading = ref(false)

const filteredSchedules = computed(() => {
  return scheduleApp.value
    ? schedules.value.filter(p => p.app_id === scheduleApp.value)
    : schedules.value
})

const switchTab = (t: 'schedule' | 'webhook') => {
  tab.value = t
  if (t === 'schedule') loadSchedules()
}

const loadSchedules = async () => {
  scheduleLoading.value = true
  try {
    // 后端按应用过滤，按已加载的应用列表逐个拉取定时计划
    const results: SchedulePlan[] = []
    for (const app of apps.value) {
      const r = await apiGet<SchedulePlan[]>(`/api/workflows/${app.id}/schedules`)
      if (r.code === 200 && Array.isArray(r.data)) {
        results.push(...r.data)
      }
    }
    schedules.value = results
  } finally {
    scheduleLoading.value = false
  }
}

const saveCron = async (plan: SchedulePlan) => {
  const res = await apiPut(`/api/workflows/schedules/${plan.id}`, { cron_expr: plan.cron_expr })
  if (res.code === 200) {
    alert('Cron 已更新')
    loadSchedules()
  } else {
    alert('更新失败: ' + res.msg)
  }
}

const toggleSchedule = async (plan: SchedulePlan) => {
  const res = await apiPut(`/api/workflows/schedules/${plan.id}`, { enabled: !plan.enabled })
  if (res.code === 200) {
    loadSchedules()
  } else {
    alert('操作失败: ' + res.msg)
  }
}

const deleteSchedule = async (plan: SchedulePlan) => {
  if (!confirm(`确定删除定时计划「${plan.node_title || plan.cron_expr}」？`)) return
  const res = await apiDelete(`/api/workflows/schedules/${plan.id}`)
  if (res.code === 200) {
    loadSchedules()
  } else {
    alert('删除失败: ' + res.msg)
  }
}

interface Webhook {
  id: string
  app_id: string
  name: string
  description: string
  webhook_key: string
  trigger_url: string
  input_schema: any
  is_active: boolean
  call_count: number
  last_called_at: string
  last_status: string
  created_at: string
  updated_at: string
}

interface WebhookLog {
  id: string
  webhook_id: string
  status: string
  response_code: number
  error_message: string
  elapsed_ms: number
  created_at: string
}

interface App {
  id: string
  name: string
  mode: string
}

const webhooks = ref<Webhook[]>([])
const apps = ref<App[]>([])
const logs = ref<WebhookLog[]>([])
const filterApp = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalPages = ref(1)
const loading = ref(false)
const showCreateModal = ref(false)
const logModal = ref(false)
const logWebhook = ref<Webhook | null>(null)

const newWebhook = ref({
  app_id: '',
  name: '',
  description: '',
  input_schema_text: '',
})

const canCreate = computed(() => {
  return newWebhook.value.app_id !== '' && newWebhook.value.name.trim() !== ''
})

const formatTime = (t: string) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN')
}

const loadWebhooks = async () => {
  loading.value = true
  try {
    const res = await apiGet<{
      items: Webhook[]
      total: number
      page: number
      page_size: number
    }>('/api/webhooks', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        app_id: filterApp.value,
      },
    })
    if (res.code === 200) {
      webhooks.value = res.data.items
      totalPages.value = Math.ceil(res.data.total / pageSize.value)
    }
  } finally {
    loading.value = false
  }
}

const loadApps = async () => {
  const res = await apiGet('/api/workflows', { params: { page_size: 100 } })
  if (res.code === 200) {
    const data = res.data as { items?: App[] } | App[]
    apps.value = Array.isArray(data) ? data : (data.items || [])
  }
}

const changePage = (page: number) => {
  currentPage.value = page
  loadWebhooks()
}

const createWebhook = async () => {
  if (!canCreate.value) return
  let inputSchema: any = {}
  if (newWebhook.value.input_schema_text.trim()) {
    try {
      inputSchema = JSON.parse(newWebhook.value.input_schema_text)
    } catch (e) {
      alert('输入参数 Schema 格式错误，请输入有效的 JSON')
      return
    }
  }

  const res = await apiPost<{
    id: string
    webhook_key: string
    trigger_url: string
  }>('/api/webhooks', {
    app_id: newWebhook.value.app_id,
    name: newWebhook.value.name,
    description: newWebhook.value.description,
    input_schema: inputSchema,
  })
  if (res.code === 200) {
    showCreateModal.value = false
    newWebhook.value = { app_id: '', name: '', description: '', input_schema_text: '' }
    loadWebhooks()
    alert(`Webhook 创建成功！\n触发 URL: ${res.data.trigger_url}`)
  } else {
    alert('创建失败: ' + res.msg)
  }
}

const copyUrl = (url: string) => {
  navigator.clipboard.writeText(url).then(() => {
    alert('已复制到剪贴板')
  })
}

const testWebhook = async (wh: Webhook) => {
  if (!confirm(`确定测试 Webhook "${wh.name}"？`)) return
  try {
    const res = await fetch(wh.trigger_url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ test: true, message: '测试调用' }),
    })
    const data = await res.json()
    if (data.code === 200) {
      alert('测试成功！')
    } else {
      alert('测试失败: ' + data.msg)
    }
    loadWebhooks()
  } catch (e: any) {
    alert('测试失败: ' + e.message)
  }
}

const regenerateKey = async (wh: Webhook) => {
  if (!confirm('确定重置 Webhook 密钥？旧密钥将立即失效。')) return
  const res = await apiPost<{ webhook_key: string; trigger_url: string }>(
    `/api/webhooks/${wh.id}/regenerate-key`,
    {}
  )
  if (res.code === 200) {
    alert(`密钥已更新！\n新 URL: ${res.data.trigger_url}`)
    loadWebhooks()
  } else {
    alert('重置失败: ' + res.msg)
  }
}

const deleteWebhook = async (wh: Webhook) => {
  if (!confirm(`确定删除 Webhook "${wh.name}"？`)) return
  const res = await apiDelete(`/api/webhooks/${wh.id}`)
  if (res.code === 200) {
    loadWebhooks()
  } else {
    alert('删除失败: ' + res.msg)
  }
}

const viewLogs = async (wh: Webhook) => {
  logWebhook.value = wh
  logModal.value = true
  const res = await apiGet<{ items: WebhookLog[] }>(`/api/webhooks/${wh.id}/logs`, {
    params: { page_size: 50 },
  })
  if (res.code === 200) {
    logs.value = res.data.items
  }
}

onMounted(async () => {
  await loadApps()
  loadWebhooks()
  loadSchedules()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.page-desc {
  color: #86909c;
  font-size: 14px;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e5e6eb;
}

.tab-btn {
  padding: 10px 18px;
  border: none;
  background: none;
  font-size: 14px;
  color: #86909c;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab-btn.active {
  color: #2e63f0;
  border-bottom-color: #2e63f0;
  font-weight: 600;
}

.wh-cron-edit {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.cron-input {
  width: 200px;
  font-family: monospace;
}

.filter-select {
  padding: 10px 16px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  outline: none;
}

.webhook-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.webhook-card {
  background: white;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
}

.webhook-card:hover {
  border-color: #2e63f0;
  box-shadow: 0 2px 8px rgba(46, 99, 240, 0.08);
}

.wh-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.wh-name {
  font-size: 16px;
  font-weight: 600;
}

.wh-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.wh-status.active {
  background: #e8ffea;
  color: #00b42a;
}

.wh-status.inactive {
  background: #f2f3f5;
  color: #86909c;
}

.wh-desc {
  color: #86909c;
  font-size: 13px;
  margin-bottom: 12px;
}

.wh-url {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  background: #f7f8fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.wh-url code {
  flex: 1;
  font-size: 12px;
  color: #2e63f0;
  word-break: break-all;
}

.wh-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 12px;
}

.wh-meta .success {
  color: #00b42a;
}

.wh-meta .error {
  color: #f53f3f;
}

.wh-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn:hover {
  border-color: #2e63f0;
  color: #2e63f0;
}

.btn-primary {
  background: #2e63f0;
  color: white;
  border-color: #2e63f0;
}

.btn-primary:hover {
  background: #1a4dd8;
  color: white;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger-outline {
  color: #f53f3f;
  border-color: #f53f3f;
}

.btn-danger-outline:hover {
  background: #ffece8;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #86909c;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 32px;
}

.page-info {
  color: #86909c;
  font-size: 14px;
}

/* Modal */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: auto;
}

.modal-lg {
  max-width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e6eb;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #86909c;
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e6eb;
}

/* Form */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
}

.required {
  color: #f53f3f;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #2e63f0;
}

.form-hint {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
  display: block;
}

textarea.form-input {
  resize: vertical;
  font-family: monospace;
}

select.form-input {
  cursor: pointer;
}

/* Logs */
.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-item {
  padding: 12px;
  border-radius: 8px;
  background: #f7f8fa;
  border-left: 4px solid #f53f3f;
}

.log-item.success {
  border-left-color: #00b42a;
}

.log-header {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}

.log-status {
  font-weight: 700;
}

.log-item.success .log-status {
  color: #00b42a;
}

.log-item.error .log-status {
  color: #f53f3f;
}

.log-code {
  color: #86909c;
}

.log-ms {
  color: #86909c;
}

.log-time {
  margin-left: auto;
  color: #86909c;
  font-size: 12px;
}

.log-error {
  margin-top: 6px;
  font-size: 12px;
  color: #f53f3f;
  word-break: break-word;
}
</style>

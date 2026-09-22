<template>
  <AppShell id="page-root" active-key="audit" main-class="main-white">
    <div class="page-pad">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">操作日志</h1>
        <p class="page-subtitle">记录平台关键操作，用于安全审计和合规检查</p>
      </div>

      <!-- 统计卡片 -->
      <div class="audit-stats">
        <div class="stat-card">
          <div class="stat-label">总操作数</div>
          <div class="stat-value">{{ stats.total || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">成功</div>
          <div class="stat-value stat-success">{{ stats.status_stats?.success || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">失败</div>
          <div class="stat-value stat-failed">{{ stats.status_stats?.failed || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">近 {{ stats.period_days || 7 }} 天</div>
          <div class="stat-value">{{ recentCount }}</div>
        </div>
      </div>

      <!-- 筛选工具条 -->
      <div class="audit-filter">
        <div class="filter-left">
          <select v-model="filter.action" @change="loadLogs" class="filter-select">
            <option value="">全部操作</option>
            <option value="login">登录</option>
            <option value="logout">登出</option>
            <option value="login_failed">登录失败</option>
            <option value="run_workflow">运行工作流</option>
            <option value="run_workflow_failed">运行失败</option>
            <option value="delete_workflow">删除工作流</option>
            <option value="create_workflow">创建工作流</option>
            <option value="publish_workflow">发布工作流</option>
          </select>
          <select v-model="filter.status" @change="loadLogs" class="filter-select">
            <option value="">全部状态</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
          </select>
          <input
            v-model="filter.keyword"
            @keyup.enter="loadLogs"
            class="filter-input"
            placeholder="搜索用户/资源/描述"
          />
          <button class="btn btn-primary" @click="loadLogs">查询</button>
          <button class="btn" @click="resetFilter">重置</button>
        </div>
        <div class="filter-right">
          <button class="btn btn-danger" @click="confirmCleanup" :disabled="!hasPermission">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="14" height="14"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>
            清理日志
          </button>
        </div>
      </div>

      <!-- 日志表格 -->
      <div class="table-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th style="width:160px">时间</th>
              <th style="width:120px">用户</th>
              <th style="width:140px">操作</th>
              <th style="width:100px">资源类型</th>
              <th>描述</th>
              <th style="width:80px">状态</th>
              <th style="width:100px">IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td class="cell-time">{{ log.created_at }}</td>
              <td>
                <div class="cell-user">
                  <span class="user-name">{{ log.user_name || '-' }}</span>
                  <span class="user-email" v-if="log.user_email">{{ log.user_email }}</span>
                </div>
              </td>
              <td>
                <span class="action-badge" :class="'action-' + log.action.split('_')[0]">
                  {{ actionLabel(log.action) }}
                </span>
              </td>
              <td>{{ resourceTypeLabel(log.resource_type) }}</td>
              <td class="cell-desc">
                <div class="desc-text" :title="log.description">{{ log.description || '-' }}</div>
                <div class="error-text" v-if="log.error_message">{{ log.error_message }}</div>
              </td>
              <td>
                <span class="status-badge" :class="log.status === 'success' ? 'status-success' : 'status-failed'">
                  {{ log.status === 'success' ? '成功' : '失败' }}
                </span>
              </td>
              <td class="cell-ip">{{ log.ip_address || '-' }}</td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="7" class="empty-cell">
                <div class="empty-content">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg>
                  <div>暂无日志记录</div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="totalPages > 1">
        <button class="btn" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="btn" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
        <select v-model.number="pageSize" @change="loadLogs" class="page-size-select">
          <option :value="10">10 条/页</option>
          <option :value="20">20 条/页</option>
          <option :value="50">50 条/页</option>
        </select>
        <span class="total-info">共 {{ total }} 条</span>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { apiGet, apiDelete } from '../api/client'

// 数据
const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref({})

// 筛选
const filter = reactive({
  action: '',
  status: '',
  keyword: '',
})

// 权限
const hasPermission = ref(true)

// 计算属性
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const recentCount = computed(() => {
  const dateStats = stats.value.date_stats || []
  return dateStats.reduce((sum, d) => sum + d.count, 0)
})

// 操作类型标签
const ACTION_LABELS = {
  login: '登录',
  logout: '登出',
  login_failed: '登录失败',
  run_workflow: '运行工作流',
  run_workflow_failed: '运行失败',
  delete_workflow: '删除工作流',
  create_workflow: '创建工作流',
  publish_workflow: '发布工作流',
  cleanup_audit_logs: '清理日志',
}

// 资源类型标签
const RESOURCE_TYPE_LABELS = {
  user: '用户',
  workflow: '工作流',
  knowledge: '知识库',
  agent: '智能体',
  model: '模型',
  audit: '审计',
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

function resourceTypeLabel(type) {
  return RESOURCE_TYPE_LABELS[type] || type || '-'
}

// 加载日志
async function loadLogs() {
  try {
    const data = await apiGet('/api/audit/logs', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        action: filter.action,
        status: filter.status,
        keyword: filter.keyword,
      },
    })
    if (data.code === 200) {
      logs.value = data.data.items
      total.value = data.data.total
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

// 加载统计
async function loadStats() {
  try {
    const data = await apiGet('/api/audit/stats', { params: { days: 7 } })
    if (data.code === 200) {
      stats.value = data.data
    }
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

// 分页
function changePage(p) {
  page.value = p
  loadLogs()
}

// 重置筛选
function resetFilter() {
  filter.action = ''
  filter.status = ''
  filter.keyword = ''
  page.value = 1
  loadLogs()
}

// 清理日志
async function confirmCleanup() {
  const days = prompt('保留最近多少天的日志？（最少 7 天，最多 365 天）', '90')
  if (!days) return
  const retainDays = parseInt(days)
  if (isNaN(retainDays) || retainDays < 7 || retainDays > 365) {
    alert('请输入 7-365 之间的数字')
    return
  }
  if (!confirm(`确定要清理 ${retainDays} 天前的日志吗？此操作不可恢复。`)) return

  try {
    const data = await apiDelete('/api/audit/logs', { body: { retain_days: retainDays } })
    if (data.code === 200) {
      alert(data.msg)
      loadLogs()
      loadStats()
    } else {
      alert(data.msg || '清理失败')
    }
  } catch (e) {
    alert('清理失败: ' + e.message)
  }
}

// 初始化
onMounted(() => {
  loadLogs()
  loadStats()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

/* 统计卡片 */
.audit-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
}
.stat-success { color: #00B42A; }
.stat-failed { color: #F53F3F; }

/* 筛选 */
.audit-filter {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.filter-left {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.filter-select,
.filter-input {
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: var(--text-primary);
}
.filter-input {
  width: 200px;
}
.filter-select:focus,
.filter-input:focus {
  outline: none;
  border-color: var(--primary);
}
.filter-right {
  display: flex;
  gap: 8px;
}

/* 表格 */
.table-wrap {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th {
  background: #f7f8fa;
  padding: 10px 12px;
  text-align: left;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.tbl td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  color: var(--text-primary);
  vertical-align: top;
}
.tbl tr:last-child td {
  border-bottom: none;
}
.tbl tr:hover td {
  background: #fafbfc;
}

.cell-time {
  white-space: nowrap;
  color: var(--text-secondary);
  font-size: 12px;
}
.cell-user {
  display: flex;
  flex-direction: column;
}
.user-name {
  font-weight: 500;
}
.user-email {
  font-size: 11px;
  color: var(--text-tertiary);
}
.cell-desc {
  max-width: 300px;
}
.desc-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.error-text {
  font-size: 11px;
  color: #F53F3F;
  margin-top: 2px;
}
.cell-ip {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 操作标签 */
.action-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #e8f4ff;
  color: #165DFF;
}
.action-login { background: #e8f4ff; color: #165DFF; }
.action-logout { background: #f0f0f0; color: #666; }
.action-login_failed,
.action-run_workflow_failed { background: #ffece8; color: #F53F3F; }
.action-run_workflow,
.action-create_workflow,
.action-publish_workflow { background: #e8fffb; color: #00B42A; }
.action-delete_workflow { background: #ffece8; color: #F53F3F; }

/* 状态标签 */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.status-success {
  background: #e8fffb;
  color: #00B42A;
}
.status-failed {
  background: #ffece8;
  color: #F53F3F;
}

/* 空状态 */
.empty-cell {
  text-align: center;
  padding: 60px 0 !important;
}
.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-tertiary);
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  justify-content: flex-end;
}
.page-info {
  font-size: 13px;
  color: var(--text-secondary);
}
.page-size-select {
  padding: 5px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 13px;
}
.total-info {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* 按钮 */
.btn {
  padding: 7px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}
.btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.btn-primary:hover {
  background: var(--primary-hover);
  color: #fff;
}
.btn-danger {
  color: #F53F3F;
  border-color: #F53F3F;
}
.btn-danger:hover {
  background: #F53F3F;
  color: #fff;
}
</style>

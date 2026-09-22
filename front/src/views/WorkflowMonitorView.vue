<template>
  <AppShell id="page-root" active-key="wf-monitor" main-class="main-white">
    <div class="page-pad">
      <!-- 顶部导航 -->
      <header class="monitor-header">
        <div class="mh-left">
          <span class="mh-title">📊 监控仪表盘</span>
        </div>
        <div class="mh-right">
          <select v-model="selectedAppId" class="mh-select" @change="loadAllData">
            <option value="">全部工作流</option>
            <option v-for="w in workflows" :key="w.id" :value="w.id">{{ w.name }}</option>
          </select>
          <select v-model="timeRange" class="mh-select" @change="loadAllData">
            <option value="1h">近 1 小时</option>
            <option value="6h">近 6 小时</option>
            <option value="24h">近 24 小时</option>
            <option value="7d">近 7 天</option>
            <option value="30d">近 30 天</option>
          </select>
          <button class="mh-refresh" @click="loadAllData" :disabled="loading">🔄 刷新</button>
        </div>
      </header>

      <!-- 概览卡片 -->
      <div class="monitor-overview">
        <div class="mo-card">
          <div class="mo-card-value">{{ overview.totalRuns || 0 }}</div>
          <div class="mo-card-label">总执行次数</div>
          <div class="mo-card-trend" :class="trendClass(overview.runTrend)">
            {{ trendText(overview.runTrend) }}
          </div>
        </div>
        <div class="mo-card">
          <div class="mo-card-value">{{ formatDuration(overview.avgDuration || 0) }}</div>
          <div class="mo-card-label">平均耗时</div>
          <div class="mo-card-trend" :class="trendClass(-overview.durationTrend)">
            {{ trendText(-overview.durationTrend) }}
          </div>
        </div>
        <div class="mo-card">
          <div class="mo-card-value" style="color: var(--success)">{{ overview.successRate || 0 }}%</div>
          <div class="mo-card-label">成功率</div>
          <div class="mo-card-trend" :class="trendClass(overview.successTrend)">
            {{ trendText(overview.successTrend) }}
          </div>
        </div>
        <div class="mo-card">
          <div class="mo-card-value" style="color: var(--danger)">{{ overview.totalErrors || 0 }}</div>
          <div class="mo-card-label">错误次数</div>
          <div class="mo-card-trend" :class="trendClass(-overview.errorTrend)">
            {{ trendText(-overview.errorTrend) }}
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="monitor-charts">
        <!-- 执行趋势图 -->
        <div class="mc-card">
          <div class="mc-card-title">执行趋势</div>
          <div class="mc-chart-area">
            <LineChart v-if="trendData.length > 0" :data="trendData" :height="220" />
            <div v-else class="mc-chart-empty">暂无数据</div>
          </div>
        </div>

        <!-- 节点耗时分布 -->
        <div class="mc-card">
          <div class="mc-card-title">节点耗时分布 (ms)</div>
          <div class="mc-chart-area">
            <BarChart v-if="nodeDurationData.length > 0" :data="nodeDurationData" :height="220" />
            <div v-else class="mc-chart-empty">暂无数据</div>
          </div>
        </div>
      </div>

      <!-- 错误排行 + 最近执行 -->
      <div class="monitor-bottom">
        <!-- 错误排行 -->
        <div class="mb-card">
          <div class="mb-card-title">🔥 高频错误</div>
          <div class="mb-card-body">
            <div v-if="topErrors.length === 0" class="mb-empty">暂无错误记录</div>
            <div v-for="(err, idx) in topErrors" :key="idx" class="mb-error-row">
              <div class="mb-error-count">{{ err.count }}x</div>
              <div class="mb-error-msg">{{ err.message }}</div>
              <div class="mb-error-node">{{ err.node_type }}</div>
            </div>
          </div>
        </div>

        <!-- 最近执行 -->
        <div class="mb-card">
          <div class="mb-card-title">🕐 最近执行</div>
          <div class="mb-card-body">
            <div v-if="recentRuns.length === 0" class="mb-empty">暂无执行记录</div>
            <div v-for="run in recentRuns" :key="run.id" class="mb-run-row">
              <div class="mb-run-status" :class="'mb-status-' + run.status"></div>
              <div class="mb-run-info">
                <div class="mb-run-name">{{ run.app_name || run.app_id }}</div>
                <div class="mb-run-meta">
                  <span>{{ formatTime(run.created_at) }}</span>
                  <span>{{ formatDuration(run.duration) }}</span>
                </div>
              </div>
              <button class="mb-run-detail" @click="viewRunDetail(run)">详情</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 告警配置 -->
      <div class="monitor-alerts">
        <div class="ma-title">⚠️ 告警配置</div>
        <div class="ma-list">
          <div v-for="(alert, idx) in alerts" :key="idx" class="ma-item">
            <div class="ma-item-label">{{ alert.label }}</div>
            <div class="ma-item-condition">{{ alert.condition }}</div>
            <div class="ma-item-status" :class="{ active: alert.enabled }">
              {{ alert.enabled ? '已启用' : '已禁用' }}
            </div>
            <label class="ma-toggle">
              <input type="checkbox" v-model="alert.enabled" @change="saveAlert(alert)" />
              <span class="ma-toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 执行详情弹窗 -->
    <div v-if="detailRun" class="monitor-modal" @click.self="detailRun = null">
      <div class="mm-content">
        <div class="mm-header">
          <span>执行详情</span>
          <button class="mm-close" @click="detailRun = null">✕</button>
        </div>
        <div class="mm-body">
          <div class="mm-row"><span>ID:</span><span>{{ detailRun.id }}</span></div>
          <div class="mm-row"><span>状态:</span><span>{{ detailRun.status }}</span></div>
          <div class="mm-row"><span>耗时:</span><span>{{ formatDuration(detailRun.duration) }}</span></div>
          <div class="mm-row"><span>开始:</span><span>{{ detailRun.created_at }}</span></div>
          <div class="mm-row"><span>结束:</span><span>{{ detailRun.finished_at || '-' }}</span></div>
          <div v-if="detailRun.error_message" class="mm-error">
            {{ detailRun.error_message }}
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { apiGet, apiPost } from '../api/client'
import { toast } from '../utils/global'
import LineChart from '../components/charts/LineChart.vue'
import BarChart from '../components/charts/BarChart.vue'

const loading = ref(false)
const selectedAppId = ref('')
const timeRange = ref('24h')
const workflows = ref([])
const overview = ref({})
const trendData = ref([])
const nodeDurationData = ref([])
const topErrors = ref([])
const recentRuns = ref([])
const alerts = ref([])
const detailRun = ref(null)

async function loadWorkflows() {
  try {
    const res = await apiGet('/api/workflows')
    if (res.code === 200) {
      workflows.value = res.data.items || res.data || []
    }
  } catch (e) {
    // silent
  }
}

async function loadOverview() {
  try {
    const params = { range: timeRange.value }
    if (selectedAppId.value) params.app_id = selectedAppId.value
    const res = await apiGet('/api/monitor/overview', { params })
    if (res.code === 200) {
      overview.value = res.data
    }
  } catch (e) {
    // silent
  }
}

async function loadTrend() {
  try {
    const params = { range: timeRange.value }
    if (selectedAppId.value) params.app_id = selectedAppId.value
    const res = await apiGet('/api/monitor/trend', { params })
    if (res.code === 200) {
      trendData.value = res.data.items || []
    }
  } catch (e) {
    trendData.value = []
  }
}

async function loadNodeDuration() {
  try {
    const params = { range: timeRange.value }
    if (selectedAppId.value) params.app_id = selectedAppId.value
    const res = await apiGet('/api/monitor/node-duration', { params })
    if (res.code === 200) {
      nodeDurationData.value = res.data.items || []
    }
  } catch (e) {
    nodeDurationData.value = []
  }
}

async function loadTopErrors() {
  try {
    const params = { range: timeRange.value, limit: 10 }
    if (selectedAppId.value) params.app_id = selectedAppId.value
    const res = await apiGet('/api/monitor/top-errors', { params })
    if (res.code === 200) {
      topErrors.value = res.data.items || []
    }
  } catch (e) {
    topErrors.value = []
  }
}

async function loadRecentRuns() {
  try {
    const params = { limit: 20 }
    if (selectedAppId.value) params.app_id = selectedAppId.value
    const res = await apiGet('/api/monitor/recent-runs', { params })
    if (res.code === 200) {
      recentRuns.value = res.data.items || []
    }
  } catch (e) {
    recentRuns.value = []
  }
}

async function loadAlerts() {
  try {
    const res = await apiGet('/api/monitor/alerts')
    if (res.code === 200) {
      alerts.value = res.data.items || defaultAlerts()
    } else {
      alerts.value = defaultAlerts()
    }
  } catch (e) {
    alerts.value = defaultAlerts()
  }
}

function defaultAlerts() {
  return [
    { id: 'err_rate', label: '错误率告警', condition: '错误率 > 5%', enabled: true },
    { id: 'duration', label: '耗时告警', condition: '执行耗时 > 30s', enabled: true },
    { id: 'fail_count', label: '连续失败告警', condition: '连续失败 > 3 次', enabled: false },
    { id: 'node_err', label: '节点错误告警', condition: '节点执行失败', enabled: true },
  ]
}

async function saveAlert(alert) {
  try {
    await apiPost('/api/monitor/alerts/' + alert.id, { enabled: alert.enabled })
    toast(alert.enabled ? '已启用' : '已禁用')
  } catch (e) {
    toast('保存失败')
  }
}

async function loadAllData() {
  loading.value = true
  await Promise.all([
    loadOverview(),
    loadTrend(),
    loadNodeDuration(),
    loadTopErrors(),
    loadRecentRuns(),
  ])
  loading.value = false
}

function viewRunDetail(run) {
  detailRun.value = run
}

function formatDuration(ms) {
  if (!ms || ms < 0) return '0ms'
  if (ms < 1000) return ms + 'ms'
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's'
  const min = Math.floor(ms / 60000)
  const sec = Math.floor((ms % 60000) / 1000)
  return min + 'm' + sec + 's'
}

function formatTime(t) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    const now = new Date()
    const diff = (now - d) / 1000
    if (diff < 60) return '刚刚'
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
    if (diff < 604800) return Math.floor(diff / 86400) + ' 天前'
    return d.toLocaleDateString()
  } catch (e) {
    return t
  }
}

function trendClass(val) {
  if (val > 0.05) return 'trend-up'
  if (val < -0.05) return 'trend-down'
  return 'trend-flat'
}

function trendText(val) {
  if (Math.abs(val) < 0.01) return '—'
  const pct = (Math.abs(val) * 100).toFixed(1)
  if (val > 0) return '↑' + pct + '%'
  return '↓' + pct + '%'
}

onMounted(async () => {
  await loadWorkflows()
  await loadAllData()
  await loadAlerts()
})

onUnmounted(() => {
  // 清理数据，释放内存
  workflows.value = []
  overview.value = {}
  trendData.value = []
  nodeDurationData.value = []
  topErrors.value = []
  recentRuns.value = []
  alerts.value = []
  detailRun.value = null
})
</script>

<style scoped>
.monitor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.mh-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mh-back {
  font-size: 22px;
  color: var(--text-2);
  text-decoration: none;
  padding: 2px 8px;
  border-radius: 4px;
}

.mh-back:hover {
  background: var(--bg-hover);
}

.mh-sep {
  color: var(--text-4);
}

.mh-title {
  font-size: 18px;
  font-weight: 700;
}

.mh-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.mh-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--input-bg);
  color: var(--text-1);
  font-size: 13px;
}

.mh-refresh {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-2);
  color: var(--text-1);
  cursor: pointer;
  font-size: 13px;
}

.mh-refresh:hover {
  background: var(--bg-hover);
}

.mh-refresh:disabled {
  opacity: 0.5;
}

/* 概览卡片 */
.monitor-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.mo-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.mo-card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-1);
}

.mo-card-label {
  font-size: 13px;
  color: var(--text-3);
  margin-top: 4px;
}

.mo-card-trend {
  font-size: 12px;
  margin-top: 6px;
}

.trend-up {
  color: var(--success);
}

.trend-down {
  color: var(--danger);
}

.trend-flat {
  color: var(--text-4);
}

/* 图表区域 */
.monitor-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.mc-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}

.mc-card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.mc-chart-area {
  min-height: 220px;
}

.mc-chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 220px;
  color: var(--text-4);
  font-size: 13px;
}

/* 底部区域 */
.monitor-bottom {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.mb-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}

.mb-card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.mb-card-body {
  max-height: 250px;
  overflow-y: auto;
}

.mb-empty {
  text-align: center;
  color: var(--text-4);
  font-size: 13px;
  padding: 20px;
}

.mb-error-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-light);
}

.mb-error-count {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.mb-error-msg {
  flex: 1;
  font-size: 12px;
  color: var(--text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mb-error-node {
  font-size: 11px;
  color: var(--text-4);
  flex-shrink: 0;
}

.mb-run-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-light);
}

.mb-run-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mb-status-success {
  background: var(--success);
}

.mb-status-fail,
.mb-status-error {
  background: var(--danger);
}

.mb-status-running {
  background: #3b82f6;
}

.mb-status-pending {
  background: var(--text-4);
}

.mb-run-info {
  flex: 1;
  min-width: 0;
}

.mb-run-name {
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mb-run-meta {
  font-size: 11px;
  color: var(--text-4);
  display: flex;
  gap: 8px;
}

.mb-run-detail {
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-2);
  color: var(--text-2);
  font-size: 11px;
  cursor: pointer;
}

.mb-run-detail:hover {
  background: var(--bg-hover);
}

/* 告警配置 */
.monitor-alerts {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}

.ma-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.ma-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ma-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-1);
  border-radius: 6px;
}

.ma-item-label {
  font-size: 13px;
  font-weight: 500;
  min-width: 120px;
}

.ma-item-condition {
  flex: 1;
  font-size: 12px;
  color: var(--text-3);
  font-family: monospace;
}

.ma-item-status {
  font-size: 11px;
  color: var(--text-4);
}

.ma-item-status.active {
  color: var(--success);
}

.ma-toggle {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
}

.ma-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.ma-toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-3);
  border-radius: 10px;
  transition: 0.2s;
}

.ma-toggle-slider:before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background: white;
  border-radius: 50%;
  transition: 0.2s;
}

.ma-toggle input:checked + .ma-toggle-slider {
  background: var(--primary);
}

.ma-toggle input:checked + .ma-toggle-slider:before {
  transform: translateX(16px);
}

/* 详情弹窗 */
.monitor-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mm-content {
  background: var(--panel);
  border-radius: 10px;
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
}

.mm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
}

.mm-close {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--text-3);
}

.mm-body {
  padding: 14px 18px;
}

.mm-row {
  display: flex;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;
}

.mm-row span:first-child {
  color: var(--text-3);
  min-width: 60px;
}

.mm-error {
  margin-top: 10px;
  padding: 10px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 6px;
  font-size: 12px;
  color: var(--danger);
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .monitor-overview {
    grid-template-columns: repeat(2, 1fr);
  }
  .monitor-charts {
    grid-template-columns: 1fr;
  }
  .monitor-bottom {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Agent 评测</h1>
      <p class="page-desc">创建评测任务，测试 Agent 的响应质量和准确性</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total || 0 }}</div>
        <div class="stat-label">评测总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.running || 0 }}</div>
        <div class="stat-label">运行中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.completed || 0 }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.avg_score ? stats.avg_score.toFixed(1) : '0.0' }}</div>
        <div class="stat-label">平均得分</div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <button class="btn btn-primary" @click="showCreateModal = true">
        + 新建评测
      </button>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索评测名称..."
        class="search-input"
        @input="handleSearch"
      />
    </div>

    <!-- 评测列表 -->
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="evaluations.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无评测任务</p>
      <button class="btn btn-primary" @click="showCreateModal = true">创建第一个评测</button>
    </div>
    <div v-else class="eval-list">
      <div v-for="ev in evaluations" :key="ev.id" class="eval-card">
        <div class="eval-header">
          <h3 class="eval-name">{{ ev.name }}</h3>
          <span class="eval-status" :class="ev.status">{{ statusLabel(ev.status) }}</span>
        </div>
        <p class="eval-desc">{{ ev.description || '暂无描述' }}</p>
        <div class="eval-meta">
          <span class="meta-item">📝 {{ ev.test_case_count || 0 }} 个测试用例</span>
          <span class="meta-item">📊 {{ ev.app_name || ev.app_id }}</span>
          <span v-if="ev.score !== null" class="meta-item score">
            得分: {{ ev.score.toFixed(1) }}
          </span>
          <span class="meta-item">🕐 {{ formatTime(ev.created_at) }}</span>
        </div>
        <div class="eval-actions">
          <button
            v-if="ev.status === 'pending'"
            class="btn btn-primary btn-sm"
            @click="runEvaluation(ev)"
          >
            运行
          </button>
          <button
            v-if="ev.status === 'running'"
            class="btn btn-danger btn-sm"
            @click="stopEvaluation(ev)"
          >
            停止
          </button>
          <button
            v-if="ev.status === 'completed'"
            class="btn btn-sm"
            @click="viewResults(ev)"
          >
            查看结果
          </button>
          <button class="btn btn-sm btn-danger-outline" @click="deleteEvaluation(ev)">
            删除
          </button>
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

    <!-- 新建评测弹窗 -->
    <div v-if="showCreateModal" class="modal-mask show">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h2>新建评测</h2>
          <button class="modal-close" @click="showCreateModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">评测名称 <span class="required">*</span></label>
            <input v-model="newEval.name" type="text" class="form-input" placeholder="输入评测名称" />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="newEval.description" class="form-input" rows="2" placeholder="评测描述（可选）" />
          </div>
          <div class="form-group">
            <label class="form-label">目标应用 <span class="required">*</span></label>
            <select v-model="newEval.app_id" class="form-input">
              <option value="">选择要评测的 Agent/工作流</option>
              <option v-for="app in apps" :key="app.id" :value="app.id">
                {{ app.name }} ({{ app.mode }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">评分阈值</label>
            <input v-model.number="newEval.threshold" type="number" class="form-input" min="0" max="100" />
            <span class="form-hint">得分低于此值的用例标记为不通过（0-100）</span>
          </div>

          <div class="form-group">
            <label class="form-label">测试用例 <span class="required">*</span></label>
            <div class="test-cases">
              <div v-for="(tc, idx) in newEval.test_cases" :key="idx" class="test-case-item">
                <div class="tc-header">
                  <span class="tc-index">用例 {{ idx + 1 }}</span>
                  <button class="btn btn-sm btn-danger-outline" @click="removeTestCase(idx)">删除</button>
                </div>
                <input v-model="tc.input" type="text" class="form-input" placeholder="输入问题" />
                <input v-model="tc.expected" type="text" class="form-input" placeholder="期望输出（关键词，逗号分隔）" />
              </div>
            </div>
            <button class="btn btn-sm btn-add" @click="addTestCase">+ 添加测试用例</button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createEvaluation" :disabled="!canCreate">
            创建
          </button>
        </div>
      </div>
    </div>

    <!-- 评测结果弹窗 -->
    <div v-if="resultModal" class="modal-mask show">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <h2>评测结果 - {{ resultEval?.name }}</h2>
          <button class="modal-close" @click="resultModal = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="resultEval" class="result-summary">
            <div class="result-score">
              <div class="score-circle" :class="scoreClass(resultEval.score)">
                {{ resultEval.score?.toFixed(0) || 0 }}
              </div>
              <div class="score-label">总分</div>
            </div>
            <div class="result-stats">
              <div class="r-stat">
                <span class="r-stat-label">通过</span>
                <span class="r-stat-value pass">{{ resultEval.pass_count || 0 }}</span>
              </div>
              <div class="r-stat">
                <span class="r-stat-label">失败</span>
                <span class="r-stat-value fail">{{ resultEval.fail_count || 0 }}</span>
              </div>
              <div class="r-stat">
                <span class="r-stat-label">总用例</span>
                <span class="r-stat-value">{{ resultEval.test_case_count || 0 }}</span>
              </div>
            </div>
          </div>
          <div class="result-details">
            <div v-for="(r, idx) in resultDetails" :key="idx" class="result-item" :class="r.passed ? 'pass' : 'fail'">
              <div class="ri-header">
                <span class="ri-status">{{ r.passed ? '✓' : '✗' }}</span>
                <span class="ri-score">得分: {{ r.score?.toFixed(0) || 0 }}</span>
              </div>
              <div class="ri-question">
                <strong>Q:</strong> {{ r.input }}
              </div>
              <div class="ri-answer">
                <strong>A:</strong> {{ r.actual || r.output || '-' }}
              </div>
              <div class="ri-expected">
                <strong>期望:</strong> {{ r.expected }}
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="resultModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiGet, apiPost, apiDelete } from '../api/client'

interface Evaluation {
  id: string
  name: string
  description: string
  app_id: string
  app_name?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  score: number | null
  threshold: number
  test_case_count: number
  pass_count?: number
  fail_count?: number
  test_cases: TestCase[]
  results?: any[]
  created_at: string
  updated_at?: string
}

interface TestCase {
  input: string
  expected: string
}

interface App {
  id: string
  name: string
  mode: string
}

const evaluations = ref<Evaluation[]>([])
const apps = ref<App[]>([])
const stats = ref({ total: 0, running: 0, completed: 0, avg_score: 0 })
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = ref(1)
const loading = ref(false)
const showCreateModal = ref(false)
const resultModal = ref(false)
const resultEval = ref<Evaluation | null>(null)
const resultDetails = ref<any[]>([])

const newEval = ref({
  name: '',
  description: '',
  app_id: '',
  threshold: 60,
  test_cases: [{ input: '', expected: '' }],
})

const canCreate = computed(() => {
  return (
    newEval.value.name.trim() !== '' &&
    newEval.value.app_id !== '' &&
    newEval.value.test_cases.length > 0 &&
    newEval.value.test_cases.every((tc) => tc.input.trim() !== '')
  )
})

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待运行',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
  }
  return map[status] || status
}

const scoreClass = (score: number | null) => {
  if (score === null) return ''
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  return 'poor'
}

const formatTime = (t: string) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN')
}

const addTestCase = () => {
  newEval.value.test_cases.push({ input: '', expected: '' })
}

const removeTestCase = (idx: number) => {
  newEval.value.test_cases.splice(idx, 1)
}

const loadEvaluations = async () => {
  loading.value = true
  try {
    const res = await apiGet<{
      items: Evaluation[]
      total: number
      page: number
      page_size: number
    }>('/api/evaluations', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        q: searchQuery.value,
      } as any,
    })
    if (res.code === 200) {
      evaluations.value = res.data.items
      totalPages.value = Math.ceil(res.data.total / pageSize.value)
    }
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  const res = await apiGet<any>('/api/evaluations/stats')
  if (res.code === 200) {
    stats.value = res.data
  }
}

const loadApps = async () => {
  const res = await apiGet('/api/workflows', { params: { page_size: 100 } })
  if (res.code === 200) {
    const data = res.data as { items?: App[] } | App[]
    apps.value = Array.isArray(data) ? data : (data.items || [])
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadEvaluations()
}

const changePage = (page: number) => {
  currentPage.value = page
  loadEvaluations()
}

const createEvaluation = async () => {
  if (!canCreate.value) return
  const res = await apiPost<{ id: string }>('/api/evaluations', {
    name: newEval.value.name,
    description: newEval.value.description,
    app_id: newEval.value.app_id,
    threshold: newEval.value.threshold,
    test_cases: newEval.value.test_cases,
  })
  if (res.code === 200) {
    showCreateModal.value = false
    newEval.value = {
      name: '',
      description: '',
      app_id: '',
      threshold: 60,
      test_cases: [{ input: '', expected: '' }],
    }
    loadEvaluations()
    loadStats()
  } else {
    alert('创建失败: ' + res.msg)
  }
}

const runEvaluation = async (ev: Evaluation) => {
  const res = await apiPost(`/api/evaluations/${ev.id}/run`, {})
  if (res.code === 200) {
    loadEvaluations()
  } else {
    alert('启动失败: ' + res.msg)
  }
}

const stopEvaluation = async (ev: Evaluation) => {
  if (!confirm('确定停止此评测？')) return
  const res = await apiPost(`/api/evaluations/${ev.id}/stop`, {})
  if (res.code === 200) {
    loadEvaluations()
  }
}

const deleteEvaluation = async (ev: Evaluation) => {
  if (!confirm(`确定删除评测 "${ev.name}"？`)) return
  const res = await apiDelete(`/api/evaluations/${ev.id}`)
  if (res.code === 200) {
    loadEvaluations()
    loadStats()
  }
}

const viewResults = (ev: Evaluation) => {
  resultEval.value = ev
  resultDetails.value = ev.results || []
  resultModal.value = true
}

onMounted(() => {
  loadEvaluations()
  loadStats()
  loadApps()
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

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2e63f0;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #86909c;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  max-width: 300px;
  padding: 10px 16px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: #2e63f0;
}

.eval-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.eval-card {
  background: white;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
}

.eval-card:hover {
  border-color: #2e63f0;
  box-shadow: 0 2px 8px rgba(46, 99, 240, 0.08);
}

.eval-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.eval-name {
  font-size: 16px;
  font-weight: 600;
}

.eval-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.eval-status.pending {
  background: #fff7e8;
  color: #ff7d00;
}

.eval-status.running {
  background: #e8f3ff;
  color: #2e63f0;
}

.eval-status.completed {
  background: #e8ffea;
  color: #00b42a;
}

.eval-status.failed {
  background: #ffece8;
  color: #f53f3f;
}

.eval-status.stopped {
  background: #f2f3f5;
  color: #86909c;
}

.eval-desc {
  color: #86909c;
  font-size: 13px;
  margin-bottom: 12px;
}

.eval-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 12px;
}

.meta-item.score {
  color: #2e63f0;
  font-weight: 600;
}

.eval-actions {
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

.btn-danger {
  background: #f53f3f;
  color: white;
  border-color: #f53f3f;
}

.btn-danger:hover {
  background: #cb272d;
  color: white;
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

.btn-add {
  border-style: dashed;
  width: 100%;
  margin-top: 8px;
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
  max-width: 600px;
  max-height: 80vh;
  overflow: auto;
}

.modal-lg {
  max-width: 700px;
}

.modal-xl {
  max-width: 800px;
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
  margin-bottom: 20px;
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
}

select.form-input {
  cursor: pointer;
}

.test-cases {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.test-case-item {
  padding: 12px;
  background: #f7f8fa;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tc-index {
  font-size: 13px;
  font-weight: 500;
  color: #4e5969;
}

/* Results */
.result-summary {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 24px;
  background: #f7f8fa;
  border-radius: 12px;
  margin-bottom: 24px;
}

.result-score {
  text-align: center;
}

.score-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: white;
  background: #f53f3f;
  margin-bottom: 8px;
}

.score-circle.good {
  background: #ff7d00;
}

.score-circle.excellent {
  background: #00b42a;
}

.score-label {
  font-size: 13px;
  color: #86909c;
}

.result-stats {
  display: flex;
  gap: 24px;
}

.r-stat {
  text-align: center;
}

.r-stat-label {
  display: block;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 4px;
}

.r-stat-value {
  font-size: 24px;
  font-weight: 700;
}

.r-stat-value.pass {
  color: #00b42a;
}

.r-stat-value.fail {
  color: #f53f3f;
}

.result-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #f53f3f;
  background: #f7f8fa;
}

.result-item.pass {
  border-left-color: #00b42a;
}

.ri-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}

.ri-status {
  font-weight: 700;
}

.result-item.pass .ri-status {
  color: #00b42a;
}

.result-item.fail .ri-status {
  color: #f53f3f;
}

.ri-score {
  color: #86909c;
}

.ri-question,
.ri-answer,
.ri-expected {
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 4px;
}

.ri-question strong,
.ri-answer strong,
.ri-expected strong {
  color: #4e5969;
}
</style>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Agent 模板</h1>
      <p class="page-desc">使用预配置模板快速创建 Agent，或保存当前配置为模板</p>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索模板名称或描述..."
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="filter-group">
        <select v-model="selectedCategory" class="filter-select" @change="loadTemplates">
          <option v-for="cat in categories" :key="cat.key" :value="cat.key">
            {{ cat.icon }} {{ cat.label }}
          </option>
        </select>
        <select v-model="sortBy" class="filter-select" @change="loadTemplates">
          <option value="created_at">最新创建</option>
          <option value="usage_count">最多使用</option>
          <option value="rating">最高评分</option>
          <option value="name">名称排序</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">+ 新建模板</button>
    </div>

    <!-- 模板列表 -->
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="templates.length === 0" class="empty-state">
      <div class="empty-icon">🤖</div>
      <p>暂无模板</p>
      <button class="btn btn-primary" @click="showCreateModal = true">创建第一个模板</button>
    </div>
    <div v-else class="template-grid">
      <div
        v-for="tpl in templates"
        :key="tpl.id"
        class="template-card"
        @click="viewTemplate(tpl)"
      >
        <div class="template-icon" :style="{ background: tpl.icon_background }">
          {{ tpl.icon }}
        </div>
        <div class="template-info">
          <h3 class="template-name">{{ tpl.name }}</h3>
          <p class="template-desc">{{ tpl.description || '暂无描述' }}</p>
          <div class="template-meta">
            <span class="meta-item">📁 {{ categoryLabel(tpl.category) }}</span>
            <span class="meta-item">⭐ {{ tpl.rating.toFixed(1) }}</span>
            <span class="meta-item">📥 {{ tpl.usage_count }}</span>
          </div>
          <div class="template-tags">
            <span v-for="tag in tpl.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
        <div class="template-actions">
          <button class="btn btn-primary btn-sm" @click.stop="useTemplate(tpl)">
            使用模板
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

    <!-- 模板详情弹窗 -->
    <div v-if="selectedTemplate" class="modal-mask show">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h2>{{ selectedTemplate.name }}</h2>
          <button class="modal-close" @click="selectedTemplate = null">×</button>
        </div>
        <div class="modal-body">
          <div class="template-detail">
            <div class="detail-header">
              <div class="detail-icon" :style="{ background: selectedTemplate.icon_background }">
                {{ selectedTemplate.icon }}
              </div>
              <div class="detail-info">
                <p class="detail-desc">{{ selectedTemplate.description || '暂无描述' }}</p>
                <div class="detail-meta">
                  <span>分类: {{ categoryLabel(selectedTemplate.category) }}</span>
                  <span>模型: {{ selectedTemplate.model_name || '未指定' }}</span>
                  <span>作者: {{ selectedTemplate.author_name || '匿名' }}</span>
                  <span>使用: {{ selectedTemplate.usage_count }} 次</span>
                  <span>评分: {{ selectedTemplate.rating.toFixed(1) }} ({{ selectedTemplate.rating_count }})</span>
                </div>
              </div>
            </div>

            <div v-if="selectedTemplate.tags.length > 0" class="detail-tags">
              <span v-for="tag in selectedTemplate.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>

            <div class="detail-section">
              <h4>系统提示词</h4>
              <div class="code-block">{{ selectedTemplate.system_prompt || '未设置' }}</div>
            </div>

            <div v-if="selectedTemplate.user_prompt_template" class="detail-section">
              <h4>用户提示词模板</h4>
              <div class="code-block">{{ selectedTemplate.user_prompt_template }}</div>
            </div>

            <div v-if="selectedTemplate.tools.length > 0" class="detail-section">
              <h4>工具列表</h4>
              <div class="tool-list">
                <div v-for="(t, i) in selectedTemplate.tools" :key="i" class="tool-item">
                  <span class="tool-name">{{ t.name }}</span>
                  <span class="tool-type">{{ t.type }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="selectedTemplate = null">取消</button>
          <button class="btn btn-primary" @click="useTemplate(selectedTemplate)">
            使用此模板
          </button>
        </div>
      </div>
    </div>

    <!-- 新建模板弹窗 -->
    <div v-if="showCreateModal" class="modal-mask show">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <h2>新建 Agent 模板</h2>
          <button class="modal-close" @click="showCreateModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">模板名称 <span class="required">*</span></label>
              <input v-model="newTemplate.name" type="text" class="form-input" placeholder="输入模板名称" />
            </div>
            <div class="form-group">
              <label class="form-label">分类</label>
              <select v-model="newTemplate.category" class="form-input">
                <option value="general">通用助手</option>
                <option value="customer">客服支持</option>
                <option value="analysis">数据分析</option>
                <option value="creative">创意写作</option>
                <option value="code">代码助手</option>
                <option value="education">教育培训</option>
                <option value="marketing">营销推广</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="newTemplate.description" class="form-input" rows="2" placeholder="模板描述（可选）" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">模型提供者</label>
              <input v-model="newTemplate.model_provider" type="text" class="form-input" placeholder="如 openai" />
            </div>
            <div class="form-group">
              <label class="form-label">模型名称</label>
              <input v-model="newTemplate.model_name" type="text" class="form-input" placeholder="如 gpt-4o-mini" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">系统提示词</label>
            <textarea v-model="newTemplate.system_prompt" class="form-input" rows="4" placeholder="定义 Agent 的角色和行为规则" />
          </div>
          <div class="form-group">
            <label class="form-label">用户提示词模板</label>
            <textarea v-model="newTemplate.user_prompt_template" class="form-input" rows="2" placeholder="如 {{#start.query#}}" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">最大迭代次数</label>
              <input v-model.number="newTemplate.max_iterations" type="number" class="form-input" min="1" max="20" />
            </div>
            <div class="form-group">
              <label class="form-label">Temperature</label>
              <input v-model.number="newTemplate.temperature" type="number" class="form-input" min="0" max="1" step="0.1" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">标签（逗号分隔）</label>
            <input v-model="newTemplate.tags_text" type="text" class="form-input" placeholder="如 客服,问答,自动化" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createTemplate" :disabled="!newTemplate.name.trim()">
            创建模板
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiGet, apiPost } from '../api/client'

interface AgentTemplate {
  id: string
  name: string
  description: string
  icon: string
  icon_background: string
  category: string
  tags: string[]
  model_provider: string
  model_name: string
  system_prompt: string
  user_prompt_template: string
  tools: any[]
  mcp_servers: string[]
  knowledge_ids: string[]
  max_iterations: number
  temperature: number
  is_public: boolean
  is_official: boolean
  author_id: string
  author_name: string
  usage_count: number
  rating: number
  rating_count: number
  status: string
  created_at: string
  updated_at: string
}

interface TemplateCategory {
  key: string
  label: string
  icon: string
}

const templates = ref<AgentTemplate[]>([])
const categories = ref<TemplateCategory[]>([])
const selectedCategory = ref('all')
const searchQuery = ref('')
const sortBy = ref('created_at')
const currentPage = ref(1)
const pageSize = ref(12)
const totalPages = ref(1)
const loading = ref(false)
const selectedTemplate = ref<AgentTemplate | null>(null)
const showCreateModal = ref(false)

const newTemplate = ref({
  name: '',
  description: '',
  category: 'general',
  model_provider: '',
  model_name: '',
  system_prompt: '',
  user_prompt_template: '',
  max_iterations: 5,
  temperature: 0.7,
  tags_text: '',
})

const categoryLabel = (key: string) => {
  const cat = categories.value.find(c => c.key === key)
  return cat ? cat.label : key
}

const loadCategories = async () => {
  const res = await apiGet<TemplateCategory[]>('/api/agent-templates/categories')
  if (res.code === 200) {
    categories.value = res.data
  }
}

const loadTemplates = async () => {
  loading.value = true
  try {
    const res = await apiGet<{
      items: AgentTemplate[]
      total: number
      page: number
      page_size: number
    }>('/api/agent-templates', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        category: selectedCategory.value,
        q: searchQuery.value,
        sort_by: sortBy.value,
      },
    })
    if (res.code === 200) {
      templates.value = res.data.items
      totalPages.value = Math.ceil(res.data.total / pageSize.value)
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadTemplates()
}

const changePage = (page: number) => {
  currentPage.value = page
  loadTemplates()
}

const viewTemplate = (tpl: AgentTemplate) => {
  selectedTemplate.value = tpl
}

const useTemplate = async (tpl: AgentTemplate) => {
  if (!confirm(`确定使用模板 "${tpl.name}" 创建新 Agent？`)) return
  const res = await apiPost<{ name: string; description: string; mode: string }>(
    `/api/agent-templates/${tpl.id}/use`,
    { name: tpl.name + ' (副本)' }
  )
  if (res.code === 200) {
    alert('Agent 配置已生成！请在编辑页面完善后保存。')
    selectedTemplate.value = null
  } else {
    alert('创建失败: ' + res.msg)
  }
}

const createTemplate = async () => {
  const tags = newTemplate.value.tags_text
    .split(',')
    .map(t => t.trim())
    .filter(Boolean)

  const res = await apiPost<{ id: string }>('/api/agent-templates', {
    name: newTemplate.value.name,
    description: newTemplate.value.description,
    category: newTemplate.value.category,
    model_provider: newTemplate.value.model_provider,
    model_name: newTemplate.value.model_name,
    system_prompt: newTemplate.value.system_prompt,
    user_prompt_template: newTemplate.value.user_prompt_template,
    max_iterations: newTemplate.value.max_iterations,
    temperature: newTemplate.value.temperature,
    tags,
  })
  if (res.code === 200) {
    showCreateModal.value = false
    newTemplate.value = {
      name: '',
      description: '',
      category: 'general',
      model_provider: '',
      model_name: '',
      system_prompt: '',
      user_prompt_template: '',
      max_iterations: 5,
      temperature: 0.7,
      tags_text: '',
    }
    loadTemplates()
  } else {
    alert('创建失败: ' + res.msg)
  }
}

onMounted(() => {
  loadCategories()
  loadTemplates()
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

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  align-items: center;
}

.search-box {
  flex: 1;
  min-width: 200px;
}

.search-input {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #2e63f0;
}

.filter-group {
  display: flex;
  gap: 8px;
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

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.template-card {
  background: white;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-card:hover {
  border-color: #2e63f0;
  box-shadow: 0 4px 12px rgba(46, 99, 240, 0.1);
  transform: translateY(-2px);
}

.template-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.template-info {
  flex: 1;
}

.template-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.template-desc {
  color: #86909c;
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.template-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}

.template-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 8px;
  background: #f2f3f5;
  border-radius: 4px;
  font-size: 11px;
  color: #4e5969;
}

.template-actions {
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

/* Detail */
.template-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  display: flex;
  gap: 16px;
}

.detail-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.detail-info {
  flex: 1;
}

.detail-desc {
  color: #4e5969;
  font-size: 14px;
  margin-bottom: 8px;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #86909c;
}

.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.detail-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.code-block {
  padding: 12px;
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow: auto;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f7f8fa;
  border-radius: 6px;
  font-size: 13px;
}

.tool-name {
  font-weight: 500;
}

.tool-type {
  color: #86909c;
  font-size: 12px;
}

/* Form */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

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

textarea.form-input {
  resize: vertical;
}

select.form-input {
  cursor: pointer;
}
</style>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>插件市场</h1>
      <p class="page-desc">浏览、安装和管理插件，扩展平台能力</p>
    </div>

    <!-- 标签页 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索插件名称或描述..."
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="filter-group">
        <select v-model="selectedType" class="filter-select" @change="loadPlugins">
          <option v-for="t in types" :key="t.key" :value="t.key">
            {{ t.icon }} {{ t.label }}
          </option>
        </select>
        <select v-model="selectedCategory" class="filter-select" @change="loadPlugins">
          <option v-for="cat in categories" :key="cat.key" :value="cat.key">
            {{ cat.icon }} {{ cat.label }}
          </option>
        </select>
        <select v-model="sortBy" class="filter-select" @change="loadPlugins">
          <option value="created_at">最新发布</option>
          <option value="download_count">最多下载</option>
          <option value="rating">最高评分</option>
          <option value="name">名称排序</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">+ 发布插件</button>
    </div>

    <!-- 已安装视图 -->
    <div v-if="activeTab === 'installed'">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="installedPlugins.length === 0" class="empty-state">
        <div class="empty-icon">📦</div>
        <p>暂无已安装的插件</p>
        <button class="btn btn-primary" @click="activeTab = 'marketplace'">去市场安装</button>
      </div>
      <div v-else class="plugin-grid">
        <div v-for="plugin in installedPlugins" :key="plugin.id" class="plugin-card">
          <div class="plugin-icon" :style="{ background: plugin.icon_background }">
            {{ plugin.icon }}
          </div>
          <div class="plugin-info">
            <h3 class="plugin-name">{{ plugin.name }}</h3>
            <p class="plugin-desc">{{ plugin.description || '暂无描述' }}</p>
            <div class="plugin-meta">
              <span class="meta-item">📦 {{ plugin.plugin_type }}</span>
              <span class="meta-item">v{{ plugin.version }}</span>
              <span class="meta-item" :class="plugin.install_status">
                {{ plugin.install_status === 'enabled' ? '✓ 已启用' : '⏸ 已停用' }}
              </span>
            </div>
          </div>
          <div class="plugin-actions">
            <button
              v-if="plugin.install_status === 'enabled'"
              class="btn btn-sm"
              @click="disablePlugin(plugin)"
            >
              停用
            </button>
            <button
              v-if="plugin.install_status !== 'enabled'"
              class="btn btn-primary btn-sm"
              @click="enablePlugin(plugin)"
            >
              启用
            </button>
            <button class="btn btn-sm btn-danger-outline" @click="uninstallPlugin(plugin)">
              卸载
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 市场视图 -->
    <div v-else>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="plugins.length === 0" class="empty-state">
        <div class="empty-icon">🧩</div>
        <p>暂无插件</p>
        <button class="btn btn-primary" @click="showCreateModal = true">发布第一个插件</button>
      </div>
      <div v-else class="plugin-grid">
        <div
          v-for="plugin in plugins"
          :key="plugin.id"
          class="plugin-card"
          @click="viewPlugin(plugin)"
        >
          <div class="plugin-icon" :style="{ background: plugin.icon_background }">
            {{ plugin.icon }}
          </div>
          <div class="plugin-info">
            <h3 class="plugin-name">{{ plugin.name }}</h3>
            <p class="plugin-desc">{{ plugin.description || '暂无描述' }}</p>
            <div class="plugin-meta">
              <span class="meta-item">📦 {{ plugin.plugin_type }}</span>
              <span class="meta-item">⭐ {{ plugin.rating.toFixed(1) }}</span>
              <span class="meta-item">📥 {{ plugin.download_count }}</span>
            </div>
            <div class="plugin-tags">
              <span v-for="tag in plugin.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
          <div class="plugin-actions">
            <button class="btn btn-primary btn-sm" @click.stop="installPlugin(plugin)">
              安装
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
    </div>

    <!-- 插件详情弹窗 -->
    <div v-if="selectedPlugin" class="modal-mask show">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h2>{{ selectedPlugin.name }}</h2>
          <button class="modal-close" @click="selectedPlugin = null">×</button>
        </div>
        <div class="modal-body">
          <div class="plugin-detail">
            <div class="detail-header">
              <div class="detail-icon" :style="{ background: selectedPlugin.icon_background }">
                {{ selectedPlugin.icon }}
              </div>
              <div class="detail-info">
                <p class="detail-desc">{{ selectedPlugin.description || '暂无描述' }}</p>
                <div class="detail-meta">
                  <span>类型: {{ selectedPlugin.plugin_type }}</span>
                  <span>版本: {{ selectedPlugin.version }}</span>
                  <span>作者: {{ selectedPlugin.author_name || '匿名' }}</span>
                  <span>下载: {{ selectedPlugin.download_count }} 次</span>
                  <span>评分: {{ selectedPlugin.rating.toFixed(1) }} ({{ selectedPlugin.rating_count }})</span>
                </div>
              </div>
            </div>

            <div v-if="selectedPlugin.tags.length > 0" class="detail-tags">
              <span v-for="tag in selectedPlugin.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>

            <div v-if="selectedPlugin.manifest && Object.keys(selectedPlugin.manifest).length > 0" class="detail-section">
              <h4>插件清单</h4>
              <div class="code-block">{{ JSON.stringify(selectedPlugin.manifest, null, 2) }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="selectedPlugin = null">取消</button>
          <button class="btn btn-primary" @click="installPlugin(selectedPlugin)">
            安装插件
          </button>
        </div>
      </div>
    </div>

    <!-- 发布插件弹窗 -->
    <div v-if="showCreateModal" class="modal-mask show">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h2>发布插件</h2>
          <button class="modal-close" @click="showCreateModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">插件名称 <span class="required">*</span></label>
              <input v-model="newPlugin.name" type="text" class="form-input" placeholder="输入插件名称" />
            </div>
            <div class="form-group">
              <label class="form-label">插件类型 <span class="required">*</span></label>
              <select v-model="newPlugin.plugin_type" class="form-input">
                <option value="tool">工具插件</option>
                <option value="workflow">工作流插件</option>
                <option value="agent">Agent 插件</option>
                <option value="mcp">MCP 插件</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="newPlugin.description" class="form-input" rows="2" placeholder="插件描述" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">版本号</label>
              <input v-model="newPlugin.version" type="text" class="form-input" placeholder="1.0.0" />
            </div>
            <div class="form-group">
              <label class="form-label">分类</label>
              <select v-model="newPlugin.category" class="form-input">
                <option value="utility">实用工具</option>
                <option value="data">数据处理</option>
                <option value="ai">AI 能力</option>
                <option value="integration">集成连接</option>
                <option value="productivity">生产力</option>
                <option value="security">安全</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">标签（逗号分隔）</label>
            <input v-model="newPlugin.tags_text" type="text" class="form-input" placeholder="如 工具,自动化,效率" />
          </div>
          <div class="form-group">
            <label class="form-label">插件包配置 (JSON)</label>
            <textarea v-model="newPlugin.package_text" class="form-input" rows="4" placeholder='{"entry": "main.py", "dependencies": []}' />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createPlugin" :disabled="!canCreate">
            发布
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiGet, apiPost, apiDelete } from '../api/client'

interface Plugin {
  id: string
  name: string
  plugin_type: string
  description: string
  version: string
  author_id: string
  author_name: string
  icon: string
  icon_background: string
  category: string
  tags: string[]
  package: any
  manifest: any
  download_url: string
  file_size: number
  checksum: string
  is_public: boolean
  is_official: boolean
  status: string
  download_count: number
  rating: number
  rating_count: number
  install_status?: string
  installed_at?: string
  created_at: string
  updated_at: string
}

interface PluginType {
  key: string
  label: string
  icon: string
}

interface PluginCategory {
  key: string
  label: string
  icon: string
}

const tabs = [
  { key: 'marketplace', label: '插件市场', icon: '🏪' },
  { key: 'installed', label: '已安装', icon: '📦' },
]

const plugins = ref<Plugin[]>([])
const installedPlugins = ref<Plugin[]>([])
const types = ref<PluginType[]>([])
const categories = ref<PluginCategory[]>([])
const selectedType = ref('all')
const selectedCategory = ref('all')
const searchQuery = ref('')
const sortBy = ref('created_at')
const activeTab = ref('marketplace')
const currentPage = ref(1)
const pageSize = ref(12)
const totalPages = ref(1)
const loading = ref(false)
const selectedPlugin = ref<Plugin | null>(null)
const showCreateModal = ref(false)

const newPlugin = ref({
  name: '',
  plugin_type: 'tool',
  description: '',
  version: '1.0.0',
  category: 'utility',
  tags_text: '',
  package_text: '',
})

const canCreate = computed(() => {
  return newPlugin.value.name.trim() !== '' && newPlugin.value.plugin_type !== ''
})

const loadTypes = async () => {
  const res = await apiGet<PluginType[]>('/api/plugins/types')
  if (res.code === 200) {
    types.value = res.data
  }
}

const loadCategories = async () => {
  const res = await apiGet<PluginCategory[]>('/api/plugins/categories')
  if (res.code === 200) {
    categories.value = res.data
  }
}

const loadPlugins = async () => {
  loading.value = true
  try {
    const res = await apiGet<{
      items: Plugin[]
      total: number
      page: number
      page_size: number
    }>('/api/plugins', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        plugin_type: selectedType.value,
        category: selectedCategory.value,
        q: searchQuery.value,
        sort_by: sortBy.value,
      },
    })
    if (res.code === 200) {
      plugins.value = res.data.items
      totalPages.value = Math.ceil(res.data.total / pageSize.value)
    }
  } finally {
    loading.value = false
  }
}

const loadInstalledPlugins = async () => {
  loading.value = true
  try {
    const res = await apiGet<Plugin[]>('/api/plugins/installed')
    if (res.code === 200) {
      installedPlugins.value = res.data
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadPlugins()
}

const changePage = (page: number) => {
  currentPage.value = page
  loadPlugins()
}

const viewPlugin = (plugin: Plugin) => {
  selectedPlugin.value = plugin
}

const installPlugin = async (plugin: Plugin) => {
  const res = await apiPost(`/api/plugins/${plugin.id}/install`, {})
  if (res.code === 200) {
    alert('安装成功！')
    loadInstalledPlugins()
  } else {
    alert('安装失败: ' + res.msg)
  }
}

const uninstallPlugin = async (plugin: Plugin) => {
  if (!confirm(`确定卸载插件 "${plugin.name}"？`)) return
  const res = await apiPost(`/api/plugins/${plugin.id}/uninstall`, {})
  if (res.code === 200) {
    loadInstalledPlugins()
  } else {
    alert('卸载失败: ' + res.msg)
  }
}

const enablePlugin = async (plugin: Plugin) => {
  const res = await apiPost(`/api/plugins/${plugin.id}/enable`, {})
  if (res.code === 200) {
    loadInstalledPlugins()
  }
}

const disablePlugin = async (plugin: Plugin) => {
  const res = await apiPost(`/api/plugins/${plugin.id}/disable`, {})
  if (res.code === 200) {
    loadInstalledPlugins()
  }
}

const createPlugin = async () => {
  if (!canCreate.value) return
  let packageObj: any = {}
  if (newPlugin.value.package_text.trim()) {
    try {
      packageObj = JSON.parse(newPlugin.value.package_text)
    } catch (e) {
      alert('插件包配置格式错误，请输入有效的 JSON')
      return
    }
  }

  const tags = newPlugin.value.tags_text
    .split(',')
    .map(t => t.trim())
    .filter(Boolean)

  const res = await apiPost<{ id: string }>('/api/plugins', {
    name: newPlugin.value.name,
    plugin_type: newPlugin.value.plugin_type,
    description: newPlugin.value.description,
    version: newPlugin.value.version,
    category: newPlugin.value.category,
    tags,
    package: packageObj,
  })
  if (res.code === 200) {
    showCreateModal.value = false
    newPlugin.value = {
      name: '',
      plugin_type: 'tool',
      description: '',
      version: '1.0.0',
      category: 'utility',
      tags_text: '',
      package_text: '',
    }
    loadPlugins()
  } else {
    alert('发布失败: ' + res.msg)
  }
}

onMounted(() => {
  loadTypes()
  loadCategories()
  loadPlugins()
  loadInstalledPlugins()
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

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e5e6eb;
  padding-bottom: 0;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #86909c;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #2e63f0;
}

.tab-btn.active {
  color: #2e63f0;
  border-bottom-color: #2e63f0;
  font-weight: 600;
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

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.plugin-card {
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

.plugin-card:hover {
  border-color: #2e63f0;
  box-shadow: 0 4px 12px rgba(46, 99, 240, 0.1);
  transform: translateY(-2px);
}

.plugin-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.plugin-info {
  flex: 1;
}

.plugin-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.plugin-desc {
  color: #86909c;
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.plugin-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}

.plugin-meta .enabled {
  color: #00b42a;
}

.plugin-meta .disabled,
.plugin-meta .installed {
  color: #86909c;
}

.plugin-tags {
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

.plugin-actions {
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
  max-width: 600px;
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

/* Detail */
.plugin-detail {
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
  font-family: monospace;
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

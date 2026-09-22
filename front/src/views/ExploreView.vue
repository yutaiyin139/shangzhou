<template>
  <AppShell active-key="explore">
    <div class="page-pad explore-page">
      <!-- 页面标题 -->
      <div class="page-title-row">
        <div>
          <div class="page-title">探索市场</div>
          <div class="page-subtitle">发现和应用社区分享的模板、智能体和工作流</div>
        </div>
      </div>

      <!-- 分类标签 -->
      <div class="filter-row">
        <div class="pills-clip">
          <div class="pills-scroll">
            <button class="pill" :class="{active: activeTab === 'all'}" @click="activeTab = 'all'">全部</button>
            <button class="pill" :class="{active: activeTab === 'templates'}" @click="activeTab = 'templates'">应用模板</button>
            <button class="pill" :class="{active: activeTab === 'agents'}" @click="activeTab = 'agents'">智能体</button>
            <button class="pill" :class="{active: activeTab === 'workflows'}" @click="activeTab = 'workflows'">工作流</button>
          </div>
        </div>
        <span class="search-input" style="min-width:260px;">
          <input v-model="searchQuery" placeholder="搜索..." @input="onSearchInput">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </span>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-wrap">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 内容区域 -->
      <div v-else>
        <!-- 应用模板 -->
        <div v-if="activeTab === 'all' || activeTab === 'templates'" class="explore-section">
          <div class="section-header">
            <h3>应用模板</h3>
            <span class="section-count">{{ filteredTemplates.length }} 个</span>
          </div>
          <div class="grid-cards" v-if="filteredTemplates.length > 0">
            <div v-for="tpl in filteredTemplates" :key="'tpl-'+tpl.id" class="mcard" @click="installTemplate(tpl)">
              <div class="m-head">
                <div class="m-icon" :style="{background: tpl.icon_background || '#EAF1FE'}">
                  <span>{{ tpl.icon || '📋' }}</span>
                </div>
                <div class="m-title-wrap">
                  <div class="m-name">{{ tpl.name }}</div>
                  <div class="m-meta">{{ tpl.display_category || '通用' }}</div>
                </div>
              </div>
              <div class="m-desc">{{ tpl.description || '暂无描述' }}</div>
              <div class="m-tags">
                <span class="tag tag-cat">{{ tpl.display_category || '通用' }}</span>
                <span class="tag" v-if="tpl.kind">{{ tpl.kind }}</span>
              </div>
              <div class="m-action">
                <button class="btn btn-sm btn-primary">安装使用</button>
              </div>
            </div>
          </div>
          <EmptyState v-else text="暂无应用模板" />
        </div>

        <!-- 智能体 -->
        <div v-if="activeTab === 'all' || activeTab === 'agents'" class="explore-section">
          <div class="section-header">
            <h3>智能体模板</h3>
            <span class="section-count">{{ filteredAgents.length }} 个</span>
          </div>
          <div class="grid-cards" v-if="filteredAgents.length > 0">
            <div v-for="agent in filteredAgents" :key="'agent-'+agent.id" class="mcard" @click="useAgent(agent)">
              <div class="m-head">
                <div class="m-icon" :style="{background: agent.icon_background || '#F5E8FF'}">
                  <span>{{ agent.icon || '🤖' }}</span>
                </div>
                <div class="m-title-wrap">
                  <div class="m-name">{{ agent.name }}</div>
                  <div class="m-meta">{{ agent.category || '通用' }}</div>
                </div>
              </div>
              <div class="m-desc">{{ agent.description || '暂无描述' }}</div>
              <div class="m-tags">
                <span class="tag tag-cat">{{ agent.category || '通用' }}</span>
                <span class="tag" v-if="agent.model_name">{{ agent.model_name }}</span>
              </div>
              <div class="m-action">
                <button class="btn btn-sm btn-primary">使用此模板</button>
              </div>
            </div>
          </div>
          <EmptyState v-else text="暂无智能体模板" />
        </div>

        <!-- 工作流 -->
        <div v-if="activeTab === 'all' || activeTab === 'workflows'" class="explore-section">
          <div class="section-header">
            <h3>工作流模板</h3>
            <span class="section-count">{{ filteredWorkflows.length }} 个</span>
          </div>
          <div class="grid-cards" v-if="filteredWorkflows.length > 0">
            <div v-for="wf in filteredWorkflows" :key="'wf-'+wf.id" class="mcard" @click="useWorkflow(wf)">
              <div class="m-head">
                <div class="m-icon" :style="{background: wf.icon_background || '#E8FFEA'}">
                  <span>{{ wf.icon || '⚙️' }}</span>
                </div>
                <div class="m-title-wrap">
                  <div class="m-name">{{ wf.name }}</div>
                  <div class="m-meta">{{ wf.category || '通用' }}</div>
                </div>
              </div>
              <div class="m-desc">{{ wf.description || '暂无描述' }}</div>
              <div class="m-tags">
                <span class="tag tag-cat">{{ wf.category || '通用' }}</span>
                <span class="tag" v-if="wf.usage_count">{{ wf.usage_count }} 次使用</span>
              </div>
              <div class="m-action">
                <button class="btn btn-sm btn-primary">使用此模板</button>
              </div>
            </div>
          </div>
          <EmptyState v-else text="暂无工作流模板" />
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { apiGet, apiPost } from '../api/client'

const activeTab = ref('all')
const searchQuery = ref('')
const loading = ref(true)

const templates = ref([])
const agents = ref([])
const workflows = ref([])

// 过滤后的数据
const filteredTemplates = computed(() => {
  if (!searchQuery.value) return templates.value
  const q = searchQuery.value.toLowerCase()
  return templates.value.filter(t =>
    (t.name || '').toLowerCase().includes(q) ||
    (t.description || '').toLowerCase().includes(q)
  )
})

const filteredAgents = computed(() => {
  if (!searchQuery.value) return agents.value
  const q = searchQuery.value.toLowerCase()
  return agents.value.filter(a =>
    (a.name || '').toLowerCase().includes(q) ||
    (a.description || '').toLowerCase().includes(q)
  )
})

const filteredWorkflows = computed(() => {
  if (!searchQuery.value) return workflows.value
  const q = searchQuery.value.toLowerCase()
  return workflows.value.filter(w =>
    (w.name || '').toLowerCase().includes(q) ||
    (w.description || '').toLowerCase().includes(q)
  )
})

// 搜索输入防抖
let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    // 搜索逻辑已在 computed 中处理
  }, 300)
}

// 加载数据
async function loadData() {
  loading.value = true
  try {
    // 加载应用模板
    const tplRes = await apiGet('/api/templates')
    if (tplRes.code === 200) {
      templates.value = tplRes.data || []
    }
  } catch (e) {
    console.error('加载模板失败:', e)
  }

  try {
    // 加载智能体模板
    const agentRes = await apiGet('/api/agent-templates')
    if (agentRes.code === 200) {
      agents.value = agentRes.data || []
    }
  } catch (e) {
    console.error('加载智能体模板失败:', e)
  }

  try {
    // 加载工作流模板
    const wfRes = await apiGet('/api/workflow-templates')
    if (wfRes.code === 200) {
      workflows.value = wfRes.data || []
    }
  } catch (e) {
    console.error('加载工作流模板失败:', e)
  }

  loading.value = false
}

// 安装模板
async function installTemplate(tpl) {
  if (!confirm(`确定要安装模板 "${tpl.name}" 吗？`)) return
  try {
    const res = await apiPost(`/api/app-templates/${tpl.marketplace_id}/create`, {
      name: tpl.name, description: tpl.description
    })

    if (res.code === 200) {
      alert('安装成功！')
      // 记录安装
      await apiPost('/api/installed-apps', {
        source_type: 'template',
        source_id: tpl.marketplace_id,
        source_name: tpl.name,
        app_name: tpl.name,
        app_mode: tpl.kind || 'workflow',
        status: 'installed'
      })
    } else {
      alert('安装失败: ' + (res.msg || '未知错误'))
    }
  } catch (e) {
    alert('安装失败: ' + e.message)
  }
}

// 使用智能体模板
async function useAgent(agent) {
  if (!confirm(`确定要使用智能体模板 "${agent.name}" 吗？`)) return
  try {
    const res = await apiPost('/api/agent-templates/' + agent.id + '/use', {})

    if (res.code === 200) {
      alert('创建成功！')
    } else {
      alert('创建失败: ' + (res.msg || '未知错误'))
    }
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

// 使用工作流模板
async function useWorkflow(wf) {
  if (!confirm(`确定要使用工作流模板 "${wf.name}" 吗？`)) return
  try {
    const res = await apiPost('/api/workflow-templates/' + wf.id + '/use', {})

    if (res.code === 200) {
      alert('创建成功！')
    } else {
      alert('创建失败: ' + (res.msg || '未知错误'))
    }
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.explore-page {
  max-width: 1200px;
}

.page-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-subtitle {
  color: var(--text-3);
  font-size: 13px;
  margin-top: 4px;
}

.explore-section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.section-count {
  color: var(--text-3);
  font-size: 12px;
}

.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--text-3);
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.mcard .m-action {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: flex-end;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.pills-clip {
  flex: 1;
  overflow: hidden;
}

.pills-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.pill {
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.pill:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.pill.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.search-input {
  display: flex;
  align-items: center;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0 10px;
}

.search-input input {
  border: none;
  background: transparent;
  padding: 8px 8px 8px 0;
  width: 100%;
  min-width: 200px;
}

.search-input svg {
  width: 16px;
  height: 16px;
  color: var(--text-3);
  flex-shrink: 0;
}

.grid-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.mcard {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.mcard:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.m-head {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.m-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.m-title-wrap {
  flex: 1;
  min-width: 0;
}

.m-name {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-meta {
  color: var(--text-3);
  font-size: 12px;
  margin-top: 2px;
}

.m-desc {
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
}

.m-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-page);
  color: var(--text-3);
  font-size: 11px;
}

.tag-cat {
  background: var(--primary-light);
  color: var(--primary);
}
</style>

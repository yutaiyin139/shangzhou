<template>
  <AppShell id="page-root" active-key="plugin-dev" main-class="main-white">
    <div class="page-pad">
      <!-- 页内标签 -->
      <div class="ps-tabs">
        <button class="ps-tab" :class="{ active: activeTab === 'info' }" @click="activeTab = 'info'"><span class="ps-tab-ico">📋</span>基本信息</button>
        <button class="ps-tab" :class="{ active: activeTab === 'manifest' }" @click="activeTab = 'manifest'"><span class="ps-tab-ico">📄</span>清单编辑</button>
        <button class="ps-tab" :class="{ active: activeTab === 'code' }" @click="activeTab = 'code'"><span class="ps-tab-ico">💻</span>代码编辑</button>
        <button class="ps-tab" :class="{ active: activeTab === 'hooks' }" @click="activeTab = 'hooks'"><span class="ps-tab-ico">🔗</span>Hook 配置</button>
        <button class="ps-tab" :class="{ active: activeTab === 'tools' }" @click="activeTab = 'tools'"><span class="ps-tab-ico">🔧</span>工具定义</button>
        <button class="ps-tab" :class="{ active: activeTab === 'test' }" @click="activeTab = 'test'"><span class="ps-tab-ico">🧪</span>测试运行</button>
        <button class="ps-tab" :class="{ active: activeTab === 'publish' }" @click="activeTab = 'publish'"><span class="ps-tab-ico">🚀</span>发布</button>
      </div>

      <!-- 主区 -->
      <div class="ps-main">
        <!-- 基本信息 -->
        <div v-if="activeTab === 'info'" class="ps-section">
          <h2 class="ps-section-title">基本信息</h2>
          <div class="ps-form">
            <div class="ps-form-row">
              <label class="ps-label">插件名称 *</label>
              <input v-model="plugin.name" class="ps-input" placeholder="如：天气查询插件">
            </div>
            <div class="ps-form-row">
              <label class="ps-label">插件类型 *</label>
              <select v-model="plugin.plugin_type" class="ps-select">
                <option value="tool">工具插件 (tool)</option>
                <option value="workflow">工作流插件 (workflow)</option>
                <option value="agent">Agent 插件 (agent)</option>
                <option value="mcp">MCP 插件 (mcp)</option>
              </select>
            </div>
            <div class="ps-form-row">
              <label class="ps-label">版本号</label>
              <input v-model="plugin.version" class="ps-input" placeholder="1.0.0">
            </div>
            <div class="ps-form-row">
              <label class="ps-label">描述</label>
              <textarea v-model="plugin.description" class="ps-textarea" rows="3" placeholder="描述插件功能和用途"></textarea>
            </div>
            <div class="ps-form-row">
              <label class="ps-label">作者</label>
              <input v-model="plugin.author" class="ps-input" placeholder="作者名">
            </div>
            <div class="ps-form-row">
              <label class="ps-label">图标 Emoji</label>
              <input v-model="plugin.icon" class="ps-input" placeholder="🧩" style="width: 80px">
            </div>
            <div class="ps-form-row">
              <label class="ps-label">图标背景色</label>
              <input v-model="plugin.icon_background" type="color" class="ps-input" style="width: 80px">
            </div>
          </div>
        </div>

        <!-- 清单编辑 -->
        <div v-else-if="activeTab === 'manifest'" class="ps-section">
          <h2 class="ps-section-title">插件清单 (manifest.json)</h2>
          <p class="ps-hint">清单文件描述插件的元数据、配置 Schema 和 Hook 声明</p>
          <textarea v-model="manifestJson" class="ps-code-editor" rows="20" spellcheck="false"></textarea>
          <div class="ps-actions">
            <button class="ps-btn" @click="formatManifest">格式化 JSON</button>
            <button class="ps-btn ps-btn-primary" @click="saveManifest">保存清单</button>
          </div>
        </div>

        <!-- 代码编辑 -->
        <div v-else-if="activeTab === 'code'" class="ps-section">
          <h2 class="ps-section-title">插件代码 (main.py)</h2>
          <p class="ps-hint">继承 BasePlugin 类，实现 Hook 方法</p>
          <textarea v-model="mainCode" class="ps-code-editor" rows="30" spellcheck="false"></textarea>
          <div class="ps-actions">
            <button class="ps-btn" @click="loadTemplate">加载模板</button>
            <button class="ps-btn ps-btn-primary" @click="saveCode">保存代码</button>
          </div>
        </div>

        <!-- Hook 配置 -->
        <div v-else-if="activeTab === 'hooks'" class="ps-section">
          <h2 class="ps-section-title">Hook 配置</h2>
          <p class="ps-hint">选择此插件需要监听的生命周期事件</p>
          <div class="ps-hooks">
            <div v-for="hook in availableHooks" :key="hook.id" class="ps-hook-item">
              <label class="ps-hook-label">
                <input type="checkbox" v-model="hook.enabled">
                <span class="ps-hook-name">{{ hook.name }}</span>
              </label>
              <span class="ps-hook-desc">{{ hook.desc }}</span>
            </div>
          </div>
        </div>

        <!-- 工具定义 -->
        <div v-else-if="activeTab === 'tools'" class="ps-section">
          <h2 class="ps-section-title">工具定义</h2>
          <p class="ps-hint">定义此插件对外暴露的工具（plugin_type=tool 时有效）</p>
          <div class="ps-tools">
            <div v-for="(tool, idx) in plugin.tools" :key="idx" class="ps-tool-card">
              <div class="ps-tool-header">
                <input v-model="tool.name" class="ps-input ps-tool-name" placeholder="工具名">
                <button class="ps-btn-icon" @click="removeTool(idx)">✕</button>
              </div>
              <input v-model="tool.description" class="ps-input" placeholder="工具描述">
              <div class="ps-tool-params">
                <label class="ps-label">参数 (JSON Schema)</label>
                <textarea v-model="tool.parameters" class="ps-code-editor" rows="4" placeholder='{"type":"object","properties":{}}'></textarea>
              </div>
            </div>
            <button class="ps-btn ps-btn-dashed" @click="addTool">+ 添加工具</button>
          </div>
        </div>

        <!-- 测试运行 -->
        <div v-else-if="activeTab === 'test'" class="ps-section">
          <h2 class="ps-section-title">测试运行</h2>
          <div class="ps-test">
            <div class="ps-form-row">
              <label class="ps-label">Hook 输入参数 (JSON)</label>
              <textarea v-model="testInput" class="ps-code-editor" rows="8" placeholder='{"context": {"query": "测试输入"}}'></textarea>
            </div>
            <button class="ps-btn ps-btn-primary" @click="runTest" :disabled="testing">
              {{ testing ? '运行中...' : '▶ 执行测试' }}
            </button>
            <div v-if="testResult" class="ps-test-result">
              <label class="ps-label">执行结果</label>
              <pre class="ps-code-block">{{ testResult }}</pre>
            </div>
          </div>
        </div>

        <!-- 发布 -->
        <div v-else-if="activeTab === 'publish'" class="ps-section">
          <h2 class="ps-section-title">发布插件</h2>
          <div class="ps-form">
            <div class="ps-publish-preview">
              <div class="pp-icon" :style="{ background: plugin.icon_background }">{{ plugin.icon || '🧩' }}</div>
              <div class="pp-info">
                <div class="pp-name">{{ plugin.name || '未命名插件' }}</div>
                <div class="pp-meta">{{ plugin.plugin_type }} · v{{ plugin.version || '1.0.0' }}</div>
                <div class="pp-desc">{{ plugin.description || '暂无描述' }}</div>
              </div>
            </div>
            <div class="ps-publish-checks">
              <div class="ps-check" :class="{ ok: !!plugin.name }">
                {{ !!plugin.name ? '✓' : '○' }} 插件名称
              </div>
              <div class="ps-check" :class="{ ok: !!plugin.plugin_type }">
                {{ !!plugin.plugin_type ? '✓' : '○' }} 插件类型
              </div>
              <div class="ps-check" :class="{ ok: !!plugin.description }">
                {{ !!plugin.description ? '✓' : '○' }} 插件描述
              </div>
              <div class="ps-check" :class="{ ok: manifestValid }">
                {{ manifestValid ? '✓' : '○' }} 清单格式正确
              </div>
            </div>
            <button class="ps-btn ps-btn-primary ps-btn-lg" @click="publishPlugin" :disabled="!canPublish">
              🚀 发布到市场
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import AppShell from '../components/AppShell.vue'
import { apiGet, apiPost, apiPut } from '../api/client'
import { toast } from '../utils/global'

const activeTab = ref('info')

const plugin = ref({
  id: '',
  name: '',
  plugin_type: 'tool',
  version: '1.0.0',
  description: '',
  author: '',
  icon: '🧩',
  icon_background: '#F5E8FF',
  category: 'utility',
  tags: [],
  manifest: {},
  tools: [],
})

const manifestJson = ref('{\n  "name": "",\n  "version": "1.0.0",\n  "plugin_type": "tool",\n  "hooks": []\n}')

const PLUGIN_TEMPLATE = `# -*- coding: utf-8 -*-
"""
插件入口文件
继承 BasePlugin 实现 Hook 方法
"""
from engine.plugin_sdk import BasePlugin
from typing import Dict


class MyPlugin(BasePlugin):
    name = "My Plugin"
    version = "1.0.0"
    plugin_type = "tool"
    description = "插件描述"
    author = ""

    def on_workflow_start(self, context: Dict) -> Dict:
        """工作流开始前"""
        return context

    def on_node_execute(self, node_type: str, node_data: Dict, context: Dict) -> Dict:
        """节点执行前"""
        return context

    def on_node_complete(self, node_type: str, node_id: str, result: Dict, context: Dict) -> Dict:
        """节点执行后"""
        return result

    def on_workflow_end(self, result: Dict, context: Dict) -> Dict:
        """工作流结束后"""
        return result
`

const mainCode = ref(PLUGIN_TEMPLATE)
const testInput = ref('{\n  "context": {\n    "query": "测试输入"\n  }\n}')
const testResult = ref('')
const testing = ref(false)
const availableHooks = ref([
  { id: 'on_workflow_start', name: 'on_workflow_start', desc: '工作流开始前', enabled: true },
  { id: 'on_node_execute', name: 'on_node_execute', desc: '节点执行前', enabled: true },
  { id: 'on_node_complete', name: 'on_node_complete', desc: '节点执行后', enabled: true },
  { id: 'on_workflow_end', name: 'on_workflow_end', desc: '工作流结束后', enabled: true },
  { id: 'on_error', name: 'on_error', desc: '出错时', enabled: false },
])
const manifestValid = computed(() => {
  try {
    JSON.parse(manifestJson.value)
    return true
  } catch {
    return false
  }
})
const canPublish = computed(() => {
  return !!plugin.value.name && !!plugin.value.plugin_type && manifestValid.value
})

function formatManifest() {
  try {
    const obj = JSON.parse(manifestJson.value)
    manifestJson.value = JSON.stringify(obj, null, 2)
  } catch (e) {
    toast('JSON 格式错误')
  }
}

function saveManifest() {
  try {
    plugin.value.manifest = JSON.parse(manifestJson.value)
    toast('清单已保存')
  } catch (e) {
    toast('JSON 格式错误')
  }
}

function saveCode() {
  toast('代码已保存')
}

function loadTemplate() {
  mainCode.value = PLUGIN_TEMPLATE
}

function addTool() {
  plugin.value.tools.push({ name: '', description: '', parameters: '{}' })
}

function removeTool(idx) {
  plugin.value.tools.splice(idx, 1)
}

async function runTest() {
  testing.value = true
  testResult.value = ''
  try {
    let params = {}
    try {
      params = JSON.parse(testInput.value)
    } catch (e) {
      toast('输入 JSON 格式错误')
      return
    }

    const res = await apiPost('/api/v1/plugins/hooks/execute', {
      hook: 'on_node_execute',
      params: { node_type: 'llm', node_data: {}, ...params },
    })
    if (res.code === 200) {
      testResult.value = JSON.stringify(res.data, null, 2)
    } else {
      testResult.value = '错误: ' + (res.msg || '未知错误')
    }
  } catch (e) {
    testResult.value = '错误: ' + e.message
  } finally {
    testing.value = false
  }
}

async function publishPlugin() {
  if (!canPublish.value) return

  // 同步 manifest
  plugin.value.manifest = JSON.parse(manifestJson.value)
  plugin.value.manifest.name = plugin.value.name
  plugin.value.manifest.plugin_type = plugin.value.plugin_type
  plugin.value.manifest.version = plugin.value.version
  plugin.value.manifest.description = plugin.value.description
  plugin.value.manifest.author = plugin.value.author
  plugin.value.manifest.hooks = availableHooks.value.filter(h => h.enabled).map(h => h.id)
  manifestJson.value = JSON.stringify(plugin.value.manifest, null, 2)

  try {
    const res = await apiPost('/api/plugins', {
      name: plugin.value.name,
      plugin_type: plugin.value.plugin_type,
      description: plugin.value.description,
      version: plugin.value.version,
      author_name: plugin.value.author,
      icon: plugin.value.icon,
      icon_background: plugin.value.icon_background,
      category: plugin.value.category,
      tags: plugin.value.tags,
      manifest: plugin.value.manifest,
      package: { tools: plugin.value.tools },
      is_public: true,
    })
    if (res.code === 200) {
      toast('发布成功！')
      setTimeout(() => { location.hash = '/plugins' }, 1000)
    } else {
      toast(res.msg || '发布失败')
    }
  } catch (e) {
    toast('发布失败: ' + e.message)
  }
}

onMounted(async () => {
  // 检查是否是编辑模式
  const m = location.hash.match(/[?&]id=([^&]+)/)
  if (m) {
    const pluginId = m[1]
    try {
      const res = await apiGet(`/api/plugins/${pluginId}`)
      if (res.code === 200) {
        const p = res.data
        plugin.value = {
          id: p.id,
          name: p.name,
          plugin_type: p.plugin_type,
          version: p.version,
          description: p.description,
          author: p.author_name,
          icon: p.icon,
          icon_background: p.icon_background,
          category: p.category,
          tags: p.tags,
          manifest: p.manifest,
          tools: p.package?.tools || [],
        }
        manifestJson.value = JSON.stringify(p.manifest, null, 2)
      }
    } catch (e) {
      toast('加载插件失败')
    }
  }
})
</script>

<style scoped>
/* 页内标签 */
.ps-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-light);
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.ps-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-2);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  font-weight: 500;
  border-radius: 6px 6px 0 0;
  transition: color .15s, background .15s;
}

.ps-tab:hover {
  color: var(--primary);
  background: var(--primary-light);
}

.ps-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

.ps-tab-ico {
  font-size: 14px;
}

.ps-main {
  min-width: 0;
}

.ps-section {
  padding: 8px 0 24px;
  max-width: 800px;
}

.ps-section-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.ps-hint {
  font-size: 13px;
  color: var(--text-3);
  margin-bottom: 16px;
}

.ps-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ps-form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ps-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.ps-input,
.ps-select,
.ps-textarea {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--input-bg);
  color: var(--text-1);
}

.ps-input:focus,
.ps-select:focus,
.ps-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.ps-code-editor {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  background: var(--bg-1);
  color: var(--text-1);
  resize: vertical;
}

.ps-code-block {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.ps-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.ps-btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-2);
  color: var(--text-1);
  cursor: pointer;
  font-size: 13px;
}

.ps-btn:hover { background: var(--bg-hover); }
.ps-btn-primary { background: var(--primary); color: white; border-color: var(--primary); }
.ps-btn-primary:hover { background: var(--primary-hover); }
.ps-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ps-btn-dashed { border-style: dashed; width: 100%; }
.ps-btn-lg { padding: 12px 24px; font-size: 14px; width: 100%; }

.ps-btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-3);
  padding: 4px;
}

.ps-btn-icon:hover { color: var(--danger); }

/* Hooks */
.ps-hooks {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ps-hook-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-1);
  border-radius: 6px;
  border: 1px solid var(--border-light);
}

.ps-hook-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  min-width: 180px;
}

.ps-hook-name {
  font-family: monospace;
  font-size: 13px;
  font-weight: 500;
}

.ps-hook-desc {
  font-size: 12px;
  color: var(--text-3);
}

/* Tools */
.ps-tools {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ps-tool-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  background: var(--bg-1);
}

.ps-tool-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.ps-tool-name {
  flex: 1;
  font-family: monospace;
  font-weight: 600;
}

.ps-tool-params {
  margin-top: 8px;
}

/* Test */
.ps-test {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ps-test-result {
  margin-top: 8px;
}

/* Publish */
.ps-publish-preview {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--bg-1);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.pp-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.pp-name { font-size: 16px; font-weight: 700; }
.pp-meta { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.pp-desc { font-size: 13px; color: var(--text-2); margin-top: 4px; }

.ps-publish-checks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.ps-check {
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-3);
  background: var(--bg-1);
  border-radius: 4px;
}

.ps-check.ok {
  color: var(--success);
  background: rgba(16, 185, 129, 0.08);
}
</style>

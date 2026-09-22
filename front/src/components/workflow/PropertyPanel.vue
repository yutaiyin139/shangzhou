<template>
  <div v-if="node" class="property-panel panel-scope">
    <ResizeHandle />
    <div class="pp-container">
      <!-- ===== 头部（sticky） ===== -->
      <header class="pp-head">
        <!-- 标题行：图标 + 标题 + 操作按钮 -->
        <div class="pp-head-row">
          <span class="pp-icon" :style="{ background: meta.color }">{{ meta.icon }}</span>
          <input class="pp-title-input" :value="displayTitle" @change="onTitleChange" />
          <div class="pp-actions">
            <button ref="menuBtnRef" class="pp-action-btn" title="节点操作" @click="menuOpen = !menuOpen">
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><circle cx="2.5" cy="8" r="1.5" fill="currentColor"/><circle cx="8" cy="8" r="1.5" fill="currentColor"/><circle cx="13.5" cy="8" r="1.5" fill="currentColor"/></svg>
            </button>
            <span class="pp-menu-sep"></span>
            <button class="pp-action-btn" title="关闭" @click="$emit('close')">✕</button>
          </div>
        </div>
        <!-- 描述行 -->
        <div class="pp-desc-row">
          <input class="pp-desc-input" placeholder="添加描述..." :value="node.data.desc" @change="onDescChange" />
        </div>
        <!-- Tab 栏 -->
        <div class="pp-tabs">
          <button class="pp-tab" :class="{ 'pp-tab-active': activeTab === 'settings' }" @click="activeTab = 'settings'">设置</button>
          <button class="pp-tab" :class="{ 'pp-tab-active': activeTab === 'lastRun' }" @click="activeTab = 'lastRun'">最近运行</button>
        </div>
      </header>

      <!-- 操作下拉菜单 -->
      <div v-if="menuOpen" ref="menuRef" class="pp-dropdown">
        <button class="pp-dropdown-item pp-dropdown-danger" @click="$emit('delete', node.id)">删除节点</button>
      </div>

      <!-- ===== Settings Tab ===== -->
      <main v-if="activeTab === 'settings'" class="pp-body">
        <div v-if="panelCrashed" class="pp-panel-error">该节点配置暂无法显示（节点数据可能不完整），请检查后重试。</div>
        <component
          v-else-if="panelComponent"
          :is="panelComponent"
          :key="node.id"
          :node="node"
          @update="onPanelUpdate"
        />

        <div v-if="nextSteps.length" class="pp-next-step">
          <div class="pp-next-step-title">下一步</div>
          <div class="pp-next-step-desc">添加后续节点</div>
          <div class="pp-next-step-list">
            <button v-for="nt in nextSteps" :key="nt" class="pp-next-step-btn" @click="onAddNext(nt)">
              {{ getNodeType(nt).title }}
            </button>
          </div>
        </div>
      </main>

      <!-- ===== Last Run Tab ===== -->
      <main v-else class="pp-body pp-lastrun">
        <div class="pp-lastrun-empty">
          <div class="pp-lastrun-ico">📊</div>
          <div class="pp-lastrun-text">暂无运行记录</div>
          <div class="pp-lastrun-hint">运行工作流后，此处将显示该节点的最近执行结果</div>
        </div>
      </main>
    </div>
  </div>

  <div v-else class="property-panel empty panel-scope">
    <div class="pp-empty">
      <div class="pp-empty-ico">🖱️</div>
      <div>选择画布上的节点进行配置</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref, watch } from 'vue'
import { getNodeType } from '../../utils/workflow/nodeRegistry'
import { resolvePanel, preloadPanels } from './panels/PanelRegistry'
import ResizeHandle from './ResizeHandle.vue'

const emit = defineEmits(['update', 'close', 'delete', 'add-next'])
const props = defineProps({ node: { type: Object, default: null } })

const menuOpen = ref(false)
// 子面板渲染兜底：某个节点面板渲染抛错时，不应污染整块面板 / 影响其它节点
const panelCrashed = ref(false)
onErrorCaptured((err) => {
  panelCrashed.value = true
  if (typeof console !== 'undefined') console.error('[PropertyPanel] 子面板渲染异常:', err)
  return false // 阻止向上冒泡，避免破坏上层渲染树
})
const activeTab = ref('settings')
const menuBtnRef = ref(null)
const menuRef = ref(null)
const nodeType = computed(() => props.node ? (props.node.data._type || props.node.data.type) : '')
const meta = computed(() => getNodeType(nodeType.value))
const displayTitle = computed(() => props.node.data.title || props.node.data._title || meta.value.title)
const panelComponent = computed(() => (nodeType.value ? resolvePanel(nodeType.value) : null))
const nextSteps = computed(() => {
  const map = {
    start: ['llm', 'question-classifier', 'knowledge-retrieval'],
    llm: ['answer', 'end', 'if-else', 'knowledge-retrieval'],
    'knowledge-retrieval': ['llm', 'answer', 'end'],
    'question-classifier': ['llm', 'answer'],
    'if-else': ['llm', 'answer'],
    iteration: ['answer', 'end'],
    'parameter-extractor': ['llm', 'end']
  }
  return map[nodeType.value] || []
})

function onDocClick(e) {
  if (menuOpen.value && !menuRef.value?.contains(e.target) && !menuBtnRef.value?.contains(e.target)) {
    menuOpen.value = false
  }
}

function onTitleChange(e) {
  if (props.node) emit('update', props.node.id, { title: e.target.value })
}

function onDescChange(e) {
  if (props.node) emit('update', props.node.id, { desc: e.target.value })
}

function onPanelUpdate(nodeId, data) {
  emit('update', nodeId, data)
}

function onAddNext(type) {
  menuOpen.value = false
  emit('add-next', props.node.id, type)
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  // 空闲预热所有节点面板 chunk，消除首次切换时的加载空白
  preloadPanels()
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

watch(() => props.node, () => {
  menuOpen.value = false
  activeTab.value = 'settings'
  panelCrashed.value = false // 切换节点时重置错误态，保证下一个节点正常渲染
}, { immediate: true })
</script>

<style>
/* ===== Dify 设计系统变量（精确值） ===== */
.panel-scope {
  /* 文本颜色 */
  --text-primary: #1D2939;
  --text-secondary: #475467;
  --text-tertiary: #667085;
  --text-quaternary: #98A2B3;
  --text-destructive: #D92D20;

  /* 面板颜色 */
  --panel-bg: #F8F9FA;
  --panel-border: #EAECF0;
  --panel-surface: #FFFFFF;

  /* 交互颜色 */
  --accent: #155EEF;
  --accent-hover: #0B4CD3;
  --accent-light: #F0F4FF;
  --state-hover: #F2F4F7;
  --state-active: #E5E6EB;

  /* 字体 */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
</style>

<style scoped>
/* ===== 面板容器（精确还原 Dify BasePanel） ===== */
.property-panel {
  width: 420px;
  height: 100%;
  background: var(--panel-bg);
  border: 0.5px solid var(--panel-border);
  border-radius: 16px 0 0 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  position: relative;
  display: flex;
  flex-direction: column;
  font-family: var(--font-sans);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.property-panel.empty {
  align-items: center;
  justify-content: center;
}
.pp-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 16px 0 0 16px;
  overflow: hidden;
}

/* ===== 左侧拖动手柄（Dify ResizeHandle） ===== */
:deep(.pp-resize-handle) {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
:deep(.pp-resize-handle::before) {
  content: '';
  display: block;
  width: 2px;
  height: 40px;
  border-radius: 1px;
  background: #D0D5DD;
  transition: background 0.15s, height 0.15s;
}
:deep(.pp-resize-handle:hover::before),
:deep(.pp-resize-handle:active::before) {
  background: var(--accent);
  height: 100%;
}

/* ===== 头部（sticky，Dify 精确参数） ===== */
.pp-head {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--panel-bg);
  border-bottom: 0.5px solid var(--panel-border);
  flex-shrink: 0;
}
/* 标题行：px-4 pt-4 pb-1 = 16px 16px 4px */
.pp-head-row {
  display: flex;
  align-items: center;
  height: 24px;
  padding: 16px 16px 4px;
}
.pp-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  margin-right: 8px;
  flex-shrink: 0;
}
/* 标题输入框：system-sm-semibold = 14px/600 */
.pp-title-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  color: var(--text-primary);
  outline: none;
  letter-spacing: -0.01em;
}
.pp-title-input::placeholder { color: var(--text-tertiary); }
.pp-actions {
  display: flex;
  align-items: center;
  margin-left: auto;
  gap: 2px;
}
/* 操作按钮：size-6 = 24px, rounded-md = 6px */
.pp-action-btn {
  width: 24px;
  height: 24px;
  border: 0;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.pp-action-btn:hover {
  background: var(--state-hover);
  color: var(--text-secondary);
}
.pp-menu-sep {
  width: 1px;
  height: 14px;
  background: var(--panel-border);
  margin: 0 3px;
}

/* 描述行：p-2 = 8px, system-xs-medium-uppercase = 12px/500/uppercase */
.pp-desc-row {
  padding: 8px 16px;
}
.pp-desc-input {
  width: 100%;
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
  line-height: 18px;
  color: var(--text-tertiary);
  outline: none;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}
.pp-desc-input::placeholder { color: var(--text-quaternary); }

/* Tab 栏：pr-3 pl-4 = 12px 16px, system-sm-semibold-uppercase */
.pp-tabs {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 16px 0 12px;
}
.pp-tab {
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 8px 0;
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 1.5px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.pp-tab:hover { color: var(--text-secondary); }
.pp-tab-active {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}

/* ===== 下拉菜单（Dify NodeActionsDropdown 风格） ===== */
.pp-dropdown {
  position: absolute;
  top: 60px;
  right: 12px;
  z-index: 30;
  min-width: 160px;
  background: var(--panel-surface);
  border: 1px solid rgba(29, 41, 57, 0.08);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(29, 33, 41, 0.16);
  padding: 4px;
}
.pp-dropdown-item {
  width: 100%;
  justify-content: space-between;
  padding: 8px 12px;
  border: 0;
  background: transparent;
  border-radius: 6px;
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}
.pp-dropdown-item:hover { background: var(--state-hover); }
.pp-dropdown-danger { color: var(--text-destructive); }
.pp-dropdown-danger:hover { background: #FEF3F2; }

/* ===== 主体（Dify 精确参数：pt-2 px-4 space-y-4） ===== */
.pp-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px 16px;
}

/* 字段 / 卡片等设计系统统一定义在下方非 scoped 的 <style> 中，
   以便通过 .property-panel 命名空间级联到子面板组件的内部 DOM
   （scoped 样式无法穿透子组件内部元素）。*/

/* ===== 下一步推荐（Dify NextStep 风格） ===== */
.pp-next-step {
  border-top: 0.5px solid var(--panel-border);
  margin-top: 16px;
  padding: 16px 0 0;
}
.pp-next-step-title {
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pp-next-step-desc {
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 18px;
  color: var(--text-quaternary);
  margin-bottom: 12px;
}
.pp-next-step-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pp-next-step-btn {
  padding: 6px 12px;
  border: 1px solid #D0D5DD;
  border-radius: 6px;
  background: var(--panel-surface);
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 18px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.pp-next-step-btn:hover {
  background: var(--accent-light);
  border-color: var(--accent);
  color: var(--accent);
}

/* ===== Last Run 空态 ===== */
.pp-lastrun {
  display: flex;
  align-items: center;
  justify-content: center;
}
.pp-lastrun-empty {
  text-align: center;
  color: var(--text-quaternary);
}
.pp-lastrun-ico { font-size: 32px; margin-bottom: 8px; }
.pp-lastrun-text {
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}
.pp-lastrun-hint {
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 18px;
  color: var(--text-quaternary);
}

/* ===== 空态 ===== */
.pp-empty {
  text-align: center;
  color: var(--text-quaternary);
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
}
.pp-empty-ico { font-size: 32px; margin-bottom: 8px; }
</style>

<style>
/* ============================================================
   面板字段设计系统（非 scoped）
   参考 Dify：统一命名空间限定在 .property-panel 内，不污染全局；
   使懒加载的子面板组件内部 DOM（.pp-field / .pp-card / …）也能继承。
   ============================================================ */
.property-panel .pp-body { font-family: var(--font-sans); color: var(--text-primary); }

/* 分区标题（如 “输入变量” / “分支”） */
.property-panel .pp-section-title {
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  letter-spacing: 0.02em;
  color: var(--text-tertiary);
  margin: 4px 0 10px;
}

/* Field 容器 */
.property-panel .pp-field { margin-bottom: 14px; }
.property-panel .pp-field:last-child { margin-bottom: 0; }

/* Field 标签（兼容两种写法：PropertyPanel 的 .pp-field-label 与子面板的裸 <label>） */
.property-panel .pp-field-label,
.property-panel .pp-field > label {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  margin-bottom: 6px;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
  line-height: 18px;
  color: var(--text-secondary);
}

/* 输入控件 */
.property-panel .pp-field input,
.property-panel .pp-field select,
.property-panel .pp-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #D0D5DD;
  border-radius: 8px;
  padding: 8px 12px;
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
  color: var(--text-primary);
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.property-panel .pp-field input::placeholder,
.property-panel .pp-field textarea::placeholder { color: var(--text-quaternary); }
.property-panel .pp-field input:hover,
.property-panel .pp-field select:hover,
.property-panel .pp-field textarea:hover { border-color: #98A2B3; }
.property-panel .pp-field input:focus,
.property-panel .pp-field select:focus,
.property-panel .pp-field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(21, 94, 239, 0.12);
  outline: none;
}
.property-panel .pp-field select { cursor: pointer; }
.property-panel .pp-field textarea { resize: vertical; min-height: 68px; line-height: 22px; }

/* 滑块（Temperature） */
.property-panel .pp-field input[type='range'] {
  width: auto;
  flex: 1;
  padding: 0;
  border: none;
  background: transparent;
  accent-color: var(--accent);
  box-shadow: none !important;
}
.property-panel .pp-range-val { font-size: 12px; color: var(--text-tertiary); margin-left: 8px; min-width: 26px; }

/* 复选框字段（如 “必填”） */
.property-panel .pp-field.pp-check { display: flex; align-items: center; min-height: 32px; }
.property-panel .pp-field.pp-check > label {
  height: auto;
  min-height: 0;
  margin: 0;
  gap: 6px;
  font-weight: 400;
  font-size: 13px;
  color: var(--text-secondary);
}
.property-panel .pp-field.pp-check input[type='checkbox'] { width: 16px; height: 16px; accent-color: var(--accent); }

/* 提示文本 */
.property-panel .pp-hint { font-size: 12px; line-height: 18px; color: var(--text-tertiary); margin-top: 4px; }

/* 行布局 */
.property-panel .pp-row,
.property-panel .pp-model-row { display: flex; gap: 8px; align-items: center; }
.property-panel .pp-model-select { flex: 1; min-width: 0; }

/* 卡片（变量 / 分支 / 参数等列表项） */
.property-panel .pp-card {
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  background: #fff;
  padding: 10px 12px;
  margin-bottom: 10px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.property-panel .pp-card:hover { border-color: #D0D5DD; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05); }
.property-panel .pp-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.property-panel .pp-card-del {
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.property-panel .pp-card-del:hover { color: var(--text-destructive); background: #FEF3F2; }

/* 添加按钮（幽灵虚线） */
.property-panel .pp-add-btn {
  width: 100%;
  padding: 8px 12px;
  border: 1px dashed #D0D5DD;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
  cursor: pointer;
  transition: all 0.15s;
}
.property-panel .pp-add-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

/* LLM 面板「配置」按钮（mp-btn 在面板作用域内的兼容样式） */
.property-panel .mp-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 8px;
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 20px;
  cursor: pointer;
  border: 1px solid #D0D5DD;
  background: #fff;
  color: var(--text-secondary);
  white-space: nowrap;
  transition: all 0.15s;
}
.property-panel .mp-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.property-panel .mp-btn-sm { padding: 6px 10px; font-size: 12px; }

/* 面板异步加载骨架（首次加载某类面板 chunk 时占位，避免主体空白） */
.property-panel .pp-loading { padding: 4px 2px; display: flex; flex-direction: column; gap: 14px; }
.property-panel .pp-loading-bar {
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(90deg, #F2F4F7 25%, #EAECF0 37%, #F2F4F7 63%);
  background-size: 400% 100%;
  animation: pp-loading-shimmer 1.3s ease infinite;
}
.property-panel .pp-loading-bar--short { width: 45%; }
.property-panel .pp-loading-bar--mid { width: 70%; }
@keyframes pp-loading-shimmer { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.property-panel .pp-panel-error {
  margin: 12px 0;
  padding: 14px 16px;
  border-radius: 8px;
  background: #FEF3F2;
  border: 1px solid #FECDCA;
  color: #B42318;
  font-size: 13px;
  line-height: 1.5;
}
</style>

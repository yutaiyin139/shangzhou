/**
 * PanelRegistry - 节点类型到面板组件的注册表
 *
 * 将工作流节点类型映射到对应的属性面板组件，
 * 实现按节点类型懒加载对应的面板。
 */
import { defineAsyncComponent, defineComponent, h } from 'vue'
import type { Component } from 'vue'

// 懒加载所有面板组件
const panelModules = import.meta.glob('./*.vue')

/** 节点类型 → 面板组件映射表 */
const panelMap: Record<string, () => Promise<Component>> = {
  // 基础节点
  start: () => import('./StartPanel.vue'),
  end: () => import('./EndPanel.vue'),
  answer: () => import('./AnswerPanel.vue'),
  'custom-note': () => import('./CustomNotePanel.vue'),

  // AI / LLM 节点
  llm: () => import('./LLMPanel.vue'),
  agent: () => import('./AgentPanel.vue'),

  // 代码执行
  code: () => import('./CodePanel.vue'),

  // 知识库
  'knowledge-retrieval': () => import('./KnowledgeRetrievalPanel.vue'),
  'knowledge_retrieval': () => import('./KnowledgeRetrievalPanel.vue'),
  'knowledge-index': () => import('./KnowledgeIndexPanel.vue'),
  'knowledge_index': () => import('./KnowledgeIndexPanel.vue'),

  // 外部调用
  'http-request': () => import('./HttpPanel.vue'),
  'http_request': () => import('./HttpPanel.vue'),
  tool: () => import('./ToolPanel.vue'),
  mcp: () => import('./MCPPanel.vue'),
  datasource: () => import('./DatasourcePanel.vue'),

  // 流程控制
  'if-else': () => import('./IfElsePanel.vue'),
  'if_else': () => import('./IfElsePanel.vue'),
  iteration: () => import('./IterationPanel.vue'),
  loop: () => import('./LoopPanel.vue'),
  'sub-graph': () => import('./SubGraphPanel.vue'),
  'sub_graph': () => import('./SubGraphPanel.vue'),

  // 批量 / 触发
  'batch-task': () => import('./BatchTaskPanel.vue'),
  'batch_task': () => import('./BatchTaskPanel.vue'),
  'trigger-schedule': () => import('./TriggerPanel.vue'),
  'trigger-webhook': () => import('./TriggerPanel.vue'),

  // 数据处理
  'variable-assigner': () => import('./VariableAssignerPanel.vue'),
  assigner: () => import('./VariableAssignerPanel.vue'),
  'variable-aggregator': () => import('./VariableAggregatorPanel.vue'),
  'variable_aggregator': () => import('./VariableAggregatorPanel.vue'),
  'template-transform': () => import('./TemplateTransformPanel.vue'),
  'template_transform': () => import('./TemplateTransformPanel.vue'),
  'list-operator': () => import('./ListOperatorPanel.vue'),
  'list_operator': () => import('./ListOperatorPanel.vue'),

  // AI 分类 / 提取
  'question-classifier': () => import('./QuestionClassifierPanel.vue'),
  'question_classifier': () => import('./QuestionClassifierPanel.vue'),
  'parameter-extractor': () => import('./ParameterExtractorPanel.vue'),
  'parameter_extractor': () => import('./ParameterExtractorPanel.vue'),
  'document-extractor': () => import('./DocumentExtractorPanel.vue'),
  'document_extractor': () => import('./DocumentExtractorPanel.vue'),

  // 人机交互
  'human-input': () => import('./HumanInputPanel.vue'),
}

/**
 * 获取节点类型对应的面板组件（异步加载函数）
 * @param nodeType 节点类型标识
 * @returns 面板组件异步加载函数，未找到返回 null
 */
export function getPanelComponent(nodeType: string): (() => Promise<Component>) | null {
  return panelMap[nodeType] || null
}

// 按节点类型缓存已创建的异步组件，保证同一类型的组件定义标识稳定。
// 关键：defineAsyncComponent 只能创建一次，若在 computed 中每次选择节点都
// 重新创建，会得到全新的组件类型，导致 <component :is> 反复卸载/重装 + 异步
// 重新解析，出现「切换节点后面板显示异常/闪烁」的问题。
const asyncPanelCache = new Map<string, Component>()

// 面板加载骨架：首次异步加载某类面板 chunk 期间，避免面板主体「空白」
// （历史上表现为「点击知识检索节点后再点其他节点，配置区域空白/显示不正常」）。
const PanelLoading = defineComponent({
  name: 'PanelLoading',
  render() {
    return h('div', { class: 'pp-loading' }, [
      h('div', { class: 'pp-loading-bar' }),
      h('div', { class: 'pp-loading-bar pp-loading-bar--short' }),
      h('div', { class: 'pp-loading-bar' }),
      h('div', { class: 'pp-loading-bar pp-loading-bar--mid' }),
    ])
  },
})

// 已加载成功的面板类型，用于失败重试判定
let chunkReloadFlagKey = 'wf-panel-chunk-reloaded'
const chunkAttempts = new Map<string, number>()

/**
 * 解析节点类型对应的面板组件（返回稳定、可缓存的异步组件实例）。
 * @param nodeType 节点类型标识
 * @returns 异步组件，未注册返回 null
 */
export function resolvePanel(nodeType: string): Component | null {
  const loader = panelMap[nodeType]
  if (!loader) return null
  let comp = asyncPanelCache.get(nodeType)
  if (!comp) {
    comp = defineAsyncComponent({
      loader: loader as () => Promise<Component>,
      loadingComponent: PanelLoading,
      // 立即显示骨架，消除默认 200ms 的空白窗口
      delay: 0,
      // chunk 加载失败（多因构建产物 hash 变更后浏览器仍引用旧 chunk）时，
      // 整页刷新一次以拉取最新资源，避免面板永久停留在空白/异常状态。
      onError(err, retry, fail) {
        const attempts = (chunkAttempts.get(nodeType) || 0) + 1
        chunkAttempts.set(nodeType, attempts)
        if (attempts <= 1 && typeof window !== 'undefined') {
          const reloaded = sessionStorage.getItem(chunkReloadFlagKey)
          if (!reloaded) {
            sessionStorage.setItem(chunkReloadFlagKey, '1')
            window.location.reload()
            return
          }
        }
        // 已刷新过一次仍失败，放弃重试并把错误抛回控制台，不再无限刷新
        fail()
        if (typeof console !== 'undefined') console.error('[PanelRegistry] 面板加载失败:', nodeType, err)
        void retry
      },
    })
    asyncPanelCache.set(nodeType, comp)
  }
  return comp
}

// 是否已预热过面板 chunk
let panelsPreloaded = false
/**
 * 空闲时预热所有面板 chunk：让「首次点击某类型节点」也能即时渲染，
 * 从根本上消除首次异步加载带来的空白/异常观感。
 */
export function preloadPanels(): void {
  if (panelsPreloaded || typeof window === 'undefined') return
  panelsPreloaded = true
  const run = () => {
    Object.values(panelMap).forEach((l) => {
      try { Promise.resolve(l()).catch(() => {}) } catch (e) { /* 忽略预热带来的失败 */ }
    })
    // 刷新标记：下次进入页面可再次预热
    try { sessionStorage.removeItem(chunkReloadFlagKey) } catch (e) { /* noop */ }
  }
  const w = window as unknown as { requestIdleCallback?: (cb: () => void, opt?: { timeout: number }) => void }
  if (w.requestIdleCallback) w.requestIdleCallback(run, { timeout: 2000 })
  else setTimeout(run, 400)
}

/**
 * 获取所有已注册的节点类型列表
 */
export function getRegisteredNodeTypes(): string[] {
  return Object.keys(panelMap)
}

export default panelMap

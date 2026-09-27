/**
 * usePanelState - PropertyPanel 共享状态 composable
 *
 * 为各面板组件提供统一的本地状态、模型/数据集/工具加载、
 * commit 机制等公共能力。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { apiGet } from '../../../api/client'

/** 节点数据 selector 解析辅助 */
export function parseSelector(selector: string): string[] {
  // "{{#node.var#}}" -> ['node', 'var']
  const m = selector.match(/#([\w.]+)#/)
  return m ? m[1].split('.') : []
}

export function formatSelector(parts: string[] | undefined[][]): string {
  if (!parts.length) return ''
  if (Array.isArray(parts[0]) && typeof parts[0] !== 'string') {
    return '{{#' + (parts as unknown as string[][]).map(p => p.join('.')).join(',') + '#}}'
  }
  return '{{#' + (parts as string[]).join('.') + '#}}'
}

export function usePanelState(props: { node: any }, emit: any) {
  const local = ref<Record<string, any>>({})
  const models = ref<any[]>([])
  const datasets = ref<any[]>([])
  const builtinSources = ref<any[]>([])
  const connectors = ref<any[]>([])
  const tools = ref<any[]>([])
  const mcpServers = ref<any[]>([])
  const mcpTools = ref<any[]>([])

  // 节点可调用内置数据源白名单
  const DATASOURCE_NODE_SUPPORTED = ['jina-reader', 'firecrawl', 'tavily', 'github', 'gitlab', 'notion']

  function cloneNodeData() {
    if (!props.node) return {}
    const d = props.node.data || {}
    return JSON.parse(JSON.stringify(d))
  }

  function commit() {
    if (!props.node) return
    emit('update', props.node.id, JSON.parse(JSON.stringify(local.value)))
  }

  function removeArrayItem(field: string, index: number) {
    if (!Array.isArray(local.value[field])) local.value[field] = []
    local.value[field].splice(index, 1)
    commit()
  }

  // 模型相关
  function formatProvider(provider: string) {
    const p = (provider || '').trim().toLowerCase()
    if (!p) return ''
    if (p.includes('/')) return p
    return 'langgenius/' + p + '/' + p
  }

  function shortProvider(provider: string) {
    const p = (provider || '').trim().toLowerCase()
    const parts = p.split('/')
    if (parts.length >= 3 && parts[0] === 'langgenius') return parts[1]
    return p
  }

  function modelOptionKey(m: any) {
    return (m.provider || '') + '::' + (m.model_name || '')
  }

  /** 节点里已存的模型 → 下拉 value（provider 存的是 langgenius/x/x，要削成短名才能和 option 对上） */
  function storedModelKey() {
    const m = local.value.model || {}
    const short = shortProvider(m.provider)
    return short && m.name ? (short + '::' + m.name) : ''
  }

  /**
   * 把下拉选中的 key 写回节点数据。
   *
   * 以前只有 commitModel() 一条路，而它读的是 modelKey.value —— 但 modelKey 是个
   * `set: () => {}` 的只读 computed，v-model 的写入被静默吞掉，于是“选了任何模型”
   * 都等于把旧值原样写回去，5 个用模型下拉的面板（LLM/Agent/批量任务/参数提取/问题分类）
   * 全部选不上。现在 setter 与 commitModel 都走这里，谁先谁后结果一致。
   */
  function applyModelKey(key: string) {
    if (!local.value.model) local.value.model = {}
    if (!key) {
      local.value.model.provider = ''
      local.value.model.name = ''
    } else {
      const idx = key.indexOf('::')
      if (idx === -1) return
      local.value.model.provider = formatProvider(key.slice(0, idx))
      local.value.model.name = key.slice(idx + 2)
      // mode 不再无条件写死 'chat'：节点原有 mode（如 completion）不能被一次改选丢掉
      local.value.model.mode = local.value.model.mode || 'chat'
    }
    if (!local.value.model.completion_params) local.value.model.completion_params = {}
    commit()
  }

  const modelKey = computed({
    get: () => {
      const key = storedModelKey()
      const m = local.value.model || {}
      if (key && !models.value.some((mo: any) => modelOptionKey(mo) === key)) {
        const alt = models.value.find((mo: any) => mo.provider === shortProvider(m.provider) && mo.model_name === m.name)
        if (alt) return modelOptionKey(alt)
      }
      return key
    },
    set: (val: string) => { applyModelKey(val || '') }
  })

  /**
   * 下拉选项列表。
   *
   * 两点都不是可有可无的修饰：
   * 1) 节点里存的模型可能根本不在已配置列表里（模板应用常带 openai/gpt-5 这种没接入的），
   *    这时 <select> 找不到匹配 option 会把整个框渲染成**空白**，看起来像“没有可选项/控件坏了”。
   *    所以把当前值补一项并标注未配置，让用户看见现状、也能直接改选。
   * 2) 同一个 provider + model_name 可以配多条凭据（不同 key / 不同 base_url），
   *    但图里只能存 provider + name + mode，区分不了凭据。按凭据逐条列出会产生
   *    **重复 value**，<select> 选完会跳回首个同值项（点 A 显示 B）→ 按 key 去重，
   *    标签用厂商/模型名而不是凭据名，与图里实际能存下的信息一致。
   * 3) 只列可对话的模型：model_configs 里混着 embedding / rerank 等类型，
   *    它们出现在 LLM 类节点的下拉里选了也不报错，要到运行期才炸。
   *    （只在这个选项列表里过滤，models 仍是后端返回的完整列表。）
   */
  const modelChoices = computed(() => {
    const CHAT_TYPES = ['llm', 'chat', '']
    const seen = new Set<string>()
    const list: { key: string; label: string }[] = []
    for (const m of models.value) {
      if (!CHAT_TYPES.includes(String(m.model_type || '').toLowerCase())) continue
      const key = modelOptionKey(m)
      if (seen.has(key)) continue
      seen.add(key)
      list.push({
        key,
        label: (m.provider_label || m.provider) + ' / ' + (m.model_label || m.model_name),
      })
    }
    const cur = storedModelKey()
    if (cur && !seen.has(cur)) {
      const m = local.value.model || {}
      list.unshift({
        key: cur,
        label: '（未配置）' + (shortProvider(m.provider) || '?') + ' / ' + (m.name || '?'),
      })
    }
    return list
  })

  const temperature = computed({
    get: () => {
      if (!local.value.model) return 0.7
      if (!local.value.model.completion_params) return 0.7
      return local.value.model.completion_params.temperature ?? 0.7
    },
    set: (val: number) => {
      if (!local.value.model) local.value.model = {}
      if (!local.value.model.completion_params) local.value.model.completion_params = {}
      local.value.model.completion_params.temperature = val
    }
  })

  const systemPrompt = computed({
    get: () => {
      const arr = local.value.prompt_template || []
      const sys = arr.find((p: any) => p.role === 'system')
      return sys ? sys.text : ''
    },
    set: (val: string) => {
      if (!Array.isArray(local.value.prompt_template)) local.value.prompt_template = []
      const idx = local.value.prompt_template.findIndex((p: any) => p.role === 'system')
      if (idx !== -1) {
        local.value.prompt_template[idx].text = val
      } else if (val) {
        local.value.prompt_template.push({ role: 'system', text: val, id: Math.random().toString(36).slice(2) })
      }
    }
  })

  const userPrompt = computed({
    get: () => {
      const arr = local.value.prompt_template || []
      const usr = arr.find((p: any) => p.role === 'user')
      return usr ? usr.text : ''
    },
    set: (val: string) => {
      if (!Array.isArray(local.value.prompt_template)) local.value.prompt_template = []
      const idx = local.value.prompt_template.findIndex((p: any) => p.role === 'user')
      if (idx !== -1) {
        local.value.prompt_template[idx].text = val
      } else if (val) {
        local.value.prompt_template.push({ role: 'user', text: val, id: Math.random().toString(36).slice(2) })
      }
    }
  })

  function commitModel(chosen?: string) {
    // 模板里写成 @change="commitModel" 时首参是 Event，退回读 modelKey（v-model 已把新值写进 local）
    applyModelKey(typeof chosen === 'string' ? chosen : modelKey.value)
  }

  function commitPrompt() {
    const sys = systemPrompt.value
    const usr = userPrompt.value
    const arr: any[] = []
    if (sys || usr) {
      if (sys) arr.push({ role: 'system', text: sys, id: Math.random().toString(36).slice(2) })
      if (usr) arr.push({ role: 'user', text: usr, id: Math.random().toString(36).slice(2) })
    }
    local.value.prompt_template = arr
    commit()
  }

  // 知识库相关
  const selectedDataset = ref('')
  function commitDataset() {
    local.value.dataset_ids = selectedDataset.value ? [selectedDataset.value] : []
    commit()
  }

  // 兼容两种历史存储形态：
  //   - Dify / 模板常见扁平：['node', 'var'] 或 ['item']
  //   - 本编辑器提交的多段：[['node', 'var'], ...]
  const querySelector = computed({
    get: () => {
      const sel: any[] = local.value.query_variable_selector || []
      if (!sel.length) return ''
      if (Array.isArray(sel[0])) {
        return sel.map((s) => '{{#' + (Array.isArray(s) ? s.join('.') : String(s)) + '#}}').join('')
      }
      return '{{#' + sel.join('.') + '#}}'
    },
    set: () => {}
  })

  function commitQuery() {
    const m = querySelector.value.match(/#([\w.]+)#/)
    local.value.query_variable_selector = m ? [m[1].split('.')] : []
    commit()
  }

  // 工具相关
  const selectedToolProvider = ref('')
  const selectedToolAction = ref('')

  const toolActions = computed(() => {
    const provider = tools.value.find(t => t.id === selectedToolProvider.value)
    return provider ? (provider.tools || []) : []
  })

  const toolParams = computed(() => {
    const provider = tools.value.find(t => t.id === selectedToolProvider.value)
    if (!provider) return []
    const action = (provider.tools || []).find((a: any) => a.name === selectedToolAction.value)
    return action ? (action.parameters || []) : []
  })

  function commitToolProvider() {
    local.value.provider_id = selectedToolProvider.value
    selectedToolAction.value = ''
    local.value.tool_name = ''
    local.value.tool_parameters = {}
    const provider = tools.value.find(t => t.id === selectedToolProvider.value)
    local.value.provider_name = provider ? provider.id : ''
    commit()
  }

  function commitToolAction() {
    local.value.tool_name = selectedToolAction.value
    local.value.tool_parameters = {}
    toolParams.value.forEach((p: any) => {
      local.value.tool_parameters[p.name] = { type: 'constant', value: '' }
    })
    commit()
  }

  function commitToolParam(_name: string) {
    if (!local.value.tool_parameters) local.value.tool_parameters = {}
    commit()
  }

  // MCP 相关
  const selectedMcpServer = ref('')
  const selectedMcpTool = ref('')

  const mcpToolParams = computed(() => {
    const tool = mcpTools.value.find(t => t.name === selectedMcpTool.value)
    return tool ? (tool.parameters || []) : []
  })

  function commitMcpServer() {
    local.value.mcp_server_id = selectedMcpServer.value
    selectedMcpTool.value = ''
    local.value.mcp_tool_name = ''
    local.value.mcp_parameters = {}
    loadMcpTools(selectedMcpServer.value)
    commit()
  }

  function commitMcpTool() {
    local.value.mcp_tool_name = selectedMcpTool.value
    local.value.mcp_parameters = {}
    mcpToolParams.value.forEach((p: any) => {
      local.value.mcp_parameters[p.name] = { type: 'constant', value: '' }
    })
    commit()
  }

  function commitMcpParam(_name: string) {
    if (!local.value.mcp_parameters) local.value.mcp_parameters = {}
    commit()
  }

  async function loadMcpTools(serverId: string) {
    if (!serverId) { mcpTools.value = []; return }
    try {
      const res = await apiGet<any[]>(`/api/mcps/${serverId}/tools`)
      mcpTools.value = res.code === 200 ? (res.data || []) : []
    } catch (e) { mcpTools.value = [] }
  }

  // 加载所有下拉数据
  async function loadAllOptions() {
    /* 统一走 apiGet：裸 fetch 不带 Authorization，遇到需要登录的接口会 401
       （/api/knowledge/datasets 就是这样一个已经默默失效的调用） */
    try {
      const res = await apiGet<any[]>('/api/model-configs')
      if (res.code === 200) models.value = (res.data || []).filter((m: any) => m.status === 1)
    } catch (e) {}
    try {
      const res = await apiGet<any[]>('/api/knowledge/datasets')
      if (res.code === 200) datasets.value = res.data || []
    } catch (e) {}
    try {
      const res = await apiGet<any[]>('/api/tools/builtin')
      if (res.code === 200) tools.value = res.data || []
    } catch (e) {}
    try {
      const res = await apiGet<any[]>('/api/mcps')
      if (res.code === 200) mcpServers.value = (res.data || []).filter((s: any) => s.enabled !== 0)
    } catch (e) {}
    try {
      const res = await apiGet<any[]>('/api/data-sources')
      if (res.code === 200) {
        builtinSources.value = (res.data || []).map((s: any) => ({
          key: s.key, name: s.name, icon: s.icon,
          supported: DATASOURCE_NODE_SUPPORTED.includes(s.key),
        }))
      }
    } catch (e) {}
    try {
      const res = await apiGet<any[]>('/api/connectors/custom')
      if (res.code === 200) connectors.value = res.data || []
    } catch (e) {}
  }

  // 监听节点变化重置状态
  watch(() => props.node, () => {
    local.value = cloneNodeData()
    selectedToolProvider.value = local.value.provider_id || ''
    selectedToolAction.value = local.value.tool_name || ''
    selectedDataset.value = (local.value.dataset_ids && local.value.dataset_ids.length) ? local.value.dataset_ids[0] : ''
    selectedMcpServer.value = local.value.mcp_server_id || ''
    selectedMcpTool.value = local.value.mcp_tool_name || ''
    if (selectedMcpServer.value) loadMcpTools(selectedMcpServer.value)
  }, { immediate: true })

  onMounted(loadAllOptions)

  return {
    local, commit, removeArrayItem,
    models, datasets, builtinSources, connectors, tools, mcpServers, mcpTools,
    modelKey, modelChoices, temperature, systemPrompt, userPrompt,
    commitModel, commitPrompt,
    selectedDataset, commitDataset,
    querySelector, commitQuery,
    selectedToolProvider, selectedToolAction, toolActions, toolParams,
    commitToolProvider, commitToolAction, commitToolParam,
    selectedMcpServer, selectedMcpTool, mcpToolParams,
    commitMcpServer, commitMcpTool, commitMcpParam, loadMcpTools,
    formatProvider, shortProvider, modelOptionKey,
  }
}

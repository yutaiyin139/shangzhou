/**
 * usePanelState - PropertyPanel 共享状态 composable
 *
 * 为各面板组件提供统一的本地状态、模型/数据集/工具加载、
 * commit 机制等公共能力。
 */
import { ref, computed, watch, onMounted } from 'vue'

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

  const modelKey = computed({
    get: () => {
      const m = local.value.model || {}
      const short = shortProvider(m.provider)
      const key = short && m.name ? (short + '::' + m.name) : ''
      if (key && !models.value.some((mo: any) => modelOptionKey(mo) === key)) {
        const alt = models.value.find((mo: any) => mo.provider === short && mo.model_name === m.name)
        if (alt) return modelOptionKey(alt)
      }
      return key
    },
    set: () => {}
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

  function commitModel() {
    if (!modelKey.value) return
    const idx = modelKey.value.indexOf('::')
    if (idx === -1) return
    const short = modelKey.value.slice(0, idx)
    const mName = modelKey.value.slice(idx + 2)
    if (!local.value.model) local.value.model = {}
    local.value.model.provider = formatProvider(short)
    local.value.model.name = mName
    local.value.model.mode = 'chat'
    if (!local.value.model.completion_params) local.value.model.completion_params = {}
    commit()
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
      const r = await fetch(`/api/mcps/${serverId}/tools`)
      const res = await r.json()
      mcpTools.value = res.code === 200 ? (res.data || []) : []
    } catch (e) { mcpTools.value = [] }
  }

  // 加载所有下拉数据
  async function loadAllOptions() {
    try {
      const r = await fetch('/api/model-configs')
      const res = await r.json()
      if (res.code === 200) models.value = (res.data || []).filter((m: any) => m.status === 1)
    } catch (e) {}
    try {
      const r = await fetch('/api/knowledge/datasets')
      const res = await r.json()
      if (res.code === 200) datasets.value = res.data || []
    } catch (e) {}
    try {
      const r = await fetch('/api/tools/builtin')
      const res = await r.json()
      if (res.code === 200) tools.value = res.data || []
    } catch (e) {}
    try {
      const r = await fetch('/api/mcps')
      const res = await r.json()
      if (res.code === 200) mcpServers.value = (res.data || []).filter((s: any) => s.enabled !== 0)
    } catch (e) {}
    try {
      const r = await fetch('/api/data-sources')
      const res = await r.json()
      if (res.code === 200) {
        builtinSources.value = (res.data || []).map((s: any) => ({
          key: s.key, name: s.name, icon: s.icon,
          supported: DATASOURCE_NODE_SUPPORTED.includes(s.key),
        }))
      }
    } catch (e) {}
    try {
      const r = await fetch('/api/connectors/custom')
      const res = await r.json()
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
    modelKey, temperature, systemPrompt, userPrompt,
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

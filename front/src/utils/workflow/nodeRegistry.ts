/**
 * 工作流节点注册表
 * 与平台 graph.data.type 对应，提供图标、标题、默认数据、端口规则
 */

/** 节点类型定义 */
interface NodeTypeConfig {
  type: string
  title: string
  description: string
  category: string
  icon: string
  color: string
  inputs: number
  outputs: number
  defaultData: Record<string, unknown>
}

/** 节点分类 */
interface NodeCategory {
  key: string
  label: string
}

/** 节点分类（带节点列表） */
interface NodeCategoryWithNodes extends NodeCategory {
  nodes: NodeTypeConfig[]
}

export const NODE_CATEGORIES: NodeCategory[] = [
  { key: 'basic', label: '基础' },
  { key: 'llm', label: 'LLM' },
  { key: 'logic', label: '逻辑' },
  { key: 'tool', label: '工具' },
  { key: 'trigger', label: '触发' },
  { key: 'output', label: '输出' }
]

export const NODE_TYPES: Record<string, NodeTypeConfig> = {
  start: {
    type: 'start',
    title: '开始',
    description: '工作流入口，定义输入变量',
    category: 'basic',
    icon: '✳',
    color: '#2E63F0',
    inputs: 0,
    outputs: 1,
    defaultData: {
      type: 'start',
      title: '开始',
      variables: []
    }
  },
  llm: {
    type: 'llm',
    title: 'LLM',
    description: '调用大语言模型生成内容',
    category: 'llm',
    icon: '✦',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'llm',
      title: 'LLM',
      model: { provider: 'langgenius/openai/openai', name: 'gpt-4o-mini', mode: 'chat', completion_params: { temperature: 0.7 } },
      prompt_template: [{ role: 'system', text: '' }],
      context: { enabled: false, variable_selector: [] },
      vision: { enabled: false }
    }
  },
  answer: {
    type: 'answer',
    title: '直接回复',
    description: '直接输出指定内容',
    category: 'output',
    icon: '↩',
    color: '#F77234',
    inputs: 1,
    outputs: 0,
    defaultData: {
      type: 'answer',
      title: '直接回复',
      answer: ''
    }
  },
  end: {
    type: 'end',
    title: '结束',
    description: '工作流终点，定义输出变量',
    category: 'output',
    icon: '⏹',
    color: '#F53F3F',
    inputs: 1,
    outputs: 0,
    defaultData: {
      type: 'end',
      title: '结束',
      outputs: []
    }
  },
  code: {
    type: 'code',
    title: '代码执行',
    description: '执行 Python/JavaScript 代码',
    category: 'tool',
    icon: '💻',
    color: '#00B2FF',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'code',
      title: '代码执行',
      code_language: 'python3',
      code: '# 输入变量通过 args 传入\n',
      outputs: { result: { type: 'string' } }
    }
  },
  'if-else': {
    type: 'if-else',
    title: '条件分支',
    description: '根据条件表达式分流',
    category: 'logic',
    icon: '◈',
    color: '#FF7D00',
    inputs: 1,
    outputs: 2,
    defaultData: {
      type: 'if-else',
      title: '条件分支',
      cases: [
        { id: 'true', name: '条件1', conditions: [] },
        { id: 'false', name: '否则', conditions: [] }
      ]
    }
  },
  'knowledge-retrieval': {
    type: 'knowledge-retrieval',
    title: '知识检索',
    description: '从知识库中检索相关内容',
    category: 'tool',
    icon: '📚',
    color: '#00B42A',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'knowledge-retrieval',
      title: '知识检索',
      query_variable_selector: [],
      dataset_ids: [],
      retrieval_mode: 'single'
    }
  },
  'http-request': {
    type: 'http-request',
    title: 'HTTP 请求',
    description: '发起 HTTP 请求获取数据',
    category: 'tool',
    icon: '🌐',
    color: '#4E5BF5',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'http-request',
      title: 'HTTP 请求',
      method: 'get',
      url: '',
      headers: '',
      params: '',
      body: ''
    }
  },
  tool: {
    type: 'tool',
    title: '工具',
    description: '调用外部工具或 API',
    category: 'tool',
    icon: '🔧',
    color: '#86909C',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'tool',
      title: '工具',
      provider_id: '',
      tool_name: '',
      tool_parameters: {}
    }
  },
  mcp: {
    type: 'mcp',
    title: 'MCP 工具',
    description: '调用 MCP 协议工具',
    category: 'tool',
    icon: '🔌',
    color: '#13C2C2',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'mcp',
      title: 'MCP 工具',
      mcp_server_id: '',
      mcp_tool_name: '',
      mcp_parameters: {}
    }
  },
  'variable-assigner': {
    type: 'variable-assigner',
    title: '变量赋值',
    description: '对变量进行赋值或合并',
    category: 'logic',
    icon: '🔀',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'variable-assigner',
      title: '变量赋值',
      variables: []
    }
  },
  assigner: {
    type: 'assigner',
    title: '变量赋值',
    description: '对变量进行赋值或合并',
    category: 'logic',
    icon: '🔀',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'assigner',
      title: '变量赋值',
      variables: []
    }
  },
  'document-extractor': {
    type: 'document-extractor',
    title: '文档提取',
    description: '从文档中提取指定字段内容',
    category: 'tool',
    icon: '📄',
    color: '#4A7FE8',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'document-extractor',
      title: '文档提取',
      variable_selector: []
    }
  },
  'template-transform': {
    type: 'template-transform',
    title: '模板转换',
    description: '使用 Jinja2 模板转换数据格式',
    category: 'tool',
    icon: '📋',
    color: '#00B2FF',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'template-transform',
      title: '模板转换',
      variables: [],
      template: ''
    }
  },
  'question-classifier': {
    type: 'question-classifier',
    title: '问题分类',
    description: '根据问题类型分流到不同分支',
    category: 'logic',
    icon: '❓',
    color: '#FF7D00',
    inputs: 1,
    outputs: 2,
    defaultData: {
      type: 'question-classifier',
      title: '问题分类',
      model: { provider: '', name: '', mode: 'chat', completion_params: { temperature: 0.7 } },
      classes: []
    }
  },
  iteration: {
    type: 'iteration',
    title: '迭代',
    description: '对数组元素逐个处理或按条件循环',
    category: 'logic',
    icon: '🔁',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'iteration',
      title: '迭代',
      input_selector: [],
      output_selector: []
    }
  },
  loop: {
    type: 'loop',
    title: '循环',
    description: '按次数或条件循环执行子流程',
    category: 'logic',
    icon: '🔄',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'loop',
      title: '循环',
      loop_type: 'count',
      count: 3,
      max_iterations: 100,
      output_variable: 'loop_results',
      output_selector: []
    }
  },
  'sub-graph': {
    type: 'sub-graph',
    title: '子工作流',
    description: '调用另一个工作流作为子流程',
    category: 'logic',
    icon: '📦',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'sub-graph',
      title: '子工作流',
      sub_app_id: '',
      sub_workflow_id: '',
      input_mapping: [],
      output_mapping: {}
    }
  },
  'list-operator': {
    type: 'list-operator',
    title: '列表操作',
    description: '对列表进行过滤、映射等操作',
    category: 'logic',
    icon: '🔢',
    color: '#722ED1',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'list-operator',
      title: '列表操作',
      operator: 'filter'
    }
  },
  'parameter-extractor': {
    type: 'parameter-extractor',
    title: '参数提取',
    description: '从文本中提取结构化参数',
    category: 'tool',
    icon: '🔍',
    color: '#86909C',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'parameter-extractor',
      title: '参数提取',
      model: { provider: '', name: '', mode: 'chat', completion_params: { temperature: 0.7 } },
      parameters: []
    }
  },
  'custom-note': {
    type: 'custom-note',
    title: '注释',
    description: '添加说明性文字，不参与执行',
    category: 'basic',
    icon: '📝',
    color: '#4A7FE8',
    inputs: 0,
    outputs: 0,
    defaultData: {
      type: 'custom-note',
      title: '注释',
      text: ''
    }
  },
  agent: {
    type: 'agent',
    title: 'Agent',
    description: '自主调用工具完成任务',
    category: 'llm',
    icon: '🤖',
    color: '#9B4DFF',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'agent',
      title: 'Agent',
      model: { provider: '', name: '', mode: 'chat', completion_params: { temperature: 0.7 } },
      prompt: ''
    }
  },
  'batch-task': {
    type: 'batch-task',
    title: '批量任务',
    description: '并行或串行处理批量子任务',
    category: 'tool',
    icon: '📦',
    color: '#00B42A',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'batch-task',
      title: '批量任务',
      input_selector: ['start', 'items'],
      task_type: 'llm',
      task_config: {
        prompt_template: '{{item}}',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        max_tokens: 1000
      },
      batch_size: 5,
      max_parallel: 1,
      error_strategy: 'continue_on_error',
      output_variable: 'batch_results',
      max_items: 500
    }
  },
  'trigger-schedule': {
    type: 'trigger-schedule',
    title: '定时触发',
    description: '按 Cron 表达式定时启动工作流',
    category: 'trigger',
    icon: '⏰',
    color: '#F5A623',
    inputs: 0,
    outputs: 1,
    defaultData: {
      type: 'trigger-schedule',
      title: '定时触发',
      cron_expr: '0 9 * * *',
      timezone: 'Asia/Shanghai',
      enabled: true
    }
  },
  'trigger-webhook': {
    type: 'trigger-webhook',
    title: 'Webhook 触发',
    description: '通过外部 HTTP 请求触发工作流',
    category: 'trigger',
    icon: '🪝',
    color: '#F5A623',
    inputs: 0,
    outputs: 1,
    defaultData: {
      type: 'trigger-webhook',
      title: 'Webhook 触发',
      enabled: true
    }
  },
  datasource: {
    type: 'datasource',
    title: '数据源',
    description: '从内置数据源检索数据',
    category: 'tool',
    icon: '🗄️',
    color: '#0FC6C2',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'datasource',
      title: '数据源',
      source_type: 'builtin',
      source_key: '',
      operation: 'search',
      query: '',
      limit: 10
    }
  },
  'knowledge-index': {
    type: 'knowledge-index',
    title: '知识索引',
    description: '将内容写入知识库索引',
    category: 'tool',
    icon: '📇',
    color: '#00B42A',
    inputs: 1,
    outputs: 1,
    defaultData: {
      type: 'knowledge-index',
      title: '知识索引',
      dataset_id: '',
      content_variable: 'content',
      document_name: '',
      max_length: 1024,
      overlap: 50,
      delimiter: '\n'
    }
  }
}

export function getNodeType(type: string): NodeTypeConfig {
  return NODE_TYPES[type] || {
    type: type || 'unknown',
    title: type ? type : '节点',
    category: 'basic',
    icon: '⬡',
    color: '#86909C',
    inputs: 1,
    outputs: 1,
    defaultData: { type: type || 'unknown', title: type ? type : '节点' }
  }
}

export function createNodeData(type: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const def = getNodeType(type)
  return { ...JSON.parse(JSON.stringify(def.defaultData)), ...overrides }
}

export function nodeCategoriesList(): NodeCategoryWithNodes[] {
  return NODE_CATEGORIES.map(cat => ({
    ...cat,
    nodes: Object.values(NODE_TYPES).filter(n => n.category === cat.key)
  }))
}

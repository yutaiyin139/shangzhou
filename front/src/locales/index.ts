/* ============ 国际化（i18n）模块 ============
 *
 * 轻量级 i18n 实现，支持中英文双语切换
 * 不依赖 vue-i18n，直接通过 reactive 对象实现
 *
 * 用法：
 *   import { t, locale } from '@/locales'
 *   {{ t('common.save') }}
 *   {{ t('nav.home') }}
 */
import { reactive, computed, Ref } from 'vue'

// ============ 类型定义 ============

/** 语言代码 */
type LocaleCode = 'zh-Hans' | 'en-US'

/** 翻译消息结构 */
interface Messages {
  [key: string]: string | Messages
}

/** 语言包 */
interface MessagePack {
  [key: string]: Messages
}

/** 插值参数 */
interface InterpolationParams {
  [key: string]: string | number
}

/** 可用语言项 */
interface AvailableLocale {
  code: LocaleCode
  label: string
}

// ============ 语言包 ============

const messages: Record<LocaleCode, MessagePack> = {
  'zh-Hans': {
    // 通用
    common: {
      save: '保存',
      cancel: '取消',
      confirm: '确定',
      delete: '删除',
      edit: '编辑',
      create: '创建',
      search: '搜索',
      reset: '重置',
      submit: '提交',
      close: '关闭',
      back: '返回',
      next: '下一步',
      prev: '上一步',
      loading: '加载中...',
      noData: '暂无数据',
      success: '操作成功',
      failed: '操作失败',
      warning: '警告',
      error: '错误',
      yes: '是',
      no: '否',
      all: '全部',
      more: '更多',
      refresh: '刷新',
      import: '导入',
      export: '导出',
      upload: '上传',
      download: '下载',
      copy: '复制',
      paste: '粘贴',
    },
    // 导航
    nav: {
      _group_agents: '智能体应用',
      _group_build: '应用构建',
      _group_components: '组件市场',
      _group_admin: '平台管理',
      home: '智能工作台',
      myAgents: '我的智能体',
      singleAgent: '单智能体应用',
      multiAgent: '多智能体应用',
      workflow: '工作流应用',
      templates: '应用模板',
      monitor: '监控仪表盘',
      models: '模型',
      knowledge: '知识库',
      skills: 'Skills',
      mcp: 'MCP',
      connectors: '数据连接器',
      tools: '工具插件',
      pluginDev: '插件开发',
      users: '用户管理',
      perms: '权限管理',
      audit: '操作日志',
      settings: '系统设置',
    },
    // 用户相关
    user: {
      login: '登录',
      logout: '退出登录',
      register: '注册',
      username: '用户名',
      password: '密码',
      email: '邮箱',
      phone: '电话',
      nickname: '昵称',
      role: '角色',
      accountInfo: '账号信息',
      welcome: '欢迎回来',
      loginTitle: '登录到熵舟',
      loginSub: '智能体工作台',
      forgotPassword: '忘记密码？',
      rememberMe: '记住我',
    },
    // 智能体
    agent: {
      create: '创建智能体',
      edit: '编辑智能体',
      delete: '删除智能体',
      name: '智能体名称',
      description: '描述',
      prompt: '提示词',
      model: '模型',
      status: '状态',
      published: '已发布',
      draft: '草稿',
      testing: '测试中',
    },
    // 知识库
    knowledge: {
      create: '创建知识库',
      edit: '编辑知识库',
      delete: '删除知识库',
      name: '知识库名称',
      description: '描述',
      documents: '文档',
      segments: '分段',
      upload: '上传文档',
      import: '导入',
      recall: '召回测试',
    },
    // 工作流
    workflow: {
      create: '创建工作流',
      edit: '编辑工作流',
      delete: '删除工作流',
      name: '工作流名称',
      run: '运行',
      stop: '停止',
      save: '保存',
      nodes: '节点',
      edges: '连接',
      variables: '变量',
    },
    // 主题
    theme: {
      light: '亮色',
      dark: '暗色',
      switchToLight: '切换到亮色',
      switchToDark: '切换到暗色',
    },
    // 搜索
    search: {
      placeholder: '搜索页面、功能、智能体...',
      noResults: '未找到匹配结果',
      quickNav: '快捷导航',
      shortcuts: '快捷键',
    },
  },

  'en-US': {
    // Common
    common: {
      save: 'Save',
      cancel: 'Cancel',
      confirm: 'Confirm',
      delete: 'Delete',
      edit: 'Edit',
      create: 'Create',
      search: 'Search',
      reset: 'Reset',
      submit: 'Submit',
      close: 'Close',
      back: 'Back',
      next: 'Next',
      prev: 'Prev',
      loading: 'Loading...',
      noData: 'No data',
      success: 'Success',
      failed: 'Failed',
      warning: 'Warning',
      error: 'Error',
      yes: 'Yes',
      no: 'No',
      all: 'All',
      more: 'More',
      refresh: 'Refresh',
      import: 'Import',
      export: 'Export',
      upload: 'Upload',
      download: 'Download',
      copy: 'Copy',
      paste: 'Paste',
    },
    // Navigation
    nav: {
      _group_agents: 'Agents',
      _group_build: 'Build',
      _group_components: 'Components',
      _group_admin: 'Admin',
      home: 'Workbench',
      myAgents: 'My Agents',
      singleAgent: 'Single Agent',
      multiAgent: 'Multi Agent',
      workflow: 'Workflow',
      templates: 'Templates',
      monitor: 'Monitor',
      models: 'Models',
      knowledge: 'Knowledge',
      skills: 'Skills',
      mcp: 'MCP',
      connectors: 'Connectors',
      tools: 'Tools',
      pluginDev: 'Plugin Dev',
      users: 'Users',
      perms: 'Permissions',
      audit: 'Audit Log',
      settings: 'Settings',
    },
    // User
    user: {
      login: 'Login',
      logout: 'Logout',
      register: 'Register',
      username: 'Username',
      password: 'Password',
      email: 'Email',
      phone: 'Phone',
      nickname: 'Nickname',
      role: 'Role',
      accountInfo: 'Account Info',
      welcome: 'Welcome back',
      loginTitle: 'Login to Shangzhou',
      loginSub: 'Agent Workbench',
      forgotPassword: 'Forgot password?',
      rememberMe: 'Remember me',
    },
    // Agent
    agent: {
      create: 'Create Agent',
      edit: 'Edit Agent',
      delete: 'Delete Agent',
      name: 'Agent Name',
      description: 'Description',
      prompt: 'Prompt',
      model: 'Model',
      status: 'Status',
      published: 'Published',
      draft: 'Draft',
      testing: 'Testing',
    },
    // Knowledge
    knowledge: {
      create: 'Create Knowledge Base',
      edit: 'Edit Knowledge Base',
      delete: 'Delete Knowledge Base',
      name: 'Knowledge Base Name',
      description: 'Description',
      documents: 'Documents',
      segments: 'Segments',
      upload: 'Upload Document',
      import: 'Import',
      recall: 'Recall Test',
    },
    // Workflow
    workflow: {
      create: 'Create Workflow',
      edit: 'Edit Workflow',
      delete: 'Delete Workflow',
      name: 'Workflow Name',
      run: 'Run',
      stop: 'Stop',
      save: 'Save',
      nodes: 'Nodes',
      edges: 'Edges',
      variables: 'Variables',
    },
    // Theme
    theme: {
      light: 'Light',
      dark: 'Dark',
      switchToLight: 'Switch to Light',
      switchToDark: 'Switch to Dark',
    },
    // Search
    search: {
      placeholder: 'Search pages, features, agents...',
      noResults: 'No results found',
      quickNav: 'Quick Navigation',
      shortcuts: 'Shortcuts',
    },
  },
}

// ============ 状态 ============

// 从 localStorage 读取语言设置
const savedLang = (localStorage.getItem('app_locale') as LocaleCode) || 'zh-Hans'

const state = reactive({
  locale: savedLang,
})

// ============ 方法 ============

/**
 * 翻译函数
 * @param key - 翻译键，如 'common.save'
 * @param params - 插值参数，如 { name: 'World' }
 */
function t(key: string, params?: InterpolationParams): string {
  const keys = key.split('.')
  let value: string | Messages = messages[state.locale]

  for (const k of keys) {
    if (value && typeof value === 'object') {
      value = value[k]
    } else {
      // 回退到中文
      value = messages['zh-Hans']
      for (const k2 of keys) {
        if (value && typeof value === 'object') {
          value = value[k2]
        } else {
          return key // 返回键名作为兜底
        }
      }
      break
    }
  }

  if (typeof value !== 'string') {
    return key // 返回键名作为兜底
  }

  // 简单的插值替换 {paramName}
  if (params) {
    return value.replace(/\{(\w+)\}/g, (match: string, paramKey: string) => {
      return params[paramKey] !== undefined ? String(params[paramKey]) : match
    })
  }

  return value
}

/**
 * 切换语言
 */
function setLocale(lang: LocaleCode): void {
  if (messages[lang]) {
    state.locale = lang
    localStorage.setItem('app_locale', lang)
    // 更新 HTML lang 属性
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('lang', lang)
    }
  }
}

/**
 * 获取当前语言
 */
const locale: Ref<LocaleCode> = computed(() => state.locale)

/**
 * 获取支持的语言列表
 */
const availableLocales: AvailableLocale[] = [
  { code: 'zh-Hans', label: '简体中文' },
  { code: 'en-US', label: 'English' },
]

export { t, setLocale, locale, availableLocales }
export default { t, setLocale, locale, availableLocales }

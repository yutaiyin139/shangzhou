/* ============ 熵舟·智能体工作台 公共工具（迁移自 assets/app.js，Vue 化） ============ */
import { logout as apiLogout, isAuthenticated, getLoginUser as getStoredUser, UserInfo } from '../api/client'

/** 导航项接口 */
interface NavItem {
  key: string
  label: string
  i18k: string  // i18n 键名（如 'nav.home'）
  href: string
  icon: string
}

/** 导航分组接口 */
interface NavGroup {
  group: string
  i18k: string  // i18n 键名
  items: NavItem[]
}

/* 导航配置（严格按照原型设计文档，href 为 vue-router 路径） */
export const NAV: NavGroup[] = [
  { group: '智能体应用', i18k: 'nav._group_agents', items: [
    { key: 'home',       label: '智能工作台',   i18k: 'nav.home',        href: '/home',         icon: 'workbench' },
    { key: 'my-agents',  label: '我的智能体',   i18k: 'nav.myAgents',    href: '/my-agents',    icon: 'robot' }
  ]},
  { group: '应用构建', i18k: 'nav._group_build', items: [
    { key: 'single',     label: '单智能体应用', i18k: 'nav.singleAgent', href: '/single-agent', icon: 'user' },
    { key: 'multi',      label: '多智能体应用', i18k: 'nav.multiAgent',  href: '/multi-agent',  icon: 'users' },
    { key: 'workflow',   label: '工作流应用',   i18k: 'nav.workflow',    href: '/workflow-app', icon: 'flow' },
    { key: 'templates',  label: '应用模板',     i18k: 'nav.templates',   href: '/app-templates',icon: 'grid' },
    { key: 'wf-monitor', label: '监控仪表盘',   i18k: 'nav.monitor',     href: '/workflow-monitor', icon: 'chart' }
  ]},
  { group: '组件市场', i18k: 'nav._group_components', items: [
    { key: 'models',      label: '模型',        i18k: 'nav.models',      href: '/models',       icon: 'cube' },
    { key: 'knowledge',   label: '知识库',      i18k: 'nav.knowledge',   href: '/knowledge',    icon: 'book' },
    { key: 'skills',      label: 'Skills',      i18k: 'nav.skills',      href: '/skills',       icon: 'clock' },
    { key: 'mcp',         label: 'MCP',         i18k: 'nav.mcp',         href: '/mcp',          icon: 'link' },
    { key: 'connectors',  label: '数据连接器',  i18k: 'nav.connectors',  href: '/connectors',   icon: 'plus-circle' },
    { key: 'tools',       label: '工具插件',    i18k: 'nav.tools',       href: '/tools',        icon: 'plug' },
    { key: 'plugin-dev',  label: '插件开发',    i18k: 'nav.pluginDev',   href: '/plugin-studio', icon: 'code' }
  ]},
  { group: '平台管理', i18k: 'nav._group_admin', items: [
    { key: 'users',      label: '用户管理',    i18k: 'nav.users',       href: '/users',        icon: 'idcard' },
    { key: 'perms',      label: '权限管理',    i18k: 'nav.perms',       href: '/permissions',  icon: 'shield' },
    { key: 'audit',      label: '操作日志',    i18k: 'nav.audit',       href: '/audit',        icon: 'doc' },
    { key: 'settings',   label: '系统设置',    i18k: 'nav.settings',    href: '/system-settings', icon: 'bell' }
  ]}
]

export const ICONS: Record<string, string> = {
  workbench: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>',
  robot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="8" width="14" height="10" rx="2"/><circle cx="9.5" cy="13" r="1" fill="currentColor"/><circle cx="14.5" cy="13" r="1" fill="currentColor"/><path d="M12 8V4M9 4h6"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5 6.5-5s6.5 1.5 6.5 5"/><circle cx="17" cy="9" r="2.6"/><path d="M16.5 15c3 .3 5 2 5 5"/></svg>',
  flow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M6 8.5v3a3 3 0 0 0 3 3M18 8.5v3a3 3 0 0 1-3 3"/></svg>',
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></svg>',
  cube: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5z"/><path d="M4 19a2 2 0 0 1 2-2h13"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/></svg>',
  link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M10 14a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 10a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>',
  'plus-circle': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 8.5v7M8.5 12h7"/></svg>',
  plug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0V7zM12 16v5"/></svg>',
  idcard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="11" r="2"/><path d="M5.5 16c.5-1.8 1.6-2.5 3-2.5s2.5.7 3 2.5M14 9h5M14 13h5"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3l7.5 3v5.5c0 4.7-3.2 8-7.5 9.5-4.3-1.5-7.5-4.8-7.5-9.5V6L12 3z"/><path d="M9 12l2.2 2.2L15.5 10"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 20h4l10-10-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 3v18h18"/><rect x="6" y="12" width="3" height="6"/><rect x="11" y="8" width="3" height="10"/><rect x="16" y="14" width="3" height="4"/></svg>',
  code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/></svg>',
}

export function icon(name: string): string {
  return '<span class="ico">' + (ICONS[name] || ICONS.grid) + '</span>'
}

/* 获取当前登录用户信息（兼容 JWT 版） */
export function getLoginUser(): UserInfo | null {
  // 优先从 api/client 获取（JWT 版本）
  const user = getStoredUser()
  if (user) return user
  // 兼容旧版
  try {
    const s = sessionStorage.getItem('loginUser')
    if (s) return JSON.parse(s)
  } catch (e) { /* ignore */ }
  return null
}

/* 检查是否已登录（JWT 版） */
export function checkAuth(): boolean {
  return isAuthenticated()
}

/* 取用户名的拼音首字母（大写），非中文则取首字符 */
export function getAvatarInitial(name: string | undefined): string {
  if (!name) return '?'
  const first = name.charAt(0)
  if (/^[a-zA-Z0-9]$/.test(first)) return first.toUpperCase()
  if (typeof pinyin !== 'undefined' && pinyin.pinyin) {
    try {
      const py = pinyin.pinyin(first, { pattern: 'first', toneType: 'none' })
      if (py && py.length) return py[0][0].toUpperCase()
    } catch (e) { /* ignore */ }
  }
  return first
}

/* 动态加载 pinyin-pro */
(function(): void {
  if (typeof window === 'undefined') return
  const s = document.createElement('script')
  s.src = 'https://unpkg.com/pinyin-pro@3.18.2/dist/index.js'
  s.async = true
  document.head.appendChild(s)
})()

/* ---------- 通用交互工具 ---------- */
export function openModal(id: string): void {
  const el = document.getElementById(id)
  if (el) el.classList.add('show')
}

export function closeModal(id: string): void {
  const el = document.getElementById(id)
  if (el) el.classList.remove('show')
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', function(e: MouseEvent) {
    const target = e.target as HTMLElement
    if (target && target.classList && target.classList.contains('modal-mask')) {
      target.classList.remove('show')
    }
  })
}

export function toast(msg: string): void {
  if (typeof document === 'undefined') return
  let t = document.getElementById('global-toast')
  if (!t) {
    t = document.createElement('div')
    t.id = 'global-toast'
    t.className = 'toast'
    document.body.appendChild(t)
  }
  t.innerHTML = '<span style="color:#00B42A">✔</span>' + msg
  t.classList.add('show')
  const timerRef = t as unknown as { _timer: ReturnType<typeof setTimeout> }
  clearTimeout(timerRef._timer)
  timerRef._timer = setTimeout(function() {
    t!.classList.remove('show')
  }, 2200)
}

export function copyAccountId(e: Event | null): void {
  if (e && e.stopPropagation) e.stopPropagation()
  const loginUser = getLoginUser()
  const text = loginUser ? ((loginUser as unknown as { account_id: string }).account_id || '') : ''
  if (!text) { toast('无账号信息'); return }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(function() { toast('账号ID已复制') })
  } else {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    toast('账号ID已复制')
  }
}

export async function logout(): Promise<void> {
  if (confirm('确定退出登录吗？')) {
    try {
      // 调用后端登出接口（吊销 Token）
      await apiLogout()
    } catch (e) {
      // 即使失败也要清除本地状态
    }
    if (typeof location !== 'undefined') location.href = '/#/login'
  }
}

/* 字符计数：textarea[data-count] + .char-count[data-for] */
export function bindCharCount(ta: HTMLTextAreaElement, counter: HTMLElement, max: number): void {
  function upd(): void { counter.textContent = ta.value.length + '/' + max }
  ta.addEventListener('input', upd)
  upd()
}

/* 简易 tabs：容器内 .tab 点击切换 active；可选 data-target 切换面板 */
export function bindTabs(container: HTMLElement, onChange?: (tab: Element) => void): void {
  container.querySelectorAll('.tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      container.querySelectorAll('.tab').forEach(function(x) { x.classList.remove('active') })
      tab.classList.add('active')
      if (onChange) onChange(tab)
    })
  })
}

/* 空状态插画 */
export const EMPTY_SVG = '<svg class="empty-ico" viewBox="0 0 100 100" fill="none"><path d="M28 22h44a4 4 0 0 1 4 4v40a4 4 0 0 1-4 4H28a4 4 0 0 1-4-4V26a4 4 0 0 1 4-4z" fill="#F2F3F5"/><path d="M24 66l-8 14h68l-8-14" fill="#E5E6EB"/><rect x="32" y="32" width="28" height="4" rx="2" fill="#D8DBE0"/><rect x="32" y="42" width="36" height="4" rx="2" fill="#D8DBE0"/><rect x="32" y="52" width="20" height="4" rx="2" fill="#D8DBE0"/><rect x="20" y="70" width="10" height="6" rx="2" fill="#2E63F0" opacity=".7"/></svg>'

/* 带参导航：跳转时保留当前 hash 内的查询参数（如 ?id=） */
export function navKeep(path: string): void {
  const q = location.hash.split('?')[1] || ''
  location.hash = path + (q ? '?' + q : '')
}

/* 兼容性兜底：挂载到 window，页面内联脚本可继续直接调用 */
declare global {
  interface Window {
    NAV: NavGroup[]
    ICONS: Record<string, string>
    icon: typeof icon
    getLoginUser: typeof getLoginUser
    getAvatarInitial: typeof getAvatarInitial
    openModal: typeof openModal
    closeModal: typeof closeModal
    toast: typeof toast
    copyAccountId: typeof copyAccountId
    logout: typeof logout
    bindCharCount: typeof bindCharCount
    bindTabs: typeof bindTabs
    EMPTY_SVG: string
    navKeep: typeof navKeep
    checkAuth: typeof checkAuth
  }
}

if (typeof window !== 'undefined') {
  window.NAV = NAV; window.ICONS = ICONS; window.icon = icon
  window.getLoginUser = getLoginUser; window.getAvatarInitial = getAvatarInitial
  window.openModal = openModal; window.closeModal = closeModal
  window.toast = toast; window.copyAccountId = copyAccountId; window.logout = logout
  window.bindCharCount = bindCharCount; window.bindTabs = bindTabs
  window.EMPTY_SVG = EMPTY_SVG; window.navKeep = navKeep
  window.checkAuth = checkAuth
}

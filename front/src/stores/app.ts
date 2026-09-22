/* ============ 应用级状态管理 ============
 *
 * 管理全局应用状态：主题、侧边栏、语言、通知
 */
import { defineStore } from 'pinia'
import { setLocale as setI18nLocale, locale as i18nLocale } from '../locales'

/** 通知类型 */
type NotificationType = 'info' | 'success' | 'warning' | 'error'

/** 通知对象接口 */
interface Notification {
  id: number
  type: NotificationType
  title: string
  message: string
  duration: number
  read: boolean
  timestamp: string
}

/** 应用状态接口 */
interface AppState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  language: 'zh-Hans' | 'en-US'
  notifications: Notification[]
  unreadCount: number
  globalLoading: boolean
  searchOpen: boolean
}

/** 添加通知的参数接口 */
interface NotificationParams {
  type?: NotificationType
  title?: string
  message?: string
  duration?: number
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    // 主题：'light' | 'dark'
    theme: 'light',

    // 侧边栏折叠状态
    sidebarCollapsed: false,

    // 当前语言：'zh-Hans' | 'en-US'
    language: 'zh-Hans',

    // 通知/消息
    notifications: [],
    unreadCount: 0,

    // 全局加载状态
    globalLoading: false,

    // 搜索面板显示状态
    searchOpen: false,
  }),

  getters: {
    /** 是否为暗色主题 */
    isDark: (state: AppState): boolean => state.theme === 'dark',

    /** 当前主题对应的 CSS 类名 */
    themeClass: (state: AppState): string => `theme-${state.theme}`,

    /** 是否有未读通知 */
    hasUnread: (state: AppState): boolean => state.unreadCount > 0,
  },

  actions: {
    /**
     * 切换主题
     */
    toggleTheme(): void {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
      this._applyTheme()
    },

    /**
     * 设置主题
     */
    setTheme(theme: 'light' | 'dark'): void {
      if (theme === 'light' || theme === 'dark') {
        this.theme = theme
        this._applyTheme()
      }
    },

    /**
     * 切换侧边栏
     */
    toggleSidebar(): void {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },

    /**
     * 设置侧边栏状态
     */
    setSidebarCollapsed(collapsed: boolean): void {
      this.sidebarCollapsed = collapsed
    },

    /**
     * 设置语言（同步到 i18n 模块）
     */
    setLanguage(lang: 'zh-Hans' | 'en-US'): void {
      this.language = lang
      setI18nLocale(lang)
    },

    /**
     * 切换语言
     */
    toggleLanguage(): void {
      const next = this.language === 'zh-Hans' ? 'en-US' : 'zh-Hans'
      this.language = next
      setI18nLocale(next)
    },

    /**
     * 初始化语言（从 localStorage 恢复，同步 i18n 模块）
     */
    initLanguage(): void {
      const saved = localStorage.getItem('app_locale') as 'zh-Hans' | 'en-US' | null
      if (saved === 'zh-Hans' || saved === 'en-US') {
        this.language = saved
        setI18nLocale(saved)
      } else {
        this.language = i18nLocale.value
      }
    },

    /**
     * 添加通知
     */
    addNotification(notification: NotificationParams): number {
      const notif: Notification = {
        id: Date.now(),
        type: notification.type || 'info',
        title: notification.title || '',
        message: notification.message || '',
        duration: notification.duration || 3000,
        read: false,
        timestamp: new Date().toISOString(),
      }
      this.notifications.unshift(notif)
      this.unreadCount++

      // 自动移除
      if (notif.duration > 0) {
        setTimeout(() => {
          this.removeNotification(notif.id)
        }, notif.duration)
      }

      return notif.id
    },

    /**
     * 移除通知
     */
    removeNotification(id: number): void {
      const idx = this.notifications.findIndex(n => n.id === id)
      if (idx > -1) {
        if (!this.notifications[idx].read) {
          this.unreadCount = Math.max(0, this.unreadCount - 1)
        }
        this.notifications.splice(idx, 1)
      }
    },

    /**
     * 标记通知为已读
     */
    markAsRead(id: number): void {
      const notif = this.notifications.find(n => n.id === id)
      if (notif && !notif.read) {
        notif.read = true
        this.unreadCount = Math.max(0, this.unreadCount - 1)
      }
    },

    /**
     * 清除所有通知
     */
    clearNotifications(): void {
      this.notifications = []
      this.unreadCount = 0
    },

    /**
     * 打开搜索面板
     */
    openSearch(): void {
      this.searchOpen = true
    },

    /**
     * 关闭搜索面板
     */
    closeSearch(): void {
      this.searchOpen = false
    },

    /**
     * 切换搜索面板
     */
    toggleSearch(): void {
      this.searchOpen = !this.searchOpen
    },

    // ============ 内部方法 ============

    /**
     * 应用主题到 DOM
     */
    _applyTheme(): void {
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', this.theme)
      }
    },

    /**
     * 从后端加载通知列表
     */
    async loadNotifications(): Promise<void> {
      try {
        const { apiGet } = await import('../api/client')
        interface NotifItem { id: number; type: string; title: string; message: string; is_read: boolean; created_at: string }
        interface NotifResp { items: NotifItem[]; unread_count: number }
        const res = await apiGet<NotifResp>('/api/notifications', { params: { page: 1, page_size: 20 } })
        if (res.code === 200 && res.data) {
          const unreadItems = res.data.items.filter(n => !n.is_read)
          this.notifications = unreadItems.map(n => ({
            id: n.id,
            type: (n.type as NotificationType) || 'info',
            title: n.title,
            message: n.message || '',
            duration: 0, // 持久通知不自动消失
            read: false,
            timestamp: n.created_at,
          }))
          this.unreadCount = res.data.unread_count || 0
        }
      } catch (e) {
        // 静默失败
      }
    },

    /**
     * 标记单条通知为已读（同步后端）
     */
    async markReadSync(id: number): Promise<void> {
      const notif = this.notifications.find(n => n.id === id)
      if (notif && !notif.read) {
        notif.read = true
        this.unreadCount = Math.max(0, this.unreadCount - 1)
      }
      try {
        const { apiPost } = await import('../api/client')
        await apiPost(`/api/notifications/${id}/read`)
      } catch (e) {
        // 静默失败
      }
    },

    /**
     * 全部标为已读（同步后端）
     */
    async markAllReadSync(): Promise<void> {
      this.notifications.forEach(n => { n.read = true })
      this.unreadCount = 0
      try {
        const { apiPost } = await import('../api/client')
        await apiPost('/api/notifications/read-all')
      } catch (e) {
        // 静默失败
      }
    },

    /**
     * 清空所有通知（同步后端）
     */
    async clearAllSync(): Promise<void> {
      this.notifications = []
      this.unreadCount = 0
      try {
        const { apiPost } = await import('../api/client')
        await apiPost('/api/notifications/clear')
      } catch (e) {
        // 静默失败
      }
    },

    /**
     * 初始化主题（从 localStorage 恢复）
     */
    initTheme(): void {
      const saved = localStorage.getItem('app_theme')
      if (saved === 'light' || saved === 'dark') {
        this.theme = saved
      } else {
        // 跟随系统偏好
        if (typeof window !== 'undefined' && window.matchMedia) {
          this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        }
      }
      this._applyTheme()
    },

    // ============ 通知轮询 ============
    _pollTimer: null as ReturnType<typeof setInterval> | null,
    _pollIntervalMs: 30_000, // 30 秒轮询间隔

    /**
     * 启动通知轮询（每 30s 拉取一次）
     */
    startNotificationPolling(): void {
      if (this._pollTimer) return
      this.loadNotifications() // 立即拉一次
      this._pollTimer = setInterval(() => {
        this.loadNotifications()
      }, this._pollIntervalMs)
    },

    /**
     * 停止通知轮询
     */
    stopNotificationPolling(): void {
      if (this._pollTimer) {
        clearInterval(this._pollTimer)
        this._pollTimer = null
      }
    },
  },
})

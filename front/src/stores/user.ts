/* ============ 用户状态管理 ============
 *
 * 管理用户认证状态、Token、角色权限、用户偏好
 * 替代原有的 sessionStorage 直接操作
 */
import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout, fetchCurrentUser, AuthTokens, UserInfo } from '../api/client'

/** 用户状态接口 */
interface UserState {
  id: string
  name: string
  nickname: string
  email: string
  phone: string
  role: string
  avatar: string
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
  interfaceLanguage: string
  interfaceTheme: string
  loading: boolean
  initialized: boolean
}

/** 认证数据接口 */
interface AuthData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user?: UserInfo
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    // 用户信息
    id: '',
    name: '',
    nickname: '',
    email: '',
    phone: '',
    role: '',
    avatar: '',

    // 认证状态
    accessToken: '',
    refreshToken: '',
    tokenType: 'Bearer',
    expiresIn: 0,

    // 用户偏好
    interfaceLanguage: 'zh-Hans',
    interfaceTheme: 'light',

    // 加载状态
    loading: false,
    initialized: false,
  }),

  getters: {
    /** 是否已登录 */
    isAuthenticated: (state: UserState): boolean => {
      if (!state.accessToken) return false
      try {
        const payload = JSON.parse(atob(state.accessToken.split('.')[1]))
        return payload.exp > Math.floor(Date.now() / 1000) + 30
      } catch (e) {
        return false
      }
    },

    /** 显示名称（优先昵称 > 用户名 > 邮箱） */
    displayName: (state: UserState): string => {
      return state.nickname || state.name || state.email || '未登录'
    },

    /** 头像首字符 */
    avatarInitial: (state: UserState): string => {
      const name = state.nickname || state.name || state.email
      if (!name) return '?'
      return name.charAt(0).toUpperCase()
    },

    /** 是否为管理员 */
    isAdmin: (state: UserState): boolean => state.role === 'admin',

    /** 用户角色列表 */
    roles: (state: UserState): string[] => state.role ? [state.role] : [],
  },

  actions: {
    /**
     * 用户登录
     */
    async login(username: string, password: string): Promise<AuthData> {
      this.loading = true
      try {
        const data = await apiLogin(username, password)
        this._setAuthData(data)
        return data
      } catch (error) {
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 用户登出
     */
    async logout(): Promise<void> {
      try {
        await apiLogout()
      } catch (e) {
        // 即使请求失败也要清除本地状态
      } finally {
        this._clearAuthData()
      }
    },

    /**
     * 刷新当前用户信息
     */
    async fetchUser(): Promise<UserInfo | null> {
      try {
        const user = await fetchCurrentUser()
        if (user) {
          this.id = user.id || ''
          this.name = user.name || user.username || ''
          this.nickname = user.nickname || ''
          this.email = user.email || ''
          this.phone = user.phone || ''
          this.role = user.role || ''
          this.interfaceLanguage = user.interface_language || 'zh-Hans'
          this.interfaceTheme = user.interface_theme || 'light'
        }
        this.initialized = true
        return user
      } catch (e) {
        this.initialized = true
        return null
      }
    },

    /**
     * 设置 Token
     */
    setTokens(tokens: AuthTokens): void {
      this.accessToken = tokens.access_token || ''
      this.refreshToken = tokens.refresh_token || ''
      this.tokenType = tokens.token_type || 'Bearer'
      this.expiresIn = tokens.expires_in || 0
    },

    /**
     * 更新用户偏好
     */
    updatePreferences(prefs: { interfaceLanguage?: string; interfaceTheme?: string }): void {
      if (prefs.interfaceLanguage !== undefined) this.interfaceLanguage = prefs.interfaceLanguage
      if (prefs.interfaceTheme !== undefined) this.interfaceTheme = prefs.interfaceTheme
    },

    /**
     * 从已有 sessionStorage 数据恢复（兼容旧版）
     */
    restoreFromSession(): void {
      try {
        const tokens = sessionStorage.getItem('auth_tokens')
        if (tokens) {
          const t = JSON.parse(tokens)
          this.accessToken = t.access_token || ''
          this.refreshToken = t.refresh_token || ''
          this.tokenType = t.token_type || 'Bearer'
          this.expiresIn = t.expires_in || 0
        }
        const user = sessionStorage.getItem('loginUser')
        if (user) {
          const u = JSON.parse(user)
          this.id = u.id || ''
          this.name = u.name || u.username || ''
          this.nickname = u.nickname || ''
          this.email = u.email || ''
          this.phone = u.phone || ''
          this.role = u.role || ''
        }
        this.initialized = true
      } catch (e) {
        this.initialized = true
      }
    },

    // ============ 内部方法 ============

    _setAuthData(data: AuthData): void {
      this.accessToken = data.access_token || ''
      this.refreshToken = data.refresh_token || ''
      this.tokenType = data.token_type || 'Bearer'
      this.expiresIn = data.expires_in || 0

      if (data.user) {
        this.id = data.user.id || ''
        this.name = data.user.name || data.user.username || ''
        this.nickname = data.user.nickname || ''
        this.email = data.user.email || ''
        this.phone = data.user.phone || ''
        this.role = data.user.role || ''
      }
    },

    _clearAuthData(): void {
      this.id = ''
      this.name = ''
      this.nickname = ''
      this.email = ''
      this.phone = ''
      this.role = ''
      this.accessToken = ''
      this.refreshToken = ''
      this.tokenType = 'Bearer'
      this.expiresIn = 0
    },
  },
})

/* ============ 熵舟·智能体工作台 —— 统一 API 客户端（JWT 认证） ============
 *
 * 特性：
 * 1. 自动注入 JWT Access Token 到 Authorization Header
 * 2. Token 过期时自动使用 Refresh Token 刷新
 * 3. 刷新失败时自动跳转登录页
 * 4. 统一的错误处理和响应解析
 */

// ============================================================
// 类型定义
// ============================================================

/** Token 对象 */
export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** API 响应格式 */
export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
}

/** 用户信息 */
export interface UserInfo {
  id: string
  name: string
  username?: string
  nickname?: string
  email: string
  phone?: string
  role?: string
  interface_language?: string
  interface_theme?: string
}

/** 登录响应 */
export interface LoginResponse {
  user: UserInfo
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** 请求选项 */
export interface RequestOptions {
  auth?: boolean
  retry?: boolean
  headers?: Record<string, string>
  body?: unknown
  method?: string
  params?: Record<string, string | number | boolean | undefined>
}

// ============================================================
// Token 管理
// ============================================================

const TOKEN_KEY = 'auth_tokens'
const USER_KEY = 'loginUser'

/**
 * 获取存储的 Token 对象
 */
export function getTokens(): AuthTokens | null {
  try {
    const raw = sessionStorage.getItem(TOKEN_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return null
}

/**
 * 保存 Token 对象到 sessionStorage
 */
export function setTokens(tokens: AuthTokens): void {
  if (tokens) {
    sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
  }
}

/**
 * 清除所有认证信息（登出时使用）
 */
export function clearAuth(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

/**
 * 获取当前登录用户信息
 */
export function getLoginUser(): UserInfo | null {
  try {
    const s = sessionStorage.getItem(USER_KEY)
    if (s) return JSON.parse(s)
  } catch (e) { /* ignore */ }
  return null
}

/**
 * 保存当前登录用户信息
 */
export function setLoginUser(user: UserInfo): void {
  if (user) {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user))
  }
}

/**
 * 检查是否已登录（有 Token 且未过期）
 */
export function isAuthenticated(): boolean {
  const tokens = getTokens()
  if (!tokens || !tokens.access_token) return false
  try {
    const payload = JSON.parse(atob(tokens.access_token.split('.')[1]))
    return payload.exp > Math.floor(Date.now() / 1000) + 30
  } catch (e) {
    return false
  }
}

// ============================================================
// Token 刷新机制（防止并发刷新）
// ============================================================

let _refreshPromise: Promise<string> | null = null

/**
 * 刷新 Access Token
 * 如果已经在刷新中，返回同一个 Promise（防止并发刷新）
 */
async function _refreshToken(): Promise<string> {
  const tokens = getTokens()
  if (!tokens || !tokens.refresh_token) {
    return Promise.reject(new Error('无 Refresh Token'))
  }
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = (async () => {
    try {
      const resp = await fetch('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      })
      const data: ApiResponse<AuthTokens> = await resp.json()
      if (data.code === 200 && data.data) {
        const newTokens: AuthTokens = {
          access_token: data.data.access_token,
          refresh_token: data.data.refresh_token,
          token_type: data.data.token_type,
          expires_in: data.data.expires_in,
        }
        setTokens(newTokens)
        return data.data.access_token
      }
      throw new Error(data.msg || '刷新失败')
    } finally {
      _refreshPromise = null
    }
  })()

  return _refreshPromise
}

// ============================================================
// 核心请求函数
// ============================================================

/**
 * 统一 API 请求客户端
 */
async function _request<T = unknown>(url: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const { auth = true, retry = true, params, ...fetchOptions } = options

  // 构建 Query String
  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value))
      }
    })
    const qs = searchParams.toString()
    if (qs) url += (url.includes('?') ? '&' : '?') + qs
  }

  // 构建 Headers
  const headers: Record<string, string> = { ...(fetchOptions.headers || {}) }
  if (auth) {
    const tokens = getTokens()
    if (tokens && tokens.access_token) {
      headers['Authorization'] = `Bearer ${tokens.access_token}`
    }
  }

  // 自动添加 Content-Type
  const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData
  if (fetchOptions.body && !headers['Content-Type'] && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  let resp = await fetch(url, { ...fetchOptions, headers } as RequestInit)

  // 401 处理：尝试刷新 Token 后重试
  if (resp.status === 401 && auth && retry) {
    try {
      const newToken = await _refreshToken()
      const retryHeaders = { ...headers, 'Authorization': `Bearer ${newToken}` }
      resp = await fetch(url, { ...fetchOptions, headers: retryHeaders } as RequestInit)
    } catch (refreshError) {
      clearAuth()
      if (typeof window !== 'undefined') {
        window.location.hash = '/login'
      }
      throw new Error('登录已过期，请重新登录')
    }
  }

  // 解析响应
  let result: ApiResponse<T>
  try {
    result = await resp.json()
  } catch (e) {
    let responseText = ''
    try {
      responseText = await resp.text()
    } catch (_) { /* ignore */ }
    const contentType = resp.headers.get('content-type') || ''
    if (contentType.includes('text/html')) {
      const titleMatch = responseText.match(/<title>(.*?)<\/title>/i)
      const errorMsg = titleMatch ? titleMatch[1] : '服务器返回 HTML 错误页面'
      throw new Error(`HTTP ${resp.status} - ${errorMsg}（请检查服务器终端输出）`)
    }
    const preview = responseText ? responseText.substring(0, 200) : '(空响应)'
    throw new Error(`服务器响应格式错误（HTTP ${resp.status}）: ${preview}`)
  }

  // 业务错误处理
  if (result.code && result.code !== 200 && result.code !== 0) {
    const err = new Error(result.msg || '请求失败') as Error & { code: number; response: ApiResponse<T> }
    err.code = result.code
    err.response = result
    throw err
  }

  return result
}

// ============================================================
// 便捷方法
// ============================================================

/** GET 请求 */
export function apiGet<T = unknown>(url: string, options: Omit<RequestOptions, 'body'> = {}): Promise<ApiResponse<T>> {
  return _request<T>(url, { ...options, method: 'GET' })
}

/** POST 请求 */
export function apiPost<T = unknown>(url: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<ApiResponse<T>> {
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  return _request<T>(url, {
    ...options,
    method: 'POST',
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  } as RequestOptions)
}

/** PUT 请求 */
export function apiPut<T = unknown>(url: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<ApiResponse<T>> {
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  return _request<T>(url, {
    ...options,
    method: 'PUT',
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  } as RequestOptions)
}

/** DELETE 请求 */
export function apiDelete<T = unknown>(url: string, options: Omit<RequestOptions, 'body'> = {}): Promise<ApiResponse<T>> {
  return _request<T>(url, { ...options, method: 'DELETE' })
}

// ============================================================
// 认证相关 API
// ============================================================

/**
 * 用户登录
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  const result = await _request<LoginResponse>('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    auth: false,
  })
  if (result.code === 200 && result.data) {
    setTokens({
      access_token: result.data.access_token,
      refresh_token: result.data.refresh_token,
      token_type: result.data.token_type,
      expires_in: result.data.expires_in,
    })
    setLoginUser(result.data.user)
    return result.data
  }
  throw new Error(result.msg || '登录失败')
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  try {
    await _request('/api/logout', { method: 'POST' })
  } catch (e) {
    // 即使请求失败也要清除本地状态
  } finally {
    clearAuth()
  }
}

/**
 * 获取当前用户信息
 */
export async function fetchCurrentUser(): Promise<UserInfo | null> {
  const result = await _request<UserInfo>('/api/me', { method: 'GET' })
  if (result.code === 200 && result.data) {
    setLoginUser(result.data)
    return result.data
  }
  return null
}

// ============================================================
// 默认导出
// ============================================================

export default {
  getTokens,
  setTokens,
  clearAuth,
  getLoginUser,
  setLoginUser,
  isAuthenticated,
  request: _request,
  get: apiGet,
  post: apiPut,
  put: apiPut,
  delete: apiDelete,
  login,
  logout,
  fetchCurrentUser,
}

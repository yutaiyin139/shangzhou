/* ============ 全局 API 客户端暴露 ============
 * 将 API 客户端函数暴露到 window 对象，
 * 供使用 data-action eval 模式的旧视图使用。
 * 新视图应直接从 '../api/client' 导入。
 */
import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { login, logout, fetchCurrentUser, getLoginUser, setLoginUser, getTokens, setTokens, clearAuth, isAuthenticated } from './client'

// 暴露到 window 对象（仅用于 data-action eval 模式）
if (typeof window !== 'undefined') {
  const w = window as any
  w.apiGet = apiGet
  w.apiPost = apiPost
  w.apiPut = apiPut
  w.apiDelete = apiDelete
  w.apiLogin = login
  w.apiLogout = logout
  w.apiFetchUser = fetchCurrentUser
  w.apiGetUser = getLoginUser
  w.apiSetUser = setLoginUser
  w.apiGetTokens = getTokens
  w.apiSetTokens = setTokens
  w.apiClearAuth = clearAuth
  w.apiIsAuth = isAuthenticated
}

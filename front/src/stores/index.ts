/* ============ 熵舟·智能体工作台 —— Pinia 状态管理入口 ============
 *
 * 统一管理应用状态：
 * 1. userStore  - 用户认证、角色、偏好设置
 * 2. appStore   - 应用级状态（主题、侧边栏、语言）
 * 3. workflowStore - 工作流编辑状态
 *
 * 替代原有的 sessionStorage 分散管理方式
 */
import { createPinia, Pinia } from 'pinia'

const pinia: Pinia = createPinia()

// 持久化插件：将指定 state 自动同步到 sessionStorage
pinia.use(({ store }) => {
  // 从 sessionStorage 恢复状态
  const savedState = sessionStorage.getItem(`pinia_${store.$id}`)
  if (savedState) {
    try {
      store.$patch(JSON.parse(savedState))
    } catch (e) { /* ignore */ }
  }

  // 监听状态变化，自动保存
  store.$subscribe((mutation, state) => {
    sessionStorage.setItem(`pinia_${store.$id}`, JSON.stringify(state))
  })
})

export default pinia

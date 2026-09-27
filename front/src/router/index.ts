/* ============ 熵舟·智能体工作台 —— 路由配置 ============ */
import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated, getAuthRole, getLoginUser } from '../api/client'
import { resolvePageTitle, navLabelByPath, toast } from '../utils/global'

/** 路由 meta 扩展 */
declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    roles?: string[]
    /** 页面名；侧边导航没覆盖到的路由可在此登记（AppShell 面包屑也会读它） */
    title?: string
  }
}

// 熵舟·智能体工作台 路由表（对应原 35 个 HTML 页面）
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue'), meta: { public: true } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('../views/ForgotPasswordView.vue'), meta: { public: true } },
  { path: '/reset-password', name: 'reset-password', component: () => import('../views/ResetPasswordView.vue'), meta: { public: true } },
  { path: '/home', name: 'home', component: () => import('../views/HomeView.vue'), meta: { requiresAuth: true } },
  { path: '/account-info', name: 'account-info', component: () => import('../views/AccountInfoView.vue'), meta: { requiresAuth: true } },
  { path: '/my-agents', name: 'my-agents', component: () => import('../views/MyAgentsView.vue'), meta: { requiresAuth: true } },
  { path: '/single-agent', name: 'single-agent', component: () => import('../views/SingleAgentView.vue'), meta: { requiresAuth: true } },
  { path: '/single-agent-edit', name: 'single-agent-edit', component: () => import('../views/SingleAgentEditView.vue'), meta: { requiresAuth: true } },
  { path: '/multi-agent', name: 'multi-agent', component: () => import('../views/MultiAgentView.vue'), meta: { requiresAuth: true } },
  { path: '/multi-agent-edit', name: 'multi-agent-edit', component: () => import('../views/MultiAgentEditView.vue'), meta: { requiresAuth: true } },
  { path: '/workflow-app', name: 'workflow-app', component: () => import('../views/WorkflowAppView.vue'), meta: { requiresAuth: true } },
  { path: '/workflow-studio', name: 'workflow-studio', component: () => import('../views/WorkflowStudioView.vue'), meta: { requiresAuth: true } },
  { path: '/app-templates', name: 'app-templates', component: () => import('../views/AppTemplatesView.vue'), meta: { requiresAuth: true } },
  { path: '/template-studio', name: 'template-studio', component: () => import('../views/TemplateStudioView.vue'), meta: { requiresAuth: true } },
  { path: '/models', name: 'models', component: () => import('../views/ModelsView.vue'), meta: { requiresAuth: true } },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/KnowledgeView.vue'), meta: { requiresAuth: true } },
  { path: '/knowledge-create', name: 'knowledge-create', component: () => import('../views/KnowledgeCreateView.vue'), meta: { requiresAuth: true } },
  { path: '/knowledge-detail/:id', name: 'knowledge-detail', component: () => import('../views/KnowledgeDetailView.vue'), meta: { requiresAuth: true }, props: true },
  { path: '/knowledge-process', name: 'knowledge-process', component: () => import('../views/KnowledgeProcessView.vue'), meta: { requiresAuth: true } },
  { path: '/skills', name: 'skills', component: () => import('../views/SkillsView.vue'), meta: { requiresAuth: true } },
  { path: '/skill-detail', name: 'skill-detail', component: () => import('../views/SkillDetailView.vue'), meta: { requiresAuth: true } },
  { path: '/mcp', name: 'mcp', component: () => import('../views/McpView.vue'), meta: { requiresAuth: true } },
  { path: '/connectors', name: 'connectors', component: () => import('../views/ConnectorsView.vue'), meta: { requiresAuth: true } },
  { path: '/tools', name: 'tools', component: () => import('../views/ToolsView.vue'), meta: { requiresAuth: true } },
  { path: '/users', name: 'users', component: () => import('../views/UsersView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/permissions', name: 'permissions', component: () => import('../views/PermissionsView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/audit', name: 'audit', component: () => import('../views/AuditView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/roles', name: 'roles', component: () => import('../views/RolesView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/functions', name: 'functions', component: () => import('../views/FunctionsView.vue'), meta: { requiresAuth: true } },
  { path: '/system-settings', name: 'system-settings', component: () => import('../views/SystemSettingsView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/agent-detail', name: 'agent-detail', component: () => import('../views/AgentDetailView.vue'), meta: { requiresAuth: true } },
  { path: '/web-agent', name: 'web-agent', component: () => import('../views/WebAgentView.vue'), meta: { requiresAuth: true } },
  { path: '/agent-chat', name: 'agent-chat', component: () => import('../views/AgentChatView.vue'), meta: { requiresAuth: true } },
  { path: '/agent-config', name: 'agent-config', component: () => import('../views/AgentConfigView.vue'), meta: { requiresAuth: true } },
  { path: '/agent-logs', name: 'agent-logs', component: () => import('../views/AgentLogsView.vue'), meta: { requiresAuth: true } },
  { path: '/agent-monitor', name: 'agent-monitor', component: () => import('../views/AgentMonitorView.vue'), meta: { requiresAuth: true } },
  { path: '/workflow-templates', name: 'workflow-templates', component: () => import('../views/WorkflowTemplatesView.vue'), meta: { requiresAuth: true } },
  { path: '/workflow-monitor', name: 'workflow-monitor', component: () => import('../views/WorkflowMonitorView.vue'), meta: { requiresAuth: true } },
  { path: '/evaluations', name: 'evaluations', component: () => import('../views/EvaluationView.vue'), meta: { requiresAuth: true } },
  { path: '/agent-templates', name: 'agent-templates', component: () => import('../views/AgentTemplatesView.vue'), meta: { requiresAuth: true } },
  { path: '/webhooks', name: 'webhooks', component: () => import('../views/WebhooksView.vue'), meta: { requiresAuth: true } },
  { path: '/plugins', name: 'plugins', component: () => import('../views/PluginsView.vue'), meta: { requiresAuth: true } },
  { path: '/plugin-studio', name: 'plugin-studio', component: () => import('../views/PluginStudioView.vue'), meta: { requiresAuth: true } },
  { path: '/explore', name: 'explore', component: () => import('../views/ExploreView.vue'), meta: { requiresAuth: true } },
  { path: '/share/chat/:token', name: 'share-chat', component: () => import('../views/ShareChatView.vue'), meta: { public: true } },
  { path: '/share/workflow/:token', name: 'share-workflow', component: () => import('../views/ShareWorkflowView.vue'), meta: { public: true } },
  { path: '/human-input-form', name: 'human-input-form', component: () => import('../views/HumanInputFormView.vue'), meta: { public: true } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// ============================================================
// 路由守卫（全局前置守卫）
// ============================================================

router.beforeEach((to, from, next) => {
  const authenticated = isAuthenticated()

  // 1. 公开路由直接放行
  if (to.meta && to.meta.public) {
    // 已登录用户访问登录页，自动跳转到首页
    if (to.path === '/login' && authenticated) {
      return next('/home')
    }
    return next()
  }

  // 2. 需要认证的路由
  if (to.meta && to.meta.requiresAuth) {
    if (!authenticated) {
      // 未登录，跳转登录页
      return next('/login')
    }
    // 3. 角色权限检查
    if (to.meta.roles && to.meta.roles.length > 0) {
      /* 角色以服务端签发的 token 载荷为准，loginUser 只作兜底：
         以前只读 sessionStorage.loginUser.role，而它会被 /api/me 覆盖、也会在新标签页里缺失，
         一旦没取到 role，管理员就被静默弹回 /home —— 没有提示也没有报错，
         而侧边栏那 4 个“平台管理”项照常渲染，看上去就是“系统设置点不动”。 */
      const userRole = (getAuthRole() || (getLoginUser()?.role || '')).toLowerCase()
      const allowed = (to.meta.roles as string[]).some(r => String(r).toLowerCase() === userRole)
      if (!allowed) {
        // 明确告知被拒，否则用户只会觉得“菜单坏了”
        toast(`无权限访问「${navLabelByPath(to.path) || to.path}」，已返回工作台`)
        return next('/home')
      }
    }
    return next()
  }

  // 4. 其他路由直接放行
  next()
})

// ============================================================
// 标签页标题（每次导航完都复位，避免离开详情页后标题粘住）
//
// 详情类页面仍会在数据回来后自己设成「<资源名> - …」；它在导航之后执行，
// 不会被这里刷掉。
// ============================================================
router.afterEach((to) => {
  const metaTitle = (to.meta && (to.meta.title as string | undefined)) || undefined
  document.title = resolvePageTitle(to.path, metaTitle)
})

export default router

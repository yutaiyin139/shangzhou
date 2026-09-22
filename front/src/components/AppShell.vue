<template>
  <div class="layout" :class="{ collapsed: appStore.sidebarCollapsed }">
    <!-- 移动端侧边栏遮罩 -->
    <div class="sidebar-overlay" :class="{ show: mobileMenuOpen }" @click="mobileMenuOpen = false"></div>
    <header class="topbar">
      <!-- 移动端菜单按钮 -->
      <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="菜单">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
      </button>
      <div class="brand">熵舟·智能体工作台</div>
      <div class="top-right">
        <!-- 搜索按钮 -->
        <button class="top-btn" @click="appStore.openSearch" title="搜索 (Cmd+K)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </button>
        <!-- 主题切换 -->
        <button class="top-btn" @click="appStore.toggleTheme" :title="appStore.isDark ? '切换到亮色' : '切换到暗色'">
          <span v-if="appStore.isDark">☀️</span>
          <span v-else>🌙</span>
        </button>
        <!-- 语言切换 -->
        <button class="top-btn lang-btn" @click="toggleLanguage" title="切换语言">
          {{ appStore.language === 'zh-Hans' ? 'EN' : '中' }}
        </button>
        <!-- 通知铃 -->
        <NotificationBell />
        <!-- 用户下拉 -->
        <div class="user-dropdown" ref="ddRef">
          <span class="item" @click="toggleMenu">
            <span class="avatar">{{ userStore.avatarInitial }}</span> ▾
          </span>
          <div class="dropdown-menu" :class="{ show: menuOpen }">
            <div class="dd-header">
              <div class="dd-name">{{ userStore.displayName }}</div>
              <div class="dd-account">
                {{ userStore.email }}
              </div>
            </div>
            <div class="dd-divider"></div>
            <div class="dd-item" @click="go('/account-info')"><span class="dd-ico">🤖</span> 账号信息</div>
            <div class="dd-item" @click="showToast('操作指南')"><span class="dd-ico">📖</span> 操作指南</div>
            <div class="dd-item" @click="showToast('产品动态')"><span class="dd-ico">🕐</span> 产品动态</div>
            <div class="dd-divider"></div>
            <div class="dd-item dd-logout" @click="doLogout"><span class="dd-ico"></span> 退出登录</div>
          </div>
        </div>
      </div>
    </header>
    <div class="layout-body">
      <aside class="sidebar" :class="{ open: mobileMenuOpen }">
        <div class="nav-scroll">
          <div v-for="g in NAV" :key="g.group" class="nav-group">
            <div class="nav-group-title">{{ t(g.i18k) || g.group }}</div>
            <router-link
              v-for="it in g.items"
              :key="it.key"
              class="nav-item"
              :class="{ active: isActive(it.key) }"
              :to="it.href"
              @click="mobileMenuOpen = false"
            >
              <span class="ico" v-html="ICONS[it.icon] || ICONS.grid"></span>
              <span class="txt">{{ t(it.i18k) || it.label }}</span>
              <span v-if="it.badge" class="badge-new">{{ it.badge }}</span>
            </router-link>
          </div>
        </div>
        <div class="collapse-btn" @click="appStore.toggleSidebar()" :title="appStore.sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'">
          <span class="txt" v-show="!appStore.sidebarCollapsed">☰ 收起</span>
          <span v-show="appStore.sidebarCollapsed" class="expand-icon">☰</span>
        </div>
      </aside>
      <main class="main" :class="mainClass">
        <!-- 面包屑导航 -->
        <nav class="breadcrumb" v-if="breadcrumbs.length > 0">
          <span v-for="(crumb, idx) in breadcrumbs" :key="idx" class="breadcrumb-item">
            <span v-if="idx < breadcrumbs.length - 1">
              <a @click="go(crumb.path)">{{ crumb.label }}</a>
              <span class="breadcrumb-separator">/</span>
            </span>
            <span v-else class="breadcrumb-current">{{ crumb.label }}</span>
          </span>
        </nav>
        <slot />
      </main>
    </div>

    <!-- 全局搜索面板 -->
    <SearchModal v-if="appStore.searchOpen" @close="appStore.closeSearch" />
  </div>
</template>

<script setup>
import { ref, computed, onActivated, onDeactivated, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAV, ICONS, toast } from '../utils/global'
import { t } from '../locales'
import { useUserStore } from '../stores/user'
import { useAppStore } from '../stores/app'
import SearchModal from './SearchModal.vue'
import NotificationBell from './NotificationBell.vue'

const props = defineProps({
  activeKey: { type: String, default: '' },
  mainClass: { type: String, default: '' }
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const menuOpen = ref(false)
const mobileMenuOpen = ref(false)
const ddRef = ref(null)

// 面包屑计算
const breadcrumbs = computed(() => {
  const crumbs = []
  const path = route.path

  // 首页
  if (path === '/home') {
    crumbs.push({ label: '智能工作台', path: '/home' })
    return crumbs
  }

  // 根据导航构建面包屑
  for (const group of NAV) {
    for (const item of group.items) {
      if (item.href === path) {
        crumbs.push({ label: group.group, path: '' })
        crumbs.push({ label: item.label, path: item.href })
        return crumbs
      }
    }
  }

  // 编辑页特殊处理
  if (path.includes('-edit') || path.includes('-detail') || path.includes('-studio')) {
    const basePath = path.replace(/-edit|-detail|-studio.*/, '')
    for (const group of NAV) {
      for (const item of group.items) {
        if (item.href === basePath) {
          crumbs.push({ label: item.label, path: basePath })
          if (path.includes('-edit')) crumbs.push({ label: '编辑', path })
          else if (path.includes('-detail')) crumbs.push({ label: '详情', path })
          else if (path.includes('-studio')) crumbs.push({ label: '工作室', path })
          return crumbs
        }
      }
    }
  }

  // 未知页面使用路由 meta 或路径
  if (route.meta?.title) {
    crumbs.push({ label: route.meta.title, path })
  }

  return crumbs
})

function isActive(key) {
  // 通过 key 查找对应的 nav item，比较 href 与当前路径
  if (key === props.activeKey) return true
  for (const group of NAV) {
    for (const item of group.items) {
      if (item.key === key) {
        return route.path === item.href
      }
    }
  }
  return route.path === key
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function go(path) {
  menuOpen.value = false
  mobileMenuOpen.value = false
  router.push(path)
}

function showToast(msg) {
  menuOpen.value = false
  toast(msg)
}

function toggleLanguage() {
  appStore.toggleLanguage()
  toast(appStore.language === 'zh-Hans' ? t('common.success') + '：已切换到中文' : t('common.success') + ': Switched to English')
}

function doLogout() {
  menuOpen.value = false
  if (confirm('确定退出登录吗？')) {
    userStore.logout()
    router.push('/login')
  }
}

function onDocClick(e) {
  if (ddRef.value && !ddRef.value.contains(e.target)) menuOpen.value = false
}

// 键盘快捷键
function onKeyDown(e) {
  // Cmd+K / Ctrl+K 打开搜索
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    appStore.toggleSearch()
  }
  // Escape 关闭搜索
  if (e.key === 'Escape' && appStore.searchOpen) {
    appStore.closeSearch()
  }
}

onActivated(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKeyDown)
  // 恢复用户状态
  userStore.restoreFromSession()
  // 启动通知轮询（每 30s 拉取一次后端通知）
  appStore.startNotificationPolling()
})

onDeactivated(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeyDown)
  // 停止通知轮询
  appStore.stopNotificationPolling()
})
</script>

<style scoped>
.top-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 16px;
  color: var(--text-2);
  transition: background 0.15s;
}
.top-btn:hover {
  background: var(--border-light);
}
.lang-btn {
  font-size: 12px;
  font-weight: 600;
  min-width: 32px;
}

/* 面包屑 */
.breadcrumb {
  padding: 12px 24px;
  font-size: 13px;
  color: var(--text-3);
  border-bottom: 1px solid var(--border-light);
}
.breadcrumb-item a {
  color: var(--text-2);
  cursor: pointer;
  text-decoration: none;
}
.breadcrumb-item a:hover {
  color: var(--primary);
}
.breadcrumb-separator {
  margin: 0 8px;
  color: var(--text-4);
}
.breadcrumb-current {
  color: var(--text-1);
  font-weight: 500;
}

/* 覆盖原有样式 */
.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

/* ============ 熵舟·智能体工作台 —— 应用入口 ============ */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'
import './styles/style.css'
import './utils/global'
import './api/global' // 暴露 API 客户端到 window 对象
import { t, locale, setLocale, availableLocales } from './locales'

const app = createApp(App)

// 注册 Pinia 状态管理
app.use(pinia)

// 注册路由
app.use(router)

// 全局提供 i18n
app.provide('t', t)
app.provide('locale', locale)
app.provide('setLocale', setLocale)
app.provide('availableLocales', availableLocales)

// 挂载应用
app.mount('#app')

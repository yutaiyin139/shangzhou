<template>
  <div class="notif-bell" ref="bellRef">
    <button class="top-btn notif-btn" @click="togglePanel" title="通知中心">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
      <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <div v-if="panelOpen" class="notif-panel">
      <div class="notif-header">
        <span class="notif-title">通知中心</span>
        <div class="notif-actions">
          <button v-if="unreadCount > 0" class="notif-action-btn" @click="markAllRead" title="全部标为已读">
            ✓ 全部已读
          </button>
          <button v-if="notifications.length > 0" class="notif-action-btn" @click="clearAll" title="清空通知">
            🗑 清空
          </button>
        </div>
      </div>

      <div class="notif-list" v-if="notifications.length > 0">
        <div
          v-for="item in notifications"
          :key="item.id"
          class="notif-item"
          :class="{ unread: !item.is_read, [`type-${item.type}`]: true }"
          @click="handleClick(item)"
        >
          <div class="notif-item-icon">
            <span v-if="item.type === 'success'">✅</span>
            <span v-else-if="item.type === 'warning'">⚠️</span>
            <span v-else-if="item.type === 'error'">❌</span>
            <span v-else>ℹ️</span>
          </div>
          <div class="notif-item-content">
            <div class="notif-item-title">{{ item.title }}</div>
            <div v-if="item.message" class="notif-item-msg">{{ item.message }}</div>
            <div class="notif-item-time">{{ formatTime(item.created_at) }}</div>
          </div>
          <button class="notif-item-del" @click.stop="deleteNotif(item.id)" title="删除">×</button>
        </div>
      </div>

      <div v-else class="notif-empty">
        <div class="notif-empty-icon">🔔</div>
        <div class="notif-empty-text">暂无新通知</div>
      </div>

      <div class="notif-footer" v-if="notifications.length > 0">
        <span class="notif-count">共 {{ total }} 条通知</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiGet, apiPost, apiDelete } from '../api/client'

const router = useRouter()
const bellRef = ref(null)
const panelOpen = ref(false)
const notifications = ref([])
const total = ref(0)
const loading = ref(false)
let pollTimer = null

const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

function togglePanel() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value) {
    loadNotifications()
  }
}

async function loadNotifications() {
  if (loading.value) return
  loading.value = true
  try {
    const res = await apiGet('/api/notifications', { params: { page: 1, page_size: 20 } })
    if (res.code === 200 && res.data) {
      notifications.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    // 静默失败，不阻塞UI
  } finally {
    loading.value = false
  }
}

async function loadUnreadCount() {
  try {
    const res = await apiGet('/api/notifications/unread-count')
    if (res.code === 200 && res.data) {
      // 仅在首次加载时填充列表
      if (notifications.value.length === 0 && res.data.unread_count > 0) {
        loadNotifications()
      }
    }
  } catch (e) {
    // 静默失败
  }
}

async function handleClick(item) {
  if (!item.is_read) {
    try {
      await apiPost(`/api/notifications/${item.id}/read`)
      item.is_read = true
    } catch (e) {
      // 静默失败
    }
  }
  if (item.link) {
    panelOpen.value = false
    router.push(item.link)
  }
}

async function markAllRead() {
  try {
    await apiPost('/api/notifications/read-all')
    notifications.value.forEach(n => { n.is_read = true })
  } catch (e) {
    // 静默失败
  }
}

async function deleteNotif(id) {
  try {
    await apiDelete(`/api/notifications/${id}`)
    notifications.value = notifications.value.filter(n => n.id !== id)
    total.value = Math.max(0, total.value - 1)
  } catch (e) {
    // 静默失败
  }
}

async function clearAll() {
  try {
    await apiPost('/api/notifications/clear')
    notifications.value = []
    total.value = 0
  } catch (e) {
    // 静默失败
  }
}

function formatTime(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return ts
  }
}

function onDocClick(e) {
  if (bellRef.value && !bellRef.value.contains(e.target)) {
    panelOpen.value = false
  }
}

onMounted(() => {
  loadUnreadCount()
  pollTimer = setInterval(loadUnreadCount, 60000) // 每分钟轮询一次
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.notif-bell {
  position: relative;
  display: inline-flex;
}

.notif-btn {
  position: relative;
  cursor: pointer;
}

.notif-badge {
  position: absolute;
  top: -4px;
  right: -6px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  line-height: 1;
}

.notif-panel {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 360px;
  max-height: 480px;
  background: var(--panel, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.notif-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border, #e5e7eb);
  flex-shrink: 0;
}

.notif-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #111);
}

.notif-actions {
  display: flex;
  gap: 8px;
}

.notif-action-btn {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--primary, #4f46e5);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.15s;
}

.notif-action-btn:hover {
  background: var(--bg-hover, #f3f4f6);
}

.notif-list {
  flex: 1;
  overflow-y: auto;
  max-height: 360px;
}

.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light, #f3f4f6);
  cursor: pointer;
  transition: background 0.15s;
}

.notif-item:hover {
  background: var(--bg-hover, #f9fafb);
}

.notif-item.unread {
  background: var(--bg-unread, #f0f5ff);
}

.notif-item.unread:hover {
  background: var(--bg-unread-hover, #e8f0fe);
}

.notif-item-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.notif-item-content {
  flex: 1;
  min-width: 0;
}

.notif-item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text, #111);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-item-msg {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  margin-top: 2px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notif-item-time {
  font-size: 11px;
  color: var(--text-muted, #9ca3af);
  margin-top: 4px;
}

.notif-item-del {
  background: none;
  border: none;
  color: var(--text-muted, #9ca3af);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
  flex-shrink: 0;
}

.notif-item:hover .notif-item-del {
  opacity: 1;
}

.notif-item-del:hover {
  color: #ef4444;
}

.notif-empty {
  padding: 40px 20px;
  text-align: center;
}

.notif-empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.notif-empty-text {
  font-size: 13px;
  color: var(--text-muted, #9ca3af);
}

.notif-footer {
  padding: 8px 16px;
  border-top: 1px solid var(--border, #e5e7eb);
  text-align: center;
  flex-shrink: 0;
}

.notif-count {
  font-size: 11px;
  color: var(--text-muted, #9ca3af);
}
</style>

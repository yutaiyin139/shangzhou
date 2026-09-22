<template>
  <Teleport to="body">
    <div class="ui-toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="ui-toast"
          :class="`ui-toast--${toast.type}`"
        >
          <span class="ui-toast__icon">
            {{ iconMap[toast.type] || 'ℹ' }}
          </span>
          <div class="ui-toast__content">
            <div v-if="toast.title" class="ui-toast__title">{{ toast.title }}</div>
            <div class="ui-toast__message">{{ toast.message }}</div>
          </div>
          <button class="ui-toast__close" @click="removeToast(toast.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const toasts = ref([])
const iconMap = {
  success: '✔',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}

let _id = 0

function addToast(toast) {
  const id = ++_id
  const newToast = {
    id,
    type: toast.type || 'info',
    title: toast.title || '',
    message: toast.message || '',
    duration: toast.duration ?? 3000,
  }
  toasts.value.push(newToast)

  if (newToast.duration > 0) {
    setTimeout(() => removeToast(id), newToast.duration)
  }

  return id
}

function removeToast(id) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx > -1) {
    toasts.value.splice(idx, 1)
  }
}

// 暴露方法给父组件
defineExpose({
  success: (message, opts = {}) => addToast({ ...opts, type: 'success', message }),
  error: (message, opts = {}) => addToast({ ...opts, type: 'error', message }),
  warning: (message, opts = {}) => addToast({ ...opts, type: 'warning', message }),
  info: (message, opts = {}) => addToast({ ...opts, type: 'info', message }),
  add: addToast,
  remove: removeToast,
})
</script>

<style scoped>
.ui-toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.ui-toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  min-width: 280px;
  max-width: 400px;
  pointer-events: auto;
  border-left: 3px solid transparent;
}

.ui-toast--success { border-left-color: var(--green); }
.ui-toast--error { border-left-color: var(--red); }
.ui-toast--warning { border-left-color: var(--orange); }
.ui-toast--info { border-left-color: var(--primary); }

.ui-toast__icon {
  font-size: 16px;
  line-height: 1.4;
  flex-shrink: 0;
}
.ui-toast--success .ui-toast__icon { color: var(--green); }
.ui-toast--error .ui-toast__icon { color: var(--red); }
.ui-toast--warning .ui-toast__icon { color: var(--orange); }
.ui-toast--info .ui-toast__icon { color: var(--primary); }

.ui-toast__content {
  flex: 1;
  min-width: 0;
}
.ui-toast__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
  margin-bottom: 2px;
}
.ui-toast__message {
  font-size: 13px;
  color: var(--text-2);
  word-break: break-word;
}

.ui-toast__close {
  background: transparent;
  border: none;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-4);
  padding: 2px;
  flex-shrink: 0;
}
.ui-toast__close:hover {
  color: var(--text-2);
}

/* 动画 */
.toast-enter-active {
  transition: all 0.3s ease;
}
.toast-leave-active {
  transition: all 0.2s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>

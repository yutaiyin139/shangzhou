<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="8" y="12" width="48" height="40" rx="4" color="var(--border)"/>
          <path d="M8 20h48" color="var(--border)"/>
          <circle cx="16" cy="16" r="2" fill="var(--text-4)"/>
          <circle cx="24" cy="16" r="2" fill="var(--text-4)"/>
          <circle cx="32" cy="16" r="2" fill="var(--text-4)"/>
          <path d="M24 32h16M24 38h10" stroke-linecap="round" color="var(--text-4)"/>
        </svg>
      </slot>
    </div>
    <div class="empty-text">{{ text }}</div>
    <div class="empty-action" v-if="$slots.action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: '暂无数据'
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: var(--text-4);
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-text {
  color: var(--text-3);
  font-size: 14px;
}

.empty-action {
  margin-top: 16px;
}
</style>

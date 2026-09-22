<template>
  <span class="ui-badge" :class="[`ui-badge--${type}`, `ui-badge--${size}`, { 'ui-badge--dot': dot }]">
    <span v-if="dot" class="ui-badge__dot"></span>
    <slot />
  </span>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'default' }, // default | primary | success | warning | error | info
  size: { type: String, default: 'medium' }, // small | medium | large
  dot: { type: Boolean, default: false },
})
</script>

<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.ui-badge--small {
  padding: 1px 6px;
  font-size: 11px;
  height: 18px;
}
.ui-badge--medium {
  padding: 2px 8px;
  font-size: 12px;
  height: 22px;
}
.ui-badge--large {
  padding: 3px 10px;
  font-size: 13px;
  height: 26px;
}

.ui-badge--default {
  background: var(--border-light);
  color: var(--text-2);
}
.ui-badge--primary {
  background: var(--primary-light);
  color: var(--primary);
}
.ui-badge--success {
  background: #e6f7e6;
  color: #16a34a;
}
.ui-badge--warning {
  background: #fef3c7;
  color: #d97706;
}
.ui-badge--error {
  background: #fee2e2;
  color: #dc2626;
}
.ui-badge--info {
  background: #dbeafe;
  color: #2563eb;
}

.ui-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
</style>

<template>
  <button
    class="ui-btn"
    :class="[
      `ui-btn--${type}`,
      `ui-btn--${size}`,
      { 'ui-btn--loading': loading, 'ui-btn--disabled': disabled, 'ui-btn--block': block }
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="ui-btn__spinner"></span>
    <slot />
  </button>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'primary' }, // primary | secondary | danger | ghost
  size: { type: String, default: 'medium' }, // small | medium | large
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])

function handleClick(e) {
  emit('click', e)
}
</script>

<style scoped>
.ui-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: var(--radius);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  font-family: inherit;
}

.ui-btn--primary {
  background: var(--primary);
  color: #fff;
}
.ui-btn--primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.ui-btn--secondary {
  background: var(--bg-page);
  border-color: var(--border);
  color: var(--text-1);
}
.ui-btn--secondary:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.ui-btn--danger {
  background: var(--red);
  color: #fff;
}
.ui-btn--danger:hover:not(:disabled) {
  background: #e03636;
}

.ui-btn--ghost {
  background: transparent;
  color: var(--text-2);
}
.ui-btn--ghost:hover:not(:disabled) {
  background: var(--border-light);
}

/* 尺寸 */
.ui-btn--small {
  padding: 4px 12px;
  font-size: 12px;
  height: 28px;
}
.ui-btn--medium {
  padding: 6px 16px;
  font-size: 14px;
  height: 34px;
}
.ui-btn--large {
  padding: 8px 24px;
  font-size: 16px;
  height: 40px;
}

/* 状态 */
.ui-btn--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ui-btn--loading {
  opacity: 0.7;
  cursor: wait;
}
.ui-btn--block {
  width: 100%;
}

/* 加载动画 */
.ui-btn__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

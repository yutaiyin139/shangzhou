<template>
  <div class="ui-spinner" :class="`ui-spinner--${size}`">
    <div class="ui-spinner__circle"></div>
    <span v-if="text" class="ui-spinner__text">{{ text }}</span>
  </div>
</template>

<script setup>
defineProps({
  size: { type: String, default: 'medium' }, // small | medium | large
  text: { type: String, default: '' },
})
</script>

<style scoped>
.ui-spinner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.ui-spinner__circle {
  border: 2px solid var(--border-light);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.ui-spinner--small .ui-spinner__circle {
  width: 14px;
  height: 14px;
}
.ui-spinner--medium .ui-spinner__circle {
  width: 20px;
  height: 20px;
}
.ui-spinner--large .ui-spinner__circle {
  width: 28px;
  height: 28px;
  border-width: 3px;
}

.ui-spinner__text {
  font-size: 13px;
  color: var(--text-2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

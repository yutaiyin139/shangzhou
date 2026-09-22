<template>
  <div class="ui-card" :class="[`ui-card--${variant}`, { 'ui-card--hoverable': hoverable, 'ui-card--padding': padding }]">
    <div v-if="$slots.header || title" class="ui-card__header">
      <slot name="header">
        <span class="ui-card__title">{{ title }}</span>
        <span v-if="subtitle" class="ui-card__subtitle">{{ subtitle }}</span>
      </slot>
    </div>
    <div class="ui-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="ui-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  variant: { type: String, default: 'default' }, // default | bordered | shadow
  hoverable: { type: Boolean, default: false },
  padding: { type: Boolean, default: true },
})
</script>

<style scoped>
.ui-card {
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
}

.ui-card--default {
  border: 1px solid var(--border-light);
}

.ui-card--bordered {
  border: 1px solid var(--border);
}

.ui-card--shadow {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.ui-card--hoverable {
  transition: box-shadow 0.2s, transform 0.2s;
  cursor: pointer;
}
.ui-card--hoverable:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.ui-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
}

.ui-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}

.ui-card__subtitle {
  font-size: 12px;
  color: var(--text-3);
  margin-left: 8px;
}

.ui-card__body {
  padding: 16px;
}
.ui-card--padding .ui-card__body {
  padding: 16px;
}

.ui-card__footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-page, #f9fafb);
}
</style>

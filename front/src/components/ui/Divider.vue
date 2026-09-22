<template>
  <div class="ui-divider" :class="[`ui-divider--${type}`, { 'ui-divider--with-text': $slots.default }]">
    <span v-if="$slots.default" class="ui-divider__text">
      <slot />
    </span>
  </div>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'horizontal' }, // horizontal | vertical
})
</script>

<style scoped>
.ui-divider {
  display: flex;
  align-items: center;
}

.ui-divider--horizontal {
  width: 100%;
  height: 1px;
  background: var(--border-light);
  margin: 16px 0;
}

.ui-divider--vertical {
  width: 1px;
  height: 100%;
  background: var(--border-light);
  margin: 0 16px;
  display: inline-block;
}

.ui-divider--with-text {
  background: transparent;
  height: auto;
  margin: 20px 0;
}
.ui-divider--with-text::before,
.ui-divider--with-text::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-light);
}

.ui-divider__text {
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-3);
  white-space: nowrap;
}
</style>

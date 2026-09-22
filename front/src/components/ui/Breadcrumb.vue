<template>
  <nav class="ui-breadcrumb">
    <span
      v-for="(item, idx) in items"
      :key="idx"
      class="ui-breadcrumb__item"
      :class="{ 'ui-breadcrumb__item--current': idx === items.length - 1 }"
    >
      <a
        v-if="idx < items.length - 1 && item.path"
        class="ui-breadcrumb__link"
        @click="navigate(item)"
      >{{ item.label }}</a>
      <span v-else class="ui-breadcrumb__text">{{ item.label }}</span>
      <span v-if="idx < items.length - 1" class="ui-breadcrumb__separator">{{ separator }}</span>
    </span>
  </nav>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true }, // [{label, path?}]
  separator: { type: String, default: '/' },
})

const emit = defineEmits(['click'])

function navigate(item) {
  emit('click', item)
}
</script>

<style scoped>
.ui-breadcrumb {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.ui-breadcrumb__item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ui-breadcrumb__link {
  color: var(--text-2);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.15s;
}
.ui-breadcrumb__link:hover {
  color: var(--primary);
}

.ui-breadcrumb__text {
  color: var(--text-1);
  font-weight: 500;
}

.ui-breadcrumb__separator {
  color: var(--text-4);
  margin: 0 2px;
}
</style>

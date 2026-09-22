<template>
  <div class="ui-collapse" :class="{ 'ui-collapse--accordion': accordion }">
    <div
      v-for="item in items"
      :key="item.key"
      class="ui-collapse__item"
      :class="{ 'ui-collapse__item--active': isActive(item.key) }"
    >
      <div class="ui-collapse__header" @click="toggle(item.key)">
        <span v-if="item.icon" class="ui-collapse__icon" v-html="item.icon"></span>
        <span class="ui-collapse__title">{{ item.title }}</span>
        <span class="ui-collapse__arrow" :class="{ 'ui-collapse__arrow--open': isActive(item.key) }">▾</span>
      </div>
      <transition name="collapse">
        <div v-if="isActive(item.key)" class="ui-collapse__body">
          <slot :name="item.key">{{ item.content }}</slot>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  items: { type: Array, required: true }, // [{key, title, icon?, content?}]
  modelValue: { type: [String, Array], default: '' },
  accordion: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const activeKeys = ref(
  Array.isArray(props.modelValue) ? [...props.modelValue] : props.modelValue ? [props.modelValue] : []
)

watch(() => props.modelValue, (val) => {
  activeKeys.value = Array.isArray(val) ? [...val] : val ? [val] : []
})

function isActive(key) {
  return activeKeys.value.includes(key)
}

function toggle(key) {
  if (props.accordion) {
    activeKeys.value = activeKeys.value.includes(key) ? [] : [key]
  } else {
    const idx = activeKeys.value.indexOf(key)
    if (idx > -1) {
      activeKeys.value.splice(idx, 1)
    } else {
      activeKeys.value.push(key)
    }
  }
  emit('update:modelValue', props.accordion ? (activeKeys.value[0] || '') : activeKeys.value)
  emit('change', activeKeys.value)
}
</script>

<style scoped>
.ui-collapse {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.ui-collapse__item {
  border-bottom: 1px solid var(--border-light);
}
.ui-collapse__item:last-child {
  border-bottom: none;
}

.ui-collapse__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  background: var(--bg-page, #f9fafb);
  transition: background 0.15s;
}
.ui-collapse__header:hover {
  background: var(--border-light);
}

.ui-collapse__icon {
  font-size: 14px;
}

.ui-collapse__title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-1);
}

.ui-collapse__arrow {
  font-size: 12px;
  color: var(--text-3);
  transition: transform 0.2s;
}
.ui-collapse__arrow--open {
  transform: rotate(180deg);
}

.ui-collapse__body {
  padding: 16px;
  background: #fff;
  border-top: 1px solid var(--border-light);
}

.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>

<template>
  <div class="ui-tabs">
    <div class="ui-tabs__header" :class="`ui-tabs--${type}`">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="ui-tabs__tab"
        :class="{ 'ui-tabs__tab--active': activeKey === tab.key }"
        @click="selectTab(tab.key)"
      >
        <span v-if="tab.icon" class="ui-tabs__icon" v-html="tab.icon"></span>
        <span>{{ tab.label }}</span>
        <span v-if="tab.count !== undefined" class="ui-tabs__count">{{ tab.count }}</span>
      </div>
    </div>
    <div class="ui-tabs__body">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  tabs: { type: Array, required: true }, // [{key, label, icon?, count?}]
  modelValue: { type: String, default: '' },
  type: { type: String, default: 'line' }, // line | card | pill
})

const emit = defineEmits(['update:modelValue', 'change'])

const activeKey = ref(props.modelValue || (props.tabs[0] && props.tabs[0].key) || '')

watch(() => props.modelValue, (val) => {
  if (val && val !== activeKey.value) {
    activeKey.value = val
  }
})

function selectTab(key) {
  activeKey.value = key
  emit('update:modelValue', key)
  emit('change', key)
}

// 导出 activeKey 供子组件使用
defineExpose({ activeKey })
</script>

<style scoped>
.ui-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ui-tabs__header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.ui-tabs--card {
  border-bottom: none;
  gap: 4px;
}

.ui-tabs--pill {
  border-bottom: none;
  gap: 4px;
  padding: 4px;
  background: var(--bg-page, #f5f5f5);
  border-radius: 8px;
}

.ui-tabs__tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-2);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.15s;
  white-space: nowrap;
}
.ui-tabs__tab:hover {
  color: var(--text-1);
}

.ui-tabs__tab--active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 500;
}

.ui-tabs--card .ui-tabs__tab {
  border: 1px solid var(--border-light);
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  margin-bottom: -1px;
  background: var(--bg-page, #f5f5f5);
}
.ui-tabs--card .ui-tabs__tab--active {
  background: #fff;
  border-color: var(--border);
  border-bottom-color: #fff;
}

.ui-tabs--pill .ui-tabs__tab {
  border: none;
  border-radius: 6px;
  margin-bottom: 0;
}
.ui-tabs--pill .ui-tabs__tab--active {
  background: #fff;
  color: var(--primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.ui-tabs__icon {
  font-size: 14px;
}

.ui-tabs__count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--border-light);
  color: var(--text-3);
}

.ui-tabs__tab--active .ui-tabs__count {
  background: var(--primary-light);
  color: var(--primary);
}

.ui-tabs__body {
  flex: 1;
  overflow-y: auto;
}
</style>

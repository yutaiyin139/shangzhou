<template>
  <div class="ui-dropdown" ref="dropdownRef" :class="{ 'ui-dropdown--open': isOpen }">
    <div class="ui-dropdown__trigger" @click="toggle">
      <slot name="trigger">
        <span class="ui-dropdown__trigger-text">{{ label }}</span>
        <span class="ui-dropdown__arrow">▾</span>
      </slot>
    </div>
    <transition name="dropdown">
      <div v-if="isOpen" class="ui-dropdown__menu" :class="`ui-dropdown__menu--${placement}`" @click.stop>
        <slot>
          <div
            v-for="item in items"
            :key="item.key || item.label"
            class="ui-dropdown__item"
            :class="{ 'ui-dropdown__item--disabled': item.disabled, 'ui-dropdown__item--divider': item.divider }"
            @click="selectItem(item)"
          >
            <span v-if="item.icon" class="ui-dropdown__item-icon" v-html="item.icon"></span>
            <span>{{ item.label }}</span>
          </div>
        </slot>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  items: { type: Array, default: () => [] }, // [{key, label, icon?, disabled?, divider?}]
  placement: { type: String, default: 'bottom-left' }, // bottom-left | bottom-right | top-left | top-right
})

const emit = defineEmits(['select', 'open', 'close'])

const dropdownRef = ref(null)
const isOpen = ref(false)

function toggle() {
  isOpen.value = !isOpen.value
  emit(isOpen.value ? 'open' : 'close')
}

function close() {
  isOpen.value = false
  emit('close')
}

function selectItem(item) {
  if (item.disabled || item.divider) return
  emit('select', item)
  close()
}

function onDocClick(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.ui-dropdown {
  position: relative;
  display: inline-flex;
}

.ui-dropdown__trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}

.ui-dropdown__trigger-text {
  font-size: 14px;
}

.ui-dropdown__arrow {
  font-size: 10px;
  color: var(--text-3);
  transition: transform 0.2s;
}
.ui-dropdown--open .ui-dropdown__arrow {
  transform: rotate(180deg);
}

.ui-dropdown__menu {
  position: absolute;
  top: 100%;
  margin-top: 4px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100;
  min-width: 160px;
  padding: 4px 0;
}

.ui-dropdown__menu--bottom-left {
  left: 0;
}
.ui-dropdown__menu--bottom-right {
  right: 0;
}
.ui-dropdown__menu--top-left {
  bottom: 100%;
  top: auto;
  margin-bottom: 4px;
  left: 0;
}
.ui-dropdown__menu--top-right {
  bottom: 100%;
  top: auto;
  margin-bottom: 4px;
  right: 0;
}

.ui-dropdown__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--text-1);
  cursor: pointer;
  transition: background 0.1s;
}
.ui-dropdown__item:hover {
  background: var(--bg-hover, #f3f4f6);
}
.ui-dropdown__item--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ui-dropdown__item--divider {
  height: 1px;
  padding: 0;
  margin: 4px 0;
  background: var(--border-light);
  cursor: default;
}

.ui-dropdown__item-icon {
  font-size: 14px;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

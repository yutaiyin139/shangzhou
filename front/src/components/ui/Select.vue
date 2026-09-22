<template>
  <div class="ui-select-wrapper" :class="{ 'ui-select--error': error, 'ui-select--disabled': disabled }">
    <label v-if="label" class="ui-select__label">{{ label }}</label>
    <div class="ui-select__container" ref="selectRef" @click="toggleOpen">
      <span v-if="$slots.prefix" class="ui-select__prefix">
        <slot name="prefix" />
      </span>
      <span class="ui-select__value" :class="{ 'ui-select__placeholder': !displayValue }">
        {{ displayValue || placeholder }}
      </span>
      <span class="ui-select__arrow" :class="{ 'ui-select__arrow--open': isOpen }">▾</span>
    </div>
    <div v-if="isOpen" class="ui-select__dropdown" @click.stop>
      <div v-if="filterable" class="ui-select__filter">
        <input v-model="filterText" placeholder="搜索..." @input="handleFilter" />
      </div>
      <div class="ui-select__options">
        <div
          v-for="opt in filteredOptions"
          :key="opt.value"
          class="ui-select__option"
          :class="{ 'ui-select__option--selected': opt.value === modelValue }"
          @click="selectOption(opt)"
        >
          <span>{{ opt.label }}</span>
          <span v-if="opt.value === modelValue" class="ui-select__check">✓</span>
        </div>
        <div v-if="filteredOptions.length === 0" class="ui-select__empty">无匹配选项</div>
      </div>
    </div>
    <div v-if="error || hint" class="ui-select__message" :class="{ 'ui-select__message--error': error }">
      {{ error || hint }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] }, // [{label, value}]
  label: { type: String, default: '' },
  placeholder: { type: String, default: '请选择...' },
  disabled: { type: Boolean, default: false },
  clearable: { type: Boolean, default: false },
  filterable: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change', 'clear'])

const selectRef = ref(null)
const isOpen = ref(false)
const filterText = ref('')

const displayValue = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : ''
})

const filteredOptions = computed(() => {
  if (!filterText.value) return props.options
  const lower = filterText.value.toLowerCase()
  return props.options.filter(o => o.label.toLowerCase().includes(lower))
})

function toggleOpen() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (!isOpen.value) filterText.value = ''
}

function selectOption(opt) {
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  isOpen.value = false
  filterText.value = ''
}

function handleFilter() {
  // 过滤由 computed 处理
}

function onDocClick(e) {
  if (selectRef.value && !selectRef.value.parentElement?.contains(e.target)) {
    isOpen.value = false
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
.ui-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
}

.ui-select__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.ui-select__container {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fff;
  padding: 8px 12px;
  cursor: pointer;
  transition: border-color 0.15s;
  min-height: 34px;
  box-sizing: border-box;
}
.ui-select__container:hover {
  border-color: var(--primary);
}
.ui-select--error .ui-select__container {
  border-color: var(--red);
}
.ui-select--disabled .ui-select__container {
  background: var(--bg-page);
  opacity: 0.6;
  cursor: not-allowed;
}

.ui-select__value {
  flex: 1;
  font-size: 14px;
  color: var(--text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ui-select__placeholder {
  color: var(--text-4);
}

.ui-select__arrow {
  font-size: 12px;
  color: var(--text-3);
  transition: transform 0.2s;
}
.ui-select__arrow--open {
  transform: rotate(180deg);
}

.ui-select__dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
}

.ui-select__filter {
  padding: 8px;
  border-bottom: 1px solid var(--border-light);
}
.ui-select__filter input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.ui-select__filter input:focus {
  border-color: var(--primary);
}

.ui-select__options {
  padding: 4px 0;
}

.ui-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--text-1);
  cursor: pointer;
  transition: background 0.1s;
}
.ui-select__option:hover {
  background: var(--bg-hover, #f3f4f6);
}
.ui-select__option--selected {
  color: var(--primary);
  font-weight: 500;
}

.ui-select__check {
  font-size: 12px;
}

.ui-select__empty {
  padding: 12px;
  text-align: center;
  font-size: 13px;
  color: var(--text-4);
}

.ui-select__message {
  font-size: 12px;
  color: var(--text-3);
}
.ui-select__message--error {
  color: var(--red);
}
</style>

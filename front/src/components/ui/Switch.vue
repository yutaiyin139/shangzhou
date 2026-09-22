<template>
  <label class="ui-switch" :class="{ 'ui-switch--checked': modelValue, 'ui-switch--disabled': disabled }">
    <input
      type="checkbox"
      class="ui-switch__input"
      :checked="modelValue"
      :disabled="disabled"
      @change="handleChange"
    />
    <span class="ui-switch__track">
      <span class="ui-switch__thumb"></span>
    </span>
    <span v-if="label || $slots.default" class="ui-switch__label">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

function handleChange(e) {
  emit('update:modelValue', e.target.checked)
  emit('change', e.target.checked)
}
</script>

<style scoped>
.ui-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.ui-switch--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ui-switch__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.ui-switch__track {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: var(--border);
  transition: background 0.2s;
  flex-shrink: 0;
}

.ui-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.ui-switch--checked .ui-switch__track {
  background: var(--primary);
}
.ui-switch--checked .ui-switch__thumb {
  transform: translateX(16px);
}

.ui-switch__label {
  font-size: 14px;
  color: var(--text-1);
}
</style>

<template>
  <div class="ui-input-wrapper" :class="{ 'ui-input--error': error, 'ui-input--disabled': disabled }">
    <label v-if="label" class="ui-input__label">{{ label }}</label>
    <div class="ui-input__container">
      <span v-if="$slots.prefix" class="ui-input__prefix">
        <slot name="prefix" />
      </span>
      <input
        class="ui-input"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :maxlength="maxlength"
        :autofocus="autofocus"
        @input="handleInput"
        @change="handleChange"
        @focus="handleFocus"
        @blur="handleBlur"
        @keyup.enter="handleEnter"
      />
      <span v-if="$slots.suffix || clearable" class="ui-input__suffix">
        <span v-if="clearable && modelValue" class="ui-input__clear" @click="handleClear">✕</span>
        <slot name="suffix" />
      </span>
    </div>
    <div v-if="error || hint" class="ui-input__message" :class="{ 'ui-input__message--error': error }">
      {{ error || hint }}
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  clearable: { type: Boolean, default: false },
  maxlength: { type: [Number, String], default: undefined },
  autofocus: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'input', 'change', 'focus', 'blur', 'enter', 'clear'])

function handleInput(e) {
  emit('update:modelValue', e.target.value)
  emit('input', e)
}

function handleChange(e) {
  emit('change', e)
}

function handleFocus(e) {
  emit('focus', e)
}

function handleBlur(e) {
  emit('blur', e)
}

function handleEnter(e) {
  emit('enter', e)
}

function handleClear() {
  emit('update:modelValue', '')
  emit('clear')
}
</script>

<style scoped>
.ui-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ui-input__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.ui-input__container {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fff;
  transition: border-color 0.15s;
}
.ui-input__container:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.ui-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--text-1);
  background: transparent;
  min-width: 0;
}
.ui-input::placeholder {
  color: var(--text-4);
}

.ui-input__prefix,
.ui-input__suffix {
  display: flex;
  align-items: center;
  padding: 0 8px;
  color: var(--text-3);
}

.ui-input__clear {
  cursor: pointer;
  font-size: 12px;
  color: var(--text-4);
}
.ui-input__clear:hover {
  color: var(--text-2);
}

.ui-input__message {
  font-size: 12px;
  color: var(--text-3);
}
.ui-input__message--error {
  color: var(--red);
}

.ui-input--error .ui-input__container {
  border-color: var(--red);
}
.ui-input--disabled .ui-input__container {
  background: var(--bg-page);
  opacity: 0.6;
}
</style>

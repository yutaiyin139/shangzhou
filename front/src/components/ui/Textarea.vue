<template>
  <div class="ui-textarea-wrapper" :class="{ 'ui-textarea--error': error, 'ui-textarea--disabled': disabled }">
    <label v-if="label" class="ui-textarea__label">{{ label }}</label>
    <textarea
      class="ui-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :rows="rows"
      :maxlength="maxlength"
      @input="handleInput"
      @change="handleChange"
      @focus="handleFocus"
      @blur="handleBlur"
    ></textarea>
    <div v-if="showCount || error || hint" class="ui-textarea__footer">
      <span v-if="error" class="ui-textarea__message ui-textarea__message--error">{{ error }}</span>
      <span v-else-if="hint" class="ui-textarea__message">{{ hint }}</span>
      <span v-if="showCount && maxlength" class="ui-textarea__count">{{ (modelValue || '').length }}/{{ maxlength }}</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  rows: { type: Number, default: 4 },
  maxlength: { type: [Number, String], default: undefined },
  showCount: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
  autoResize: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'input', 'change', 'focus', 'blur'])

function handleInput(e) {
  emit('update:modelValue', e.target.value)
  emit('input', e)
  if (props.autoResize) {
    autoResize(e.target)
  }
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

function autoResize(el) {
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}
</script>

<style scoped>
.ui-textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ui-textarea__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.ui-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  color: var(--text-1);
  background: #fff;
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.ui-textarea::placeholder {
  color: var(--text-4);
}
.ui-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.ui-textarea--error .ui-textarea {
  border-color: var(--red);
}
.ui-textarea--disabled .ui-textarea {
  background: var(--bg-page);
  opacity: 0.6;
}

.ui-textarea__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ui-textarea__message {
  font-size: 12px;
  color: var(--text-3);
  flex: 1;
}
.ui-textarea__message--error {
  color: var(--red);
}

.ui-textarea__count {
  font-size: 12px;
  color: var(--text-4);
  flex-shrink: 0;
}
</style>

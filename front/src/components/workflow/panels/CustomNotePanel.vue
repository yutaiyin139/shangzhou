<template>
  <div class="custom-note-panel">
    <div class="note-field">
      <div class="note-label">注释内容</div>
      <textarea
        :value="node.data.text || ''"
        @input="onInput"
        @change="onChange"
        placeholder="输入注释内容..."
        rows="4"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

function onInput(e) {
  // 实时更新本地显示
  if (props.node) {
    props.node.data.text = e.target.value
  }
}

function onChange(e) {
  if (props.node) {
    emit('update', props.node.id, { text: e.target.value })
  }
}
</script>

<style scoped>
.custom-note-panel {
  padding: 4px 0;
}
.note-field {
  margin-bottom: 12px;
}
.note-label {
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  color: #475467;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.note-field textarea {
  width: 100%;
  border: 0.5px solid #D0D5DD;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 20px;
  color: #1D2939;
  background: #fff;
  resize: vertical;
  min-height: 80px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.note-field textarea:focus {
  border-color: #155EEF;
  box-shadow: 0 0 0 3px rgba(21, 94, 239, 0.1);
}
</style>

<template>
  <div>
    <div class="pp-field">
      <label>语言</label>
      <select v-model="local.code_language" @change="commit">
        <option value="python3">Python 3</option>
        <option value="javascript">JavaScript</option>
        <option value="json">JSON</option>
      </select>
    </div>
    <div class="pp-field">
      <label>代码</label>
      <textarea v-model="local.code" rows="10" @change="commit"></textarea>
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)
</script>

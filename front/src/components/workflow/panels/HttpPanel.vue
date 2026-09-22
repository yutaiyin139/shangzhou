<template>
  <div>
    <div class="pp-field">
      <label>方法</label>
      <select v-model="local.method" @change="commit">
        <option value="get">GET</option>
        <option value="post">POST</option>
        <option value="put">PUT</option>
        <option value="delete">DELETE</option>
      </select>
    </div>
    <div class="pp-field">
      <label>URL</label>
      <input v-model="local.url" @change="commit">
    </div>
    <div class="pp-field">
      <label>Headers (JSON)</label>
      <textarea v-model="local.headers" rows="3" @change="commit"></textarea>
    </div>
    <div class="pp-field">
      <label>Body</label>
      <textarea v-model="local.body" rows="4" @change="commit"></textarea>
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)
</script>

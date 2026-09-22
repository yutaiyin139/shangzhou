<template>
  <div>
    <div class="pp-field">
      <label>知识库</label>
      <select v-model="selectedDataset" @change="commitDataset">
        <option value="">请选择知识库</option>
        <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
    </div>
    <div class="pp-field">
      <label>查询变量</label>
      <input v-model="querySelector" @change="commitQuery" placeholder="如 {{#start.query#}}">
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, datasets, selectedDataset, querySelector,
  commitDataset, commitQuery,
} = usePanelState(props, emit)
</script>

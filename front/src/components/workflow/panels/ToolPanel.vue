<template>
  <div>
    <div class="pp-field">
      <label>工具提供者</label>
      <select v-model="selectedToolProvider" @change="commitToolProvider">
        <option value="">请选择工具</option>
        <option v-for="t in tools" :key="t.id" :value="t.id">{{ t.name }}</option>
      </select>
    </div>
    <div class="pp-field" v-if="selectedToolProvider">
      <label>Action</label>
      <select v-model="selectedToolAction" @change="commitToolAction">
        <option value="">请选择 Action</option>
        <option v-for="a in toolActions" :key="a.name" :value="a.name">{{ a.label || a.name }}</option>
      </select>
    </div>
    <div v-if="toolParams.length" class="pp-section-title">参数</div>
    <div v-for="p in toolParams" :key="p.name" class="pp-field">
      <label>{{ p.label || p.name }} {{ p.required ? '*' : '' }}</label>
      <input v-model="local.tool_parameters[p.name].value" @change="commitToolParam(p.name)">
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, tools, selectedToolProvider, selectedToolAction,
  toolActions, toolParams, commitToolProvider, commitToolAction, commitToolParam,
} = usePanelState(props, emit)
</script>

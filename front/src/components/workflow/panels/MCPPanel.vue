<template>
  <div>
    <div class="pp-field">
      <label>MCP 服务器</label>
      <select v-model="selectedMcpServer" @change="commitMcpServer">
        <option value="">请选择 MCP 服务器</option>
        <option v-for="s in mcpServers" :key="s.id" :value="String(s.id)">{{ s.name }} ({{ s.mtype }})</option>
      </select>
      <div v-if="mcpServers.length === 0" class="pp-hint">暂无可用 MCP 服务器，请先在「MCP」页面添加。</div>
    </div>
    <div class="pp-field" v-if="selectedMcpServer">
      <label>工具名称</label>
      <select v-model="selectedMcpTool" @change="commitMcpTool">
        <option value="">请选择工具</option>
        <option v-for="t in mcpTools" :key="t.name" :value="t.name">{{ t.label || t.name }}</option>
      </select>
    </div>
    <div v-if="mcpToolParams.length" class="pp-section-title">参数</div>
    <div v-for="p in mcpToolParams" :key="p.name" class="pp-field">
      <label>{{ p.label || p.name }} {{ p.required ? '*' : '' }}</label>
      <input v-model="local.mcp_parameters[p.name].value" @change="commitMcpParam(p.name)">
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, mcpServers, mcpTools, selectedMcpServer, selectedMcpTool,
  mcpToolParams, commitMcpServer, commitMcpTool, commitMcpParam,
} = usePanelState(props, emit)
</script>

<template>
  <div>
    <div class="pp-section-title">基本信息</div>
    <div class="pp-field">
      <label>节点类型</label>
      <div class="pp-hint">{{ nodeType }}</div>
    </div>
    <div class="pp-field">
      <label>节点 ID</label>
      <div class="pp-hint">{{ node?.id }}</div>
    </div>
    <div class="pp-section-title">配置</div>
    <div class="pp-hint">此节点类型暂无专用配置面板。</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ node: { type: Object, default: null } })

const nodeType = computed(() => props.node ? (props.node.data._type || props.node.data.type) : '')
</script>

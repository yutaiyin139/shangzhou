<template>
  <div class="wf-node" :class="{ selected: selected }">
    <Handle type="target" :position="Position.Left" />
    <div class="wf-node-inner">
      <div class="wf-node-icon" :style="{ background: nodeMeta.color + '1A' }">
        <span class="wf-node-ico" :style="{ background: nodeMeta.color }">{{ nodeMeta.icon }}</span>
      </div>
      <div class="wf-node-content">
        <div class="wf-node-title">{{ displayTitle }}</div>
        <div class="wf-node-desc">{{ nodeMeta.description || nodeMeta.title }}</div>
      </div>
    </div>
    <!-- 迭代节点：双输出口（loop + end） -->
    <template v-if="isIteration">
      <Handle id="loop" type="source" :position="Position.Right" class="wf-handle-top">
        <span class="handle-label">loop</span>
      </Handle>
      <Handle id="end" type="source" :position="Position.Right" class="wf-handle-bottom">
        <span class="handle-label">end</span>
      </Handle>
    </template>
    <!-- 条件分支节点：双输出口 -->
    <template v-else-if="isIfElse">
      <Handle id="yes" type="source" :position="Position.Right" class="wf-handle-top">
        <span class="handle-label handle-label-yes">Yes</span>
      </Handle>
      <Handle id="no" type="source" :position="Position.Right" class="wf-handle-bottom">
        <span class="handle-label handle-label-no">No</span>
      </Handle>
    </template>
    <!-- 默认单输出口 -->
    <template v-else>
      <Handle type="source" :position="Position.Right" />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { getNodeType } from '../../utils/workflow/nodeRegistry'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

const nodeMeta = computed(() => getNodeType(props.data._type))
const displayTitle = computed(() => props.data.title || props.data._title || nodeMeta.value.title)
const isIteration = computed(() => props.data._type === 'iteration')
const isIfElse = computed(() => props.data._type === 'if-else')
</script>

<style scoped>
.wf-node {
  position: relative;
  width: 260px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(29, 33, 41, 0.06);
  border: 1.5px solid transparent;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.wf-node.selected {
  border-color: #155EEF;
  box-shadow: 0 4px 16px rgba(21, 94, 239, 0.15);
}
.wf-node-inner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
}
.wf-node-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wf-node-ico {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
}
.wf-node-content {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}
.wf-node-title {
  font-size: 13px;
  font-weight: 600;
  color: #1D2939;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}
.wf-node-desc {
  font-size: 11px;
  color: #98A2B3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
  line-height: 1.3;
}
.handle-label {
  font-size: 10px;
  color: #98A2B3;
  position: absolute;
  right: 12px;
  white-space: nowrap;
  top: 50%;
  transform: translateY(-50%);
}
.handle-label-yes { color: #12B76A; }
.handle-label-no { color: #F04438; }
.wf-handle-top { top: 55%; }
.wf-handle-bottom { top: 78%; }
</style>

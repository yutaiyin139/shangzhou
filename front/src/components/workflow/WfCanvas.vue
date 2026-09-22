<template>
  <div class="wf-canvas" @drop="onDrop" @dragover="onDragOver">
    <VueFlow
      v-model="elements"
      :node-types="nodeTypes"
      :default-viewport="defaultViewport"
      :min-zoom="0.2"
      :max-zoom="4"
      fit-view-on-init
      @node-click="onNodeClick"
      @pane-click="onPaneClick"
      @connect="onConnect"
      @node-drag-stop="pushGraphUpdate"
      @nodes-initialized="onNodesInitialized"
    >
      <Background pattern-color="#E5E6EB" :gap="16" :size="1" />
      <Controls />
      <MiniMap pannable zoomable />
    </VueFlow>
  </div>
</template>

<script setup>
import { ref, watch, markRaw } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import WfNode from './WfNode.vue'
import { graphToElements, elementsToGraph, createVueFlowNode, newNodeId } from '../../utils/workflow/graphUtils'
import { autoLayout } from '../../utils/workflow/layout'

const props = defineProps({
  graph: { type: Object, default: () => ({ nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } }) }
})

const emit = defineEmits(['select-node', 'deselect', 'update:graph'])

const nodeTypes = { 'wf-node': markRaw(WfNode) }

const elements = ref([])
const defaultViewport = ref({ x: 0, y: 0, zoom: 1 })
const vueFlowInstance = useVueFlow()

function syncFromGraph() {
  const { nodes, edges } = graphToElements(props.graph)
  elements.value = [...nodes, ...edges]
  defaultViewport.value = props.graph.viewport || { x: 0, y: 0, zoom: 1 }
}

watch(() => props.graph, syncFromGraph, { immediate: true })

function onNodeClick(event) {
  // Vue Flow 2.x passes event as first arg; node data is in event.node
  const node = event && event.node ? event.node : event
  emit('select-node', node)
}

function onPaneClick() {
  emit('deselect')
}

function onConnect(params) {
  const edge = {
    id: newNodeId(),
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle,
    type: 'default',
    data: {}
  }
  elements.value.push(edge)
  pushGraphUpdate()
}

function getGraph() {
  const nodes = elements.value.filter(el => !el.source)
  const edges = elements.value.filter(el => el.source)
  const vp = vueFlowInstance.getViewport ? vueFlowInstance.getViewport() : (vueFlowInstance.viewport?.value || { x: 0, y: 0, zoom: 1 })
  return elementsToGraph(nodes, edges, vp)
}

function pushGraphUpdate() {
  emit('update:graph', getGraph())
}

function onDragOver(event) {
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}

function onDrop(event) {
  event.preventDefault()
  const type = event.dataTransfer.getData('application/wf-node-type')
  if (!type) return
  const rect = event.currentTarget.getBoundingClientRect()
  const position = vueFlowInstance.project({
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  })
  const node = createVueFlowNode(type, position)
  elements.value.push(node)
  pushGraphUpdate()
  emit('select-node', node)
}

function addNode(type, position) {
  const node = createVueFlowNode(type, position || { x: 100, y: 100 })
  elements.value.push(node)
  pushGraphUpdate()
  return node
}

function removeNode(nodeId) {
  elements.value = elements.value.filter(el => el.id !== nodeId && (!el.source || (el.source !== nodeId && el.target !== nodeId)))
  pushGraphUpdate()
}

function updateNodeData(nodeId, patch) {
  const idx = elements.value.findIndex(el => el.id === nodeId && !el.source)
  if (idx >= 0) {
    elements.value[idx] = { ...elements.value[idx], data: { ...elements.value[idx].data, ...patch } }
    pushGraphUpdate()
  }
}

function fitView() {
  vueFlowInstance.fitView()
}

function applyLayout() {
  const nodes = elements.value.filter(el => !el.source)
  const edges = elements.value.filter(el => el.source)
  const laid = autoLayout(nodes, edges)
  elements.value = [...laid, ...edges]
  pushGraphUpdate()
  vueFlowInstance.fitView()
}

function setGraph(graph) {
  // 外部整体替换图（撤销/重做/恢复版本），同步内部 elements 但不触发 update 回环
  const { nodes, edges } = graphToElements(graph || { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } })
  elements.value = [...nodes, ...edges]
  defaultViewport.value = (graph && graph.viewport) || { x: 0, y: 0, zoom: 1 }
}

function onNodesInitialized() {
  // 等节点初始化完成后再 fitView，避免初始节点位置未计算导致显示异常
  vueFlowInstance.fitView()
}

function addEdge(edge) {
  elements.value.push(edge)
  pushGraphUpdate()
}

defineExpose({ addNode, removeNode, updateNodeData, fitView, getGraph, syncFromGraph, applyLayout, setGraph, addEdge })
</script>

<style scoped>
.wf-canvas { width: 100%; height: 100%; position: relative; }

/* Dify 风格连线动画：运行态虚线流动 */
:deep(.vue-flow__edge-path) {
  stroke: var(--primary, #155EEF);
  stroke-width: 2;
  fill: none;
}
:deep(.vue-flow__edge.animated .vue-flow__edge-path) {
  stroke: #12B76A;
  stroke-dasharray: 5 5;
  animation: wf-dashflow 0.5s linear infinite;
}
@keyframes wf-dashflow {
  to { stroke-dashoffset: -10; }
}
:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: var(--primary, #155EEF);
  stroke-width: 2.5;
}

/* 节点手柄（Handle）对齐 Dify：小圆点 + 白色边框 */
:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: #fff;
  border: 2px solid var(--primary, #155EEF);
  border-radius: 50%;
  transition: background 0.15s, border-color 0.15s;
}
:deep(.vue-flow__handle:hover) {
  background: var(--primary, #155EEF);
}
:deep(.vue-flow__handle.connectingto) {
  background: var(--primary, #155EEF);
}
:deep(.vue-flow__handle-top) { top: -5px; }
:deep(.vue-flow__handle-bottom) { bottom: -5px; }
:deep(.vue-flow__handle-left) { left: -5px; }
:deep(.vue-flow__handle-right) { right: -5px; }

/* 连线中点插入按钮（Dify 风格 + 号） */
:deep(.vue-flow__edgebutton) {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--primary, #155EEF);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
:deep(.vue-flow__edgebutton:hover) {
  background: #0B4CD3;
}

/* 选中态节点浮层效果 */
:deep(.vue-flow__node.selected) {
  z-index: 10 !important;
}

/* MiniMap 对齐 Dify 配色 */
:deep(.vue-flow__minimap) {
  background: #F2F4F7;
  border-radius: 8px;
  overflow: hidden;
}
:deep(.vue-flow__minimap-mask) {
  fill: rgba(29, 33, 41, 0.45);
}
:deep(.vue-flow__minimap-node) {
  fill: var(--primary, #155EEF);
  opacity: 0.7;
}

/* Controls 对齐 Dify */
:deep(.vue-flow__controls) {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(29, 33, 41, 0.1);
}
:deep(.vue-flow__controls-button) {
  width: 28px;
  height: 28px;
  background: #fff;
  border-bottom: 1px solid #E5E6EB;
  color: #475467;
}
:deep(.vue-flow__controls-button:hover) {
  background: #F2F4F7;
}
:deep(.vue-flow__controls-button svg) {
  fill: currentColor;
}
</style>

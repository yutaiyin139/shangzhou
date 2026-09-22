<template>
  <div
    class="pp-resize-handle"
    @mousedown="onMouseDown"
    @touchstart="onTouchStart"
  >
    <div class="pp-resize-handle-bar"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['resize'])

const isDragging = ref(false)
const startX = ref(0)
const startWidth = ref(0)

function onMouseDown(e) {
  isDragging.value = true
  startX.value = e.clientX
  startWidth.value = 420 // 默认面板宽度
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  e.preventDefault()
}

function onTouchStart(e) {
  isDragging.value = true
  startX.value = e.touches[0].clientX
  startWidth.value = 420
  document.addEventListener('touchmove', onTouchMove)
  document.addEventListener('touchend', onTouchEnd)
  e.preventDefault()
}

function onMouseMove(e) {
  if (!isDragging.value) return
  const delta = startX.value - e.clientX // 向左拖 = 变宽
  const newWidth = Math.max(400, Math.min(720, startWidth.value + delta))
  emit('resize', newWidth)
}

function onTouchMove(e) {
  if (!isDragging.value) return
  const delta = startX.value - e.touches[0].clientX
  const newWidth = Math.max(400, Math.min(720, startWidth.value + delta))
  emit('resize', newWidth)
}

function onMouseUp() {
  isDragging.value = false
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

function onTouchEnd() {
  isDragging.value = false
  document.removeEventListener('touchmove', onTouchMove)
  document.removeEventListener('touchend', onTouchEnd)
}
</script>

<style scoped>
.pp-resize-handle {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.pp-resize-handle-bar {
  width: 2px;
  height: 40px;
  border-radius: 1px;
  background: #D0D5DD;
  transition: background 0.15s, height 0.15s;
}
.pp-resize-handle:hover .pp-resize-handle-bar,
.pp-resize-handle:active .pp-resize-handle-bar {
  background: #155EEF;
  height: 100%;
}
</style>

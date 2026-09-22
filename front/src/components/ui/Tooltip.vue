<template>
  <div class="ui-tooltip-wrapper" @mouseenter="showTip" @mouseleave="hideTip">
    <slot />
    <transition name="tooltip">
      <div
        v-if="visible"
        class="ui-tooltip"
        :class="`ui-tooltip--${placement}`"
        :style="tipStyle"
      >
        <slot name="content">{{ content }}</slot>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  content: { type: String, default: '' },
  placement: { type: String, default: 'top' }, // top | bottom | left | right
  delay: { type: Number, default: 200 },
})

const visible = ref(false)
const triggerRef = ref(null)
let showTimer = null

const tipStyle = computed(() => {
  return {}
})

function showTip() {
  showTimer = setTimeout(() => {
    visible.value = true
  }, props.delay)
}

function hideTip() {
  if (showTimer) clearTimeout(showTimer)
  visible.value = false
}
</script>

<style scoped>
.ui-tooltip-wrapper {
  position: relative;
  display: inline-flex;
}

.ui-tooltip {
  position: absolute;
  z-index: 1000;
  padding: 6px 10px;
  background: #1f2937;
  color: #fff;
  font-size: 12px;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  line-height: 1.4;
}

.ui-tooltip--top {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 6px;
}
.ui-tooltip--bottom {
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 6px;
}
.ui-tooltip--left {
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-right: 6px;
}
.ui-tooltip--right {
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-left: 6px;
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}
.tooltip-enter-from.ui-tooltip--top,
.tooltip-leave-to.ui-tooltip--top {
  transform: translateX(-50%) translateY(4px);
}
.tooltip-enter-from.ui-tooltip--bottom,
.tooltip-leave-to.ui-tooltip--bottom {
  transform: translateX(-50%) translateY(-4px);
}
</style>

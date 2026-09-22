<template>
  <div class="bar-chart">
    <svg :viewBox="`0 0 ${width} ${height}`" :style="{ width: '100%', height: height + 'px' }">
      <!-- Y轴网格线 -->
      <line
        v-for="i in 5"
        :key="'grid-' + i"
        :x1="padding.left"
        :y1="padding.top + (chartHeight / 4) * (i - 1)"
        :x2="width - padding.right"
        :y2="padding.top + (chartHeight / 4) * (i - 1)"
        stroke="var(--border)"
        stroke-dasharray="3,3"
      />
      <!-- 柱状 -->
      <rect
        v-for="(bar, idx) in bars"
        :key="'bar-' + idx"
        :x="bar.x"
        :y="bar.y"
        :width="barWidth"
        :height="bar.height"
        rx="3"
        fill="var(--primary)"
        fill-opacity="0.8"
      >
        <title>{{ data[idx]?.label }}: {{ data[idx]?.value }}ms</title>
      </rect>
      <!-- X轴标签 -->
      <text
        v-for="(bar, idx) in bars"
        :key="'xlabel-' + idx"
        :x="bar.x + barWidth / 2"
        :y="height - 4"
        text-anchor="middle"
        font-size="9"
        fill="var(--text-4)"
      >{{ data[idx]?.label?.slice(0, 8) || '' }}</text>
      <!-- Y轴标签 -->
      <text
        v-for="(val, idx) in yLabels"
        :key="'ylabel-' + idx"
        :x="padding.left - 6"
        :y="padding.top + (chartHeight / 4) * idx + 4"
        text-anchor="end"
        font-size="10"
        fill="var(--text-4)"
      >{{ val }}</text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{label, value}]
  height: { type: Number, default: 200 },
})

const width = 500
const padding = { top: 20, right: 20, bottom: 30, left: 50 }
const chartWidth = computed(() => width - padding.left - padding.right)
const chartHeight = computed(() => props.height - padding.top - padding.bottom)

const maxValue = computed(() => {
  if (props.data.length === 0) return 1000
  const max = Math.max(...props.data.map(d => d.value || 0))
  return max > 0 ? max * 1.1 : 1000
})

const barWidth = computed(() => {
  if (props.data.length === 0) return 20
  const total = chartWidth.value / props.data.length
  return Math.max(8, Math.min(40, total * 0.7))
})

const bars = computed(() => {
  if (props.data.length === 0) return []
  const total = chartWidth.value / props.data.length
  return props.data.map((d, i) => {
    const h = ((d.value || 0) / maxValue.value) * chartHeight.value
    return {
      x: padding.left + total * i + (total - barWidth.value) / 2,
      y: padding.top + chartHeight.value - h,
      height: h,
    }
  })
})

const yLabels = computed(() => {
  const labels = []
  for (let i = 0; i < 5; i++) {
    const val = (maxValue.value / 4) * (4 - i)
    labels.push(val >= 1000 ? (val / 1000).toFixed(1) + 's' : Math.round(val) + 'ms')
  }
  return labels
})
</script>

<style scoped>
.bar-chart {
  width: 100%;
}
</style>

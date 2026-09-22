<template>
  <div class="line-chart">
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
      <!-- 折线 -->
      <polyline
        v-if="points.length > 1"
        :points="pointsStr"
        fill="none"
        stroke="var(--primary)"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- 填充区域 -->
      <polygon
        v-if="points.length > 1"
        :points="areaPointsStr"
        fill="var(--primary)"
        fill-opacity="0.1"
      />
      <!-- 数据点 -->
      <circle
        v-for="(pt, idx) in points"
        :key="'pt-' + idx"
        :cx="pt.x"
        :cy="pt.y"
        r="3"
        fill="var(--primary)"
        stroke="var(--panel)"
        stroke-width="2"
      >
        <title>{{ data[idx]?.label }}: {{ data[idx]?.value }}</title>
      </circle>
      <!-- X轴标签 -->
      <text
        v-for="(pt, idx) in xLabels"
        :key="'xlabel-' + idx"
        :x="pt.x"
        :y="height - 4"
        text-anchor="middle"
        font-size="10"
        fill="var(--text-4)"
      >{{ pt.label }}</text>
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
  if (props.data.length === 0) return 100
  const max = Math.max(...props.data.map(d => d.value || 0))
  return max > 0 ? max * 1.1 : 100
})

const points = computed(() => {
  if (props.data.length === 0) return []
  const step = props.data.length > 1 ? chartWidth.value / (props.data.length - 1) : chartWidth.value
  return props.data.map((d, i) => ({
    x: padding.left + step * i,
    y: padding.top + chartHeight.value - ((d.value || 0) / maxValue.value) * chartHeight.value,
  }))
})

const pointsStr = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

const areaPointsStr = computed(() => {
  if (points.value.length === 0) return ''
  const bottom = padding.top + chartHeight.value
  const first = points.value[0]
  const last = points.value[points.value.length - 1]
  return `${first.x},${bottom} ${pointsStr.value} ${last.x},${bottom}`
})

const xLabels = computed(() => {
  if (props.data.length === 0) return []
  const step = Math.max(1, Math.floor(props.data.length / 6))
  const totalStep = chartWidth.value / Math.max(1, props.data.length - 1)
  return props.data
    .map((d, i) => ({ idx: i, label: d?.label || '', x: padding.left + totalStep * i }))
    .filter((_, i) => i % step === 0 || i === props.data.length - 1)
})

const yLabels = computed(() => {
  const labels = []
  for (let i = 0; i < 5; i++) {
    const val = (maxValue.value / 4) * (4 - i)
    labels.push(val >= 1000 ? (val / 1000).toFixed(1) + 'k' : Math.round(val))
  }
  return labels
})
</script>

<style scoped>
.line-chart {
  width: 100%;
}
</style>

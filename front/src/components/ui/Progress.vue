<template>
  <div class="ui-progress" :class="`ui-progress--${type}`">
    <div v-if="showInfo && type === 'line'" class="ui-progress__info">
      <span class="ui-progress__text">{{ text }}</span>
      <span class="ui-progress__percent">{{ percent }}%</span>
    </div>
    <div class="ui-progress__track">
      <div
        class="ui-progress__bar"
        :class="`ui-progress__bar--${status}`"
        :style="{ width: `${Math.min(100, Math.max(0, percent))}%` }"
      >
        <div v-if="animated && percent < 100" class="ui-progress__bar--striped"></div>
      </div>
    </div>
    <div v-if="type === 'circle'" class="ui-progress__circle-info">
      <slot>
        <span class="ui-progress__percent">{{ percent }}%</span>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  percent: { type: Number, default: 0 },
  type: { type: String, default: 'line' }, // line | circle
  status: { type: String, default: 'default' }, // default | success | warning | error
  showInfo: { type: Boolean, default: true },
  text: { type: String, default: '' },
  animated: { type: Boolean, default: false },
  strokeWidth: { type: Number, default: 8 },
})
</script>

<style scoped>
.ui-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ui-progress__info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ui-progress__text {
  font-size: 13px;
  color: var(--text-2);
}

.ui-progress__percent {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-1);
}

.ui-progress__track {
  width: 100%;
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  overflow: hidden;
}

.ui-progress__bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.ui-progress__bar--default {
  background: var(--primary);
}
.ui-progress__bar--success {
  background: #16a34a;
}
.ui-progress__bar--warning {
  background: #d97706;
}
.ui-progress__bar--error {
  background: #dc2626;
}

.ui-progress__bar--striped {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 16px 16px;
  animation: progress-stripe 1s linear infinite;
}

@keyframes progress-stripe {
  from { background-position: 0 0; }
  to { background-position: 16px 0; }
}

/* Circle type */
.ui-progress--circle {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.ui-progress--circle .ui-progress__track {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: conic-gradient(var(--primary) calc(var(--percent) * 1%), var(--border-light) 0);
}

.ui-progress__circle-info {
  font-size: 14px;
}
</style>

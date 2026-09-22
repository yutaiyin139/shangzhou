<template>
  <div class="thought-chain">
    <div class="tc-header" @click="expanded = !expanded">
      <svg class="tc-icon" :class="{expanded}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke-linecap="round"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
      <span class="tc-title">思考过程</span>
      <span class="tc-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>

    <div v-if="expanded" class="tc-body">
      <div v-for="(step, idx) in steps" :key="idx" class="tc-step">
        <div class="tc-step-line">
          <div class="tc-dot" :class="step.type"></div>
          <div v-if="idx < steps.length - 1" class="tc-connector"></div>
        </div>
        <div class="tc-step-content">
          <div class="tc-step-header">
            <span class="tc-step-type" :class="step.type">{{ typeLabel(step.type) }}</span>
            <span class="tc-step-time" v-if="step.duration">{{ step.duration }}ms</span>
          </div>
          <div class="tc-step-text">{{ step.content }}</div>
          <div v-if="step.tool" class="tc-tool-call">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 3v4a1 1 0 001 1h4"/><path d="M17 21H7a2 2 0 01-2-2V5a2 2 0 012-2h7l5 5v11a2 2 0 01-2 2z"/></svg>
            <span class="tc-tool-name">{{ step.tool }}</span>
            <span v-if="step.tool_input" class="tc-tool-input">{{ step.tool_input }}</span>
          </div>
          <div v-if="step.observation" class="tc-observation">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
            <span>{{ step.observation }}</span>
          </div>
        </div>
      </div>

      <div v-if="steps.length === 0" class="tc-empty">
        暂无思考过程记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  steps: {
    type: Array,
    default: () => []
  }
})

const expanded = ref(true)

function typeLabel(type) {
  const labels = {
    'thinking': '思考',
    'action': '行动',
    'observation': '观察',
    'planning': '规划',
    'reflection': '反思',
    'answer': '回答'
  }
  return labels[type] || type
}
</script>

<style scoped>
.thought-chain {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  margin-bottom: 16px;
  overflow: hidden;
}

.tc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.tc-header:hover {
  background: var(--bg-page);
}

.tc-icon {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  transition: transform 0.2s;
}

.tc-icon.expanded {
  transform: rotate(90deg);
}

.tc-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  flex: 1;
}

.tc-toggle {
  font-size: 12px;
  color: var(--text-3);
}

.tc-body {
  padding: 0 16px 16px;
  border-top: 1px solid var(--border-light);
}

.tc-step {
  display: flex;
  gap: 12px;
  position: relative;
}

.tc-step-line {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 20px;
}

.tc-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-4);
  margin-top: 14px;
  flex-shrink: 0;
}

.tc-dot.thinking { background: var(--purple); }
.tc-dot.action { background: var(--primary); }
.tc-dot.observation { background: var(--green); }
.tc-dot.planning { background: var(--orange); }
.tc-dot.reflection { background: #722ED1; }
.tc-dot.answer { background: var(--green); }

.tc-connector {
  width: 2px;
  flex: 1;
  background: var(--border-light);
  margin-top: 4px;
}

.tc-step-content {
  flex: 1;
  padding: 12 0;
  min-width: 0;
}

.tc-step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.tc-step-type {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.tc-step-type.thinking { background: var(--purple-bg); color: var(--purple); }
.tc-step-type.action { background: var(--primary-light); color: var(--primary); }
.tc-step-type.observation { background: var(--green-bg); color: var(--green); }
.tc-step-type.planning { background: var(--orange-bg); color: var(--orange); }
.tc-step-type.reflection { background: var(--purple-bg); color: var(--purple); }
.tc-step-type.answer { background: var(--green-bg); color: var(--green); }

.tc-step-time {
  font-size: 11px;
  color: var(--text-4);
}

.tc-step-text {
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.6;
  word-break: break-word;
}

.tc-tool-call {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--bg-page);
  border-radius: 6px;
  font-size: 12px;
}

.tc-tool-call svg {
  width: 14px;
  height: 14px;
  color: var(--text-3);
  flex-shrink: 0;
}

.tc-tool-name {
  font-weight: 500;
  color: var(--text-1);
}

.tc-tool-input {
  color: var(--text-3);
  font-family: monospace;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.tc-observation {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--green-bg);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-2);
}

.tc-observation svg {
  width: 14px;
  height: 14px;
  color: var(--green);
  flex-shrink: 0;
  margin-top: 2px;
}

.tc-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-4);
  font-size: 13px;
}
</style>

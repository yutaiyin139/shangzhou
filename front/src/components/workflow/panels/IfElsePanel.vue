<template>
  <div>
    <div class="pp-section-title">分支</div>
    <div v-for="(c, i) in local.cases" :key="c.id || i" class="pp-card">
      <div class="pp-card-head">
        <span>{{ c.name || '分支' }}</span>
      </div>
      <div class="pp-field">
        <label>条件</label>
        <div v-if="!c.conditions || c.conditions.length === 0" class="pp-hint">
          未设置条件（此分支将作为兜底分支）
        </div>
        <div v-for="(cond, ci) in (c.conditions || [])" :key="ci" class="cond-row">
          <select v-model="cond.variable" @change="commit" class="cond-select">
            <option value="">选择变量</option>
            <option v-for="v in availableVariables" :key="v" :value="v">{{ v }}</option>
          </select>
          <select v-model="cond.operator" @change="commit" class="cond-select">
            <option value="equals">等于</option>
            <option value="not_equals">不等于</option>
            <option value="contains">包含</option>
            <option value="not_contains">不包含</option>
            <option value="starts_with">开头是</option>
            <option value="ends_with">结尾是</option>
            <option value="greater_than">大于</option>
            <option value="less_than">小于</option>
            <option value="greater_equal">大于等于</option>
            <option value="less_equal">小于等于</option>
            <option value="is_empty">为空</option>
            <option value="is_not_empty">不为空</option>
            <option value="regex">正则匹配</option>
          </select>
          <input v-model="cond.value" @change="commit" placeholder="值" class="cond-input">
          <button class="cond-del" @click="removeCondition(i, ci)" title="删除条件">✕</button>
        </div>
        <button class="pp-add-btn cond-add" @click="addCondition(i)">+ 添加条件</button>
      </div>
    </div>
    <div class="pp-hint" style="line-height:1.6">
      条件分支按顺序评估，第一个满足条件的分支将被执行。<br>
      支持变量引用：选择上游节点的输出变量作为条件判断依据。<br>
      多个条件之间为 AND 逻辑（全部满足才走此分支）。
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const availableVariables = computed(() => {
  const vars = ['query', 'text', 'output', 'result', 'answer']
  if (local.value.cases) {
    local.value.cases.forEach((c) => {
      if (c.conditions) {
        c.conditions.forEach((cond) => {
          if (cond.variable && !vars.includes(cond.variable)) {
            vars.push(cond.variable)
          }
        })
      }
    })
  }
  return vars
})

function addCondition(caseIndex) {
  if (!Array.isArray(local.value.cases[caseIndex].conditions)) {
    local.value.cases[caseIndex].conditions = []
  }
  local.value.cases[caseIndex].conditions.push({ variable: '', operator: 'equals', value: '' })
  commit()
}

function removeCondition(caseIndex, conditionIndex) {
  if (Array.isArray(local.value.cases[caseIndex].conditions)) {
    local.value.cases[caseIndex].conditions.splice(conditionIndex, 1)
  }
  commit()
}
</script>

<style scoped>
.cond-row{ display: flex; gap: 4px; margin-bottom: 6px; align-items: center; }
.cond-select{ flex: 1; min-width: 0; border: 1px solid var(--border); border-radius: 6px; padding: 6px 4px; font-size: 12px; outline: none; background: #fff; }
.cond-input{ flex: 1; min-width: 0; border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font-size: 12px; outline: none; }
.cond-del{ border: none; background: none; color: var(--red); cursor: pointer; font-size: 14px; padding: 4px 6px; flex-shrink: 0; }
.cond-del:hover{ background: #FFF0F0; border-radius: 4px; }
.cond-add{ margin-top: 4px; font-size: 12px; }
</style>

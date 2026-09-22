<template>
  <div>
    <div class="pp-section-title">变量赋值</div>
    <div v-for="(v, i) in local.variables" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>赋值 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeArrayItem('variables', i)">删除</button>
      </div>
      <div class="pp-field">
        <label>目标变量</label>
        <input v-model="v.variable" @change="commit">
      </div>
      <div class="pp-field">
        <label>来源表达式</label>
        <input v-model="v.value" @change="commit" placeholder="如 {{#start.query#}}">
      </div>
    </div>
    <button class="pp-add-btn" @click="addAssign">+ 添加赋值</button>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit, removeArrayItem } = usePanelState(props, emit)

function addAssign() {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.push({ variable: '', value: '' })
  commit()
}
</script>

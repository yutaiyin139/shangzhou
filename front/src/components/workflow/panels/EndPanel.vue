<template>
  <div>
    <div class="pp-section-title">输出变量</div>
    <div v-for="(o, i) in local.outputs" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>输出 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeArrayItem('outputs', i)">删除</button>
      </div>
      <div class="pp-field">
        <label>变量名</label>
        <input v-model="o.variable" @change="commit">
      </div>
      <div class="pp-field">
        <label>取值表达式</label>
        <input v-model="o.value_selector" @change="commit" placeholder="如 {{#nodeId.text#}}">
      </div>
    </div>
    <button class="pp-add-btn" @click="addOutput">+ 添加输出</button>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit, removeArrayItem } = usePanelState(props, emit)

function addOutput() {
  if (!Array.isArray(local.value.outputs)) local.value.outputs = []
  local.value.outputs.push({ variable: '', value_selector: [] })
  commit()
}
</script>

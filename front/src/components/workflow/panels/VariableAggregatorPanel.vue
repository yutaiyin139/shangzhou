<template>
  <div>
    <div class="pp-field">
      <label>输出类型</label>
      <select v-model="local.output_type" @change="commit">
        <option value="object">对象（Object）</option>
        <option value="array">数组（Array）</option>
        <option value="string">字符串拼接（String）</option>
      </select>
      <div class="pp-hint">选择聚合后的输出格式</div>
    </div>
    <div v-if="local.output_type === 'string'" class="pp-field">
      <label>分隔符</label>
      <input v-model="local.separator" @change="commit" placeholder="如 , 或 / 或 换行">
      <div class="pp-hint">字符串拼接时的分隔符</div>
    </div>
    <div class="pp-section-title">聚合变量列表</div>
    <div v-for="(v, i) in local.variables" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>变量 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeAggregatorVariable(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>变量名</label>
        <input v-model="v.variable" @change="commit" placeholder="如 result, name">
      </div>
      <div class="pp-field">
        <label>变量选择器</label>
        <input v-model="v.value_selector_text" @change="commitValueSelector(v)" placeholder="如 node1.output 或 result">
        <div class="pp-hint">格式: 节点ID.输出变量名</div>
      </div>
      <div class="pp-field">
        <label>默认值</label>
        <input v-model="v.default" @change="commit" placeholder="变量不存在时的默认值">
      </div>
    </div>
    <button class="pp-add-btn" @click="addAggregatorVariable">+ 添加变量</button>
    <div class="pp-section-title">输出变量名</div>
    <div class="pp-field">
      <label>输出变量名</label>
      <input v-model="local.output" @change="commit" placeholder="aggregated_output">
      <div class="pp-hint">聚合结果保存到的变量名</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      变量聚合节点用于合并来自多个分支的变量。<br>
      1. 对象模式：{变量名: 值, ...}<br>
      2. 数组模式：[值1, 值2, ...]<br>
      3. 字符串模式：用分隔符拼接所有值
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

function addAggregatorVariable() {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.push({ variable: '', value_selector: [], value_selector_text: '', default: '' })
  commit()
}

function removeAggregatorVariable(index) {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.splice(index, 1)
  commit()
}

function commitValueSelector(v) {
  if (v.value_selector_text) {
    v.value_selector = v.value_selector_text.split('.').filter(Boolean)
  } else {
    v.value_selector = []
  }
  commit()
}
</script>

<template>
  <div>
    <div class="pp-field">
      <label>子工作流应用 ID</label>
      <input v-model="local.sub_app_id" @change="commit" placeholder="输入要调用的工作流应用 ID">
      <div class="pp-hint">要调用的子工作流应用 ID</div>
    </div>
    <div class="pp-field">
      <label>子工作流 ID（可选）</label>
      <input v-model="local.sub_workflow_id" @change="commit" placeholder="指定具体的工作流版本">
      <div class="pp-hint">留空则使用最新版本</div>
    </div>
    <div class="pp-section-title">输入映射</div>
    <div v-for="(m, i) in local.input_mapping" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>输入 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeSubGraphInput(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>变量名</label>
        <input v-model="m.variable" @change="commit" placeholder="子工作流中的变量名">
      </div>
      <div class="pp-field">
        <label>来源选择器</label>
        <input v-model="m.value_selector_text" @change="commitSubGraphInputSelector(m)" placeholder="如 start.query">
        <div class="pp-hint">格式: 节点ID.输出变量名</div>
      </div>
    </div>
    <button class="pp-add-btn" @click="addSubGraphInput">+ 添加输入映射</button>
    <div class="pp-section-title">输出映射</div>
    <div class="pp-hint" style="margin-bottom:8px">将子工作流输出映射到当前变量</div>
    <div v-for="(val, key) in local.output_mapping" :key="key" class="pp-card">
      <div class="pp-field">
        <label>子工作流输出键</label>
        <input :value="key" @change="updateSubGraphOutputKey(key, $event.target.value)" placeholder="如 result">
      </div>
      <div class="pp-field">
        <label>映射到变量</label>
        <input :value="val" @change="updateSubGraphOutputVal(key, $event.target.value)" placeholder="如 my_result">
      </div>
    </div>
    <div class="pp-field">
      <label>添加输出映射</label>
      <div class="pp-row">
        <input v-model="newOutputKey" placeholder="输出键">
        <input v-model="newOutputVal" placeholder="变量名">
        <button class="pp-add-btn" @click="addSubGraphOutput">添加</button>
      </div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      子工作流节点用于调用其他工作流作为子流程。<br>
      1. 输入映射：将当前变量传递给子工作流<br>
      2. 输出映射：将子工作流结果映射回当前上下文<br>
      3. 支持工作流复用和模块化设计
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const newOutputKey = ref('')
const newOutputVal = ref('')

function addSubGraphInput() {
  if (!Array.isArray(local.value.input_mapping)) local.value.input_mapping = []
  local.value.input_mapping.push({ variable: '', value_selector: [], value_selector_text: '' })
  commit()
}

function removeSubGraphInput(index) {
  if (!Array.isArray(local.value.input_mapping)) local.value.input_mapping = []
  local.value.input_mapping.splice(index, 1)
  commit()
}

function commitSubGraphInputSelector(m) {
  m.value_selector = m.value_selector_text ? m.value_selector_text.split('.').filter(Boolean) : []
  commit()
}

function updateSubGraphOutputKey(oldKey, newKey) {
  if (!local.value.output_mapping) local.value.output_mapping = {}
  const val = local.value.output_mapping[oldKey]
  delete local.value.output_mapping[oldKey]
  if (newKey) local.value.output_mapping[newKey] = val
  commit()
}

function updateSubGraphOutputVal(key, val) {
  if (!local.value.output_mapping) local.value.output_mapping = {}
  local.value.output_mapping[key] = val
  commit()
}

function addSubGraphOutput() {
  if (!local.value.output_mapping) local.value.output_mapping = {}
  if (newOutputKey.value) {
    local.value.output_mapping[newOutputKey.value] = newOutputVal.value
    newOutputKey.value = ''
    newOutputVal.value = ''
  }
  commit()
}
</script>

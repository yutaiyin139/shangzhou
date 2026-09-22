<template>
  <div>
    <div class="pp-field">
      <label>模型</label>
      <select v-model="modelKey" @change="commitModel">
        <option value="">请选择模型</option>
        <option v-for="m in models" :key="modelOptionKey(m)" :value="modelOptionKey(m)">
          {{ m.credential_name || m.provider }} / {{ m.model_name }}
        </option>
      </select>
      <div v-if="models.length === 0" class="pp-hint">暂无可用模型，请先在「模型」页面添加模型配置。</div>
    </div>
    <div class="pp-field">
      <label>Temperature</label>
      <input type="range" min="0" max="1" step="0.1" v-model.number="temperature" @change="commit">
      <span class="pp-range-val">{{ temperature }}</span>
      <div class="pp-hint">分类任务建议使用较低温度（0.1-0.3）以提高准确性</div>
    </div>
    <div class="pp-field">
      <label>查询变量选择器</label>
      <input v-model="classifierQuerySelector" @change="commitClassifierQuery" placeholder="如 start.query">
      <div class="pp-hint">选择要分类的输入变量</div>
    </div>
    <div class="pp-section-title">分类类别</div>
    <div v-for="(c, i) in local.classes" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>类别 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeClassifierClass(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>类别 ID</label>
        <input v-model="c.id" @change="commit" placeholder="如 1, 2, 3">
      </div>
      <div class="pp-field">
        <label>类别标签</label>
        <input v-model="c.label" @change="commit" placeholder="如 技术支持, 销售咨询">
      </div>
      <div class="pp-field">
        <label>类别描述</label>
        <textarea v-model="c.name" rows="3" @change="commit" placeholder="描述该类别的特征和示例问题"></textarea>
      </div>
    </div>
    <button class="pp-add-btn" @click="addClassifierClass">+ 添加类别</button>
    <div class="pp-section-title">输出变量名</div>
    <div class="pp-field">
      <label>输出变量名</label>
      <input v-model="local.output" @change="commit" placeholder="classification">
      <div class="pp-hint">分类结果保存到的变量名</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      问题分类节点使用 LLM 对输入进行智能分类。<br>
      1. 定义多个分类类别（含标签和描述）<br>
      2. LLM 根据描述将输入分配到最匹配的类别<br>
      3. 分类结果包含 class_id、class_label、class_index<br>
      4. 可配合条件分支节点实现不同类别走不同流程
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, models, modelKey, temperature,
  commitModel, modelOptionKey,
} = usePanelState(props, emit)

const classifierQuerySelector = computed({
  get: () => {
    const sel = local.value.query_variable_selector || []
    return sel.join('.')
  },
  set: (val) => {
    local.value.query_variable_selector = val ? val.split('.').filter(Boolean) : []
  }
})

function commitClassifierQuery() {
  if (classifierQuerySelector.value) {
    local.value.query_variable_selector = classifierQuerySelector.value.split('.').filter(Boolean)
  } else {
    local.value.query_variable_selector = []
  }
  commit()
}

function addClassifierClass() {
  if (!Array.isArray(local.value.classes)) local.value.classes = []
  const newId = String((local.value.classes.length + 1))
  local.value.classes.push({ id: newId, label: '', name: '' })
  commit()
}

function removeClassifierClass(index) {
  if (!Array.isArray(local.value.classes)) local.value.classes = []
  local.value.classes.splice(index, 1)
  commit()
}
</script>

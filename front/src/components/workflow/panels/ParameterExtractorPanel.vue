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
      <div class="pp-hint">参数提取建议使用较低温度（0.1-0.3）以提高准确性</div>
    </div>
    <div class="pp-field">
      <label>输入文本变量选择器</label>
      <input v-model="extractorQuerySelector" @change="commitExtractorQuery" placeholder="如 start.query">
      <div class="pp-hint">选择要提取参数的输入文本变量</div>
    </div>
    <div class="pp-section-title">提取参数定义</div>
    <div v-for="(p, i) in local.parameters" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>参数 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeExtractorParam(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>参数名</label>
        <input v-model="p.name" @change="commit" placeholder="如 order_id, name">
      </div>
      <div class="pp-field">
        <label>参数描述</label>
        <textarea v-model="p.description" rows="2" @change="commit" placeholder="描述该参数的含义和提取规则"></textarea>
      </div>
      <div class="pp-field">
        <label>类型</label>
        <select v-model="p.type" @change="commit">
          <option value="string">字符串</option>
          <option value="number">数字</option>
          <option value="integer">整数</option>
          <option value="boolean">布尔值</option>
          <option value="array">数组</option>
        </select>
      </div>
      <div class="pp-field pp-check">
        <label><input type="checkbox" v-model="p.required" @change="commit"> 必填</label>
      </div>
    </div>
    <button class="pp-add-btn" @click="addExtractorParam">+ 添加参数</button>
    <div class="pp-section-title">输出变量名</div>
    <div class="pp-field">
      <label>输出变量名</label>
      <input v-model="local.output" @change="commit" placeholder="extracted_params">
      <div class="pp-hint">提取结果保存到的变量名</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      参数提取节点使用 LLM 从文本中提取结构化参数。<br>
      1. 定义要提取的参数（名称、描述、类型）<br>
      2. LLM 从输入文本中提取对应的值<br>
      3. 支持类型：字符串、数字、整数、布尔值、数组<br>
      4. 必填参数缺失时会记录在 missing_required 中
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

const extractorQuerySelector = computed({
  get: () => {
    const sel = local.value.query || []
    return sel.join('.')
  },
  set: (val) => {
    local.value.query = val ? val.split('.').filter(Boolean) : []
  }
})

function commitExtractorQuery() {
  if (extractorQuerySelector.value) {
    local.value.query = extractorQuerySelector.value.split('.').filter(Boolean)
  } else {
    local.value.query = []
  }
  commit()
}

function addExtractorParam() {
  if (!Array.isArray(local.value.parameters)) local.value.parameters = []
  local.value.parameters.push({ name: '', description: '', type: 'string', required: false })
  commit()
}

function removeExtractorParam(index) {
  if (!Array.isArray(local.value.parameters)) local.value.parameters = []
  local.value.parameters.splice(index, 1)
  commit()
}
</script>

<template>
  <div>
    <div class="pp-field">
      <label>模板内容</label>
      <textarea v-model="local.template" rows="6" @change="commit" placeholder="输入模板，使用 {{变量名}} 引用变量"></textarea>
      <div class="pp-hint">支持 {{variable}} 和 <code v-pre>{{#node.variable#}}</code> 语法</div>
    </div>
    <div class="pp-section-title">变量映射</div>
    <div v-for="(v, i) in local.variables" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>变量 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeTemplateVar(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>变量名</label>
        <input v-model="v.variable" @change="commit" placeholder="如 title, content">
      </div>
      <div class="pp-field">
        <label>变量选择器</label>
        <input v-model="v.value_selector_text" @change="commitTemplateVarSelector(v)" placeholder="如 start.query">
        <div class="pp-hint">格式: 节点ID.变量名</div>
      </div>
    </div>
    <button class="pp-add-btn" @click="addTemplateVar">+ 添加变量</button>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      模板转换节点使用模板格式化输出文本。<br>
      1. 使用 <code v-pre>{{变量名}}</code> 语法引用变量<br>
      2. 支持 <code v-pre>{{#node.variable#}}</code> 直接引用<br>
      3. 适用于生成报告、格式化输出等场景
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

function addTemplateVar() {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.push({ variable: '', value_selector: [], value_selector_text: '' })
  commit()
}

function removeTemplateVar(index) {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.splice(index, 1)
  commit()
}

function commitTemplateVarSelector(v) {
  if (v.value_selector_text) {
    v.value_selector = v.value_selector_text.split('.').filter(Boolean)
  } else {
    v.value_selector = []
  }
  commit()
}
</script>

<template>
  <div>
    <div class="pp-section-title">输入变量</div>
    <div v-for="(v, i) in local.variables" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>变量 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeArrayItem('variables', i)">删除</button>
      </div>
      <div class="pp-field">
        <label>变量名</label>
        <input v-model="v.variable" @change="commit">
      </div>
      <div class="pp-field">
        <label>类型</label>
        <select v-model="v.type" @change="commit">
          <option value="string">文本</option>
          <option value="number">数字</option>
          <option value="file">文件</option>
          <option value="paragraph">段落</option>
        </select>
      </div>
      <div class="pp-field">
        <label>显示名称</label>
        <input v-model="v.label" @change="commit">
      </div>
      <div class="pp-field pp-check">
        <label><input type="checkbox" v-model="v.required" @change="commit"> 必填</label>
      </div>
    </div>
    <button class="pp-add-btn" @click="addVariable">+ 添加变量</button>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit, removeArrayItem } = usePanelState(props, emit)

function addVariable() {
  if (!Array.isArray(local.value.variables)) local.value.variables = []
  local.value.variables.push({ variable: '', label: '', type: 'paragraph', required: true })
  commit()
}
</script>

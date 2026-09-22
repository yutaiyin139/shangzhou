<template>
  <div>
    <div class="pp-field">
      <label>提示信息</label>
      <textarea v-model="local.message" rows="3" @change="commit" placeholder="显示给用户的提示信息"></textarea>
    </div>
    <div class="pp-section-title">表单字段</div>
    <div v-for="(f, i) in local.form_fields" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>字段 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeFormField(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>字段名</label>
        <input v-model="f.name" @change="commit" placeholder="如 name, email">
      </div>
      <div class="pp-field">
        <label>显示标签</label>
        <input v-model="f.label" @change="commit" placeholder="如 姓名, 邮箱">
      </div>
      <div class="pp-field">
        <label>类型</label>
        <select v-model="f.type" @change="commit">
          <option value="text">文本</option>
          <option value="textarea">多行文本</option>
          <option value="number">数字</option>
          <option value="select">下拉选择</option>
          <option value="checkbox">复选框</option>
        </select>
      </div>
      <div class="pp-field">
        <label>占位符</label>
        <input v-model="f.placeholder" @change="commit" placeholder="输入提示">
      </div>
      <div class="pp-field pp-check">
        <label><input type="checkbox" v-model="f.required" @change="commit"> 必填</label>
      </div>
      <div v-if="f.type === 'select'" class="pp-field">
        <label>选项（每行一个）</label>
        <textarea v-model="f.options_text" @change="commitSelectOptions(f)" rows="3" placeholder="选项1&#10;选项2&#10;选项3"></textarea>
      </div>
    </div>
    <button class="pp-add-btn" @click="addFormField">+ 添加字段</button>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      Human Input 节点会暂停工作流执行，等待用户填写表单。<br>
      1. 用户填写表单并提交<br>
      2. 工作流从暂停处继续执行<br>
      3. 表单数据可通过变量访问
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

function addFormField() {
  if (!Array.isArray(local.value.form_fields)) local.value.form_fields = []
  local.value.form_fields.push({ name: '', label: '', type: 'text', placeholder: '', required: false })
  commit()
}

function removeFormField(index) {
  if (!Array.isArray(local.value.form_fields)) local.value.form_fields = []
  local.value.form_fields.splice(index, 1)
  commit()
}

function commitSelectOptions(f) {
  if (f.options_text) {
    f.options = f.options_text.split('\n').filter(Boolean)
  } else {
    f.options = []
  }
  commit()
}
</script>

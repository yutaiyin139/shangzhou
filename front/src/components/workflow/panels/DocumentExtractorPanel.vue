<template>
  <div>
    <div class="pp-field">
      <label>文件变量选择器</label>
      <input v-model="docExtractorSelector" @change="commitDocExtractor" placeholder="如 start.original_file">
      <div class="pp-hint">选择要提取文本的文件变量</div>
    </div>
    <div class="pp-field pp-check">
      <label><input type="checkbox" v-model="local.is_array_file" @change="commit"> 文件数组</label>
      <div class="pp-hint">勾选表示输入是文件数组</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      文档提取节点从上传的文件中提取文本内容。<br>
      1. 支持格式：TXT、MD、PDF、DOCX、CSV、JSON<br>
      2. 可处理单个文件或文件数组<br>
      3. 提取的文本可用于后续 LLM 分析或知识检索
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const docExtractorSelector = computed({
  get: () => {
    const sel = local.value.variable_selector || []
    return sel.join('.')
  },
  set: (val) => {
    local.value.variable_selector = val ? val.split('.').filter(Boolean) : []
  }
})

function commitDocExtractor() {
  if (docExtractorSelector.value) {
    local.value.variable_selector = docExtractorSelector.value.split('.').filter(Boolean)
  } else {
    local.value.variable_selector = []
  }
  commit()
}
</script>

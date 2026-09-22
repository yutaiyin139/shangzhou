<template>
  <div>
    <div class="pp-field">
      <label>目标知识库</label>
      <select v-model="local.dataset_id" @change="commit">
        <option value="">请选择知识库</option>
        <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
      <div v-if="datasets.length === 0" class="pp-hint">暂无知识库，请先在「知识库」页创建</div>
    </div>
    <div class="pp-field">
      <label>文本变量名</label>
      <input v-model="local.content_variable" @change="commit" placeholder="content">
      <div class="pp-hint">上游节点输出中用作索引内容的变量（缺省依次尝试 content/text/answer/result）</div>
    </div>
    <div class="pp-field">
      <label>文档名</label>
      <input v-model="local.document_name" @change="commit" placeholder="留空自动命名，支持 {{变量}}">
    </div>
    <div class="pp-section-title">分段设置</div>
    <div class="pp-field">
      <label>分段最大长度</label>
      <input type="number" v-model.number="local.max_length" @change="commit" min="256" max="8192">
    </div>
    <div class="pp-field">
      <label>分段重叠</label>
      <input type="number" v-model.number="local.overlap" @change="commit" min="0" max="512">
    </div>
    <div class="pp-field">
      <label>分隔符</label>
      <input v-model="local.delimiter" @change="commit" placeholder="\n">
    </div>
    <div class="pp-section-title">输出变量</div>
    <div class="pp-hint" style="line-height:1.6">
      document_id / segment_count / knowledge_index_status<br>
      文本将自动分段写入知识库并触发向量化，可在「知识库」页查看。
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit, datasets } = usePanelState(props, emit)
</script>

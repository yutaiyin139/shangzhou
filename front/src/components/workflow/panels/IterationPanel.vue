<template>
  <div>
    <div class="pp-field">
      <label>输入列表（变量选择器）</label>
      <input v-model="iterationInputSelector" @change="commitIterationInput" placeholder="如 items 或 start.items">
      <div class="pp-hint">选择要迭代的列表变量</div>
    </div>
    <div class="pp-field">
      <label>最大迭代次数</label>
      <input type="number" v-model.number="local.max_iterations" @change="commit" min="1" max="1000">
      <div class="pp-hint">安全限制，防止无限循环</div>
    </div>
    <div class="pp-field">
      <label>输出变量</label>
      <div class="pp-hint" style="margin-bottom:8px">从迭代结果中提取的变量</div>
      <div v-for="(o, i) in local.output_selector" :key="i" class="pp-card">
        <div class="pp-card-head">
          <span>输出 {{ i + 1 }}</span>
          <button class="pp-card-del" @click="removeOutputSelector(i)">删除</button>
        </div>
        <div class="pp-field">
          <label>变量名</label>
          <input v-model="o.variable" @change="commit" placeholder="如 result">
        </div>
      </div>
      <button class="pp-add-btn" @click="addOutputSelector">+ 添加输出变量</button>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      迭代节点会对输入列表中的每个元素执行子流程。<br>
      1. 将子流程节点连接到迭代节点的「loop」输出口<br>
      2. 子流程中可使用 <code>item</code> 访问当前元素<br>
      3. 迭代结果会聚合为列表输出
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const iterationInputSelector = computed({
  get: () => {
    const sel = local.value.input_selector || []
    return sel.join('.')
  },
  set: (val) => {
    local.value.input_selector = val ? val.split('.').filter(Boolean) : []
  }
})

function commitIterationInput() {
  commit()
}

function addOutputSelector() {
  if (!Array.isArray(local.value.output_selector)) local.value.output_selector = []
  local.value.output_selector.push({ variable: '' })
  commit()
}

function removeOutputSelector(index) {
  if (!Array.isArray(local.value.output_selector)) local.value.output_selector = []
  local.value.output_selector.splice(index, 1)
  commit()
}
</script>

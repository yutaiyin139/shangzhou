<template>
  <div>
    <div class="pp-field">
      <label>循环类型</label>
      <select v-model="local.loop_type" @change="commit">
        <option value="count">按次数循环</option>
        <option value="condition">按条件循环</option>
        <option value="infinite">无限循环（需内部 break）</option>
      </select>
      <div class="pp-hint">选择循环的执行方式</div>
    </div>
    <div v-if="local.loop_type === 'count'" class="pp-field">
      <label>循环次数</label>
      <input type="number" v-model.number="local.count" @change="commit" min="0" max="1000">
      <div class="pp-hint">循环执行的次数</div>
    </div>
    <div v-if="local.loop_type === 'condition'" class="pp-field">
      <label>循环条件变量</label>
      <input v-model="loopConditionVar" @change="commitLoopCondition" placeholder="如 start.running">
      <div class="pp-hint">条件为真时继续循环</div>
    </div>
    <div v-if="local.loop_type === 'condition'" class="pp-field">
      <label>条件操作符</label>
      <select v-model="local.condition.operator" @change="commit">
        <option value="equals">等于</option>
        <option value="not_equals">不等于</option>
        <option value="greater_than">大于</option>
        <option value="less_than">小于</option>
        <option value="is_not_empty">不为空</option>
      </select>
    </div>
    <div v-if="local.loop_type === 'condition'" class="pp-field">
      <label>条件值</label>
      <input v-model="local.condition.value" @change="commit" placeholder="比较值">
    </div>
    <div class="pp-field">
      <label>最大迭代次数</label>
      <input type="number" v-model.number="local.max_iterations" @change="commit" min="1" max="1000">
      <div class="pp-hint">安全限制，防止无限循环</div>
    </div>
    <div class="pp-field">
      <label>输出变量名</label>
      <input v-model="local.output_variable" @change="commit" placeholder="loop_results">
      <div class="pp-hint">循环结果保存到的变量名</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      循环节点支持三种模式：<br>
      1. 按次数：固定执行 N 次<br>
      2. 按条件：条件为真时继续<br>
      3. 无限循环：需内部 break 退出<br>
      循环中可使用 <code>_loop.index</code> 访问当前索引
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const loopConditionVar = computed({
  get: () => {
    const sel = local.value.condition?.variable || []
    return Array.isArray(sel) ? sel.join('.') : (sel || '')
  },
  set: (val) => {
    if (!local.value.condition) local.value.condition = {}
    local.value.condition.variable = val ? val.split('.').filter(Boolean) : []
  }
})

function commitLoopCondition() {
  commit()
}
</script>

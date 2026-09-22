<template>
  <div>
    <div class="pp-field">
      <label>输入列表选择器</label>
      <input v-model="listOpSelector" @change="commitListOp" placeholder="如 node1.items">
      <div class="pp-hint">选择要操作的列表变量</div>
    </div>
    <div class="pp-field">
      <label>变量类型</label>
      <select v-model="local.var_type" @change="commit">
        <option value="array[string]">字符串数组</option>
        <option value="array[number]">数字数组</option>
        <option value="array[file]">文件数组</option>
        <option value="array[object]">对象数组</option>
      </select>
    </div>
    <div class="pp-section-title">过滤条件</div>
    <div class="pp-field pp-check">
      <label><input type="checkbox" v-model="local.filter_by.enabled" @change="commit"> 启用过滤</label>
    </div>
    <div v-if="local.filter_by && local.filter_by.enabled">
      <div class="pp-field">
        <label>字段名</label>
        <input v-model="local.filter_by.key" @change="commit" placeholder="如 name, type">
      </div>
      <div class="pp-field">
        <label>操作符</label>
        <select v-model="local.filter_by.operator" @change="commit">
          <option value="contains">包含</option>
          <option value="not_contains">不包含</option>
          <option value="equals">等于</option>
          <option value="not_equals">不等于</option>
          <option value="starts_with">开头是</option>
          <option value="ends_with">结尾是</option>
          <option value="regex">正则匹配</option>
        </select>
      </div>
      <div class="pp-field">
        <label>值</label>
        <input v-model="local.filter_by.value" @change="commit" placeholder="过滤值">
      </div>
    </div>
    <div class="pp-section-title">排序</div>
    <div class="pp-field pp-check">
      <label><input type="checkbox" v-model="local.sort_by.enabled" @change="commit"> 启用排序</label>
    </div>
    <div v-if="local.sort_by && local.sort_by.enabled">
      <div class="pp-field">
        <label>排序字段</label>
        <input v-model="local.sort_by.key" @change="commit" placeholder="如 name, date">
      </div>
      <div class="pp-field">
        <label>排序方式</label>
        <select v-model="local.sort_by.value" @change="commit">
          <option value="asc">升序</option>
          <option value="desc">降序</option>
        </select>
      </div>
    </div>
    <div class="pp-section-title">提取字段</div>
    <div class="pp-field pp-check">
      <label><input type="checkbox" v-model="local.extract_by.enabled" @change="commit"> 启用提取</label>
    </div>
    <div v-if="local.extract_by && local.extract_by.enabled">
      <div class="pp-field">
        <label>提取字段</label>
        <input v-model="local.extract_by.key" @change="commit" placeholder="如 id, name">
      </div>
    </div>
    <div class="pp-section-title">数量限制</div>
    <div class="pp-field">
      <label>限制数量</label>
      <input type="number" v-model.number="local.limit" @change="commit" min="0" placeholder="0 表示不限制">
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      列表操作节点对列表数据进行过滤、排序、提取。<br>
      1. 过滤：按条件筛选列表项<br>
      2. 排序：按字段升序/降序排列<br>
      3. 提取：从对象数组中提取指定字段<br>
      4. 限制：限制返回数量
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const listOpSelector = computed({
  get: () => {
    const sel = local.value.variable || []
    return sel.join('.')
  },
  set: (val) => {
    local.value.variable = val ? val.split('.').filter(Boolean) : []
  }
})

function commitListOp() {
  if (listOpSelector.value) {
    local.value.variable = listOpSelector.value.split('.').filter(Boolean)
  } else {
    local.value.variable = []
  }
  commit()
}
</script>

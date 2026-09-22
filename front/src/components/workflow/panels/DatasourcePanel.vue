<template>
  <div>
    <div class="pp-field">
      <label>来源类型</label>
      <select v-model="local.source_type" @change="commit">
        <option value="builtin">内置数据源</option>
        <option value="connector">自定义连接器</option>
      </select>
    </div>
    <template v-if="local.source_type === 'builtin'">
      <div class="pp-field">
        <label>数据源</label>
        <select v-model="local.source_key" @change="commit">
          <option value="">请选择数据源</option>
          <option v-for="s in builtinSources" :key="s.key" :value="s.key">
            {{ s.icon }} {{ s.name }}<template v-if="!s.supported">（暂不支持）</template>
          </option>
        </select>
        <div v-if="builtinSources.length === 0" class="pp-hint">未获取到数据源列表</div>
      </div>
      <div class="pp-field">
        <label>操作</label>
        <select v-model="local.operation" @change="commit">
          <option value="search">搜索</option>
          <option value="list">列表</option>
          <option value="fetch">抓取（需 URL）</option>
        </select>
      </div>
    </template>
    <template v-else>
      <div class="pp-field">
        <label>连接器</label>
        <select v-model="local.source_key" @change="commit">
          <option value="">请选择连接器</option>
          <option v-for="c in connectors" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>
        <div v-if="connectors.length === 0" class="pp-hint">暂无自定义连接器，请先在「连接器」页创建</div>
      </div>
    </template>
    <div class="pp-field">
      <label>查询词 / URL</label>
      <input v-model="local.query" @change="commit" placeholder="支持 {{变量}} 引用">
      <div class="pp-hint">搜索关键词或要抓取的网页地址</div>
    </div>
    <div class="pp-field">
      <label>返回条数</label>
      <input type="number" v-model.number="local.limit" @change="commit" min="1" max="50">
    </div>
    <div class="pp-section-title">输出变量</div>
    <div class="pp-hint" style="line-height:1.6">
      documents（结果列表）/ content（首条文本）/ datasource_status<br>
      在「连接器」页安装并配置对应数据源后方可调用。
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit, builtinSources, connectors } = usePanelState(props, emit)
</script>

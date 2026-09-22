<template>
  <div>
    <!-- 定时触发 -->
    <template v-if="nodeType === 'trigger-schedule'">
      <div class="pp-field">
        <label>Cron 表达式</label>
        <input v-model="local.cron_expr" @change="commit" placeholder="*/5 * * * *">
        <div class="pp-hint">5 段格式：分 时 日 月 周。如 0 9 * * *（每天 9 点）、*/5 * * * *（每 5 分钟）</div>
      </div>
      <div class="pp-field">
        <label>时区</label>
        <select v-model="local.timezone" @change="commit">
          <option value="Asia/Shanghai">Asia/Shanghai（北京时间）</option>
          <option value="UTC">UTC</option>
        </select>
      </div>
      <div class="pp-field pp-check">
        <label><input type="checkbox" v-model="local.enabled" @change="commit"> 启用</label>
      </div>
      <div class="pp-section-title">使用说明</div>
      <div class="pp-hint" style="line-height:1.6">
        定时触发节点是入口节点：保存工作流后，系统按 Cron 计划自动运行整个工作流。<br>
        节点输出 trigger_type / trigger_time 变量，供下游节点引用。<br>
        计划列表可在「Webhook / 触发器」页面查看和管理。
      </div>
    </template>

    <!-- Webhook 触发 -->
    <template v-else-if="nodeType === 'trigger-webhook'">
      <div class="pp-field pp-check">
        <label><input type="checkbox" v-model="local.enabled" @change="commit"> 启用</label>
      </div>
      <div class="pp-section-title">使用说明</div>
      <div class="pp-hint" style="line-height:1.6">
        Webhook 触发节点是入口节点：保存工作流后自动生成触发地址，
        向该地址 POST 请求即可启动工作流（与「Webhook / 触发器」页的管理型 Webhook 一致）。<br>
        请求体 JSON 字段会作为 trigger_* 输入变量透传给下游节点。
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePanelState } from './usePanelState'
import { getNodeType } from '../../../utils/workflow/nodeRegistry'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)

const nodeType = computed(() => props.node ? (props.node.data._type || props.node.data.type) : '')
</script>

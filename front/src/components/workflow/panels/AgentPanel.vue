<template>
  <div>
    <div class="pp-field">
      <label>模型</label>
      <div class="pp-model-row">
        <select v-model="modelKey" @change="commitModel" class="pp-model-select">
          <option value="">请选择模型</option>
          <option v-for="o in modelChoices" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
        <button class="mp-btn mp-btn-outline mp-btn-sm" @click="showModelModal = true" title="配置模型供应商">
          ⚙️ 配置
        </button>
      </div>
      <div v-if="modelChoices.length === 0" class="pp-hint">暂无可用模型，请点击「配置」按钮添加模型供应商。</div>
    </div>
    <!-- 模型配置模态窗口 -->
    <ModelProviderModal :visible="showModelModal" @close="showModelModal = false; refreshModels()" />
    <div class="pp-field">
      <label>Temperature</label>
      <input type="range" min="0" max="1" step="0.1" v-model.number="temperature" @change="commit">
      <span class="pp-range-val">{{ temperature }}</span>
    </div>
    <div class="pp-field">
      <label>系统提示词（Agent 角色）</label>
      <textarea v-model="local.prompt" rows="4" @change="commit" placeholder="定义 Agent 的角色和行为规则"></textarea>
    </div>
    <div class="pp-field">
      <label>用户任务/问题</label>
      <textarea v-model="local.user_prompt" rows="3" @change="commit" placeholder="如 {{#start.query#}}"></textarea>
    </div>
    <div class="pp-field">
      <label>最大迭代次数</label>
      <input type="number" v-model.number="local.max_iterations" @change="commit" min="1" max="20">
      <div class="pp-hint">Agent 最多执行多少次工具调用</div>
    </div>
    <div class="pp-section-title">工具列表</div>
    <div v-for="(t, i) in local.tools" :key="i" class="pp-card">
      <div class="pp-card-head">
        <span>工具 {{ i + 1 }}</span>
        <button class="pp-card-del" @click="removeTool(i)">删除</button>
      </div>
      <div class="pp-field">
        <label>工具名称</label>
        <input v-model="t.name" @change="commit">
      </div>
      <div class="pp-field">
        <label>描述</label>
        <input v-model="t.description" @change="commit">
      </div>
      <div class="pp-field">
        <label>类型</label>
        <select v-model="t.type" @change="commit">
          <option value="http">HTTP 请求</option>
          <option value="code">代码执行</option>
          <option value="knowledge">知识检索</option>
          <option value="calculator">计算器</option>
        </select>
      </div>
      <div v-if="t.type === 'http'" class="pp-field">
        <label>URL</label>
        <input v-model="t.url" @change="commit" placeholder="https://api.example.com/search">
      </div>
      <div v-if="t.type === 'http'" class="pp-field">
        <label>方法</label>
        <select v-model="t.method" @change="commit">
          <option value="get">GET</option>
          <option value="post">POST</option>
        </select>
      </div>
      <div v-if="t.type === 'code'" class="pp-field">
        <label>代码</label>
        <textarea v-model="t.code" rows="4" @change="commit" placeholder="result = args['input'].upper()"></textarea>
      </div>
      <div v-if="t.type === 'knowledge'" class="pp-field">
        <label>知识库</label>
        <select v-model="t.dataset_id" @change="commitKnowledgeDataset(t)">
          <option value="">请选择知识库</option>
          <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
    </div>
    <button class="pp-add-btn" @click="addTool">+ 添加工具</button>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      Agent 节点使用 ReAct 模式（推理+行动）：<br>
      1. LLM 根据任务决定调用工具或直接回答<br>
      2. 工具执行结果反馈给 LLM<br>
      3. 循环直到得出最终答案<br>
      4. 可使用变量：{{item}} 访问当前元素
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePanelState } from './usePanelState'
import ModelProviderModal from '../../ModelProviderModal.vue'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, models, datasets, modelKey, modelChoices, temperature,
  commitModel, loadAllOptions: refreshModels,
} = usePanelState(props, emit)

const showModelModal = ref(false)

function addTool() {
  if (!Array.isArray(local.value.tools)) local.value.tools = []
  local.value.tools.push({ name: '', description: '', type: 'http', url: '', method: 'get' })
  commit()
}

function removeTool(index) {
  if (!Array.isArray(local.value.tools)) local.value.tools = []
  local.value.tools.splice(index, 1)
  commit()
}

function commitKnowledgeDataset(t) {
  if (t.dataset_id) {
    t.dataset_ids = [t.dataset_id]
  } else {
    t.dataset_ids = []
  }
  commit()
}
</script>

<style scoped>
.pp-model-row { display: flex; gap: 8px; align-items: center; }
.pp-model-select { flex: 1; }
</style>

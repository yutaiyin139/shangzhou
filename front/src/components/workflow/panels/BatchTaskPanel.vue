<template>
  <div>
    <div class="pp-field">
      <label>输入列表选择器</label>
      <input v-model="batchInputSelector" @change="commitBatchInput" placeholder="如 start.items">
      <div class="pp-hint">选择要批量处理的列表变量</div>
    </div>
    <div class="pp-field">
      <label>任务类型</label>
      <select v-model="local.task_type" @change="commit">
        <option value="llm">LLM 调用</option>
        <option value="code">代码执行</option>
        <option value="http">HTTP 请求</option>
        <option value="template">模板转换</option>
      </select>
      <div class="pp-hint">选择批量执行的任务类型</div>
    </div>
    <template v-if="local.task_type === 'llm'">
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
      </div>
      <!-- 模型配置模态窗口 -->
      <ModelProviderModal :visible="showModelModal" @close="showModelModal = false; refreshModels()" />
      <div class="pp-field">
        <label>Temperature</label>
        <input type="range" min="0" max="1" step="0.1" v-model.number="temperature" @change="commit">
        <span class="pp-range-val">{{ temperature }}</span>
      </div>
      <div class="pp-field">
        <label>Prompt 模板</label>
        <textarea v-model="local.task_config.prompt_template" rows="4" @change="commit" placeholder="使用 {{item}} 引用当前元素"></textarea>
        <div class="pp-hint">使用 {{item}} 和 {{item.字段名}} 引用元素属性</div>
      </div>
      <div class="pp-field">
        <label>最大 Token 数</label>
        <input type="number" v-model.number="local.task_config.max_tokens" @change="commit" min="1" max="32000">
      </div>
    </template>
    <template v-if="local.task_type === 'code'">
      <div class="pp-field">
        <label>语言</label>
        <select v-model="local.task_config.language" @change="commit">
          <option value="python3">Python 3</option>
          <option value="javascript">JavaScript</option>
        </select>
      </div>
      <div class="pp-field">
        <label>代码</label>
        <textarea v-model="local.task_config.code" rows="8" @change="commit" placeholder="result = item.upper()"></textarea>
        <div class="pp-hint">使用 item 变量访问当前元素</div>
      </div>
    </template>
    <template v-if="local.task_type === 'http'">
      <div class="pp-field">
        <label>方法</label>
        <select v-model="local.task_config.method" @change="commit">
          <option value="get">GET</option>
          <option value="post">POST</option>
          <option value="put">PUT</option>
          <option value="delete">DELETE</option>
        </select>
      </div>
      <div class="pp-field">
        <label>URL</label>
        <input v-model="local.task_config.url" @change="commit" placeholder="https://api.example.com/process">
        <div class="pp-hint">使用 {{item}} 引用元素值</div>
      </div>
      <div class="pp-field">
        <label>Headers (JSON)</label>
        <textarea v-model="local.task_config.headers" rows="3" @change="commit"></textarea>
      </div>
      <div class="pp-field">
        <label>Body 模板</label>
        <textarea v-model="local.task_config.body_template" rows="4" @change="commit" placeholder='{"data": "{{item}}"}'></textarea>
      </div>
    </template>
    <template v-if="local.task_type === 'template'">
      <div class="pp-field">
        <label>模板内容</label>
        <textarea v-model="local.task_config.template" rows="6" @change="commit" placeholder="处理结果: {{item}}"></textarea>
        <div class="pp-hint">使用 {{item}} 引用当前元素</div>
      </div>
    </template>
    <div class="pp-section-title">批处理配置</div>
    <div class="pp-field">
      <label>批次大小</label>
      <input type="number" v-model.number="local.batch_size" @change="commit" min="1" max="100">
      <div class="pp-hint">每批处理的元素数量</div>
    </div>
    <div class="pp-field">
      <label>最大并发数</label>
      <input type="number" v-model.number="local.max_parallel" @change="commit" min="1" max="20">
      <div class="pp-hint">同时执行的任务数量</div>
    </div>
    <div class="pp-field">
      <label>错误处理策略</label>
      <select v-model="local.error_strategy" @change="commit">
        <option value="continue_on_error">继续执行（跳过错误）</option>
        <option value="fail_fast">遇到错误立即停止</option>
        <option value="skip_error">跳过错误项</option>
      </select>
      <div class="pp-hint">批处理遇到错误时的处理方式</div>
    </div>
    <div class="pp-field">
      <label>最大处理数量</label>
      <input type="number" v-model.number="local.max_items" @change="commit" min="1" max="10000">
      <div class="pp-hint">最多处理的元素总数（安全限制）</div>
    </div>
    <div class="pp-field">
      <label>输出变量名</label>
      <input v-model="local.output_variable" @change="commit" placeholder="batch_results">
      <div class="pp-hint">批量结果保存到的变量名</div>
    </div>
    <div class="pp-section-title">使用说明</div>
    <div class="pp-hint" style="line-height:1.6">
      批量任务节点对列表中的每个元素执行相同操作。<br>
      1. 选择要处理的列表变量<br>
      2. 配置任务类型（LLM/代码/HTTP/模板）<br>
      3. 设置批次大小和并发数<br>
      4. 结果会聚合为列表输出
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePanelState } from './usePanelState'
import ModelProviderModal from '../../ModelProviderModal.vue'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, models, modelKey, modelChoices, temperature,
  commitModel, loadAllOptions: refreshModels,
} = usePanelState(props, emit)

const showModelModal = ref(false)

const batchInputSelector = computed({

  get: () => {
    const sel = local.value.input_selector || []
    return Array.isArray(sel) ? sel.join('.') : (sel || '')
  },
  set: (val) => {
    local.value.input_selector = val ? val.split('.').filter(Boolean) : []
  }
})

function commitBatchInput() {
  commit()
}
</script>

<style scoped>
.pp-model-row { display: flex; gap: 8px; align-items: center; }
.pp-model-select { flex: 1; }
</style>

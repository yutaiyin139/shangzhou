<template>
  <div class="share-layout">
    <div class="share-container">
      <!-- 头部 -->
      <div class="share-header">
        <div class="share-brand">
          <div class="share-logo">熵舟</div>
          <span class="share-divider">|</span>
          <span class="share-type">工作流</span>
        </div>
        <div class="share-actions">
          <a class="share-login-link" href="/#/login">登录使用</a>
        </div>
      </div>

      <!-- 工作流区域 -->
      <div class="share-workflow" v-if="!loading && !error">
        <div class="share-title" v-if="appInfo.name">{{ appInfo.name }}</div>
        <div class="share-desc" v-if="appInfo.description">{{ appInfo.description }}</div>

        <!-- 输入表单 -->
        <div class="wf-inputs-section">
          <h4>输入参数</h4>
          <div v-for="input in inputs" :key="input.variable" class="wf-input-item">
            <label class="wf-input-label">
              {{ input.label || input.variable }}
              <span v-if="input.required" class="wf-required">*</span>
            </label>
            <input
              v-if="input.type === 'string' || input.type === 'text'"
              v-model="formData[input.variable]"
              :placeholder="input.description || ''"
              class="wf-input"
            >
            <textarea
              v-else-if="input.type === 'textarea'"
              v-model="formData[input.variable]"
              :placeholder="input.description || ''"
              class="wf-input wf-textarea"
              rows="3"
            ></textarea>
            <input
              v-else-if="input.type === 'number'"
              v-model.number="formData[input.variable]"
              type="number"
              :placeholder="input.description || ''"
              class="wf-input"
            >
          </div>
          <button class="wf-run-btn" @click="runWorkflow" :disabled="running">
            <span v-if="running">运行中...</span>
            <span v-else>运行工作流</span>
          </button>
        </div>

        <!-- 输出结果 -->
        <div v-if="output" class="wf-output-section">
          <h4>运行结果</h4>
          <div class="wf-output-content">
            <pre>{{ formatOutput(output) }}</pre>
          </div>
          <div v-if="elapsedTime" class="wf-output-meta">
            耗时: {{ elapsedTime }}ms
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="share-loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 错误状态 -->
      <div v-if="error" class="share-error">
        <div class="share-error-icon">⚠️</div>
        <div>{{ error }}</div>
      </div>
    </div>

    <!-- 页脚 -->
    <div class="share-footer">
      <span>Powered by 熵舟·智能体工作台</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, apiPost } from '../api/client'

const route = useRoute()
const token = route.params.token

const loading = ref(true)
const error = ref('')
const running = ref(false)
const appInfo = ref({})
const inputs = ref([])
const formData = ref({})
const output = ref(null)
const elapsedTime = ref(0)

async function loadAppInfo() {
  try {
    const res = await apiGet(`/api/share/workflow/${token}/info`)
    appInfo.value = res.data?.app || {}
    inputs.value = res.data?.inputs || []
    // 初始化表单数据
    inputs.value.forEach(inp => {
      if (inp.default !== undefined) {
        formData.value[inp.variable] = inp.default
      }
    })
  } catch (e) {
    error.value = '加载失败，请检查链接是否正确'
  }
  loading.value = false
}

async function runWorkflow() {
  // 验证必填项
  for (const inp of inputs.value) {
    if (inp.required && !formData.value[inp.variable]) {
      alert(`请填写: ${inp.label || inp.variable}`)
      return
    }
  }

  running.value = true
  output.value=null
  const startTime = Date.now()

  try {
    const res = await apiPost(`/api/share/workflow/${token}/run`, { inputs: formData.value })

    output.value = res.data?.outputs || res.data
    elapsedTime.value = res.data?.elapsed_time || (Date.now() - startTime)
  } catch (e) {
    error.value = '运行失败: ' + e.message
  }

  running.value = false
}

function formatOutput(data) {
  if (typeof data === 'string') return data
  return JSON.stringify(data, null, 2)
}

onMounted(() => {
  loadAppInfo()
})
</script>

<style scoped>
.share-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-page);
}

.share-container {
  flex: 1;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 0 20px;
}

.share-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-light);
}

.share-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.share-logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}

.share-divider {
  color: var(--text-4);
}

.share-type {
  color: var(--text-2);
  font-size: 14px;
}

.share-login-link {
  color: var(--primary);
  font-size: 13px;
  text-decoration: none;
}

.share-login-link:hover {
  text-decoration: underline;
}

.share-workflow {
  padding: 24px 0;
}

.share-title {
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 8px;
}

.share-desc {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  margin-bottom: 32px;
}

.wf-inputs-section {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 24px;
}

.wf-inputs-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
}

.wf-input-item {
  margin-bottom: 16px;
}

.wf-input-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  margin-bottom: 6px;
}

.wf-required {
  color: var(--red);
}

.wf-input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  background: var(--bg-input);
  color: var(--text-1);
}

.wf-input:focus {
  border-color: var(--primary);
}

.wf-textarea {
  resize: vertical;
  min-height: 80px;
}

.wf-run-btn {
  width: 100%;
  padding: 14px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.15s;
}

.wf-run-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}

.wf-run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.wf-output-section {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 24px;
}

.wf-output-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}

.wf-output-content {
  background: var(--bg-page);
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.wf-output-content pre {
  font-family: monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-2);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.wf-output-meta {
  text-align: right;
  font-size: 12px;
  color: var(--text-4);
  margin-top: 8px;
}

.share-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-3);
  padding: 60px 0;
}

.share-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--red);
  padding: 60px 0;
}

.share-error-icon {
  font-size: 48px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.share-footer {
  text-align: center;
  padding: 16px;
  color: var(--text-4);
  font-size: 12px;
  border-top: 1px solid var(--border-light);
}
</style>

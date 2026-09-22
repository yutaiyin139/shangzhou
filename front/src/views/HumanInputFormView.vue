<template>
  <div class="hif-root">
    <div class="hif-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="hif-loading">
        <div class="hif-spinner"></div>
        <p>正在加载表单...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="hif-error">
        <div class="hif-error-icon">⚠️</div>
        <h2>无法加载表单</h2>
        <p>{{ error }}</p>
        <button class="hif-btn" @click="loadForm">重试</button>
      </div>

      <!-- 已提交状态 -->
      <div v-else-if="submitted" class="hif-success">
        <div class="hif-success-icon">✅</div>
        <h2>提交成功</h2>
        <p>您的输入已提交，工作流将继续执行。</p>
        <p class="hif-success-sub">您可以关闭此页面。</p>
      </div>

      <!-- 表单 -->
      <div v-else-if="form" class="hif-form">
        <div class="hif-header">
          <div class="hif-app-icon">⏸️</div>
          <div class="hif-header-info">
            <h1>工作流等待您的输入</h1>
            <p class="hif-app-name">「{{ form.app_name || '智能应用' }}」</p>
          </div>
        </div>

        <div v-if="form.message" class="hif-message">
          <h3>📋 提示信息</h3>
          <p>{{ form.message }}</p>
        </div>

        <div v-if="form.fields && form.fields.length > 0" class="hif-fields">
          <h3>请填写以下信息</h3>
          <div v-for="field in form.fields" :key="field.name" class="hif-field">
            <label>
              {{ field.label || field.name }}
              <span v-if="field.required" class="hif-required">*</span>
            </label>
            <input
              v-if="field.type === 'text' || field.type === 'string'"
              v-model="formData[field.name]"
              :placeholder="field.placeholder || ''"
              class="hif-input"
            />
            <textarea
              v-else-if="field.type === 'textarea'"
              v-model="formData[field.name]"
              :placeholder="field.placeholder || ''"
              class="hif-textarea"
              rows="4"
            ></textarea>
            <select
              v-else-if="field.type === 'select'"
              v-model="formData[field.name]"
              class="hif-select"
            >
              <option value="">请选择...</option>
              <option v-for="opt in (field.options || [])" :key="opt.value" :value="opt.value">
                {{ opt.label || opt.value }}
              </option>
            </select>
            <input
              v-else-if="field.type === 'number'"
              v-model.number="formData[field.name]"
              type="number"
              :placeholder="field.placeholder || ''"
              class="hif-input"
            />
            <input
              v-else-if="field.type === 'date'"
              v-model="formData[field.name]"
              type="date"
              class="hif-input"
            />
            <input
              v-else
              v-model="formData[field.name]"
              :placeholder="field.placeholder || ''"
              class="hif-input"
            />
            <p v-if="field.description" class="hif-field-desc">{{ field.description }}</p>
          </div>
        </div>

        <div class="hif-actions">
          <button
            class="hif-btn hif-btn-primary"
            @click="submitForm"
            :disabled="submitting"
          >
            {{ submitting ? '提交中...' : '提交' }}
          </button>
        </div>

        <p v-if="submitError" class="hif-submit-error">{{ submitError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, apiPost } from '../api/client'

const route = useRoute()

const loading = ref(true)
const error = ref('')
const form = ref(null)
const formData = reactive({})
const submitting = ref(false)
const submitted = ref(false)
const submitError = ref('')

onMounted(() => {
  loadForm()
})

async function loadForm() {
  loading.value = true
  error.value = ''

  const formKey = route.query.form_key || route.query.run_id
  if (!formKey) {
    error.value = '缺少表单标识参数（form_key 或 run_id）'
    loading.value = false
    return
  }

  try {
    const res = await apiGet(`/api/workflows/human-input-forms/${formKey}`)
    if (res.code === 200 && res.data) {
      form.value = res.data
      // 初始化表单数据
      if (res.data.fields) {
        res.data.fields.forEach(f => {
          formData[f.name] = f.default_value || ''
        })
      }
    } else {
      error.value = res.msg || '表单不存在或已过期'
    }
  } catch (e) {
    error.value = '加载失败：' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

async function submitForm() {
  // 必填校验
  if (form.value && form.value.fields) {
    for (const f of form.value.fields) {
      if (f.required && !formData[f.name]) {
        submitError.value = `请填写「${f.label || f.name}」`
        return
      }
    }
  }

  submitting.value = true
  submitError.value = ''

  const formKey = route.query.form_key || route.query.run_id

  try {
    const res = await apiPost(`/api/workflows/human-input-forms/${formKey}/submit`, {
      data: formData
    })
    if (res.code === 200) {
      submitted.value = true
    } else {
      submitError.value = res.msg || '提交失败'
    }
  } catch (e) {
    submitError.value = '提交失败：' + (e.message || '未知错误')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.hif-root {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.hif-container {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  max-width: 560px;
  width: 100%;
  padding: 40px;
}

.hif-loading {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
}

.hif-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.hif-error, .hif-success {
  text-align: center;
  padding: 40px 20px;
}

.hif-error-icon, .hif-success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.hif-error h2, .hif-success h2 {
  font-size: 20px;
  color: #111;
  margin-bottom: 8px;
}

.hif-error p {
  color: #6b7280;
  margin-bottom: 20px;
}

.hif-success-sub {
  color: #9ca3af;
  font-size: 13px;
  margin-top: 8px;
}

.hif-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.hif-app-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.hif-header-info h1 {
  font-size: 22px;
  font-weight: 600;
  color: #111;
  margin: 0;
}

.hif-app-name {
  color: #4f46e5;
  font-size: 14px;
  margin-top: 4px;
}

.hif-message {
  background: #f0f5ff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.hif-message h3 {
  font-size: 14px;
  color: #333;
  margin: 0 0 8px 0;
}

.hif-message p {
  color: #555;
  line-height: 1.6;
  margin: 0;
}

.hif-fields h3 {
  font-size: 16px;
  color: #333;
  margin: 0 0 16px 0;
}

.hif-field {
  margin-bottom: 20px;
}

.hif-field label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.hif-required {
  color: #ef4444;
}

.hif-input, .hif-textarea, .hif-select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #111;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.hif-input:focus, .hif-textarea:focus, .hif-select:focus {
  outline: none;
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.hif-textarea {
  resize: vertical;
  min-height: 80px;
}

.hif-field-desc {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

.hif-actions {
  margin-top: 24px;
  text-align: center;
}

.hif-btn {
  padding: 10px 24px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.hif-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.hif-btn-primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
  font-weight: 500;
  padding: 12px 48px;
  font-size: 15px;
}

.hif-btn-primary:hover {
  background: #4338ca;
  border-color: #4338ca;
}

.hif-btn-primary:disabled {
  background: #9ca3af;
  border-color: #9ca3af;
  cursor: not-allowed;
}

.hif-submit-error {
  color: #ef4444;
  font-size: 13px;
  text-align: center;
  margin-top: 12px;
}
</style>

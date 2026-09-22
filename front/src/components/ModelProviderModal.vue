<template>
  <!-- 模态窗口遮罩 -->
  <div v-if="visible" class="mp-modal-mask" @click.self="close">
    <div class="mp-modal-container">
      <!-- 模态窗口头部 -->
      <div class="mp-modal-header">
        <div class="mp-modal-title-wrap">
          <h2 class="mp-modal-title">模型供应商</h2>
          <span class="mp-modal-subtitle">安装并配置模型供应商，工作空间中的所有成员都可以使用</span>
        </div>
        <button class="mp-modal-close" @click="close">✕</button>
      </div>

      <!-- 模态窗口主体 -->
      <div class="mp-modal-body">
        <!-- 顶部：已配置供应商 -->
        <section class="mp-section" v-if="installedProviders.length > 0">
          <div class="mp-section-head">
            <h3 class="mp-section-title">已配置</h3>
            <span class="mp-section-count">{{ installedProviders.length }} 个供应商</span>
          </div>
          <div class="mp-installed-grid">
            <div
              v-for="p in installedProviders"
              :key="p.provider_name"
              class="mp-installed-card"
              :style="{ '--bg': p.icon_background || '#E8F3FF' }"
            >
              <div class="mp-installed-main" @click="openInstalledDetail(p)">
                <div class="mp-installed-icon" :style="{ background: p.icon_background || '#E8F3FF' }">
                  <span>{{ p.icon || (p.provider_label || p.provider_name || '?').charAt(0) }}</span>
                </div>
                <div class="mp-installed-info">
                  <div class="mp-installed-name">{{ p.provider_label }}</div>
                  <div class="mp-installed-count">{{ p.model_count }} 个模型</div>
                </div>
                <div class="mp-installed-badge">已配置</div>
              </div>
              <div class="mp-installed-test">
                <button
                  class="mp-btn mp-btn-text mp-btn-sm"
                  :disabled="testLoadingId === p.latest_config_id"
                  @click.stop="testById(p.latest_config_id, p.provider_name)"
                >
                  <span v-if="testLoadingId === p.latest_config_id">⏳</span>
                  <span v-else>🔌 测试</span>
                </button>
                <span
                  v-if="testResults[p.provider_name]"
                  :class="testResults[p.provider_name].success ? 'mp-test-ok' : 'mp-test-fail'"
                >
                  {{ testResults[p.provider_name].success ? '✓ ' + testResults[p.provider_name].elapsed_ms + 'ms' : '✗ ' + testResults[p.provider_name].msg }}
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- 搜索和筛选 -->
        <div class="mp-toolbar">
          <div class="mp-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="16" height="16">
              <circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>
            </svg>
            <input
              v-model="searchQuery"
              class="mp-search-input"
              placeholder="搜索模型供应商..."
            />
          </div>
          <div class="mp-filter">
            <button
              v-for="f in filters"
              :key="f.value"
              class="mp-filter-btn"
              :class="{ active: currentFilter === f.value }"
              @click="currentFilter = f.value"
            >
              {{ f.label }}
            </button>
          </div>
        </div>

        <!-- 可安装供应商网格 -->
        <section class="mp-section">
          <div class="mp-section-head">
            <h3 class="mp-section-title">全部模型供应商</h3>
            <span class="mp-section-count">{{ filteredProviders.length }} 个</span>
          </div>
          <div class="mp-provider-grid">
            <div
              v-for="p in filteredProviders"
              :key="p.provider_name"
              class="mp-provider-card"
              :class="{ installed: p.is_installed }"
            >
              <div class="mp-card-main">
                <div class="mp-card-head">
                  <div class="mp-card-icon" :style="{ background: p.icon_background || '#E8F3FF' }">
                    <span>{{ p.icon || (p.provider_label || p.provider_name || '?').charAt(0) }}</span>
                  </div>
                  <div class="mp-card-body">
                    <div class="mp-card-row-title">
                      <span class="mp-card-name" :title="p.provider_label">{{ p.provider_label }}</span>
                      <span v-if="p.is_installed" class="mp-badge-installed">已配置</span>
                    </div>
                    <div class="mp-card-vendor" :title="p.provider_name">{{ p.provider_name }}</div>
                  </div>
                </div>
                <div class="mp-card-desc">{{ p.description || '暂无描述' }}</div>
                <div class="mp-card-types">
                  <span v-for="t in parseTypes(p.supported_model_types).slice(0, 4)" :key="t" class="mp-type-tag">
                    {{ typeLabel(t) }}
                  </span>
                </div>
              </div>
              <!-- 悬停操作层 -->
              <div class="mp-card-overlay">
                <button class="mp-overlay-btn mp-overlay-btn-models" @click="openProviderDetail(p)">
                  <span>详情</span>
                  <svg class="mp-overlay-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                </button>
                <button
                  v-if="!p.is_installed"
                  class="mp-overlay-btn mp-overlay-btn-primary"
                  @click="openInstallModal(p)"
                >
                  安装
                </button>
                <button
                  v-else
                  class="mp-overlay-btn mp-overlay-btn-primary"
                  @click="openInstallModal(p)"
                >
                  配置
                </button>
              </div>
            </div>
          </div>
          <div v-if="filteredProviders.length === 0" class="mp-empty">
            <div class="mp-empty-icon">🔍</div>
            <div class="mp-empty-text">未找到匹配的模型供应商</div>
          </div>
        </section>
      </div>
    </div>

    <!-- 供应商详情弹窗 -->
    <div v-if="showDetail" class="mp-modal-mask mp-nested" @click.self="showDetail = false">
      <div class="mp-modal mp-modal-lg">
        <div class="mp-modal-head">
          <div class="mp-modal-title-wrap">
            <div class="mp-modal-icon" :style="{ background: detailProvider?.icon_background || '#E8F3FF' }">
              <span>{{ detailProvider?.icon || (detailProvider?.provider_label || detailProvider?.provider_name || '?').charAt(0) }}</span>
            </div>
            <div>
              <div class="mp-modal-title">{{ detailProvider?.provider_label }}</div>
              <div class="mp-modal-subtitle">{{ detailProvider?.description }}</div>
            </div>
          </div>
          <button class="mp-modal-close" @click="showDetail = false">✕</button>
        </div>
        <div class="mp-modal-body">
          <div v-if="detailProvider?.help_text" class="mp-help-box">
            <span class="mp-help-icon">💡</span>
            <span>{{ detailProvider.help_text }}</span>
            <a v-if="detailProvider?.help_url" :href="detailProvider.help_url" target="_blank" class="mp-help-link">获取 API Key ↗</a>
          </div>
          <div class="mp-detail-section">
            <div class="mp-detail-label">支持的模型类型</div>
            <div class="mp-detail-types">
              <span v-for="t in parseTypes(detailProvider?.supported_model_types)" :key="t" class="mp-type-tag mp-type-tag-lg">
                {{ typeLabel(t) }}
              </span>
            </div>
          </div>
          <div class="mp-detail-section">
            <div class="mp-detail-label">可用模型</div>
            <div v-if="detailModels.length > 0" class="mp-model-table">
              <div class="mp-model-row mp-model-header">
                <span class="mp-model-col-name">模型名称</span>
                <span class="mp-model-col-type">类型</span>
                <span class="mp-model-col-ctx">上下文</span>
                <span class="mp-model-col-cap">能力</span>
              </div>
              <div v-for="m in detailModels" :key="m.model_name" class="mp-model-row">
                <span class="mp-model-col-name">
                  <b>{{ m.model_label }}</b>
                  <small>{{ m.model_name }}</small>
                </span>
                <span class="mp-model-col-type"><span class="mp-type-tag">{{ typeLabel(m.model_type) }}</span></span>
                <span class="mp-model-col-ctx">{{ formatContext(m.context_size) }}</span>
                <span class="mp-model-col-cap">
                  <span v-if="m.supports_vision" title="支持视觉">👁</span>
                  <span v-if="m.supports_function_calling" title="支持函数调用">⚡</span>
                  <span v-if="m.supports_streaming" title="支持流式">🌊</span>
                </span>
              </div>
            </div>
            <div v-else class="mp-empty mp-empty-sm">暂无可用模型</div>
          </div>
        </div>
        <div class="mp-modal-foot">
          <button class="mp-btn" @click="showDetail = false">关闭</button>
          <button
            v-if="!detailProvider?.is_installed"
            class="mp-btn mp-btn-primary"
            @click="showDetail = false; openInstallModal(detailProvider)"
          >
            安装此供应商
          </button>
          <button
            v-else
            class="mp-btn mp-btn-outline"
            @click="showDetail = false; openInstallModal(detailProvider)"
          >
            配置模型
          </button>
        </div>
      </div>
    </div>

    <!-- 安装/配置弹窗 -->
    <div v-if="showInstall" class="mp-modal-mask mp-nested" @click.self="showInstall = false">
      <div class="mp-modal mp-modal-xl">
        <div class="mp-modal-head">
          <div class="mp-modal-title-wrap">
            <div class="mp-modal-icon" :style="{ background: installProvider?.icon_background || '#E8F3FF' }">
              <span>{{ installProvider?.icon || (installProvider?.provider_label || installProvider?.provider_name || '?').charAt(0) }}</span>
            </div>
            <div>
              <div class="mp-modal-title">{{ installProvider?.is_installed ? '配置模型' : '安装 ' + (installProvider?.provider_label || '') }}</div>
              <div class="mp-modal-subtitle">配置凭据后，工作空间中的所有成员都可以使用此模型</div>
            </div>
          </div>
          <button class="mp-modal-close" @click="showInstall = false">✕</button>
        </div>
        <div class="mp-modal-body">
          <div v-if="installProvider?.help_text" class="mp-help-box">
            <span class="mp-help-icon">💡</span>
            <span>{{ installProvider.help_text }}</span>
            <a v-if="installProvider?.help_url" :href="installProvider.help_url" target="_blank" class="mp-help-link">获取 API Key ↗</a>
          </div>
          <div class="mp-form-item">
            <label class="mp-form-label">凭据名称</label>
            <input v-model="installForm.credential_name" class="mp-form-input" placeholder="请输入凭据名称（如：我的 OpenAI 配置）" />
          </div>
          <div class="mp-form-item">
            <label class="mp-form-label">API Key <span class="mp-req">*</span></label>
            <div class="mp-input-group">
              <input
                v-model="installForm.api_key"
                :type="showApiKey ? 'text' : 'password'"
                class="mp-form-input"
                :class="{ error: installErrors.api_key }"
                placeholder="在此输入您的 API Key"
                @input="installErrors.api_key = ''"
              />
              <button class="mp-input-toggle" @click="showApiKey = !showApiKey">{{ showApiKey ? '🙈' : '👁' }}</button>
            </div>
            <div v-if="installErrors.api_key" class="mp-form-error">{{ installErrors.api_key }}</div>
          </div>
          <div class="mp-form-item">
            <label class="mp-form-label">API Base URL</label>
            <input v-model="installForm.api_base_url" class="mp-form-input" :placeholder="installProvider?.default_base_url || 'https://api.example.com/v1'" />
            <div class="mp-form-hint">默认: {{ installProvider?.default_base_url || '无' }}</div>
          </div>
          <div class="mp-form-item">
            <label class="mp-form-label">模型名称 <span class="mp-req">*</span></label>
            <select v-model="installForm.model_name" class="mp-form-input" @change="onModelSelect">
              <option value="">请选择模型</option>
              <option v-for="m in installModels" :key="m.model_name" :value="m.model_name">
                {{ m.model_label }} ({{ m.model_name }})
              </option>
            </select>
            <div v-if="installErrors.model_name" class="mp-form-error">{{ installErrors.model_name }}</div>
          </div>
          <div class="mp-form-section">
            <div class="mp-form-section-title" @click="showParams = !showParams">
              <span class="mp-collapse-arrow" :class="{ open: showParams }">▶</span>
              模型参数
              <span class="mp-form-section-hint">高级配置</span>
            </div>
            <div v-show="showParams" class="mp-params-grid">
              <div class="mp-form-item">
                <label class="mp-form-label">Temperature</label>
                <input v-model.number="installForm.temperature" type="number" step="0.1" min="0" max="2" class="mp-form-input" />
              </div>
              <div class="mp-form-item">
                <label class="mp-form-label">Max Tokens</label>
                <input v-model.number="installForm.max_tokens" type="number" min="1" class="mp-form-input" />
              </div>
              <div class="mp-form-item">
                <label class="mp-form-label">Top P</label>
                <input v-model.number="installForm.top_p" type="number" step="0.1" min="0" max="1" class="mp-form-input" />
              </div>
              <div class="mp-form-item">
                <label class="mp-form-label">Presence Penalty</label>
                <input v-model.number="installForm.presence_penalty" type="number" step="0.1" min="-2" max="2" class="mp-form-input" />
              </div>
              <div class="mp-form-item">
                <label class="mp-form-label">Frequency Penalty</label>
                <input v-model.number="installForm.frequency_penalty" type="number" step="0.1" min="-2" max="2" class="mp-form-input" />
              </div>
              <div class="mp-form-item">
                <label class="mp-form-label">上下文窗口</label>
                <input v-model.number="installForm.context_size" type="number" min="1" class="mp-form-input" />
              </div>
            </div>
          </div>
          <div class="mp-form-section">
            <div class="mp-form-section-title" @click="showCaps = !showCaps">
              <span class="mp-collapse-arrow" :class="{ open: showCaps }">▶</span>
              模型能力
            </div>
            <div v-show="showCaps" class="mp-cap-grid">
              <label class="mp-cap-item">
                <input type="checkbox" v-model="installForm.supports_vision" />
                <span class="mp-cap-check"></span>
                <span class="mp-cap-icon">👁</span>
                <span class="mp-cap-label">视觉理解</span>
              </label>
              <label class="mp-cap-item">
                <input type="checkbox" v-model="installForm.supports_function_calling" />
                <span class="mp-cap-check"></span>
                <span class="mp-cap-icon">⚡</span>
                <span class="mp-cap-label">函数调用</span>
              </label>
              <label class="mp-cap-item">
                <input type="checkbox" v-model="installForm.supports_streaming" />
                <span class="mp-cap-check"></span>
                <span class="mp-cap-icon">🌊</span>
                <span class="mp-cap-label">流式输出</span>
              </label>
            </div>
          </div>
        </div>
        <div class="mp-modal-foot mp-modal-foot-split">
          <div class="mp-test-area">
            <button class="mp-btn mp-btn-text" :disabled="testLoading" @click="testConnection">
              <span v-if="testLoading">⏳ 测试中...</span>
              <span v-else-if="testResult" :class="testResult.success ? 'mp-test-ok' : 'mp-test-fail'">
                {{ testResult.success ? '✓ ' + testResult.msg : '✗ ' + testResult.msg }}
                <small v-if="testResult.elapsed_ms">({{ testResult.elapsed_ms }}ms)</small>
              </span>
              <span v-else>🔌 测试连接</span>
            </button>
          </div>
          <div class="mp-modal-actions">
            <button class="mp-btn" @click="showInstall = false">取消</button>
            <button class="mp-btn mp-btn-primary" :disabled="installLoading" @click="submitInstall">
              {{ installLoading ? '保存中...' : (installProvider?.is_installed ? '添加配置' : '安装并保存') }}
            </button>
          </div>
        </div>
        <div class="mp-secure">🔒 您的密钥将使用 <b>PKCS1_OAEP</b> 技术进行加密和存储。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { toast } from '../utils/global'
import { apiGet, apiPost } from '../api/client'

const props = defineProps({
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'installed'])

// ========== 状态 ==========
const allProviders = ref([])
const installedProviders = ref([])
const searchQuery = ref('')
const currentFilter = ref('all')
const showDetail = ref(false)
const showInstall = ref(false)
const detailProvider = ref(null)
const detailModels = ref([])
const installProvider = ref(null)
const installModels = ref([])
const showApiKey = ref(false)
const showParams = ref(false)
const showCaps = ref(false)
const installLoading = ref(false)
const testLoading = ref(false)
const testResult = ref(null)
const testLoadingId = ref(null)
const testResults = ref({})

const installForm = reactive({
  credential_name: '',
  api_key: '',
  api_base_url: '',
  model_name: '',
  model_label: '',
  model_type: 'llm',
  temperature: 0.7,
  max_tokens: 2048,
  top_p: 1.0,
  presence_penalty: 0.0,
  frequency_penalty: 0.0,
  context_size: 4096,
  supports_vision: false,
  supports_function_calling: false,
  supports_streaming: true,
})

const installErrors = reactive({ api_key: '', model_name: '' })

const filters = [
  { value: 'all', label: '全部' },
  { value: 'installed', label: '已安装' },
  { value: 'llm', label: 'LLM' },
  { value: 'embedding', label: 'Embedding' },
  { value: 'tts', label: 'TTS' },
  { value: 'stt', label: 'STT' },
]

// ========== 计算属性 ==========
const filteredProviders = computed(() => {
  let list = allProviders.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(p =>
      (p.provider_label || '').toLowerCase().includes(q) ||
      (p.provider_name || '').toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q)
    )
  }
  if (currentFilter.value === 'installed') {
    list = list.filter(p => p.is_installed)
  } else if (currentFilter.value !== 'all') {
    list = list.filter(p => parseTypes(p.supported_model_types).includes(currentFilter.value))
  }
  return list
})

// ========== 方法 ==========
function parseTypes(types) {
  if (!types) return []
  if (Array.isArray(types)) return types
  try { return JSON.parse(types) } catch { return [] }
}

function typeLabel(t) {
  const map = { llm: 'LLM', embedding: 'Embedding', rerank: 'Rerank', tts: 'TTS', stt: 'STT' }
  return map[t] || t
}

function formatContext(size) {
  if (!size) return '-'
  if (size >= 1000000) return (size / 1000000).toFixed(1) + 'M'
  if (size >= 1000) return (size / 1000).toFixed(0) + 'K'
  return String(size)
}

function close() {
  emit('close')
}

async function loadInstalled() {
  try {
    const data = await apiGet('/api/model-providers/installed')
    if (data.code === 200) installedProviders.value = data.data || []
  } catch (e) { console.error('加载已安装供应商失败', e) }
}

async function loadProviders() {
  try {
    const data = await apiGet('/api/model-providers')
    if (data.code === 200) allProviders.value = data.data || []
  } catch (e) { console.error('加载供应商列表失败', e) }
}

async function openProviderDetail(p) {
  detailProvider.value = p
  detailModels.value = []
  showDetail.value = true
  try {
    const data = await apiGet(`/api/model-providers/${p.provider_name}`)
    if (data.code === 200) {
      detailProvider.value = data.data
      detailModels.value = data.data.models || []
    }
  } catch (e) { console.error('加载供应商详情失败', e) }
}

function openInstalledDetail(p) {
  const provider = allProviders.value.find(x => x.provider_name === p.provider_name)
  if (provider) openProviderDetail(provider)
}

function openInstallModal(p) {
  installProvider.value = p
  testResult.value = null
  showApiKey.value = false
  showParams.value = false
  showCaps.value = false
  Object.assign(installForm, {
    credential_name: p.provider_label + ' - ' + new Date().toLocaleDateString('zh-CN'),
    api_key: '',
    api_base_url: p.default_base_url || '',
    model_name: '',
    model_label: '',
    model_type: 'llm',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
    presence_penalty: 0.0,
    frequency_penalty: 0.0,
    context_size: 4096,
    supports_vision: false,
    supports_function_calling: false,
    supports_streaming: true,
  })
  installErrors.api_key = ''
  installErrors.model_name = ''
  showInstall.value = true
  loadInstallModels(p)
}

async function loadInstallModels(p) {
  try {
    const data = await apiGet(`/api/model-providers/${p.provider_name}`)
    if (data.code === 200) {
      installModels.value = (data.data.models || []).filter(m => m.model_type === 'llm')
      if (installModels.value.length > 0 && !installForm.model_name) {
        const first = installModels.value[0]
        installForm.model_name = first.model_name
        installForm.model_label = first.model_label
        installForm.model_type = first.model_type
        installForm.max_tokens = first.max_output_tokens || 2048
        installForm.context_size = first.context_size || 4096
        installForm.supports_vision = !!first.supports_vision
        installForm.supports_function_calling = !!first.supports_function_calling
        installForm.supports_streaming = !!first.supports_streaming
      }
    }
  } catch (e) { console.error('加载模型列表失败', e) }
}

function onModelSelect() {
  const m = installModels.value.find(x => x.model_name === installForm.model_name)
  if (m) {
    installForm.model_label = m.model_label
    installForm.model_type = m.model_type
    installForm.max_tokens = m.max_output_tokens || 2048
    installForm.context_size = m.context_size || 4096
    installForm.supports_vision = !!m.supports_vision
    installForm.supports_function_calling = !!m.supports_function_calling
    installForm.supports_streaming = !!m.supports_streaming
  }
}

async function testConnection() {
  if (!installForm.api_key) {
    installErrors.api_key = '请输入 API Key'
    return
  }
  testLoading.value = true
  testResult.value = null
  try {
    const data = await apiPost('/api/model-configs/test', {
      provider: installProvider.value?.provider_name,
      api_key: installForm.api_key,
      api_base_url: installForm.api_base_url,
      model_name: installForm.model_name,
      model_type: installForm.model_type,
    })
    testResult.value = data.data || data
  } catch (e) {
    testResult.value = { success: false, msg: '网络异常: ' + e.message }
  } finally {
    testLoading.value = false
  }
}

async function testById(configId, providerName) {
  if (!configId) return
  testLoadingId.value = configId
  testResults.value[providerName] = null
  try {
    const data = await apiPost(`/api/model-configs/${configId}/test`)
    if (data && data.data) {
      testResults.value[providerName] = data.data
    } else if (data) {
      testResults.value[providerName] = data
    } else {
      testResults.value[providerName] = { success: false, msg: '测试返回数据为空' }
    }
  } catch (e) {
    testResults.value[providerName] = { success: false, msg: '网络异常: ' + (e.message || e) }
  } finally {
    testLoadingId.value = null
  }
}

async function submitInstall() {
  let ok = true
  if (!installForm.api_key.trim()) {
    installErrors.api_key = '请输入 API Key'
    ok = false
  }
  if (!installForm.model_name) {
    installErrors.model_name = '请选择模型'
    ok = false
  }
  if (!ok) return

  installLoading.value = true
  try {
    const data = await apiPost(`/api/model-providers/${installProvider.value.provider_name}/install`, { ...installForm })
    if (data.code === 200) {
      toast('安装成功')
      showInstall.value = false
      await Promise.all([loadInstalled(), loadProviders()])
      emit('installed')
    } else {
      toast(data.msg || '安装失败')
    }
  } catch (e) {
    toast('网络异常: ' + e.message)
  } finally {
    installLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    loadInstalled()
    loadProviders()
  }
}, { immediate: true })
</script>

<style scoped>
/* ========== 模态窗口遮罩 ========== */
.mp-modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
  backdrop-filter: blur(2px);
}
.mp-nested { z-index: 1010; }

/* ========== 模态窗口容器 ========== */
.mp-modal-container {
  background: #fff; border-radius: 16px; width: 90%; max-width: 1200px;
  max-height: 85vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08);
}

/* ========== 模态窗口头部 ========== */
.mp-modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--border-lighter, #f0f0f0);
  flex-shrink: 0;
}
.mp-modal-title-wrap { display: flex; flex-direction: column; gap: 4px; }
.mp-modal-title { font-size: 20px; font-weight: 600; color: var(--text-1); margin: 0; }
.mp-modal-subtitle { font-size: 13px; color: var(--text-3); }
.mp-modal-close {
  width: 32px; height: 32px; border-radius: 8px; border: none;
  background: transparent; cursor: pointer; font-size: 16px; color: var(--text-3);
  display: flex; align-items: center; justify-content: center;
}
.mp-modal-close:hover { background: #f5f5f5; }

/* ========== 模态窗口主体 ========== */
.mp-modal-body {
  padding: 20px 24px; overflow-y: auto; flex: 1;
}

/* ========== 区块标题 ========== */
.mp-section { margin-bottom: 24px; }
.mp-section-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.mp-section-title { font-size: 16px; font-weight: 600; color: var(--text-1); margin: 0; }
.mp-section-count { font-size: 13px; color: var(--text-3); }

/* ========== 已配置供应商网格 ========== */
.mp-installed-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.mp-installed-card {
  display: flex; flex-direction: column; gap: 8px;
  background: #fff; border: 0.5px solid var(--border-light); border-radius: 12px;
  padding: 16px; transition: all 0.2s;
  position: relative; overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.mp-installed-card:hover { border-color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.mp-installed-main { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.mp-installed-icon {
  width: 40px; height: 40px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; padding: 6px; box-sizing: border-box;
  font-size: 18px; font-weight: 700; color: #fff;
}
.mp-installed-icon span { font-size: 18px; font-weight: 700; color: #fff; line-height: 1; }
.mp-installed-info { flex: 1; min-width: 0; }
.mp-installed-name { font-size: 14px; font-weight: 600; color: var(--text-1); }
.mp-installed-count { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.mp-installed-badge {
  font-size: 11px; color: var(--green); background: var(--green-bg);
  padding: 2px 8px; border-radius: 10px; flex-shrink: 0;
}
.mp-installed-test {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding-top: 8px; border-top: 1px solid var(--border-lighter, #f5f5f5);
  font-size: 12px;
}
.mp-installed-test .mp-btn { padding: 3px 10px; font-size: 12px; }

/* ========== 工具栏 ========== */
.mp-toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.mp-search {
  display: flex; align-items: center; gap: 8px;
  background: #fff; border: 1px solid var(--border-light); border-radius: 8px;
  padding: 8px 12px; flex: 1; min-width: 240px; max-width: 400px;
  color: var(--text-3);
}
.mp-search:focus-within { border-color: var(--primary); }
.mp-search-input { border: none; outline: none; flex: 1; font-size: 14px; color: var(--text-1); background: transparent; }
.mp-filter { display: flex; gap: 6px; flex-wrap: wrap; }

/* ========== 供应商卡片网格 ========== */
.mp-provider-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.mp-provider-card {
  position: relative; overflow: hidden; min-height: 120px;
  background: #fff; border: 0.5px solid var(--border-light); border-radius: 12px;
  display: flex; flex-direction: column;
  transition: box-shadow 0.2s, border-color 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.mp-provider-card:hover { border-color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.mp-provider-card.installed { border-color: var(--green-border, #b7eb8f); }
.mp-card-main { padding: 16px 16px 12px; display: flex; flex-direction: column; gap: 10px; flex: 1; }
.mp-card-head { display: flex; gap: 12px; align-items: flex-start; }
.mp-card-icon {
  width: 40px; height: 40px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; padding: 8px; box-sizing: border-box;
  font-size: 18px; font-weight: 700; color: #fff;
}
.mp-card-icon span { font-size: 18px; font-weight: 700; color: #fff; }
.mp-card-body { flex: 1; min-width: 0; }
.mp-card-row-title { display: flex; align-items: center; gap: 8px; min-height: 20px; }
.mp-card-name { font-size: 14px; font-weight: 600; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 20px; }
.mp-badge-installed { flex-shrink: 0; font-size: 11px; line-height: 16px; padding: 0 6px; border-radius: 9px; background: var(--green-bg); color: var(--green); }
.mp-card-vendor { font-size: 11px; color: var(--text-3); line-height: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mp-card-desc {
  font-size: 12px; color: var(--text-3); line-height: 16px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 32px;
}
.mp-card-types { display: flex; gap: 4px; flex-wrap: wrap; }
.mp-type-tag {
  font-size: 10px; line-height: 16px; padding: 0 6px; border-radius: 4px;
  background: var(--tag-bg, #F0F0F0); color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.02em; white-space: nowrap;
}
.mp-type-tag-lg { font-size: 12px; padding: 4px 10px; }

/* ========== 悬停操作层 ========== */
.mp-card-overlay {
  position: absolute; inset: 0; display: flex; align-items: flex-end; gap: 8px; padding: 12px;
  background: linear-gradient(to top, rgba(255,255,255,0.98) 60%, rgba(255,255,255,0.0));
  opacity: 0; transition: opacity 0.2s;
}
.mp-provider-card:hover .mp-card-overlay { opacity: 1; }
.mp-overlay-btn {
  flex: 1; height: 32px; border-radius: 8px; font-size: 13px; font-weight: 500;
  display: flex; align-items: center; justify-content: center; gap: 4px;
  cursor: pointer; transition: all 0.2s; border: 1px solid var(--border-light);
  background: #fff; color: var(--text-2);
}
.mp-overlay-btn:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-bg, rgba(21,94,239,0.04)); }
.mp-overlay-btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.mp-overlay-btn-primary:hover { background: var(--primary-hover); color: #fff; }
.mp-overlay-arrow { width: 14px; height: 14px; }

/* ========== 按钮 ========== */
.mp-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 14px; border-radius: 6px; font-size: 13px;
  border: 1px solid var(--border-light); background: #fff; color: var(--text-2);
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.mp-btn:hover { border-color: var(--primary); color: var(--primary); }
.mp-btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.mp-btn-primary:hover { background: var(--primary-hover); color: #fff; }
.mp-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.mp-btn-outline { border-color: var(--primary); color: var(--primary); background: transparent; }
.mp-btn-text { border: none; background: transparent; color: var(--primary); padding: 6px 8px; }
.mp-btn-text:hover { background: var(--primary-bg, rgba(22,119,255,0.06)); }
.mp-btn-text:disabled { opacity: 0.6; cursor: not-allowed; }
.mp-btn-sm { padding: 3px 10px; font-size: 12px; }

/* ========== 筛选按钮 ========== */
.mp-filter-btn {
  padding: 6px 14px; border-radius: 16px; font-size: 13px;
  border: 1px solid var(--border-light); background: #fff; color: var(--text-2);
  cursor: pointer; transition: all 0.2s;
}
.mp-filter-btn:hover { border-color: var(--primary); color: var(--primary); }
.mp-filter-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

/* ========== 详情弹窗 ========== */
.mp-modal {
  background: #fff; border-radius: 16px; width: 90%; max-width: 600px;
  max-height: 85vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.mp-modal-lg { max-width: 720px; }
.mp-modal-xl { max-width: 780px; }
.mp-modal-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--border-lighter, #f0f0f0);
}
.mp-modal-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; padding: 8px; box-sizing: border-box;
  font-size: 22px; font-weight: 700; color: #fff;
}
.mp-modal-icon span { font-size: 22px; font-weight: 700; color: #fff; }
.mp-modal-foot {
  display: flex; align-items: center; justify-content: flex-end; gap: 10px;
  padding: 16px 24px; border-top: 1px solid var(--border-lighter, #f0f0f0);
}
.mp-modal-foot-split { justify-content: space-between; }
.mp-modal-actions { display: flex; gap: 10px; }

/* ========== 帮助框 ========== */
.mp-help-box {
  display: flex; align-items: center; gap: 8px;
  background: var(--blue-bg, #e6f4ff); border: 1px solid var(--blue-border, #91caff);
  border-radius: 8px; padding: 10px 14px; font-size: 13px; color: var(--text-2);
  margin-bottom: 18px;
}
.mp-help-icon { font-size: 16px; }
.mp-help-link { color: var(--primary); margin-left: auto; white-space: nowrap; }

/* ========== 详情区块 ========== */
.mp-detail-section { margin-bottom: 20px; }
.mp-detail-label { font-size: 14px; font-weight: 600; color: var(--text-1); margin-bottom: 10px; }
.mp-detail-types { display: flex; gap: 6px; flex-wrap: wrap; }

/* ========== 模型表格 ========== */
.mp-model-table { border: 1px solid var(--border-light); border-radius: 8px; overflow: hidden; }
.mp-model-row {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 10px;
  padding: 10px 14px; font-size: 13px; align-items: center;
  border-bottom: 1px solid var(--border-lighter, #f5f5f5);
}
.mp-model-row:last-child { border-bottom: none; }
.mp-model-header { background: #fafafa; font-weight: 600; color: var(--text-2); font-size: 12px; }
.mp-model-col-name { display: flex; flex-direction: column; }
.mp-model-col-name small { color: var(--text-3); font-size: 11px; }
.mp-model-col-cap { display: flex; gap: 6px; font-size: 14px; }

/* ========== 表单 ========== */
.mp-form-item { margin-bottom: 16px; }
.mp-form-label { display: block; font-size: 13px; font-weight: 500; color: var(--text-1); margin-bottom: 6px; }
.mp-req { color: var(--red); }
.mp-form-input {
  width: 100%; padding: 8px 12px; border: 1px solid var(--border-light);
  border-radius: 6px; font-size: 14px; color: var(--text-1); background: #fff;
  transition: border-color 0.2s; box-sizing: border-box;
}
.mp-form-input:focus { outline: none; border-color: var(--primary); }
.mp-form-input.error { border-color: var(--red); }
.mp-form-hint { font-size: 12px; color: var(--text-3); margin-top: 4px; }
.mp-form-error { font-size: 12px; color: var(--red); margin-top: 4px; }
.mp-input-group { position: relative; display: flex; align-items: center; }
.mp-input-group .mp-form-input { padding-right: 40px; }
.mp-input-toggle {
  position: absolute; right: 8px; background: none; border: none;
  cursor: pointer; font-size: 16px; padding: 4px;
}

/* ========== 折叠区块 ========== */
.mp-form-section { border: 1px solid var(--border-light); border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
.mp-form-section-title {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; font-size: 13px; font-weight: 500; color: var(--text-1);
  cursor: pointer; background: #fafafa; user-select: none;
}
.mp-collapse-arrow { font-size: 10px; transition: transform 0.2s; display: inline-block; }
.mp-collapse-arrow.open { transform: rotate(90deg); }
.mp-form-section-hint { font-size: 11px; color: var(--text-3); margin-left: auto; }

/* ========== 参数网格 ========== */
.mp-params-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
  padding: 14px;
}
.mp-params-grid .mp-form-item { margin-bottom: 0; }
.mp-params-grid .mp-form-label { font-size: 12px; }

/* ========== 能力选择 ========== */
.mp-cap-grid { display: flex; gap: 16px; padding: 14px; flex-wrap: wrap; }
.mp-cap-item {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  font-size: 13px; color: var(--text-2);
}
.mp-cap-item input[type="checkbox"] { display: none; }
.mp-cap-check {
  width: 16px; height: 16px; border: 1.5px solid var(--border);
  border-radius: 4px; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; flex-shrink: 0;
}
.mp-cap-item input:checked + .mp-cap-check { background: var(--primary); border-color: var(--primary); }
.mp-cap-item input:checked + .mp-cap-check::after { content: '✓'; color: #fff; font-size: 11px; }
.mp-cap-icon { font-size: 16px; }

/* ========== 测试结果 ========== */
.mp-test-area { font-size: 13px; }
.mp-test-ok { color: var(--green); }
.mp-test-fail { color: var(--red); }
.mp-test-ok small, .mp-test-fail small { color: var(--text-3); margin-left: 4px; }

/* ========== 安全提示 ========== */
.mp-secure {
  background: #F7F8FA; color: var(--text-2); font-size: 12px;
  text-align: center; padding: 10px 20px; border-radius: 0 0 12px 12px;
}
.mp-secure b { color: var(--primary); font-weight: 500; }

/* ========== 空状态 ========== */
.mp-empty { text-align: center; padding: 60px 0; color: var(--text-3); }
.mp-empty-icon { font-size: 40px; margin-bottom: 12px; }
.mp-empty-text { font-size: 14px; }
.mp-empty-sm { padding: 30px 0; }

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .mp-modal { width: 95%; max-height: 90vh; }
  .mp-params-grid { grid-template-columns: 1fr; }
  .mp-provider-grid { grid-template-columns: repeat(2, 1fr); }
  .mp-installed-grid { grid-template-columns: repeat(2, 1fr); }
  .mp-model-row { grid-template-columns: 1fr 1fr; gap: 6px; }
  .mp-model-col-ctx, .mp-model-col-cap { display: none; }
}
</style>.sup
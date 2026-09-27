<template>
  <div id="page-root" class="page-root knowledge-detail-root">
    <!-- 加载态 -->
    <div class="kd-loading" v-if="!dataset.id && !loadError">
      <div class="kd-spinner"></div>
      <div class="kd-loading-t">加载知识库信息...</div>
    </div>
    <!-- 错误态 -->
    <div class="kd-loading" v-else-if="loadError">
      <div class="kd-load-error">⚠ {{ loadError }}</div>
      <button class="btn" style="margin-top:14px;" @click="loadDataset">重新加载</button>
      <button class="btn" style="margin-top:14px;margin-left:10px;" @click="goBack">返回列表</button>
    </div>
    <div class="kd-shell" v-else>
      <!-- 左窄栏 -->
      <aside class="kd-side">
        <div class="kd-side-top">
          <button class="kd-back" title="返回" @click="goBack">‹</button>
          <span class="kd-home" title="首页" @click="goHome"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg></span>
          <span class="kd-crumb">/ 知识库</span>
        </div>

        <div class="kd-kb">
          <span class="ava">🤖</span>
          <span class="nm">{{ dataset.name || '加载中...' }}</span>
        </div>

        <nav class="kd-menu" id="kdMenu">
          <div class="kd-mitem" :class="{ active: activeTab === 'documents' }" @click="activeTab = 'documents'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h8l4 4v14H6V3z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 16h6"/></svg></span>文档
          </div>
          <div class="kd-mitem" :class="{ active: activeTab === 'segments' }" @click="activeTab = 'segments'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/></svg></span>分段管理
          </div>
          <div class="kd-mitem" :class="{ active: activeTab === 'recall' }" @click="activeTab = 'recall'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor"/></svg></span>召回测试
          </div>
          <div class="kd-mitem" :class="{ active: activeTab === 'import' }" @click="activeTab = 'import'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 4v12M6 10l6 6 6-6M4 20h16"/></svg></span>导入数据
          </div>
          <div class="kd-mitem" :class="{ active: activeTab === 'metadata' }" @click="activeTab = 'metadata'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg></span>元数据
          </div>
          <div class="kd-mitem" :class="{ active: activeTab === 'keywords' }" @click="activeTab = 'keywords'">
            <span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/><path d="M11 8v6M8 11h6"/></svg></span>关键词索引
          </div>
        </nav>

        <div class="kd-stats">
          <!-- 后端给的是下划线名 doc_count；以前读 dataset.docCount（驼峰）永远是 undefined，
               导致列表有文档而顶部计数恒显示 0。拿不到字段时退回表格里实际列出的条数。 -->
          <div class="kd-stat"><div class="n">{{ documents.length || dataset.doc_count || 0 }}</div><div class="l">文档</div></div>
          <div class="kd-stat"><div class="n">{{ totalSegments }}</div><div class="l">分段</div></div>
        </div>
      </aside>

      <!-- 主区：文档列表 -->
      <main class="kd-main" v-if="activeTab === 'documents'">
        <div class="kd-title">文档</div>
        <div class="kd-sub">知识库的所有文件都在这里显示，整个知识库都可以通过 Chat 插件进行索引。</div>

        <div class="kd-toolbar">
          <span class="search-input" style="min-width:200px;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
            <input placeholder="搜索文档" v-model="searchQuery">
          </span>
          <span class="right">
            <button class="btn btn-primary" @click="goCreate">＋ 添加文件</button>
          </span>
        </div>

        <!-- 空态 -->
        <div class="kd-empty" v-if="documents.length === 0">
          <div class="kd-empty-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/><path d="M12 11v6M9 14h6"/></svg></div>
          <div class="kd-empty-t">还没有文档</div>
          <div class="kd-empty-d">您可以上传文件，从网站同步，或者从 Notion 导入。</div>
          <button class="btn" style="color:var(--primary);border-color:#B8CCFF;" @click="goCreate">＋ 添加文件</button>
        </div>

        <!-- 文档表格 -->
        <div class="table-wrap" v-if="documents.length > 0">
          <table class="tbl">
            <thead><tr><th>名称</th><th>字数</th><th>分段数</th><th>上传时间</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="doc in filteredDocuments" :key="doc.id">
                <td>📄 {{ doc.name }}</td>
                <td>{{ doc.word_count || 0 }}</td>
                <td>{{ doc.segment_count || 0 }}</td>
                <td>{{ formatDate(doc.created_at) }}</td>
                <td><span class="tag tag-green" v-if="doc.indexing_status === 'completed'">✅ 可用</span>
                    <span class="tag tag-yellow" v-else>⏳ 处理中</span></td>
                <td>
                  <a class="link" @click="viewSegments(doc)">分段</a>
                  <a class="link link-red" @click="deleteDoc(doc)">删除</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>

      <!-- 主区：分段管理 -->
      <main class="kd-main" v-if="activeTab === 'segments'">
        <div class="kd-title">分段管理</div>
        <div class="kd-sub" v-if="currentDoc">文档：{{ currentDoc.name }}（{{ segments.length }} 个分段）</div>
        <div class="kd-sub" v-else>请从文档列表选择一个文档查看分段</div>

        <div class="kd-toolbar">
          <button class="btn" @click="activeTab = 'documents'">← 返回文档</button>
          <span class="right">
            <button class="btn btn-primary" @click="addSegment" v-if="currentDoc">＋ 添加分段</button>
          </span>
        </div>

        <!-- 分段加载中 -->
        <div class="kd-loading" v-if="segmentsLoading" style="height:200px;">
          <div class="kd-spinner"></div>
          <div class="kd-loading-t">加载分段中...</div>
        </div>

        <!-- 分段列表 -->
        <div class="table-wrap" v-else-if="segments.length > 0">
          <table class="tbl">
            <thead><tr><th>#</th><th>内容</th><th>类型</th><th>字数</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="(seg, idx) in segments" :key="seg.id">
                <td>{{ idx + 1 }}</td>
                <td class="seg-content">
                  <div v-if="editingSegId !== seg.id">{{ seg.content }}</div>
                  <textarea v-else v-model="editContent" class="seg-edit" rows="3"></textarea>
                </td>
                <td>
                  <span class="tag" :class="seg.segment_type === 'qa' ? 'tag-blue' : (seg.segment_type === 'child' ? 'tag-green' : '')">
                    {{ seg.segment_type === 'qa' ? 'Q&A' : (seg.segment_type === 'child' ? '子段落' : (seg.segment_type === 'parent' ? '父段落' : '通用')) }}
                  </span>
                </td>
                <td>{{ seg.word_count || 0 }}</td>
                <td>
                  <template v-if="editingSegId !== seg.id">
                    <a class="link" @click="startEdit(seg)">编辑</a>
                    <a class="link link-red" @click="deleteSegment(seg)">删除</a>
                  </template>
                  <template v-else>
                    <a class="link" @click="saveEdit(seg)">保存</a>
                    <a class="link" @click="cancelEdit">取消</a>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="kd-empty" v-else-if="currentDoc && !segmentsLoading">
          <div class="kd-empty-t">该文档暂无分段</div>
        </div>
      </main>

      <!-- 主区：召回测试 -->
      <main class="kd-main" v-if="activeTab === 'recall'">
        <div class="kd-title">召回测试</div>
        <div class="kd-sub">测试知识库的检索效果，输入问题查看匹配的分段。</div>

        <div class="recall-box">
          <div class="recall-input">
            <input v-model="recallQuery" placeholder="输入测试问题，如：产品有哪些功能？" @keyup.enter="runRecallTest">
            <label class="recall-rerank">
              <input type="checkbox" v-model="recallUseRerank"> 使用 Rerank
            </label>
            <button class="btn btn-primary" @click="runRecallTest" :disabled="recallLoading">
              {{ recallLoading ? '检索中...' : '测试' }}
            </button>
          </div>

          <!-- 元数据过滤 -->
          <div class="recall-metadata-filter" v-if="metadataFields.length > 0">
            <div class="rmf-header" @click="showMetadataFilter = !showMetadataFilter">
              <span>🔍 元数据过滤（{{ activeMetadataFilters.length }} 个活跃条件）</span>
              <span class="rmf-toggle">{{ showMetadataFilter ? '▲' : '▼' }}</span>
            </div>
            <div v-if="showMetadataFilter" class="rmf-body">
              <div v-for="field in metadataFields" :key="field.id" class="rmf-field">
                <label>{{ field.name }}</label>
                <select v-model="metadataFilterValues[field.name]" class="rmf-select">
                  <option value="">全部</option>
                  <option value="__not_empty__">非空</option>
                  <option v-for="val in getMetadataValues(field.name)" :key="val" :value="val">{{ val }}</option>
                </select>
              </div>
              <button class="btn btn-sm" @click="clearMetadataFilters" v-if="activeMetadataFilters.length > 0">清除过滤</button>
            </div>
          </div>

          <div class="recall-results" v-if="recallResults.length > 0">
            <div class="recall-info">共 {{ recallTotalSegments }} 个分段，匹配到 {{ recallResults.length }} 个结果</div>
            <div class="recall-item" v-for="(item, idx) in recallResults" :key="item.id">
              <div class="recall-rank">#{{ idx + 1 }}</div>
              <div class="recall-content">
                <div class="recall-text">{{ item.content }}</div>
                <div class="recall-meta">
                  <span class="tag" :class="item.segment_type === 'qa' ? 'tag-blue' : 'tag-green'">
                    {{ item.segment_type === 'qa' ? 'Q&A' : item.segment_type || '通用' }}
                  </span>
                  <span class="recall-score" v-if="item.score !== undefined">匹配度: {{ (item.score * 100).toFixed(1) }}%</span>
                  <span class="recall-score" v-if="item.rerank_score !== undefined">Rerank: {{ (item.rerank_score * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
          <div class="kd-empty" v-else-if="recallLoaded">
            <div class="kd-empty-t">没有匹配的结果</div>
          </div>
        </div>
      </main>

      <!-- 主区：导入数据 -->
      <main class="kd-main" v-if="activeTab === 'import'">
        <div class="kd-title">导入数据</div>
        <div class="kd-sub">从 Notion 或网站导入文档到知识库。</div>

        <div class="import-section">
          <h3>从 Notion 导入</h3>
          <div class="import-form">
            <label>Notion Token</label>
            <input v-model="notionToken" placeholder="secret_xxxxx" type="password">
            <label>页面 ID</label>
            <input v-model="notionPageId" placeholder="页面 ID（UUID）">
            <button class="btn btn-primary" @click="importNotion" :disabled="importLoading">
              {{ importLoading ? '导入中...' : '导入' }}
            </button>
          </div>
        </div>

        <div class="import-section">
          <h3>从网站导入</h3>
          <div class="import-form">
            <label>网站 URL</label>
            <input v-model="websiteUrl" placeholder="https://example.com">
            <label>CSS 选择器（可选）</label>
            <input v-model="websiteSelector" placeholder="如：.content 或 #main">
            <button class="btn btn-primary" @click="importWebsite" :disabled="importLoading">
              {{ importLoading ? '导入中...' : '导入' }}
            </button>
          </div>
        </div>
      </main>

      <!-- 主区：元数据管理 -->
      <main class="kd-main" v-if="activeTab === 'metadata'">
        <div class="kd-title">元数据管理</div>
        <div class="kd-sub">为数据集定义结构化元数据字段，并绑定到分段，实现精确检索过滤。</div>

        <!-- 字段定义区 -->
        <div class="metadata-section">
          <h3>元数据字段</h3>
          <div class="metadata-add-form">
            <input v-model="newMetaName" placeholder="字段名（如：部门）" class="meta-input">
            <select v-model="newMetaType" class="meta-select">
              <option value="string">文本</option>
              <option value="number">数字</option>
              <option value="date">日期</option>
              <option value="enum">枚举</option>
            </select>
            <input v-model="newMetaDesc" placeholder="说明（可选）" class="meta-input meta-desc">
            <button class="btn btn-primary" @click="addMetadataField" :disabled="!newMetaName.trim()">添加字段</button>
          </div>

          <div class="metadata-fields-list" v-if="metadataFields.length > 0">
            <div class="metadata-field-item" v-for="f in metadataFields" :key="f.id">
              <div class="mf-info">
                <span class="mf-name">{{ f.name }}</span>
                <span class="mf-type">{{ {string: '文本', number: '数字', date: '日期', enum: '枚举'}[f.type] || f.type }}</span>
                <span class="mf-desc" v-if="f.description">{{ f.description }}</span>
              </div>
              <div class="mf-actions">
                <button class="btn btn-sm" @click="editField(f)">编辑</button>
                <button class="btn btn-sm btn-danger" @click="deleteField(f)">删除</button>
              </div>
            </div>
          </div>
          <div class="kd-empty" v-else>
            <div class="kd-empty-t">暂无元数据字段</div>
            <div class="kd-empty-d">添加字段后，可在分段管理中绑定元数据值。</div>
          </div>
        </div>

        <!-- 分段绑定区 -->
        <div class="metadata-section" v-if="metadataFields.length > 0 && segments.length > 0">
          <h3>分段元数据绑定</h3>
          <div class="metadata-bind-list">
            <div class="metadata-bind-item" v-for="seg in segments" :key="seg.id">
              <div class="mb-seg-content">{{ (seg.content || '').substring(0, 80) }}...</div>
              <div class="mb-bindings">
                <div class="mb-binding" v-for="f in metadataFields" :key="f.id">
                  <label>{{ f.name }}:</label>
                  <input
                    :value="getSegmentMetaValue(seg.id, f.name)"
                    @blur="updateSegmentMeta(seg.id, f.name, $event.target.value)"
                    :placeholder="'输入' + f.name"
                    class="meta-bind-input"
                  >
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <!-- 主区：关键词索引管理 -->
      <main class="kd-main" v-if="activeTab === 'keywords'">
        <div class="kd-title">关键词索引</div>
        <div class="kd-sub">使用 jieba 分词为分段建立关键词索引，支持向量+关键词混合检索，提升中文检索精度。</div>

        <!-- 索引状态卡片 -->
        <div class="keyword-stats-cards">
          <div class="keyword-stat-card">
            <div class="ksc-number">{{ keywordStats.keyword_count || 0 }}</div>
            <div class="ksc-label">索引关键词</div>
          </div>
          <div class="keyword-stat-card">
            <div class="ksc-number">{{ keywordStats.indexed_segments || 0 }}</div>
            <div class="ksc-label">已索引分段</div>
          </div>
          <div class="keyword-stat-card">
            <div class="ksc-number">{{ totalSegments }}</div>
            <div class="ksc-label">总分段数</div>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="keyword-actions">
          <button class="btn btn-primary" @click="buildKeywordIndex" :disabled="keywordBuilding">
            {{ keywordBuilding ? '构建中...' : '重建关键词索引' }}
          </button>
          <button class="btn" @click="loadKeywordStats" :disabled="keywordBuilding">刷新统计</button>
        </div>

        <!-- 关键词检索测试 -->
        <div class="keyword-section">
          <h3>关键词检索测试</h3>
          <div class="keyword-search-box">
            <input v-model="keywordTestQuery" placeholder="输入测试关键词，如：人工智能" @keyup.enter="runKeywordTest">
            <button class="btn btn-primary" @click="runKeywordTest" :disabled="keywordTestLoading">
              {{ keywordTestLoading ? '检索中...' : '测试' }}
            </button>
          </div>
          <div class="keyword-test-results" v-if="keywordTestResults.length > 0">
            <div class="keyword-test-info">匹配到 {{ keywordTestResults.length }} 个结果</div>
            <div class="keyword-result-item" v-for="(item, idx) in keywordTestResults" :key="item.segment_id">
              <div class="kri-rank">#{{ idx + 1 }}</div>
              <div class="kri-body">
                <div class="kri-content">{{ item.content || '(已删除)' }}</div>
                <div class="kri-meta">
                  <span class="tag tag-green" v-if="item.matched_keywords && item.matched_keywords.length > 0">
                    匹配: {{ item.matched_keywords.join(', ') }}
                  </span>
                  <span class="kri-score">得分: {{ (item.score * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
          <div class="kd-empty" v-else-if="keywordTestLoaded">
            <div class="kd-empty-t">没有匹配的结果</div>
            <div class="kd-empty-d">请先构建关键词索引，或尝试其他关键词。</div>
          </div>
        </div>
      </main>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api, { apiPost } from '../api/client'
import { toast } from '../utils/global'

const props = defineProps({
  id: String
})

const dataset = ref({})
const documents = ref([])
const segments = ref([])
const loadError = ref('')
const currentDoc = ref(null)
const activeTab = ref('documents')
const searchQuery = ref('')
const totalSegments = ref(0)
const segmentsLoading = ref(false)

// 分段编辑
const editingSegId = ref(null)
const editContent = ref('')

// 召回测试
const recallQuery = ref('')
const recallUseRerank = ref(false)
const recallResults = ref([])
const recallTotalSegments = ref(0)
const recallLoading = ref(false)
const recallLoaded = ref(false)
const showMetadataFilter = ref(false)
const metadataFilterValues = ref({})  // {fieldName: value}
const metadataValueCache = ref({})  // {fieldName: [values]}

// 计算活跃的元数据过滤条件
const activeMetadataFilters = computed(() => {
  const filters = []
  for (const [name, value] of Object.entries(metadataFilterValues.value)) {
    if (value) {
      filters.push({ name, value, operator: value === '__not_empty__' ? 'not_empty' : 'eq' })
    }
  }
  return filters
})

// 获取元数据字段的所有可用值
function getMetadataValues(fieldName) {
  if (!metadataValueCache.value[fieldName]) {
    // 从已加载的分段元数据中收集值
    const values = new Set()
    for (const segMeta of Object.values(segmentMetaMap.value)) {
      if (segMeta[fieldName]) values.add(segMeta[fieldName])
    }
    metadataValueCache.value[fieldName] = Array.from(values).slice(0, 20)
  }
  return metadataValueCache.value[fieldName] || []
}

function clearMetadataFilters() {
  metadataFilterValues.value = {}
}

// 导入
const notionToken = ref('')
const notionPageId = ref('')
const websiteUrl = ref('')
const websiteSelector = ref('')
const importLoading = ref(false)

// 元数据管理
const metadataFields = ref([])
const newMetaName = ref('')
const newMetaType = ref('string')
const newMetaDesc = ref('')
const segmentMetaMap = ref({})  // {segmentId: {fieldName: value}}

// 关键词索引（3.2）
const keywordStats = ref({ keyword_count: 0, indexed_segments: 0 })
const keywordBuilding = ref(false)
const keywordTestQuery = ref('')
const keywordTestResults = ref([])
const keywordTestLoading = ref(false)
const keywordTestLoaded = ref(false)

const filteredDocuments = computed(() => {
  if (!searchQuery.value) return documents.value
  const q = searchQuery.value.toLowerCase()
  return documents.value.filter(d => (d.name || '').toLowerCase().includes(q))
})

function goBack() { location.hash = '/knowledge' }
function goHome() { location.hash = '/home' }
function goCreate() { location.hash = '/knowledge-create' }

function formatDate(dt) {
  if (!dt) return ''
  try {
    const d = new Date(dt)
    return d.toLocaleString('zh-CN')
  } catch (e) { return dt }
}

async function loadDataset() {
  loadError.value = ''
  const datasetId = props.id || location.hash.split('/').pop()
  if (!datasetId || datasetId === 'knowledge-detail' || datasetId === 'knowledge') {
    loadError.value = '知识库 ID 缺失，请从列表页进入'
    return
  }
  try {
    const res = await api.get(`/api/knowledge/datasets/${datasetId}`)
    if (res.code === 200) {
      dataset.value = res.data
      documents.value = res.data.documents || []
      // 并发获取分段数（不阻塞渲染）
      await Promise.allSettled(documents.value.map(async (doc) => {
        try {
          const segRes = await api.get(`/api/knowledge/datasets/${datasetId}/documents/${doc.id}/segments`)
          if (segRes.code === 200) {
            doc.segment_count = segRes.data.total || 0
            totalSegments.value += doc.segment_count
          }
        } catch (e) { /* ignore */ }
      }))
    } else {
      loadError.value = res.msg || '加载失败'
    }
  } catch (e) {
    loadError.value = '加载知识库失败: ' + (e.message || e)
  }
}

async function viewSegments(doc) {
  currentDoc.value = doc
  activeTab.value = 'segments'
  segmentsLoading.value = true
  await loadSegments(doc.id)
  segmentsLoading.value = false
}

async function loadSegments(docId) {
  const datasetId = props.id || location.hash.split('/').pop()
  try {
    const res = await api.get(`/api/knowledge/datasets/${datasetId}/documents/${docId}/segments`)
    if (res.code === 200) {
      segments.value = res.data.segments || []
    } else {
      toast(res.msg || '加载分段失败')
    }
  } catch (e) {
    toast('加载分段失败')
  }
}

function startEdit(seg) {
  editingSegId.value = seg.id
  editContent.value = seg.content
}

function cancelEdit() {
  editingSegId.value = null
  editContent.value = ''
}

async function saveEdit(seg) {
  try {
    const res = await api.put(`/api/knowledge/segments/${seg.id}`, { content: editContent.value })
    if (res.code === 200) {
      toast('保存成功')
      seg.content = editContent.value
      seg.word_count = editContent.value.replace(/\n/g, '').replace(/ /g, '').length
      cancelEdit()
    } else {
      toast(res.msg || '保存失败')
    }
  } catch (e) {
    toast('保存失败')
  }
}

async function addSegment() {
  const content = prompt('请输入分段内容：')
  if (!content || !content.trim()) return
  try {
    const res = await api.post('/api/knowledge/segments', {
      document_id: currentDoc.value.id,
      content: content.trim()
    })
    if (res.code === 200) {
      toast('添加成功')
      await loadSegments(currentDoc.value.id)
    } else {
      toast(res.msg || '添加失败')
    }
  } catch (e) {
    toast('添加失败')
  }
}

async function deleteSegment(seg) {
  if (!confirm('确定要删除该分段吗？')) return
  try {
    const res = await api.delete(`/api/knowledge/segments/${seg.id}`)
    if (res.code === 200) {
      toast('删除成功')
      segments.value = segments.value.filter(s => s.id !== seg.id)
    } else {
      toast(res.msg || '删除失败')
    }
  } catch (e) {
    toast('删除失败')
  }
}

async function deleteDoc(doc) {
  if (!confirm(`确定要删除文档「${doc.name}」吗？`)) return
  try {
    const res = await api.delete(`/api/knowledge/datasets/${dataset.value.id}/documents/${doc.id}`)
    if (res.code === 200) {
      toast('删除成功')
      documents.value = documents.value.filter(d => d.id !== doc.id)
    } else {
      toast(res.msg || '删除失败')
    }
  } catch (e) {
    toast('删除失败')
  }
}

async function runRecallTest() {
  if (!recallQuery.value.trim()) {
    toast('请输入测试问题')
    return
  }
  recallLoading.value = true
  recallLoaded.value = false
  try {
    const res = await apiPost('/api/knowledge/recall-test', {
      dataset_id: dataset.value.id,
      query: recallQuery.value.trim(),
      top_k: 10,
      use_rerank: recallUseRerank.value,
      metadata_filters: activeMetadataFilters.value,
    })
    if (res.code === 200) {
      recallResults.value = res.data.results || []
      recallTotalSegments.value = res.data.total_segments || 0
      recallLoaded.value = true
    } else {
      toast(res.msg || '测试失败')
    }
  } catch (e) {
    toast('召回测试失败')
  } finally {
    recallLoading.value = false
  }
}

async function importNotion() {
  if (!notionToken.value.trim() || !notionPageId.value.trim()) {
    toast('请填写 Notion Token 和页面 ID')
    return
  }
  importLoading.value = true
  try {
    const res = await api.post('/api/knowledge/import/notion', {
      notion_token: notionToken.value.trim(),
      page_id: notionPageId.value.trim(),
      dataset_id: dataset.value.id
    })
    if (res.code === 200) {
      toast(`导入成功，共 ${res.data.segment_count} 个分段`)
      notionToken.value = ''
      notionPageId.value = ''
      loadDataset()
    } else {
      toast(res.msg || '导入失败')
    }
  } catch (e) {
    toast('导入失败')
  } finally {
    importLoading.value = false
  }
}

async function importWebsite() {
  if (!websiteUrl.value.trim()) {
    toast('请填写网站 URL')
    return
  }
  importLoading.value = true
  try {
    const res = await api.post('/api/knowledge/import/website', {
      url: websiteUrl.value.trim(),
      selector: websiteSelector.value.trim() || undefined,
      dataset_id: dataset.value.id
    })
    if (res.code === 200) {
      toast(`导入成功，共 ${res.data.segment_count} 个分段`)
      websiteUrl.value = ''
      websiteSelector.value = ''
      loadDataset()
    } else {
      toast(res.msg || '导入失败')
    }
  } catch (e) {
    toast('导入失败')
  } finally {
    importLoading.value = false
  }
}

// ============================================================
// 元数据管理
// ============================================================

async function loadMetadataFields() {
  const datasetId = props.id || location.hash.split('/').pop()
  try {
    const res = await api.get(`/api/knowledge/datasets/${datasetId}/metadata-fields`)
    if (res.code === 200) {
      metadataFields.value = res.data || []
    }
  } catch (e) { /* ignore */ }
}

async function addMetadataField() {
  const datasetId = props.id || location.hash.split('/').pop()
  if (!newMetaName.value.trim()) return
  try {
    const res = await api.post(`/api/knowledge/datasets/${datasetId}/metadata-fields`, {
      name: newMetaName.value.trim(),
      type: newMetaType.value,
      description: newMetaDesc.value.trim()
    })
    if (res.code === 200) {
      toast('字段创建成功')
      newMetaName.value = ''
      newMetaDesc.value = ''
      await loadMetadataFields()
    } else {
      toast(res.msg || '创建失败')
    }
  } catch (e) {
    toast('创建失败')
  }
}

async function editField(f) {
  const newName = prompt('字段名：', f.name)
  if (newName === null) return
  const newDesc = prompt('说明：', f.description || '')
  if (newDesc === null) return
  const datasetId = props.id || location.hash.split('/').pop()
  try {
    const res = await api.put(`/api/knowledge/datasets/${datasetId}/metadata-fields/${f.id}`, {
      name: newName.trim(),
      description: newDesc.trim()
    })
    if (res.code === 200) {
      toast('更新成功')
      await loadMetadataFields()
    } else {
      toast(res.msg || '更新失败')
    }
  } catch (e) {
    toast('更新失败')
  }
}

async function deleteField(f) {
  if (!confirm(`确定删除字段「${f.name}」吗？相关绑定也会被删除。`)) return
  const datasetId = props.id || location.hash.split('/').pop()
  try {
    const res = await api.delete(`/api/knowledge/datasets/${datasetId}/metadata-fields/${f.id}`)
    if (res.code === 200) {
      toast('删除成功')
      await loadMetadataFields()
    } else {
      toast(res.msg || '删除失败')
    }
  } catch (e) {
    toast('删除失败')
  }
}

function getSegmentMetaValue(segId, fieldName) {
  return segmentMetaMap.value[segId]?.[fieldName] || ''
}

async function updateSegmentMeta(segId, fieldName, value) {
  const datasetId = props.id || location.hash.split('/').pop()
  // 获取当前所有绑定
  const current = segmentMetaMap.value[segId] || {}
  const updated = { ...current, [fieldName]: value }
  // 移除空值
  if (!value.trim()) {
    delete updated[fieldName]
  }
  try {
    const res = await api.put(`/api/knowledge/datasets/${datasetId}/segments/${segId}/metadata`, {
      metadata: updated
    })
    if (res.code === 200) {
      // 更新本地缓存
      segmentMetaMap.value[segId] = { ...updated }
      toast('元数据已更新')
    } else {
      toast(res.msg || '更新失败')
    }
  } catch (e) {
    toast('更新失败')
  }
}

async function loadSegmentMetadata() {
  if (!segments.value.length) return
  for (const seg of segments.value) {
    try {
      const res = await api.get(`/api/knowledge/segments/${seg.id}/metadata`)
      if (res.code === 200 && res.data) {
        segmentMetaMap.value[seg.id] = res.data
      }
    } catch (e) { /* ignore */ }
  }
}

// Watch for tab change to metadata
import { watch } from 'vue'
watch(activeTab, async (tab) => {
  if (tab === 'metadata') {
    await loadMetadataFields()
    // 加载分段（使用第一个文档）
    if (!segments.value.length && documents.value.length > 0) {
      const firstDoc = documents.value[0]
      currentDoc.value = firstDoc
      await loadSegments(firstDoc.id)
    }
    if (segments.value.length) {
      await loadSegmentMetadata()
    }
  } else if (tab === 'keywords') {
    await loadKeywordStats()
  }
})

// ============================================================
// 关键词索引管理（3.2）
// ============================================================

async function loadKeywordStats() {
  const datasetId = props.id || location.hash.split('/').pop()
  try {
    const res = await api.get(`/api/knowledge/datasets/${datasetId}/keyword-index`)
    if (res.code === 200) {
      keywordStats.value = res.data || {}
    }
  } catch (e) { /* ignore */ }
}

async function buildKeywordIndex() {
  const datasetId = props.id || location.hash.split('/').pop()
  if (!confirm('确定要重建关键词索引吗？这可能需要一些时间。')) return
  keywordBuilding.value = true
  try {
    const res = await api.post(`/api/knowledge/datasets/${datasetId}/keyword-index`, { batch_size: 100 })
    if (res.code === 200) {
      toast(`索引构建完成：${res.data.indexed_segments} 个分段，${res.data.keyword_count} 个关键词`)
      keywordStats.value = res.data
    } else {
      toast(res.msg || '构建失败')
    }
  } catch (e) {
    toast('构建失败')
  } finally {
    keywordBuilding.value = false
  }
}

async function runKeywordTest() {
  const datasetId = props.id || location.hash.split('/').pop()
  if (!keywordTestQuery.value.trim()) {
    toast('请输入测试关键词')
    return
  }
  keywordTestLoading.value = true
  keywordTestLoaded.value = false
  try {
    const res = await api.post(`/api/knowledge/datasets/${datasetId}/keyword-search`, {
      query: keywordTestQuery.value.trim(),
      top_k: 10
    })
    if (res.code === 200) {
      keywordTestResults.value = res.data.results || []
      // 补充分段内容
      for (const item of keywordTestResults.value) {
        if (!item.content) {
          try {
            const segRes = await api.get(`/api/knowledge/segments/${item.segment_id}`)
            if (segRes.code === 200) {
              item.content = segRes.data.content || ''
            }
          } catch (e) { /* ignore */ }
        }
      }
      keywordTestLoaded.value = true
    } else {
      toast(res.msg || '测试失败')
    }
  } catch (e) {
    toast('测试失败')
  } finally {
    keywordTestLoading.value = false
  }
}

onMounted(() => {
  loadDataset()
})
</script>

<style>
.knowledge-detail-root{ background:#fff; min-height:100vh; }
.kd-shell{ display:flex; height:100vh; overflow:hidden; background:#fff; }

/* ---------- 左窄栏 ---------- */
.kd-side{ width:250px; background:#F7F8FA; border-right:1px solid var(--border-light); display:flex; flex-direction:column; flex-shrink:0; }
.kd-side-top{ display:flex; align-items:center; gap:4px; padding:12px 10px 4px 14px; }
.kd-back{ width:24px; height:24px; border:none; background:none; font-size:18px; color:var(--text-1); display:inline-flex; align-items:center; justify-content:center; border-radius:6px; cursor:pointer; }
.kd-back:hover{ background:#EEF0F3; }
.kd-home{ width:24px; height:24px; color:var(--text-1); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; border-radius:6px; }
.kd-home:hover{ background:#EEF0F3; }
.kd-home svg{ width:17px; height:17px; }
.kd-crumb{ font-size:14px; font-weight:700; margin-left:2px; user-select:none; }

.kd-kb{ display:flex; align-items:center; gap:10px; margin:10px 14px 6px; padding:6px 4px; }
.kd-kb .ava{ width:38px; height:38px; border-radius:10px; background:#FBF0DC; display:flex; align-items:center; justify-content:center; font-size:21px; flex-shrink:0; }
.kd-kb .nm{ font-size:15px; font-weight:600; }

.kd-menu{ padding:6px 10px; }
.kd-mitem{ display:flex; align-items:center; gap:10px; padding:8px 10px; margin:2px 0; border-radius:8px; font-size:14px; color:var(--text-1); cursor:pointer; user-select:none; }
.kd-mitem:hover{ background:#EEF0F3; }
.kd-mitem.active{ background:var(--primary-light); color:var(--primary); font-weight:500; }
.kd-mitem .mi{ width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center; color:inherit; }
.kd-mitem .mi svg{ width:16px; height:16px; }

.kd-stats{ display:flex; gap:36px; padding:14px 20px 10px; margin-top:auto; }
.kd-stat .n{ font-size:18px; font-weight:700; }
.kd-stat .l{ font-size:12px; color:var(--text-3); margin-top:2px; }

/* ---------- 主区 ---------- */
.kd-main{ flex:1; overflow-y:auto; padding:26px 30px 60px; background:#fff; }
.kd-title{ font-size:18px; font-weight:600; }
.kd-sub{ color:var(--text-3); font-size:13px; margin-top:6px; }

.kd-toolbar{ display:flex; align-items:center; gap:10px; margin-top:18px; flex-wrap:wrap; }
.kd-toolbar .right{ margin-left:auto; display:flex; gap:10px; }

/* 空态 */
.kd-empty{ display:flex; flex-direction:column; align-items:center; padding:120px 0 140px; }
.kd-empty-ico{ width:56px; height:56px; border-radius:12px; background:#F7F8FA; border:1px solid var(--border-light); display:flex; align-items:center; justify-content:center; color:var(--text-3); margin-bottom:16px; }
.kd-empty-ico svg{ width:26px; height:26px; }
.kd-empty-t{ font-size:16px; font-weight:700; }
.kd-empty-d{ font-size:14px; color:var(--text-2); margin:10px 0 20px; }

.table-wrap{ margin-top:18px; }

/* 分段内容 */
.seg-content{ max-width:400px; }
.seg-content div{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.seg-edit{ width:100%; border:1px solid var(--primary); border-radius:6px; padding:8px; font-size:13px; resize:vertical; }

/* 召回测试 */
.recall-box{ margin-top:20px; }
.recall-input{ display:flex; align-items:center; gap:10px; }
.recall-input input[type="text"], .recall-input input:not([type]){ flex:1; padding:10px 14px; border:1px solid var(--border-light); border-radius:8px; font-size:14px; }
.recall-rerank{ display:flex; align-items:center; gap:4px; font-size:13px; color:var(--text-2); white-space:nowrap; }

.recall-results{ margin-top:20px; }
.recall-info{ font-size:13px; color:var(--text-3); margin-bottom:10px; }
.recall-item{ display:flex; gap:12px; padding:14px; border:1px solid var(--border-light); border-radius:8px; margin-bottom:10px; }
.recall-item:hover{ background:#F7F8FA; }
.recall-rank{ width:32px; height:32px; border-radius:50%; background:var(--primary-light); color:var(--primary); display:flex; align-items:center; justify-content:center; font-weight:700; flex-shrink:0; }
.recall-content{ flex:1; }
.recall-text{ font-size:14px; line-height:1.6; }
.recall-meta{ display:flex; align-items:center; gap:10px; margin-top:8px; }
.recall-score{ font-size:12px; color:var(--text-3); }

/* 元数据过滤 */
.recall-metadata-filter{ margin-top:12px; border:1px solid var(--border-light); border-radius:8px; overflow:hidden; }
.rmf-header{ display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:#F9FAFB; cursor:pointer; font-size:13px; color:var(--text-2); user-select:none; }
.rmf-header:hover{ background:#F3F4F6; }
.rmf-toggle{ font-size:10px; }
.rmf-body{ padding:14px; display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; }
.rmf-field{ display:flex; flex-direction:column; gap:4px; }
.rmf-field label{ font-size:12px; color:var(--text-3); }
.rmf-select{ padding:6px 10px; border:1px solid var(--border-light); border-radius:6px; font-size:13px; min-width:120px; }
.rmf-select:focus{ outline:none; border-color:var(--primary); }

/* 导入 */
.import-section{ margin-top:24px; padding:20px; border:1px solid var(--border-light); border-radius:10px; }
.import-section h3{ font-size:15px; font-weight:600; margin-bottom:14px; }
.import-form{ display:flex; flex-direction:column; gap:10px; }
.import-form label{ font-size:13px; color:var(--text-2); }
.import-form input{ padding:8px 12px; border:1px solid var(--border-light); border-radius:6px; font-size:14px; }
.import-form .btn{ align-self:flex-start; margin-top:6px; }

/* 标签 */
.tag{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; background:#F2F3F5; color:var(--text-2); }
.tag-green{ background:#E6F7E6; color:#16A34A; }
.tag-yellow{ background:#FEF3C7; color:#D97706; }
.tag-blue{ background:#DBEAFE; color:#2563EB; }

/* ---------- 元数据管理 ---------- */
.metadata-section{ margin-top:24px; }
.metadata-section h3{ font-size:15px; font-weight:600; margin-bottom:12px; color:var(--text-1); }
.metadata-add-form{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:16px; }
.meta-input{ padding:6px 10px; border:1px solid var(--border-light); border-radius:6px; font-size:13px; width:160px; }
.meta-input.meta-desc{ width:200px; }
.meta-select{ padding:6px 8px; border:1px solid var(--border-light); border-radius:6px; font-size:13px; }
.metadata-fields-list{ display:flex; flex-direction:column; gap:8px; }
.metadata-field-item{ display:flex; align-items:center; justify-content:space-between; padding:10px 14px; border:1px solid var(--border-light); border-radius:8px; background:#FAFBFC; }
.mf-info{ display:flex; align-items:center; gap:10px; }
.mf-name{ font-weight:600; font-size:14px; color:var(--text-1); }
.mf-type{ font-size:12px; padding:2px 8px; border-radius:4px; background:var(--primary-light); color:var(--primary); }
.mf-desc{ font-size:12px; color:var(--text-3); }
.mf-actions{ display:flex; gap:6px; }
.btn-sm{ padding:4px 10px; font-size:12px; }
.btn-danger{ color:var(--red); border-color:var(--red); }
.metadata-bind-list{ display:flex; flex-direction:column; gap:12px; }
.metadata-bind-item{ padding:12px 14px; border:1px solid var(--border-light); border-radius:8px; }
.mb-seg-content{ font-size:13px; color:var(--text-2); margin-bottom:10px; line-height:1.5; }
.mb-bindings{ display:flex; flex-wrap:wrap; gap:10px; }
.mb-binding{ display:flex; align-items:center; gap:6px; }
.mb-binding label{ font-size:12px; color:var(--text-3); white-space:nowrap; }
.meta-bind-input{ padding:4px 8px; border:1px solid var(--border-light); border-radius:4px; font-size:12px; width:140px; }

/* ---------- 关键词索引管理（3.2） ---------- */
.keyword-stats-cards{ display:flex; gap:16px; margin-top:20px; }
.keyword-stat-card{ flex:1; background:#FAFBFC; border:1px solid var(--border-light); border-radius:10px; padding:18px 20px; text-align:center; }
.ksc-number{ font-size:28px; font-weight:700; color:var(--primary); }
.ksc-label{ font-size:13px; color:var(--text-3); margin-top:4px; }
.keyword-actions{ display:flex; gap:10px; margin-top:20px; }
.keyword-section{ margin-top:28px; }
.keyword-section h3{ font-size:15px; font-weight:600; margin-bottom:12px; color:var(--text-1); }
.keyword-search-box{ display:flex; gap:10px; margin-bottom:16px; }
.keyword-search-box input{ flex:1; padding:8px 12px; border:1px solid var(--border-light); border-radius:6px; font-size:13px; }
.keyword-test-results{ display:flex; flex-direction:column; gap:10px; }
.keyword-test-info{ font-size:13px; color:var(--text-3); margin-bottom:4px; }
.keyword-result-item{ display:flex; gap:12px; padding:12px 14px; border:1px solid var(--border-light); border-radius:8px; background:#FAFBFC; }
.kri-rank{ font-size:16px; font-weight:700; color:var(--primary); min-width:32px; }
.kri-body{ flex:1; }
.kri-content{ font-size:13px; color:var(--text-2); line-height:1.5; margin-bottom:8px; }
.kri-meta{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.kri-score{ font-size:12px; color:var(--text-3); }

/* 加载态 */
.kd-loading{ display:flex; flex-direction:column; align-items:center; justify-content:center; }
.kd-spinner{ width:36px; height:36px; border:3px solid var(--border-light); border-top-color:var(--primary); border-radius:50%; animation:kd-spin 0.8s linear infinite; }
@keyframes kd-spin{ to{ transform:rotate(360deg); } }
.kd-loading-t{ margin-top:14px; color:var(--text-3); font-size:14px; }
.kd-load-error{ margin-top:14px; color:var(--red, #DC2626); font-size:14px; text-align:center; padding: 20px; }

/* 链接 */
.link{ color:var(--primary); cursor:pointer; margin-right:10px; font-size:13px; }
.link:hover{ text-decoration:underline; }
.link-red{ color:var(--red); }

/* 搜索 */
.search-input{ display:inline-flex; align-items:center; gap:6px; background:#F2F3F5; border-radius:6px; padding:6px 10px; }
.search-input svg{ width:16px; height:16px; color:var(--text-3); }
.search-input input{ border:none; background:none; outline:none; font-size:13px; min-width:160px; }

/* 按钮 */
.btn{ padding:7px 14px; border:1px solid var(--border-light); background:#fff; border-radius:6px; font-size:13px; cursor:pointer; color:var(--text-1); }
.btn:hover{ background:#F7F8FA; }
.btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
.btn-primary:hover{ background:var(--primary-dark); }
.btn-primary:disabled{ opacity:0.6; cursor:not-allowed; }
</style>

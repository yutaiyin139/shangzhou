<template>
  <div class="modal-mask show" @click.self="$emit('close')">
    <div class="ver-box" :class="{ 'ver-box--wide': diffResult }">
      <div class="ver-head">
        <span class="ver-title">{{ diffMode ? '版本对比' : '版本历史' }}</span>
        <button v-if="diffMode" class="ver-back" @click="exitDiff">← 返回</button>
        <button class="ver-close" @click="$emit('close')">✕</button>
      </div>

      <!-- Diff 结果视图 -->
      <div v-if="diffResult" class="ver-body ver-diff-body">
        <div class="ver-diff-summary">
          <span class="ver-diff-stat ver-diff-add">+{{ diffResult.summary.nodes_added }} 节点</span>
          <span class="ver-diff-stat ver-diff-rem">-{{ diffResult.summary.nodes_removed }} 节点</span>
          <span class="ver-diff-stat ver-diff-chg">~{{ diffResult.summary.nodes_changed }} 变更</span>
          <span class="ver-diff-stat ver-diff-add">+{{ diffResult.summary.edges_added }} 边</span>
          <span class="ver-diff-stat ver-diff-rem">-{{ diffResult.summary.edges_removed }} 边</span>
        </div>

        <div v-if="diffResult.nodes.added.length" class="ver-diff-section">
          <div class="ver-diff-section-title ver-diff-add">新增节点 ({{ diffResult.nodes.added.length }})</div>
          <div v-for="n in diffResult.nodes.added" :key="'a-'+n.id" class="ver-diff-item">{{ n.title }}</div>
        </div>
        <div v-if="diffResult.nodes.removed.length" class="ver-diff-section">
          <div class="ver-diff-section-title ver-diff-rem">删除节点 ({{ diffResult.nodes.removed.length }})</div>
          <div v-for="n in diffResult.nodes.removed" :key="'r-'+n.id" class="ver-diff-item">{{ n.title }}</div>
        </div>
        <div v-if="diffResult.nodes.changed.length" class="ver-diff-section">
          <div class="ver-diff-section-title ver-diff-chg">变更节点 ({{ diffResult.nodes.changed.length }})</div>
          <div v-for="n in diffResult.nodes.changed" :key="'c-'+n.id" class="ver-diff-item ver-diff-chg-item">
            <span>{{ n.title }}</span>
            <small v-for="(chg, key) in n.changes" :key="key" class="ver-diff-chg-key">{{ key }}</small>
          </div>
        </div>
        <div v-if="diffResult.edges.added.length" class="ver-diff-section">
          <div class="ver-diff-section-title ver-diff-add">新增连接 ({{ diffResult.edges.added.length }})</div>
          <div v-for="(e, i) in diffResult.edges.added" :key="'ea-'+i" class="ver-diff-item ver-diff-edge">{{ e.source }} → {{ e.target }}</div>
        </div>
        <div v-if="diffResult.edges.removed.length" class="ver-diff-section">
          <div class="ver-diff-section-title ver-diff-rem">删除连接 ({{ diffResult.edges.removed.length }})</div>
          <div v-for="(e, i) in diffResult.edges.removed" :key="'er-'+i" class="ver-diff-item ver-diff-edge">{{ e.source }} → {{ e.target }}</div>
        </div>

        <div v-if="diffResult.summary.nodes_added === 0 && diffResult.summary.nodes_removed === 0 && diffResult.summary.nodes_changed === 0 && diffResult.summary.edges_added === 0 && diffResult.summary.edges_removed === 0" class="ver-empty">
          两个版本完全相同
        </div>
      </div>

      <!-- 版本列表视图 -->
      <div v-else class="ver-body">
        <div v-if="versions.length === 0" class="ver-empty">暂无已发布的版本</div>
        <div class="ver-list-wrap">
          <div v-for="v in versions" :key="v.version_number" class="ver-item" :class="{ 'ver-item--selected': selected.includes(v.version_number) }">
            <label v-if="diffMode" class="ver-check">
              <input type="checkbox" :checked="selected.includes(v.version_number)" @change="toggleSelect(v.version_number)" />
            </label>
            <div class="ver-main">
              <div class="ver-name">{{ v.name || ('v' + v.version_number) }}</div>
              <div class="ver-meta">{{ v.created_at }} · 版本 #{{ v.version_number }}</div>
              <div v-if="v.comment" class="ver-comment">{{ v.comment }}</div>
            </div>
            <button v-if="!diffMode" class="ver-restore" :disabled="restoring === v.version_number" @click="restore(v)">
              {{ restoring === v.version_number ? '恢复中…' : '恢复' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div v-if="!diffResult" class="ver-foot">
        <button class="ver-btn ver-btn-diff" :disabled="versions.length < 2" @click="enterDiff">对比版本</button>
      </div>
      <div v-else class="ver-foot">
        <button class="ver-btn" @click="exitDiff">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { authFetch } from '../../api/client'
import { toast } from '../../utils/global'

const props = defineProps({
  appId: { type: String, required: true }
})
const emit = defineEmits(['close', 'restored'])

const versions = ref([])
const restoring = ref(null)
const diffMode = ref(false)
const selected = ref([])
const diffResult = ref(null)

async function load() {
  try {
    const r = await authFetch('/api/workflows/' + encodeURIComponent(props.appId) + '/versions')
    const res = await r.json()
    if (res.code === 200) versions.value = res.data || []
  } catch (e) {}
}

async function restore(v) {
  restoring.value = v.version_number
  try {
    const r = await authFetch('/api/workflows/' + encodeURIComponent(props.appId) + '/versions/' + v.version_number + '/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    const res = await r.json()
    if (res.code === 200) {
      toast('已恢复到版本 #' + v.version_number)
      emit('restored')
      emit('close')
    } else {
      toast(res.msg || '恢复失败')
    }
  } catch (e) { toast('恢复失败') } finally { restoring.value = null }
}

function enterDiff() {
  diffMode.value = true
  selected.value = []
  diffResult.value = null
}

function exitDiff() {
  diffMode.value = false
  selected.value = []
  diffResult.value = null
}

function toggleSelect(vid) {
  const idx = selected.value.indexOf(vid)
  if (idx > -1) {
    selected.value.splice(idx, 1)
  } else if (selected.value.length >= 2) {
    // 已选 2 个，替换最早的一个
    selected.value.shift()
    selected.value.push(vid)
  } else {
    selected.value.push(vid)
  }
  // 选满 2 个自动触发对比
  if (selected.value.length === 2) {
    runDiff()
  } else {
    diffResult.value = null
  }
}

async function runDiff() {
  if (selected.value.length !== 2) return
  try {
    const r = await authFetch('/api/workflows/' + encodeURIComponent(props.appId) + '/versions/diff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vid_a: selected.value[0], vid_b: selected.value[1] })
    })
    const res = await r.json()
    if (res.code === 200) {
      diffResult.value = res.data
    } else {
      toast(res.msg || '对比失败')
    }
  } catch (e) { toast('对比失败') }
}

onMounted(load)
</script>

<style scoped>
.modal-mask{ position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 300; display: flex; align-items: center; justify-content: center; }
.ver-box{ background: #fff; border-radius: 12px; width: 480px; max-width: 92vw; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 12px 40px rgba(0,0,0,.18); }
.ver-box--wide{ width: 600px; }
.ver-head{ display: flex; align-items: center; padding: 16px 20px 0; gap: 10px; }
.ver-title{ font-size: 16px; font-weight: 700; }
.ver-back{ border: none; background: none; color: var(--primary); font-size: 13px; cursor: pointer; padding: 4px 8px; }
.ver-back:hover{ background: var(--primary-bg, rgba(22,119,255,.06)); border-radius: 4px; }
.ver-close{ margin-left: auto; border: none; background: none; font-size: 18px; color: var(--text-3); cursor: pointer; }
.ver-body{ flex: 1; overflow-y: auto; padding: 12px 20px 16px; }
.ver-empty{ color: var(--text-3); text-align: center; padding: 30px 0; font-size: 13px; }
.ver-list-wrap{ display: flex; flex-direction: column; }
.ver-item{ display: flex; align-items: center; gap: 10px; padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.ver-item:last-child{ border-bottom: none; }
.ver-item--selected{ background: var(--primary-bg, rgba(22,119,255,.04)); margin: 0 -12px; padding: 12px; border-radius: 8px; }
.ver-check{ flex-shrink: 0; display: flex; align-items: center; }
.ver-check input{ width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); }
.ver-main{ flex: 1; min-width: 0; }
.ver-name{ font-size: 14px; font-weight: 600; }
.ver-meta{ font-size: 12px; color: var(--text-3); margin-top: 3px; }
.ver-comment{ font-size: 12px; color: var(--text-2); margin-top: 3px; }
.ver-restore{ border: 1px solid var(--border); background: #fff; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: var(--primary); cursor: pointer; white-space: nowrap; }
.ver-restore:hover{ border-color: var(--primary); }
.ver-restore:disabled{ opacity: .5; cursor: not-allowed; }
.ver-foot{ display: flex; justify-content: flex-end; padding: 12px 20px; border-top: 1px solid var(--border-lighter, #f0f0f0); }
.ver-btn{ border: 1px solid var(--border); background: #fff; border-radius: 6px; padding: 7px 16px; font-size: 13px; color: var(--text-2); cursor: pointer; }
.ver-btn:hover{ border-color: var(--primary); color: var(--primary); }
.ver-btn:disabled{ opacity: .4; cursor: not-allowed; }
.ver-btn-diff{ color: var(--primary); border-color: var(--primary); background: var(--primary-bg, rgba(22,119,255,.04)); }

/* Diff 视图 */
.ver-diff-body{ padding: 16px 20px; }
.ver-diff-summary{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.ver-diff-stat{ font-size: 12px; padding: 3px 10px; border-radius: 12px; font-weight: 500; }
.ver-diff-add{ background: var(--green-bg, #f6ffed); color: var(--green, #52c41a); }
.ver-diff-rem{ background: var(--red-bg, #fff2f0); color: var(--red, #ff4d4f); }
.ver-diff-chg{ background: var(--orange-bg, #fff7e6); color: var(--orange, #fa8c16); }
.ver-diff-section{ margin-bottom: 14px; }
.ver-diff-section-title{ font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.ver-diff-item{ font-size: 13px; padding: 5px 10px; background: var(--bg-page, #fafafa); border-radius: 5px; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ver-diff-chg-item{ background: var(--orange-bg, #fff7e6); }
.ver-diff-chg-key{ font-size: 11px; background: rgba(0,0,0,.06); padding: 1px 6px; border-radius: 3px; color: var(--text-3); text-transform: uppercase; }
.ver-diff-edge{ font-family: monospace; font-size: 12px; }
</style>

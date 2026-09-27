<template>
  <div class="modal-mask show" @click.self="$emit('close')">
    <div class="vp-box">
      <div class="vp-head">
        <span class="vp-title">变量</span>
        <button class="vp-close" @click="$emit('close')">✕</button>
      </div>
      <div class="vp-body">
        <div class="vp-tabs">
          <button class="vp-tab" :class="{ active: tab === 'env' }" @click="tab = 'env'">环境变量</button>
          <button class="vp-tab" :class="{ active: tab === 'conv' }" @click="tab = 'conv'">会话变量</button>
        </div>

        <div v-if="tab === 'env'" class="vp-list">
          <div v-for="(v, key) in envVars" :key="key" class="vp-card">
            <div class="vp-card-head">
              <span class="vp-key">{{ key }}</span>
              <button class="vp-del" @click="delEnv(key)">删除</button>
            </div>
            <input class="vp-input" v-model="envVars[key]" placeholder="变量值">
          </div>
          <div class="vp-add-row">
            <input v-model="newEnvKey" placeholder="变量名">
            <input v-model="newEnvVal" placeholder="变量值">
            <button class="vp-add" @click="addEnv">添加</button>
          </div>
        </div>

        <div v-else class="vp-list">
          <div v-for="(v, key) in convVars" :key="key" class="vp-card">
            <div class="vp-card-head">
              <span class="vp-key">{{ key }}</span>
              <button class="vp-del" @click="delConv(key)">删除</button>
            </div>
            <input class="vp-input" v-model="convVars[key]" placeholder="默认值">
          </div>
          <div class="vp-add-row">
            <input v-model="newConvKey" placeholder="变量名">
            <input v-model="newConvVal" placeholder="默认值">
            <button class="vp-add" @click="addConv">添加</button>
          </div>
        </div>
      </div>
      <div class="vp-foot">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { authFetch } from '../../api/client'

const props = defineProps({
  appId: { type: String, required: true }
})
const emit = defineEmits(['close', 'saved'])

const tab = ref('env')
const envVars = ref({})
const convVars = ref({})
const newEnvKey = ref('')
const newEnvVal = ref('')
const newConvKey = ref('')
const newConvVal = ref('')
const saving = ref(false)

async function load() {
  try {
    const r = await authFetch('/api/workflows/' + encodeURIComponent(props.appId) + '/variables')
    const res = await r.json()
    if (res.code === 200) {
      envVars.value = res.data.environment_variables || {}
      convVars.value = res.data.conversation_variables || {}
    }
  } catch (e) {}
}

function addEnv() {
  if (!newEnvKey.value.trim()) return
  envVars.value[newEnvKey.value.trim()] = newEnvVal.value
  newEnvKey.value = ''
  newEnvVal.value = ''
}
function delEnv(key) { delete envVars.value[key] }
function addConv() {
  if (!newConvKey.value.trim()) return
  convVars.value[newConvKey.value.trim()] = newConvVal.value
  newConvKey.value = ''
  newConvVal.value = ''
}
function delConv(key) { delete convVars.value[key] }

async function save() {
  saving.value = true
  try {
    const r = await authFetch('/api/workflows/' + encodeURIComponent(props.appId) + '/variables', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ environment_variables: envVars.value, conversation_variables: convVars.value })
    })
    const res = await r.json()
    if (res.code === 200) {
      emit('saved', { environment_variables: envVars.value, conversation_variables: convVars.value })
      emit('close')
    }
  } catch (e) {} finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.modal-mask{ position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 300; display: flex; align-items: center; justify-content: center; }
.vp-box{ background: #fff; border-radius: 12px; width: 520px; max-width: 92vw; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 12px 40px rgba(0,0,0,.18); }
.vp-head{ display: flex; align-items: center; padding: 16px 20px 0; }
.vp-title{ font-size: 16px; font-weight: 700; }
.vp-close{ margin-left: auto; border: none; background: none; font-size: 18px; color: var(--text-3); cursor: pointer; }
.vp-body{ flex: 1; overflow-y: auto; padding: 12px 20px; }
.vp-tabs{ display: flex; gap: 8px; margin-bottom: 14px; }
.vp-tab{ border: 1px solid var(--border); background: #fff; border-radius: 8px; padding: 7px 14px; font-size: 13px; cursor: pointer; color: var(--text-2); }
.vp-tab.active{ background: var(--primary); color: #fff; border-color: var(--primary); }
.vp-list{ display: flex; flex-direction: column; gap: 10px; }
.vp-card{ background: #F7F8FA; border-radius: 8px; padding: 10px; }
.vp-card-head{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.vp-key{ font-size: 13px; font-weight: 600; }
.vp-del{ border: none; background: none; color: var(--red); font-size: 12px; cursor: pointer; }
.vp-input{ width: 100%; border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font-size: 13px; outline: none; box-sizing: border-box; }
.vp-add-row{ display: flex; gap: 8px; }
.vp-add-row input{ flex: 1; border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font-size: 13px; outline: none; }
.vp-add{ border: none; background: var(--primary); color: #fff; border-radius: 6px; padding: 7px 14px; font-size: 13px; cursor: pointer; }
.vp-foot{ display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px 16px; border-top: 1px solid var(--border-light); }
.vp-foot .btn{ padding: 8px 18px; border-radius: 8px; font-size: 13px; cursor: pointer; border: 1px solid var(--border); background: #fff; color: var(--text-1); }
.vp-foot .btn-primary{ background: var(--primary); color: #fff; border-color: var(--primary); }
</style>

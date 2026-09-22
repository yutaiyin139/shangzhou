<template>
  <div class="share-layout">
    <div class="share-container">
      <!-- 头部 -->
      <div class="share-header">
        <div class="share-brand">
          <div class="share-logo">熵舟</div>
          <span class="share-divider">|</span>
          <span class="share-type">智能对话</span>
        </div>
        <div class="share-actions">
          <a class="share-login-link" href="/#/login">登录使用</a>
        </div>
      </div>

      <!-- 聊天区域 -->
      <div class="share-chat" v-if="!loading">
        <div class="share-title" v-if="appInfo.name">{{ appInfo.name }}</div>
        <div class="share-desc" v-if="appInfo.description">{{ appInfo.description }}</div>

        <!-- 消息列表 -->
        <div class="share-messages" ref="msgList">
          <div v-for="(msg, idx) in messages" :key="idx" class="share-msg" :class="msg.role">
            <div class="share-msg-avatar">
              <span v-if="msg.role === 'user'">👤</span>
              <span v-else>🤖</span>
            </div>
            <div class="share-msg-content">
              <div class="share-msg-text">{{ msg.content }}</div>
              <div class="share-msg-time">{{ msg.time }}</div>
            </div>
          </div>

          <div v-if="messages.length === 0" class="share-empty">
            <div class="share-empty-icon">💬</div>
            <div>开始对话吧</div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="share-input-area">
          <div class="share-input-wrap">
            <textarea
              v-model="inputMessage"
              placeholder="输入消息..."
              @keydown.enter.exact.prevent="sendMessage"
              rows="1"
              :disabled="sending"
            ></textarea>
            <button class="share-send-btn" @click="sendMessage" :disabled="sending || !inputMessage.trim()">
              <span v-if="sending">发送中...</span>
              <span v-else>发送</span>
            </button>
          </div>
          <div class="share-input-hint">内容由 AI 生成，仅供参考</div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-else class="share-loading">
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
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, apiPost } from '../api/client'

const route = useRoute()
const token = route.params.token

const loading = ref(true)
const sending = ref(false)
const error = ref('')
const appInfo = ref({})
const messages = ref([])
const inputMessage = ref('')
const msgList = ref(null)

async function loadAppInfo() {
  try {
    const res = await apiGet(`/api/share/chat/${token}/info`)
    appInfo.value = res.data || {}
  } catch (e) {
    error.value = '加载失败，请检查链接是否正确'
  }
  loading.value = false
}

async function sendMessage() {
  const msg = inputMessage.value.trim()
  if (!msg || sending.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: msg,
    time: new Date().toLocaleTimeString()
  })
  inputMessage.value = ''
  sending.value = true

  await nextTick()
  scrollToBottom()

  try {
    const res = await apiPost(`/api/share/chat/${token}/message`, { message: msg })

    messages.value.push({
      role: 'assistant',
      content: res.data?.reply || res.data?.content || '抱歉，我无法回答这个问题',
      time: new Date().toLocaleTimeString()
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '网络错误，请稍后重试',
      time: new Date().toLocaleTimeString()
    })
  }

  sending.value = false
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (msgList.value) {
    msgList.value.scrollTop = msgList.value.scrollHeight
  }
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
  display: flex;
  flex-direction: column;
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

.share-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
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
  margin-bottom: 24px;
}

.share-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  min-height: 300px;
  max-height: calc(100vh - 350px);
}

.share-msg {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.share-msg.user {
  flex-direction: row-reverse;
}

.share-msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  border: 1px solid var(--border-light);
}

.share-msg-content {
  max-width: 70%;
}

.share-msg.user .share-msg-content {
  text-align: right;
}

.share-msg-text {
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.share-msg.user .share-msg-text {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.share-msg-time {
  font-size: 11px;
  color: var(--text-4);
  margin-top: 4px;
}

.share-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--text-4);
}

.share-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.share-input-area {
  border-top: 1px solid var(--border-light);
  padding-top: 16px;
}

.share-input-wrap {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.share-input-wrap textarea {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  background: var(--bg-input);
  color: var(--text-1);
  max-height: 120px;
}

.share-input-wrap textarea:focus {
  border-color: var(--primary);
}

.share-send-btn {
  padding: 12px 24px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.share-send-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}

.share-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.share-input-hint {
  text-align: center;
  font-size: 11px;
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

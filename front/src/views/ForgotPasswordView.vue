<template>
  <div class="lp">
    <div class="lp-brand">
      <h1>熵舟·<span class="blue">智能体工作台</span></h1>
      <p>链接无限可能，开启智能未来</p>
    </div>

    <div class="lp-card">
      <div id="panel-forgot">
        <h2>忘记密码</h2>
        <div class="sub">输入注册邮箱，我们将发送重置链接</div>
        <form novalidate @submit.prevent="doForgot" v-if="!sent">
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>
            <input type="email" placeholder="请输入注册邮箱" autocomplete="off" v-model="email">
          </div>
          <div class="lp-err" id="forgot-err">{{ errorMsg }}</div>
          <button type="submit" class="lp-btn" id="forgot-btn" :disabled="loading">{{ loading ? '发送中…' : '发送重置链接' }}</button>
        </form>
        <div v-else class="success-box">
          <svg class="success-icon" viewBox="0 0 24 24" fill="none" stroke="#52C41A" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>
          <div class="success-title">重置链接已发送</div>
          <div class="success-desc">如果该邮箱已注册，您将收到一封包含重置链接的邮件。链接 1 小时内有效。</div>
        </div>
        <div class="lp-link">
          <a href="javascript:void(0)" @click="goLogin">返回登录</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from '../utils/global'

const router = useRouter()
const email = ref('')
const errorMsg = ref('')
const loading = ref(false)
const sent = ref(false)

function goLogin() {
  router.push('/login')
}

async function doForgot() {
  errorMsg.value = ''
  if (!email.value.trim()) { errorMsg.value = '请输入邮箱'; return }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    errorMsg.value = '请输入有效的邮箱地址'; return
  }

  loading.value = true
  try {
    const resp = await fetch('/api/password/forgot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value.trim().toLowerCase() })
    })
    const data = await resp.json()
    if (data.code === 200) {
      sent.value = true
      toast('重置链接已发送')
    } else {
      errorMsg.value = data.msg || '发送失败'
    }
  } catch (e) {
    errorMsg.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.lp{ position:relative; height:100vh; display:flex; align-items:center; justify-content:space-between;
     padding:0 20%; background:#E9F1FC url('/login-bg.png') center/cover no-repeat; overflow:hidden; }
.lp-brand{ position:relative; z-index:2; margin-bottom:12vh; }
.lp-brand h1{ font-size:42px; font-weight:800; letter-spacing:2px; color:#1D2129; }
.lp-brand h1 .blue{ color:#2E63F0; }
.lp-brand p{ margin-top:18px; font-size:15px; color:#6B7787; letter-spacing:1px; }
.lp-card{ position:relative; z-index:2; width:400px; background:rgba(255,255,255,.72);
  backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border:1px solid rgba(255,255,255,.85); border-radius:14px;
  box-shadow:0 12px 48px rgba(46,99,240,.10); padding:38px 36px 28px; }
.lp-card h2{ font-size:21px; font-weight:700; color:#1D2129; }
.lp-card .sub{ font-size:12.5px; color:#86909C; margin:8px 0 26px; }
.lp-field{ position:relative; margin-bottom:16px; }
.lp-field .fico{ position:absolute; left:13px; top:50%; transform:translateY(-50%); width:16px; height:16px; color:#A9B4C0; }
.lp-field input{ width:100%; height:44px; border:1px solid #E2E8F0; border-radius:8px; background:#fff;
  padding:0 40px 0 36px; font-size:13.5px; transition:border-color .15s; box-sizing:border-box; }
.lp-field input:focus{ border-color:#2E63F0; box-shadow:0 0 0 3px rgba(46,99,240,.10); outline:none; }
.lp-err{ color:#F53F3F; font-size:12px; min-height:18px; margin:-6px 0 8px; }
.lp-btn{ width:100%; height:46px; border:none; border-radius:8px; font-size:15px; font-weight:600; color:#fff;
  background:linear-gradient(90deg,#2E63F0,#4A86F8); cursor:pointer; letter-spacing:2px; transition:opacity .15s; }
.lp-btn:hover{ opacity:.92; }
.lp-btn:disabled{ opacity:.7; cursor:not-allowed; }
.lp-link{ text-align:center; font-size:12px; color:#9AA5B1; margin-top:18px; }
.lp-link a{ color:#2E63F0; }
.success-box{ text-align:center; padding:20px 0; }
.success-icon{ width:48px; height:48px; margin-bottom:16px; }
.success-title{ font-size:16px; font-weight:600; color:#1D2129; margin-bottom:8px; }
.success-desc{ font-size:13px; color:#86909C; line-height:1.6; }
@media (max-width:900px){ .lp{ justify-content:center; padding:0 5%; } .lp-brand{ display:none; } }
</style>

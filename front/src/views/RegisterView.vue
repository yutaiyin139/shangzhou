<template>
  <div class="lp">
    <div class="lp-brand">
      <h1>熵舟·<span class="blue">智能体工作台</span></h1>
      <p>链接无限可能，开启智能未来</p>
    </div>

    <div class="lp-card">
      <div id="panel-register">
        <h2>用户注册</h2>
        <div class="sub">创建账号，开始使用熵舟·智能体工作台</div>
        <div v-if="!configLoading && !allowRegister" class="lp-closed">
          系统当前已关闭自助注册，请联系管理员开通。
          <div class="lp-link"><a href="javascript:void(0)" @click="goLogin">返回登录</a></div>
        </div>
        <form v-else novalidate @submit.prevent="doRegister">
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6"/></svg>
            <input type="text" placeholder="请输入账号" autocomplete="off" v-model="username">
          </div>
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
            <input type="email" placeholder="请输入邮箱" autocomplete="off" v-model="email">
          </div>
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
            <input id="reg-pwd" type="password" placeholder="请输入密码（8位以上，含字母+数字）" v-model="password">
          </div>
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2L15 8.5L22 9.5L17 14.5L18 21.5L12 18.5L6 21.5L7 14.5L2 9.5L9 8.5Z"/></svg>
            <input type="password" placeholder="请再次输入密码" v-model="confirmPassword">
          </div>
          <div class="lp-field" v-if="requireInvite">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 7l2-2 4 4-2 2-1-1-3 3 1 1-4 4-2-2 4-4-1-1 3-3z"/><path d="M9 15l-2 2"/></svg>
            <input type="text" placeholder="请输入邀请码" autocomplete="off" v-model="inviteCode">
          </div>
          <div class="lp-err" id="reg-err">{{ errorMsg }}</div>
          <button type="submit" class="lp-btn" id="reg-btn" :disabled="loading">{{ loading ? '注册中…' : '注 册' }}</button>
        </form>
        <div class="lp-link">
          已有账号？<a href="javascript:void(0)" @click="goLogin">立即登录</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from '../utils/global'

const router = useRouter()
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const inviteCode = ref('')
const errorMsg = ref('')
const loading = ref(false)
// 注册策略（来自 /api/register-config）
const configLoading = ref(true)
const allowRegister = ref(true)
const requireInvite = ref(false)

onMounted(async () => {
  try {
    const resp = await fetch('/api/register-config')
    const data = await resp.json()
    if (data && data.code === 200 && data.data) {
      allowRegister.value = !!data.data.allow_register
      requireInvite.value = !!data.data.require_invite_code
    }
  } catch (e) {
    // 获取失败时保持默认开放，最终以后端校验为准
  } finally {
    configLoading.value = false
  }
})

function goLogin() {
  router.push('/login')
}

async function doRegister() {
  errorMsg.value = ''
  if (!username.value.trim()) { errorMsg.value = '请输入账号'; return }
  if (!email.value.trim()) { errorMsg.value = '请输入邮箱'; return }
  if (!password.value) { errorMsg.value = '请输入密码'; return }
  if (password.value.length < 8) { errorMsg.value = '密码至少 8 位'; return }
  if (!/[a-zA-Z]/.test(password.value) || !/[0-9]/.test(password.value)) {
    errorMsg.value = '密码需同时包含字母和数字'; return
  }
  if (password.value !== confirmPassword.value) { errorMsg.value = '两次密码输入不一致'; return }
  if (requireInvite.value && !inviteCode.value.trim()) { errorMsg.value = '请输入邀请码'; return }

  loading.value = true
  try {
    const resp = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
        email: email.value.trim().toLowerCase(),
        invite_code: inviteCode.value.trim()
      })
    })
    const data = await resp.json()
    if (data.code === 200) {
      toast('注册成功，请登录')
      router.push('/login')
    } else {
      errorMsg.value = data.msg || '注册失败'
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
  background:linear-gradient(90deg,#2E63F0,#4A86F8); cursor:pointer; letter-spacing:6px; transition:opacity .15s; }
.lp-btn:hover{ opacity:.92; }
.lp-btn:disabled{ opacity:.7; cursor:not-allowed; }
.lp-link{ text-align:center; font-size:12px; color:#9AA5B1; margin-top:18px; }
.lp-link a{ color:#2E63F0; }
.lp-closed{ text-align:center; color:#86909C; font-size:14px; line-height:1.9; padding:24px 0 8px; }
@media (max-width:900px){ .lp{ justify-content:center; padding:0 5%; } .lp-brand{ display:none; } }
</style>

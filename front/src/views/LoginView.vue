<template>
  <div class="lp">
    <div class="lp-brand">
      <h1>熵舟·<span class="blue">智能体工作台</span></h1>
      <p>链接无限可能，开启智能未来</p>
    </div>

    <div class="lp-card">
      <div class="lp-tabs">
        <button type="button" class="lt" :class="{ active: !qrMode }" id="tab-account" @click="switchTab(false)">账号登录</button>
        <button type="button" class="lt" :class="{ active: qrMode }" id="tab-qr" @click="switchTab(true)">蓝信扫码</button>
      </div>
      <div id="panel-account" v-show="!qrMode">
        <h2>欢迎登录</h2>
        <div class="sub">登录熵舟·智能体工作台，开启高效体验</div>
        <form id="login-form" novalidate @submit.prevent="doLogin">
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6"/></svg>
            <input id="login-user" type="text" placeholder="请输入账号" autocomplete="off" v-model="username">
          </div>
          <div class="lp-field">
            <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
            <input id="login-pwd" type="password" placeholder="请输入密码" v-model="password">
            <button type="button" class="eye" id="pwd-eye" title="显示/隐藏密码">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="2.5"/></svg>
            </button>
          </div>
          <div class="lp-captcha" v-if="captchaEnabled">
            <div class="lp-field">
              <svg class="fico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l7.5 3v5.5c0 4.7-3.2 8-7.5 9.5-4.3-1.5-7.5-4.8-7.5-9.5V6L12 3z"/><path d="M9 12l2.2 2.2L15.5 10"/></svg>
              <input id="login-captcha" type="text" placeholder="请输入图形验证码" autocomplete="off" maxlength="4" v-model="captchaInput">
            </div>
            <canvas class="captcha-img" id="captcha-canvas" width="192" height="88" title="点击刷新验证码" @click="drawCaptcha"></canvas>
            <button type="button" class="captcha-refresh" id="captcha-refresh" title="刷新验证码" @click="drawCaptcha">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v5h-5"/></svg>
            </button>
          </div>
          <div class="lp-err" id="login-err">{{ errorMsg }}</div>
          <button type="submit" class="lp-btn" id="login-btn" :disabled="loading">{{ loading ? '登录中…' : '登 录' }}</button>
        </form>
        <!-- SSO 登录分隔线 -->
        <div class="lp-sso-divider" v-if="oauthProviders.length > 0">
          <span>或使用以下方式登录</span>
        </div>
        <!-- SSO 登录按钮 -->
        <div class="lp-sso-buttons" v-if="oauthProviders.length > 0">
          <button
            v-for="p in oauthProviders"
            :key="p.name"
            class="lp-sso-btn"
            :class="'lp-sso-' + p.name"
            @click="doOAuthLogin(p.name)"
            :title="'使用 ' + p.label + ' 登录'"
          >
            <span class="lp-sso-icon">{{ p.icon }}</span>
            <span class="lp-sso-label">{{ p.label }} 登录</span>
          </button>
        </div>
        <div class="lp-link" style="text-align:center;margin-top:12px;">
          还没有账号？<a href="javascript:void(0)" @click="router.push('/register')">立即注册</a>
        </div>
        <div class="lp-link" style="text-align:center;margin-top:6px;">
          <a href="javascript:void(0)" @click="router.push('/forgot-password')">忘记密码？</a>
        </div>
        <div class="lp-agree">点击登录即表示您同意我们的 <a href="javascript:void(0)" @click="showTerms()">服务协议</a></div>
      </div>
      <div class="qr-panel" :class="{ show: qrMode }" id="panel-qr">
        <div class="qr-box"><canvas id="qr-canvas" width="160" height="160"></canvas></div>
        <div class="qr-tip">请使用蓝信 App 扫码登录</div>
        <div class="qr-sub">扫码后请在手机上确认登录</div>
        <button type="button" class="qr-refresh" id="qr-refresh" @click="drawQr">刷新二维码</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from '../utils/global'
import { login } from '../api/client'

const router = useRouter()
const qrMode = ref(false)
const code = ref('')
const username = ref('')
const password = ref('')
const captchaInput = ref('')
const errorMsg = ref('')
const loading = ref(false)
const oauthProviders = ref([])

/* 登录图形验证码开关（与后端 LOGIN_LOCKOUT_ENABLED 同样由根目录 .env 控制）：
 * - 项目根 .env 写 `VITE_LOGIN_CAPTCHA=false` 则关闭图形验证码（开发阶段）
 * - 缺省（未设置或非 false）为启用，生产构建默认保留验证
 * - 修改 .env 后需重启 dev 服务器 / 重新 build 才会生效
 */
const captchaEnabled = String(import.meta.env.VITE_LOGIN_CAPTCHA ?? 'true').trim().toLowerCase()
  !== 'false'

/* 加载 OAuth 提供商列表 */
function loadOAuthProviders(){
  fetch('/api/oauth/providers').then(function(r){ return r.json() }).then(function(res){
    if (res.code === 200 && res.data){
      oauthProviders.value = res.data
    }
  }).catch(function(){})
}

/* OAuth 登录 */
function doOAuthLogin(provider){
  var redirectUrl = '/'
  var url = '/api/oauth/authorize/' + provider + '?redirect_url=' + encodeURIComponent(redirectUrl)
  window.location.href = url
}

function drawCaptcha(){
  var canvas = document.getElementById('captcha-canvas');
  if (!canvas) return;
  var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  code.value = '';
  for (var i = 0; i < 4; i++) code.value += chars.charAt(Math.floor(Math.random() * chars.length));
  var ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#F4F8FD'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (var n = 0; n < 40; n++){
    ctx.fillStyle = 'rgba(46,99,240,' + (Math.random() * 0.25 + 0.08) + ')';
    ctx.fillRect(Math.random() * canvas.width, Math.random() * canvas.height, 2, 2);
  }
  for (var l = 0; l < 3; l++){
    ctx.strokeStyle = 'rgba(120,160,230,.45)'; ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(Math.random() * 40, Math.random() * 88);
    ctx.bezierCurveTo(Math.random() * 192, Math.random() * 88, Math.random() * 192, Math.random() * 88, 150 + Math.random() * 42, Math.random() * 88);
    ctx.stroke();
  }
  for (var c = 0; c < 4; c++){
    ctx.save();
    ctx.font = 'bold ' + (34 + Math.floor(Math.random() * 8)) + 'px Arial';
    ctx.fillStyle = ['#2E63F0', '#1F4FD8', '#4A86F8', '#2952CC'][c % 4];
    ctx.translate(28 + c * 44, 56 + (Math.random() * 10 - 5));
    ctx.rotate((Math.random() * 30 - 15) * Math.PI / 180);
    ctx.fillText(code.value[c], -12, 0);
    ctx.restore();
  }
}

function drawQr(){
  var qrCanvas = document.getElementById('qr-canvas');
  if (!qrCanvas) return;
  var ctx = qrCanvas.getContext('2d');
  var N = 25, size = qrCanvas.width, cell = size / N;
  ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = '#1D2129';
  function finder(cx, cy){
    ctx.fillRect(cx * cell, cy * cell, 7 * cell, 7 * cell);
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect((cx + 1) * cell, (cy + 1) * cell, 5 * cell, 5 * cell);
    ctx.fillStyle = '#1D2129';
    ctx.fillRect((cx + 2) * cell, (cy + 2) * cell, 3 * cell, 3 * cell);
  }
  function inFinder(x, y){
    return (x < 8 && y < 8) || (x >= N - 8 && y < 8) || (x < 8 && y >= N - 8);
  }
  for (var y = 0; y < N; y++){
    for (var x = 0; x < N; x++){
      if (inFinder(x, y)) continue;
      if (Math.random() < 0.45) ctx.fillRect(x * cell, y * cell, cell, cell);
    }
  }
  finder(0, 0); finder(N - 7, 0); finder(0, N - 7);
}

function switchTab(toQr){
  qrMode.value = toQr;
  if (toQr) drawQr();
}

function shake(el){
  el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake');
}

/* P3：服务协议 */
function showTerms(){
  if (typeof openModal === 'function'){
    openModal('服务协议',
      '<div class="help-content">' +
        '<h4>熵舟·智能体工作台服务协议</h4>' +
        '<p>欢迎使用熵舟·智能体工作台。点击「登录」即表示您同意以下条款：</p>' +
        '<ul>' +
          '<li>您应妥善保管账号和密码</li>' +
          '<li>不得利用本平台从事违法违规活动</li>' +
          '<li>您上传的数据仅用于智能体服务</li>' +
          '<li>我们将保护您的隐私和数据安全</li>' +
        '</ul>' +
        '<p style="color:var(--text-3);font-size:12px;">如有疑问，请联系管理员。</p>' +
      '</div>'
    );
  } else {
    toast('服务协议：请妥善保管账号，不得用于违规活动');
  }
}

async function doLogin(){
  errorMsg.value = '';
  if (!username.value.trim()){ shake(document.getElementById('login-user')); errorMsg.value = '请输入账号'; return; }
  if (!password.value.trim()){ shake(document.getElementById('login-pwd')); errorMsg.value = '请输入密码'; return; }
  if (captchaEnabled) {
    if (!captchaInput.value.trim()){ shake(document.getElementById('login-captcha')); errorMsg.value = '请输入图形验证码'; return; }
    if (captchaInput.value.trim().toUpperCase() !== code.value){
      shake(document.getElementById('login-captcha')); errorMsg.value = '验证码错误，请重新输入'; captchaInput.value = ''; drawCaptcha(); return;
    }
  }
  loading.value = true;
  try {
    // 使用统一的 API 客户端登录（自动保存 JWT Token）
    await login(username.value.trim(), password.value);
    router.push('/home');
  } catch (e) {
    errorMsg.value = e.message || '登录失败';
    drawCaptcha();
    captchaInput.value = '';
  } finally {
    loading.value = false;
  }
}

onMounted(function(){
  if (captchaEnabled) drawCaptcha();
  drawQr();
  loadOAuthProviders();
  document.getElementById('pwd-eye').addEventListener('click', function(){
    var pwd = document.getElementById('login-pwd');
    pwd.type = pwd.type === 'password' ? 'text' : 'password';
  });
  // 输入时清除错误提示
  username.value = ''; password.value = ''; captchaInput.value = '';
});
</script>

<style>
.lp{ position:relative; height:100vh; display:flex; align-items:center; justify-content:space-between;
     padding:0 20%; background:#E9F1FC url('/login-bg.png') center/cover no-repeat; overflow:hidden; }
/* 左侧品牌区 */
.lp-brand{ position:relative; z-index:2; margin-bottom:12vh; }
.lp-brand h1{ font-size:42px; font-weight:800; letter-spacing:2px; color:#1D2129; }
.lp-brand h1 .blue{ color:#2E63F0; }
.lp-brand p{ margin-top:18px; font-size:15px; color:#6B7787; letter-spacing:1px; }
/* 右侧登录卡 */
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
.lp-field .eye{ position:absolute; right:12px; top:50%; transform:translateY(-50%); width:17px; height:17px;
  color:#A9B4C0; cursor:pointer; background:none; border:none; padding:0; }
.lp-field .eye:hover{ color:#2E63F0; }
/* 验证码 */
.lp-captcha{ display:flex; gap:10px; margin-bottom:22px; }
.lp-captcha .lp-field{ flex:1; margin-bottom:0; }
.captcha-img{ width:96px; height:44px; border:1px solid #E2E8F0; border-radius:8px; background:#F4F8FD; cursor:pointer; flex-shrink:0; }
.captcha-refresh{ width:30px; border:none; background:none; color:#A9B4C0; cursor:pointer; display:flex; align-items:center; justify-content:center; }
.captcha-refresh:hover{ color:#2E63F0; }
.captcha-refresh svg{ width:17px; height:17px; }
.lp-err{ color:#F53F3F; font-size:12px; min-height:18px; margin:-6px 0 8px; }
.lp-btn{ width:100%; height:46px; border:none; border-radius:8px; font-size:15px; font-weight:600; color:#fff;
  background:linear-gradient(90deg,#2E63F0,#4A86F8); cursor:pointer; letter-spacing:6px; transition:opacity .15s; }
.lp-btn:hover{ opacity:.92; }
.lp-btn:disabled{ opacity:.7; cursor:not-allowed; }
.lp-link{ text-align:center; font-size:12px; color:#9AA5B1; margin-top:18px; }
.lp-link a{ color:#2E63F0; }
.lp-agree{ text-align:center; font-size:12px; color:#9AA5B1; margin-top:18px; }
.lp-agree a{ color:#2E63F0; }
/* SSO 登录 */
.lp-sso-divider{ display:flex; align-items:center; gap:12px; margin:18px 0 12px; font-size:12px; color:#9AA5B1; }
.lp-sso-divider::before,.lp-sso-divider::after{ content:''; flex:1; height:1px; background:var(--border-light); }
.lp-sso-buttons{ display:flex; flex-direction:column; gap:8px; }
.lp-sso-btn{
  display:flex; align-items:center; justify-content:center; gap:8px;
  padding:10px 16px; border:1px solid var(--border); border-radius:8px;
  background:#fff; cursor:pointer; font-size:14px; color:var(--text-1);
  transition:all .15s;
}
.lp-sso-btn:hover{ border-color:var(--primary); background:var(--primary-light); }
.lp-sso-icon{ font-size:18px; }
.lp-sso-label{ font-weight:500; }
.lp-sso-google:hover{ border-color:#4285F4; background:rgba(66,133,244,.06); }
.lp-sso-github:hover{ border-color:#333; background:rgba(51,51,51,.04); }
/* 登录方式切换 */
.lp-tabs{ display:flex; gap:26px; margin-bottom:22px; }
.lp-tabs .lt{ font-size:15px; color:#86909C; cursor:pointer; padding-bottom:8px; border:none; background:none;
  border-bottom:2px solid transparent; font-weight:500; }
.lp-tabs .lt:hover{ color:#2E63F0; }
.lp-tabs .lt.active{ color:#1D2129; border-bottom-color:#2E63F0; font-weight:600; }
/* 蓝信扫码面板 */
.qr-panel{ display:none; flex-direction:column; align-items:center; padding:6px 0 4px; }
.qr-panel.show{ display:flex; }
.qr-box{ width:176px; height:176px; border:1px solid #E2E8F0; border-radius:10px; background:#fff;
  display:flex; align-items:center; justify-content:center; }
.qr-tip{ margin-top:16px; font-size:14px; color:#1D2129; }
.qr-sub{ margin-top:6px; font-size:12px; color:#86909C; }
.qr-refresh{ margin-top:14px; font-size:13px; color:#2E63F0; background:none; border:none; cursor:pointer; }
.qr-refresh:hover{ text-decoration:underline; }
@media (max-width:900px){ .lp{ justify-content:center; padding:0 5%; } .lp-brand{ display:none; } }
</style>

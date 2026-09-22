<template>
  <AppShell id="page-root" active-key="settings" main-class="main-white">
    <div class="page-pad">
      <div class="ss-header">
        <h2>系统设置</h2>
        <p class="ss-sub">配置 SMTP 邮件服务器、站点信息等系统参数</p>
      </div>

      <div class="ss-tabs">
        <button :class="['ss-tab', { active: tab === 'smtp' }]" @click="tab = 'smtp'">SMTP 配置</button>
        <button :class="['ss-tab', { active: tab === 'site' }]" @click="tab = 'site'">站点设置</button>
        <button :class="['ss-tab', { active: tab === 'security' }]" @click="tab = 'security'">安全设置</button>
      </div>

    <!-- SMTP 配置 -->
    <div v-show="tab === 'smtp'" class="ss-section">
      <div class="ss-card">
        <h3>邮件服务器配置</h3>
        <div class="ss-form">
          <div class="ss-row">
            <label>SMTP 服务器地址</label>
            <input v-model="settings.smtp_host" placeholder="smtp.example.com">
          </div>
          <div class="ss-row">
            <label>端口</label>
            <input v-model="settings.smtp_port" placeholder="587" style="width:120px">
            <label class="ss-check"><input type="checkbox" v-model="settings.smtp_use_tls" true-value="1" false-value="0"> 使用 TLS</label>
          </div>
          <div class="ss-row">
            <label>用户名</label>
            <input v-model="settings.smtp_user" placeholder="noreply@example.com">
          </div>
          <div class="ss-row">
            <label>密码</label>
            <input v-model="settings.smtp_password" type="password" placeholder="SMTP 密码或授权码">
          </div>
          <div class="ss-row">
            <label>发件人地址</label>
            <input v-model="settings.smtp_from" placeholder="熵舟 <noreply@example.com>">
          </div>
          <div class="ss-actions">
            <button class="ss-btn ss-btn-primary" @click="saveSettings" :disabled="saving">{{ saving ? '保存中…' : '保存配置' }}</button>
            <button class="ss-btn ss-btn-test" @click="testSmtp" :disabled="testing">{{ testing ? '发送中…' : '发送测试邮件' }}</button>
          </div>
        </div>
      </div>
      <div class="ss-card">
        <h3>SMTP 测试</h3>
        <div class="ss-form">
          <div class="ss-row">
            <label>收件人邮箱</label>
            <input v-model="testEmail" placeholder="用于接收测试邮件的邮箱">
          </div>
          <div class="ss-tip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
            <span>配置 SMTP 后，点击"发送测试邮件"验证配置是否正确。测试邮件将发送到上方填写的邮箱。</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 站点设置 -->
    <div v-show="tab === 'site'" class="ss-section">
      <div class="ss-card">
        <h3>站点信息</h3>
        <div class="ss-form">
          <div class="ss-row">
            <label>站点名称</label>
            <input v-model="settings.site_name" placeholder="熵舟·智能体工作台">
          </div>
          <div class="ss-row">
            <label>站点描述</label>
            <input v-model="settings.site_description" placeholder="链接无限可能，开启智能未来">
          </div>
          <div class="ss-row">
            <label>是否开放注册</label>
            <label class="ss-check"><input type="checkbox" v-model="settings.allow_register" true-value="1" false-value="0"> 允许用户自助注册</label>
          </div>
          <div class="ss-row" v-if="settings.allow_register === '1'">
            <label>注册邀请码</label>
            <input v-model="settings.register_invite_code" placeholder="留空=无需邀请码；非空则注册必须填写" style="width:260px">
            <span style="color:#86909C;font-size:12px;margin-left:8px">留空表示不启用邀请码</span>
          </div>
          <div class="ss-actions">
            <button class="ss-btn ss-btn-primary" @click="saveSettings" :disabled="saving">{{ saving ? '保存中…' : '保存配置' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 安全设置 -->
    <div v-show="tab === 'security'" class="ss-section">
      <div class="ss-card">
        <h3>安全策略</h3>
        <div class="ss-form">
          <div class="ss-row">
            <label>登录失败锁定阈值</label>
            <input v-model="settings.lockout_threshold" placeholder="5" style="width:120px">
            <span style="color:#86909C;font-size:12px;margin-left:8px">次失败后锁定账号</span>
          </div>
          <div class="ss-row">
            <label>锁定时长</label>
            <input v-model="settings.lockout_duration" placeholder="900" style="width:120px">
            <span style="color:#86909C;font-size:12px;margin-left:8px">秒（900=15分钟）</span>
          </div>
          <div class="ss-row">
            <label>Access Token 有效期</label>
            <input v-model="settings.token_expiry" placeholder="7200" style="width:120px">
            <span style="color:#86909C;font-size:12px;margin-left:8px">秒（7200=2小时）</span>
          </div>
          <div class="ss-actions">
            <button class="ss-btn ss-btn-primary" @click="saveSettings" :disabled="saving">{{ saving ? '保存中…' : '保存配置' }}</button>
          </div>
        </div>
      </div>
    </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast } from '../utils/global'
import { apiGet, apiPost, apiPut } from '../api/client'

const tab = ref('smtp')
const settings = ref({
  smtp_host: '',
  smtp_port: '587',
  smtp_user: '',
  smtp_password: '',
  smtp_from: '',
  smtp_use_tls: '1',
  smtp_configured: '0',
  site_name: '熵舟·智能体工作台',
  site_description: '链接无限可能，开启智能未来',
  allow_register: '1',
  register_invite_code: '',
  lockout_threshold: '5',
  lockout_duration: '900',
  token_expiry: '7200',
})
const testEmail = ref('')
const saving = ref(false)
const testing = ref(false)

onMounted(async () => {
  try {
    const data = await apiGet('/api/system/settings')
    if (data) {
      // 不覆盖密码（脱敏显示）
      const pwd = settings.value.smtp_password
      Object.assign(settings.value, data)
      if (data.smtp_password === '********') {
        settings.value.smtp_password = pwd || ''
      }
    }
  } catch (e) {
    // 首次加载可能无设置
  }
})

async function saveSettings() {
  saving.value = true
  try {
    await apiPut('/api/system/settings', settings.value)
    toast('设置保存成功')
  } catch (e) {
    toast('保存失败: ' + (e.message || ''))
  } finally {
    saving.value = false
  }
}

async function testSmtp() {
  if (!testEmail.value) { toast('请输入测试收件人邮箱'); return }
  testing.value = true
  try {
    await apiPost('/api/system/smtp/test', {
      smtp_host: settings.value.smtp_host,
      smtp_port: settings.value.smtp_port,
      smtp_user: settings.value.smtp_user,
      smtp_password: settings.value.smtp_password,
      smtp_from: settings.value.smtp_from,
      use_tls: settings.value.smtp_use_tls,
      to_email: testEmail.value,
    })
    toast('测试邮件已发送，请查收')
  } catch (e) {
    toast('测试失败: ' + (e.message || ''))
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.ss-header h2{ font-size:22px; font-weight:700; color:#1D2129; margin:0 0 4px; }
.ss-sub{ font-size:13px; color:#86909C; margin:0 0 24px; }
.ss-tabs{ display:flex; gap:4px; border-bottom:1px solid #E2E8F0; margin-bottom:24px; }
.ss-tab{ padding:10px 20px; border:none; background:none; font-size:14px; color:#86909C; cursor:pointer;
  border-bottom:2px solid transparent; margin-bottom:-1px; font-weight:500; }
.ss-tab:hover{ color:#2E63F0; }
.ss-tab.active{ color:#2E63F0; border-bottom-color:#2E63F0; font-weight:600; }
.ss-card{ background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:24px; margin-bottom:20px; }
.ss-card h3{ font-size:16px; font-weight:600; color:#1D2129; margin:0 0 16px; }
.ss-form{ }
.ss-row{ display:flex; align-items:center; margin-bottom:16px; }
.ss-row label{ width:140px; font-size:13px; color:#4E5969; flex-shrink:0; }
.ss-row input[type=text], .ss-row input:not([type]){ flex:1; height:36px; border:1px solid #E2E8F0; border-radius:6px;
  padding:0 12px; font-size:13px; transition:border-color .15s; }
.ss-row input:focus{ border-color:#2E63F0; outline:none; box-shadow:0 0 0 3px rgba(46,99,240,.08); }
.ss-check{ display:flex; align-items:center; gap:6px; font-size:13px; color:#4E5969; cursor:pointer; width:auto !important; }
.ss-check input{ accent-color:#2E63F0; }
.ss-actions{ display:flex; gap:12px; margin-top:20px; padding-left:140px; }
.ss-btn{ height:36px; padding:0 20px; border:none; border-radius:6px; font-size:13px; font-weight:500; cursor:pointer;
  transition:opacity .15s; }
.ss-btn-primary{ background:linear-gradient(90deg,#2E63F0,#4A86F8); color:#fff; }
.ss-btn-test{ background:#F0F5FF; color:#2E63F0; border:1px solid #C5D6F7; }
.ss-btn:hover{ opacity:.9; }
.ss-btn:disabled{ opacity:.6; cursor:not-allowed; }
.ss-tip{ display:flex; gap:10px; padding:12px 16px; background:#FFFBE6; border:1px solid #FFE58F;
  border-radius:8px; font-size:12px; color:#AD6800; line-height:1.6; margin-top:12px; }
.ss-tip svg{ width:18px; height:18px; flex-shrink:0; margin-top:1px; }
</style>

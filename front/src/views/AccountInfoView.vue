<template>
  <AppShell id="page-root" active-key="account-info" main-class="main-white">
    <div class="page-pad">
            <div class="page-header">
              <div class="back-btn" data-action="history.back()" title="返回">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
              </div>
              <h2>账号信息</h2>
            </div>
    
            <div class="account-card">
              <!-- 用户头像区 -->
              <div class="avatar-section">
                <div class="avatar-lg" id="avatar-letter">鼎</div>
                <div class="avatar-info">
                  <div class="name" id="display-name">鼎正</div>
                  <div class="role" id="display-role">管理员</div>
                </div>
              </div>
    
              <div class="section-title">基本信息</div>
    
              <div class="form-row">
                <div class="label">用户名</div>
                <div class="pwd-toggle" style="flex:1;max-width:360px">
                  <input class="form-input" id="f-username" placeholder="请输入用户名">
                </div>
              </div>
    
              <div class="form-row">
                <div class="label">账号ID</div>
                <div class="value readonly" id="f-account-id">-</div>
              </div>
    
              <div class="form-row">
                <div class="label">邮箱</div>
                <div style="flex:1;max-width:360px">
                  <input class="form-input" id="f-email" type="email" placeholder="请输入邮箱">
                </div>
              </div>
    
              <div class="form-row">
                <div class="label">手机号</div>
                <div style="flex:1;max-width:360px">
                  <input class="form-input" id="f-phone" placeholder="请输入手机号">
                </div>
              </div>
    
              <div class="form-row">
                <div class="label">角色</div>
                <div class="value readonly" id="f-role">-</div>
              </div>
    
              <div class="form-row">
                <div class="label">创建时间</div>
                <div class="value readonly" id="f-created">-</div>
              </div>
    
              <div class="section-title" style="margin-top:8px">修改密码</div>
    
              <div class="form-row">
                <div class="label">新密码</div>
                <div style="display:flex;align-items:center;flex:1;max-width:360px">
                  <div class="pwd-toggle" style="flex:1">
                    <input class="form-input" id="f-password" type="password" placeholder="留空则不修改密码">
                    <button class="eye-btn" id="pwd-eye" title="显示/隐藏">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="2.5"/></svg>
                    </button>
                  </div>
                  <button class="btn-change-pwd" id="btn-open-pwd-modal">修改密码</button>
                </div>
              </div>
    
              <div class="btn-row">
                <button class="btn btn-primary" id="btn-save">保存修改</button>
                <button class="btn" id="btn-cancel">取消</button>
              </div>

              <!-- API Key 管理 -->
              <div class="section-title" style="margin-top:28px">API Key 管理</div>
              <div class="apikey-desc">使用 API Key 通过编程方式访问熵舟服务。</div>
              <div class="apikey-list" id="apikey-list">
                <div class="apikey-empty">加载中…</div>
              </div>
              <div class="apikey-actions">
                <button class="btn btn-primary" id="btn-create-apikey">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;margin-right:4px"><path d="M12 5v14M5 12h14"/></svg>
                  创建 API Key
                </button>
              </div>
            </div>
          </div>
    <!-- 重置密码模态窗口 -->
    <div class="modal-mask" id="modal-reset-pwd">
      <div class="modal-box">
        <h3>重置密码</h3>
        <div class="modal-field">
          <label>原密码</label>
          <div class="pwd-wrap">
            <input type="password" id="m-old-pwd" placeholder="请输入">
            <button class="eye-btn" data-action="toggleModalPwd(&#x27;m-old-pwd&#x27;, this)">😝</button>
          </div>
        </div>
        <div class="modal-field">
          <label>新密码</label>
          <div class="pwd-wrap">
            <input type="password" id="m-new-pwd" placeholder="请输入">
            <button class="eye-btn" data-action="toggleModalPwd(&#x27;m-new-pwd&#x27;, this)">😝</button>
          </div>
        </div>
        <div class="modal-field">
          <label>确认密码</label>
          <div class="pwd-wrap">
            <input type="password" id="m-confirm-pwd" placeholder="请输入">
            <button class="eye-btn" data-action="toggleModalPwd(&#x27;m-confirm-pwd&#x27;, this)">😝</button>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" id="btn-modal-cancel">取消</button>
          <button class="btn btn-reset" id="btn-modal-reset">重置</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal, getLoginUser } from '../utils/global'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

onMounted(function(){
  var root = document.querySelector('#page-root');
  function onRootClick(e){
    var el = e.target && e.target.closest ? e.target.closest('[data-action]') : null;
    if (!el) return;
    var code = el.getAttribute('data-action');
    if (!code) return;
    try { eval(code.replace(/\bthis\b/g, 'el')); } catch(err){ console.error('[page action]', err); }
  }
  if (root) root.addEventListener('click', onRootClick);
  
  var API = '';
  var originalData = null;
  var curUid = (getLoginUser() || {}).id || 1;  // 当前登录用户 id（未登录回退 1）
  
  /* ========== 加载账户信息 ========== */
  function loadAccount(){
    apiGet('/api/account', { params: { uid: curUid } }).then(function(res){
      if (res.code !== 200 || !res.data) return;
      var d = res.data;
      originalData = JSON.parse(JSON.stringify(d));

      document.getElementById('avatar-letter').textContent = (d.username || '?').charAt(0).toUpperCase();
      document.getElementById('display-name').textContent = d.username || '-';
      document.getElementById('display-role').textContent = d.role_name || '普通用户';

      document.getElementById('f-username').value = d.username || '';
      document.getElementById('f-account-id').textContent = d.account_id || '-';
      document.getElementById('f-email').value = d.email || '';
      document.getElementById('f-phone').value = d.phone || '';
      document.getElementById('f-role').textContent = d.role_name || '-';
      document.getElementById('f-created').textContent = d.created_at || '-';
    }).catch(function(err){ console.error('加载失败:', err); });
  }
  
  loadAccount();
  
  /* ========== 密码可见性 ========== */
  document.getElementById('pwd-eye').addEventListener('click', function(){
    var inp = document.getElementById('f-password');
    inp.type = inp.type === 'password' ? 'text' : 'password';
  });
  
  /* ========== 保存 ========== */
  document.getElementById('btn-save').addEventListener('click', function(){
    var payload = {
      uid: curUid,
      username: document.getElementById('f-username').value.trim(),
      email: document.getElementById('f-email').value.trim(),
      phone: document.getElementById('f-phone').value.trim()
    };
    var pwd = document.getElementById('f-password').value.trim();
    if (pwd) payload.password = pwd;
  
    apiPut('/api/account', payload).then(function(res){
      if (res.code === 200){
        toast('保存成功');
        document.getElementById('f-password').value = '';
        /* 同步顶栏登录态 */
        var lu = getLoginUser();
        if (lu && String(lu.id) === String(curUid)){
          lu.username = payload.username; lu.email = payload.email; lu.phone = payload.phone;
          sessionStorage.setItem('loginUser', JSON.stringify(lu));
        }
        loadAccount();
      } else {
        toast(res.msg || '保存失败');
      }
    }).catch(function(err){ toast('网络错误'); });
  });
  
  /* ========== 取消 ========== */
  document.getElementById('btn-cancel').addEventListener('click', function(){
    if (originalData){
      document.getElementById('f-username').value = originalData.username || '';
      document.getElementById('f-email').value = originalData.email || '';
      document.getElementById('f-phone').value = originalData.phone || '';
      var pwdField = document.getElementById('f-password');
      pwdField.value = '';
      pwdField.readOnly = false;
      pwdField.placeholder = '留空则不修改密码';
    }
    toast('已重置');
  });
  
  /* ========== 重置密码模态窗口 ========== */
  function toggleModalPwd(id, btn){
    var inp = document.getElementById(id);
    inp.type = inp.type === 'password' ? 'text' : 'password';
  }
  
  document.getElementById('btn-open-pwd-modal').addEventListener('click', function(){
    document.getElementById('modal-reset-pwd').classList.add('show');
    document.getElementById('m-old-pwd').value = '';
    document.getElementById('m-new-pwd').value = '';
    document.getElementById('m-confirm-pwd').value = '';
  });
  
  document.getElementById('btn-modal-cancel').addEventListener('click', function(){
    document.getElementById('modal-reset-pwd').classList.remove('show');
  });
  
  document.getElementById('modal-reset-pwd').addEventListener('click', function(e){
    if (e.target === this) this.classList.remove('show');
  });
  
  document.getElementById('btn-modal-reset').addEventListener('click', function(){
    var oldPwd = document.getElementById('m-old-pwd').value.trim();
    var newPwd = document.getElementById('m-new-pwd').value.trim();
    var confirmPwd = document.getElementById('m-confirm-pwd').value.trim();

    if (!oldPwd){ toast('请输入原密码'); return; }
    if (!newPwd){ toast('请输入新密码'); return; }
    if (newPwd !== confirmPwd){ toast('两次输入的新密码不一致'); return; }

    /* 调用后端验证并更新密码 */
    apiPut('/api/account', { uid: curUid, old_password: oldPwd, password: newPwd }).then(function(res){
      document.getElementById('modal-reset-pwd').classList.remove('show');
      var pwdField = document.getElementById('f-password');
      pwdField.value = newPwd;
      pwdField.readOnly = true;
      pwdField.placeholder = '已修改（不可编辑）';
      toast('密码重置成功');
    }).catch(function(){ toast('网络错误'); });
  });

  /* ========== API Key 管理 ========== */

  function loadApiKeys(){
    apiGet('/api/account/api-keys', { params: { uid: curUid } }).then(function(res){
      renderApiKeys(res.data);
    }).catch(function(){
      var list = document.getElementById('apikey-list');
      if (list) list.innerHTML = '<div class="apikey-empty">网络错误</div>';
    });
  }

  function renderApiKeys(items){
    var list = document.getElementById('apikey-list');
    if (!list) return;
    if (!items || !items.length){
      list.innerHTML = '<div class="apikey-empty">暂无 API Key，点击上方按钮创建</div>';
      return;
    }
    list.innerHTML = items.map(function(item){
      return '<div class="apikey-item" data-id="' + item.id + '">' +
        '<div class="apikey-info">' +
          '<span class="apikey-token">' + esc(item.token || '') + '</span>' +
          '<span class="apikey-meta">' + esc(item.type || 'app') + ' · ' + esc(item.created_at || '') + '</span>' +
        '</div>' +
        '<button class="apikey-del" data-id="' + item.id + '" title="删除">✕</button>' +
      '</div>';
    }).join('');

    // 绑定删除事件
    list.querySelectorAll('.apikey-del').forEach(function(btn){
      btn.addEventListener('click', function(){
        var id = this.getAttribute('data-id');
        if (!confirm('确定要删除此 API Key 吗？删除后无法恢复。')) return;
        apiDelete('/api/account/api-keys/' + id, { params: { uid: curUid } })
          .then(function(res){
            toast('已删除');
            loadApiKeys();
          }).catch(function(){ toast('网络错误'); });
      });
    });
  }

  function createApiKey(){
    apiPost('/api/account/api-keys', { name: 'API Key', type: 'app' }, { params: { uid: curUid } }).then(function(res){
      toast('API Key 创建成功');
      // 显示完整 key（仅此一次）
      alert('您的 API Key（仅显示一次，请妥善保存）:\n\n' + res.data.token);
      loadApiKeys();
    }).catch(function(){ toast('网络错误'); });
  }

  var btnCreateApikey = document.getElementById('btn-create-apikey');
  if (btnCreateApikey){
    btnCreateApikey.addEventListener('click', createApiKey);
  }

  loadApiKeys();
})
</script>
<style>
.page-header{ display:flex; align-items:center; gap:12px; margin-bottom:24px; }
  .page-header .back-btn{ width:32px; height:32px; border-radius:6px; border:1px solid var(--border); background:#fff; display:flex; align-items:center; justify-content:center; cursor:pointer; color:var(--text-2); }
  .page-header .back-btn:hover{ border-color:var(--primary); color:var(--primary); }
  .page-header .back-btn svg{ width:16px; height:16px; }
  .page-header h2{ font-size:18px; font-weight:700; }

  .account-card{ background:#fff; border-radius:10px; border:1px solid var(--border-light); padding:32px 36px; max-width:640px; }
  .account-card .section-title{ font-size:15px; font-weight:600; color:var(--text-1); margin-bottom:20px; padding-bottom:12px; border-bottom:1px solid var(--border-light); }

  .form-row{ display:flex; align-items:center; margin-bottom:20px; }
  .form-row .label{ width:100px; font-size:14px; color:var(--text-2); flex-shrink:0; }
  .form-row .value{ font-size:14px; color:var(--text-1); flex:1; }
  .form-row .value.readonly{ color:var(--text-3); }

  .form-input{ width:100%; max-width:360px; border:1px solid var(--border); border-radius:6px; padding:9px 12px; font-size:14px; transition:border-color .15s; }
  .form-input:focus{ border-color:var(--primary); box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  .form-input[readonly]{ background:#F7F8FA; color:var(--text-3); cursor:not-allowed; }

  .btn-row{ display:flex; gap:12px; margin-top:28px; padding-top:20px; border-top:1px solid var(--border-light); }
  .btn{ padding:8px 24px; border-radius:6px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); transition:all .15s; }
  .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .btn-primary:hover{ background:var(--primary-hover); border-color:var(--primary-hover); color:#fff; }

  .pwd-toggle{ position:relative; }
  .pwd-toggle .eye-btn{ position:absolute; right:10px; top:50%; transform:translateY(-50%); background:none; border:none; color:var(--text-4); cursor:pointer; padding:4px; }
  .pwd-toggle .eye-btn:hover{ color:var(--text-2); }
  .pwd-toggle .eye-btn svg{ width:16px; height:16px; }
  .pwd-toggle .form-input{ padding-right:36px; }

  .avatar-section{ display:flex; align-items:center; gap:16px; margin-bottom:24px; }
  .avatar-lg{ width:56px; height:56px; border-radius:50%; background:linear-gradient(135deg,#7BA7FF,#2E63F0); color:#fff; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:700; }
  .avatar-info .name{ font-size:18px; font-weight:700; color:var(--text-1); }
  .avatar-info .role{ font-size:12px; color:var(--text-3); margin-top:2px; }

  .btn-change-pwd{ margin-left:12px; padding:8px 18px; border-radius:6px; font-size:13px; cursor:pointer; border:1px solid var(--primary); background:#fff; color:var(--primary); transition:all .15s; white-space:nowrap; }
  .btn-change-pwd:hover{ background:var(--primary); color:#fff; }

  /* 重置密码模态窗口 */
  .modal-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:200; display:none; align-items:center; justify-content:center; }
  .modal-mask.show{ display:flex; }
  .modal-box{ background:#fff; border-radius:12px; width:420px; padding:28px 32px 24px; box-shadow:0 12px 40px rgba(0,0,0,.15); }
  .modal-box h3{ font-size:20px; font-weight:700; margin-bottom:24px; color:var(--text-1); }
  .modal-field{ margin-bottom:18px; }
  .modal-field label{ display:block; font-size:15px; font-weight:600; color:var(--text-1); margin-bottom:8px; }
  .modal-field input{ width:100%; height:44px; border:1px solid var(--border); border-radius:8px; padding:0 40px 0 14px; font-size:14px; background:#F4F5F7; transition:border-color .15s; }
  .modal-field input:focus{ border-color:var(--primary); background:#fff; outline:none; box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  .modal-field .pwd-wrap{ position:relative; }
  .modal-field .pwd-wrap .eye-btn{ position:absolute; right:10px; top:50%; transform:translateY(-50%); background:none; border:none; font-size:18px; cursor:pointer; }
  .modal-foot{ display:flex; justify-content:flex-end; gap:12px; margin-top:24px; }
  .modal-foot .btn{ padding:9px 28px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .modal-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .modal-foot .btn-reset{ background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }
  .modal-foot .btn-reset:hover{ background:var(--primary-hover); border-color:var(--primary-hover); color:#fff; }

  /* ---------- API Key 管理 ---------- */
  .apikey-desc{ font-size:13px; color:var(--text-3); margin-bottom:16px; }
  .apikey-list{ display:flex; flex-direction:column; gap:8px; margin-bottom:16px; }
  .apikey-empty{ text-align:center; font-size:13px; color:var(--text-3); padding:20px; background:#F7F8FA; border-radius:8px; }
  .apikey-item{ display:flex; align-items:center; gap:12px; padding:12px 16px; background:#F7F8FA; border-radius:8px; border:1px solid var(--border-light); }
  .apikey-info{ flex:1; min-width:0; display:flex; flex-direction:column; gap:4px; }
  .apikey-token{ font-family:'Courier New', monospace; font-size:13px; color:var(--text-1); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .apikey-meta{ font-size:11px; color:var(--text-3); }
  .apikey-del{ width:28px; height:28px; border:none; background:transparent; color:var(--text-4); cursor:pointer; border-radius:6px; font-size:14px; display:flex; align-items:center; justify-content:center; }
  .apikey-del:hover{ background:#FFECE8; color:#F53F3F; }
  .apikey-actions{ display:flex; gap:10px; }
  .apikey-actions .btn-primary{ display:inline-flex; align-items:center; }
</style>

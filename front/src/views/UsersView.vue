<template>
  <AppShell id="page-root" active-key="users" main-class="main-white">
    <div class="page-pad">
            <!-- 页内标签 -->
            <div class="tabs">
              <button class="tab active">用户管理</button>
              <button class="tab" id="tab-roles">角色管理</button>
              <button class="tab" id="tab-funcs">功能管理</button>
            </div>
    
            <!-- 工具条 -->
            <div style="display:flex;gap:10px;margin-top:16px;align-items:center;flex-wrap:wrap">
              <button class="btn btn-primary" id="btn-add-user">＋ 新建用户</button>
              <div style="margin-left:auto;display:flex;gap:10px;align-items:center">
                <div class="search-input" style="background:#fff;border:1px solid var(--border)">
                  <input id="user-search" placeholder="用户名称/账号ID">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
                </div>
                <button class="btn" style="padding:7px 10px" title="刷新" id="btn-refresh">
                  <svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 3v5h-5"/></svg>
                </button>
              </div>
            </div>
    
            <!-- 用户表格 -->
            <div class="table-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th style="width:44px"><input type="checkbox" class="cbx" id="cbx-all"></th>
                    <th>用户名称</th><th>昵称</th><th>角色</th><th>状态</th><th>添加时间</th><th style="width:90px">操作</th>
                  </tr>
                </thead>
                <tbody id="user-tbody">
                  <!-- 动态渲染：loadUsers() 会从 /api/users 加载真实数据 -->
                </tbody>
              </table>
              <!-- 空状态提示（无用户时显示） -->
              <div id="users-empty" style="display:none;padding:40px;text-align:center;color:#999;">
                暂无用户，点击"新建用户"添加
              </div>
              <!-- 加载状态 -->
              <div id="users-loading" style="padding:20px;text-align:center;color:#666;">
                加载中...
              </div>
            </div>
          </div>
    <!-- 新建用户弹窗（对照 image49） -->
    <div class="modal-mask" id="modal-add-user">
      <div class="modal">
        <div class="modal-head">
          <span class="modal-title">新建用户</span>
          <button class="modal-close" data-action="closeModal(&#x27;modal-add-user&#x27;)">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <div class="form-label">用户名称 <span class="req">*</span></div>
            <input class="form-input" id="f-name" placeholder="请输入用户名称">
          </div>
          <div class="form-item">
            <div class="form-label">昵称</div>
            <input class="form-input" id="f-nickname" placeholder="请输入昵称（可选）">
          </div>
          <div class="form-item">
            <div class="form-label">密码 <span class="req">*</span></div>
            <input class="form-input" id="f-pwd" type="password" placeholder="8位以上，需含字母和数字">
          </div>
          <div class="form-item">
            <div class="form-label">邮箱 <span class="req">*</span></div>
            <input class="form-input" id="f-email" placeholder="必填，用于登录和通知">
          </div>
          <div class="form-item">
            <div class="form-label">手机号</div>
            <input class="form-input" id="f-phone" placeholder="请输入手机号（选填）">
          </div>
          <div class="form-item">
            <div class="form-label">角色</div>
            <select class="form-sel" id="f-role">
              <option value="">请选择角色</option>
              <option>管理员</option>
              <option>普通用户</option>
              <option>访客</option>
            </select>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-primary" id="f-btn-create">创建</button>
          <button class="btn" data-action="closeModal(&#x27;modal-add-user&#x27;)">取消</button>
        </div>
      </div>
    </div>
    
    <!-- 设置角色弹窗 -->
    <div class="modal-mask" id="modal-set-role">
      <div class="modal" style="width:420px">
        <div class="modal-head">
          <span class="modal-title">设置角色</span>
          <button class="modal-close" data-action="closeModal(&#x27;modal-set-role&#x27;)">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-item" style="margin-bottom:6px">
            <div class="form-label">角色</div>
            <select class="form-sel" id="sr-role">
              <option>管理员</option>
              <option>普通用户</option>
              <option>访客</option>
            </select>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-primary" id="sr-ok">确定</button>
          <button class="btn" data-action="closeModal(&#x27;modal-set-role&#x27;)">取消</button>
        </div>
      </div>
    </div>
    
    <!-- 移除确认弹窗 -->
    <div class="modal-mask" id="modal-confirm">
      <div class="modal" style="width:400px">
        <div class="modal-head">
          <span class="modal-title">确认移除</span>
          <button class="modal-close" data-action="closeModal(&#x27;modal-confirm&#x27;)">✕</button>
        </div>
        <div class="confirm-body" id="confirm-text">确定移除该用户吗？</div>
        <div class="modal-foot" style="padding-top:14px">
          <button class="btn btn-primary" id="confirm-ok">确定</button>
          <button class="btn" data-action="closeModal(&#x27;modal-confirm&#x27;)">取消</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
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
  var tbody = document.getElementById('user-tbody');
  var cbxAll = document.getElementById('cbx-all');
  
  /* 页内标签跳转（使用 router.push 确保导航可靠） */
  document.getElementById('tab-roles').addEventListener('click', function(){ window.location.hash = '#/roles'; });
  document.getElementById('tab-funcs').addEventListener('click', function(){ window.location.hash = '#/functions'; });
  
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function nowStr(){
    var d = new Date();
    return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) + ' ' +
           pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  
  /* ========== 加载用户列表 ========== */
  function loadUsers(){
    document.getElementById('users-loading').style.display = '';
    document.getElementById('users-empty').style.display = 'none';
    apiGet('/api/users').then(function(res){
      tbody.innerHTML = '';
      var users = res.data || [];
      if (users.length === 0) {
        document.getElementById('users-empty').style.display = '';
        document.getElementById('users-loading').style.display = 'none';
        refreshState();
        return;
      }
      users.forEach(function(u){
        var tr = document.createElement('tr');
        tr.setAttribute('data-uid', u.id);
        var roleName = u.role_name || '未分配';
        tr.innerHTML =
          '<td><input type="checkbox" class="cbx"></td>' +
          '<td>' + (u.username || '') + '</td>' +
          '<td>' + (u.nickname || '') + '</td>' +
          '<td><span class="tag tag-blue role-cell">' + roleName + '</span></td>' +
          '<td><span class="st"><span class="st-dot"></span>' + (u.status === 1 ? '启用' : '禁用') + '</span></td>' +
          '<td>' + (u.created_at || '') + '</td>' +
          '<td><div class="op-col">' +
            '<button class="link row-set-role">设置角色</button>' +
            '<button class="link link-red row-del">移除</button>' +
          '</div></td>';
        tbody.appendChild(tr);
      });
      document.getElementById('users-loading').style.display = 'none';
      refreshState();
    }).catch(function(err){
      document.getElementById('users-loading').style.display = 'none';
      console.error('[loadUsers]', err);
      toast && toast.error && toast.error('加载用户列表失败');
    });
  }
  
  /* ========== 加载角色下拉 ========== */
  function loadRoleOptions(selId){
    apiGet('/api/roles').then(function(res){
      var sel = document.getElementById(selId);
      sel.innerHTML = '<option value="">请选择角色</option>';
      res.data.forEach(function(r){
        var opt = document.createElement('option');
        opt.value = r.name; opt.textContent = r.name;
        sel.appendChild(opt);
      });
    });
  }
  
  /* ========== 刷新状态 ========== */
  function refreshState(){
    var checked = tbody.querySelectorAll('input.cbx:checked').length;
    var rows = tbody.querySelectorAll('tr').length;
    cbxAll.checked = rows > 0 && checked === rows;
  }
  
  /* 全选 */
  cbxAll.addEventListener('change', function(){
    tbody.querySelectorAll('input.cbx').forEach(function(c){
      if (c.closest('tr').style.display !== 'none') c.checked = cbxAll.checked;
    });
    refreshState();
  });
  tbody.addEventListener('change', function(e){
    if (e.target.classList.contains('cbx')) refreshState();
  });
  
  /* ========== 移除确认 ========== */
  var confirmCb = null;
  function askConfirm(text, cb){
    document.getElementById('confirm-text').textContent = text;
    confirmCb = cb;
    openModal('modal-confirm');
  }
  document.getElementById('confirm-ok').addEventListener('click', function(){
    closeModal('modal-confirm');
    if (confirmCb){ var cb = confirmCb; confirmCb = null; cb(); }
  });
  
  /* ========== 行操作：移除 / 设置角色 ========== */
  tbody.addEventListener('click', function(e){
    var tr = e.target.closest('tr');
    if (!tr) return;
    if (e.target.classList.contains('row-del')){
      var uid = tr.getAttribute('data-uid');
      var name = tr.children[1].textContent;
      askConfirm('确定移除用户「' + name + '」吗？', function(){
        apiDelete('/api/users/' + uid)
          .then(function(res){
            tr.remove(); refreshState(); toast('已移除');
          })
          .catch(function(){ toast('移除失败'); });
      });
    }
    if (e.target.classList.contains('row-set-role')){
      curRoleUid = tr.getAttribute('data-uid');
      var cur = tr.querySelector('.role-cell').textContent;
      document.getElementById('sr-role').value = (cur === '未分配') ? '' : cur;
      openModal('modal-set-role');
    }
  });
  
  /* ========== 设置角色弹窗 ========== */
  var curRoleUid = null;
  document.getElementById('sr-ok').addEventListener('click', function(){
    var v = document.getElementById('sr-role').value;
    if (!curRoleUid) return;
    apiPut('/api/users/' + curRoleUid + '/roles', { role: v }).then(function(res){
      if (curRoleUid){
        var tr = tbody.querySelector('tr[data-uid="' + curRoleUid + '"]');
        if (tr) tr.querySelector('.role-cell').textContent = v || '未分配';
      }
      closeModal('modal-set-role');
      toast('已设置角色');
    }).catch(function(){ toast('设置失败'); });
  });
  
  /* ========== 搜索（回车过滤） ========== */
  document.getElementById('user-search').addEventListener('keydown', function(e){
    if (e.key !== 'Enter') return;
    var kw = this.value.trim();
    tbody.querySelectorAll('tr').forEach(function(tr){
      var name = tr.children[1].textContent;
      var nickname = tr.children[2].textContent;
      tr.style.display = (!kw || name.indexOf(kw) !== -1 || nickname.indexOf(kw) !== -1) ? '' : 'none';
    });
    refreshState();
  });
  
  /* ========== 刷新 ========== */
  document.getElementById('btn-refresh').addEventListener('click', function(){
    document.getElementById('user-search').value = '';
    loadUsers();
    toast('已刷新');
  });
  
  /* ========== 新建用户 ========== */
  document.getElementById('btn-add-user').addEventListener('click', function(){
    ['f-name','f-nickname','f-pwd','f-email','f-phone'].forEach(function(id){
      var el = document.getElementById(id); el.value = ''; el.classList.remove('err');
    });
    document.getElementById('f-role').value = '';
    loadRoleOptions('f-role');
    openModal('modal-add-user');
  });

  document.getElementById('f-btn-create').addEventListener('click', function(){
    var required = [
      { id:'f-name',    label:'用户名称' },
      { id:'f-pwd',     label:'密码' },
      { id:'f-email',   label:'邮箱' }
    ];
    for (var i = 0; i < required.length; i++){
      var r = required[i];
      var el = document.getElementById(r.id);
      el.classList.remove('err');
      if (!el.value.trim()){
        el.classList.add('err');
        el.focus();
        toast('请输入' + r.label);
        return;
      }
    }
    var body = {
      username: document.getElementById('f-name').value.trim(),
      nickname: document.getElementById('f-nickname').value.trim(),
      password: document.getElementById('f-pwd').value.trim(),
      email: document.getElementById('f-email').value.trim(),
      phone: document.getElementById('f-phone').value.trim(),
      role: document.getElementById('f-role').value
    };
    apiPost('/api/users', body).then(function(res){
      closeModal('modal-add-user');
      toast('创建成功');
      loadUsers();
    }).catch(function(){ toast('创建失败'); });
  });
  
  /* ========== 初始化 ========== */
  loadUsers();
  loadRoleOptions('sr-role');
})
</script>
<style>
.ico-svg{ width:15px; height:15px; vertical-align:-2px; }
  /* 状态绿点 */
  .st{ display:inline-flex; align-items:center; gap:6px; }
  .st-dot{ width:8px; height:8px; border-radius:50%; background:var(--green); display:inline-block; }
  /* 操作列两行链接 */
  .op-col{ display:flex; flex-direction:column; align-items:flex-start; gap:2px; }
  /* 表单红框校验 */
  .form-input.err,.form-sel.err{ border-color:var(--red); }
  .form-sel{ width:100%; border:1px solid var(--border); border-radius:6px; padding:9px 12px; font-size:14px; background:#fff; appearance:none;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2386909C' stroke-width='2'><path d='M6 9l6 6 6-6'/></svg>");
    background-repeat:no-repeat; background-position:right 12px center; cursor:pointer; }
  .form-sel:focus{ border-color:var(--primary); box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  /* 新建用户弹窗（对照 image49） */
  #modal-add-user .modal{ width:440px; }
  #modal-add-user .modal-title{ font-size:16px; }
  #modal-add-user .modal-head{ padding:22px 28px 0; }
  #modal-add-user .modal-body{ padding:20px 28px 6px; }
  #modal-add-user .form-item{ margin-bottom:14px; }
  #modal-add-user .form-label{ color:var(--text-1); margin-bottom:8px; }
  #modal-add-user .modal-foot{ justify-content:center; padding:6px 28px 24px; }
  #modal-add-user .modal-foot .btn{ min-width:84px; }
  /* 确认弹窗 */
  .confirm-body{ padding:22px 24px 8px; font-size:14px; color:var(--text-2); line-height:1.7; }
</style>

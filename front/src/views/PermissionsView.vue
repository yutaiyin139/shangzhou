<template>
  <AppShell id="page-root" active-key="perms" main-class="main-white">
    <div class="page-pad">
      <div class="page-head">
        <div class="page-title">权限管理</div>
        <div class="ops">
          <button class="btn btn-primary" id="btn-save-perms">保存权限设置</button>
        </div>
      </div>
    
            <div class="perm-cols">
              <!-- 左栏：选择角色 -->
              <div class="perm-left">
                <div class="pl-head">
                  <span class="t">选择角色</span>
                  <button class="btn btn-sm" id="btn-role-refresh">刷新</button>
                </div>
                <div class="search-input" style="width:100%;background:#fff;border:1px solid var(--border);min-width:0">
                  <input id="role-search" placeholder="角色名称">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
                </div>
                <div id="role-list" style="margin-top:12px">
                  <div class="role-item active" data-role="admin">
                    <div class="r-name">管理员</div>
                    <div class="r-count">5 个用户</div>
                  </div>
                  <div class="role-item" data-role="normal">
                    <div class="r-name">普通用户</div>
                    <div class="r-count">2 个用户</div>
                  </div>
                  <div class="role-item" data-role="guest">
                    <div class="r-name">访客</div>
                    <div class="r-count">1 个用户</div>
                  </div>
                </div>
              </div>
    
              <!-- 右栏：权限勾选 -->
              <div class="perm-right">
                <div class="tabs" id="perm-tabs">
                  <button class="tab active">功能权限</button>
                </div>
    
                <div id="perm-tree">
                  <div class="perm-group-bar">智能体管理</div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="004">
                    <span class="p-name">智能工作台</span>
                    <span class="p-code">004</span>
                  </div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="003">
                    <span class="p-name">单智能体应用</span>
                    <span class="p-code">003</span>
                  </div>
    
                  <div class="perm-group-bar">权限管理</div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="permission:manage">
                    <span class="p-name">权限管理</span>
                    <span class="p-code">permission:manage</span>
                  </div>
    
                  <div class="perm-group-bar">用户管理</div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="user:manage">
                    <span class="p-name">用户管理</span>
                    <span class="p-code">user:manage</span>
                  </div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="user:view">
                    <span class="p-name">查看用户</span>
                    <span class="p-code">user:view</span>
                  </div>
    
                  <div class="perm-group-bar">角色管理</div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="role:manage">
                    <span class="p-name">角色管理</span>
                    <span class="p-code">role:manage</span>
                  </div>
                  <div class="perm-row">
                    <input type="checkbox" class="cbx p-cbx" data-code="role:view">
                    <span class="p-name">查看角色</span>
                    <span class="p-code">role:view</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'

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
  var curRoleId = null;
  var allPerms = [];
  
  /* ========== 加载角色列表 ========== */
  function loadRoles(){
    apiGet(API + '/api/roles').then(function(res){
      if (res.code !== 200) return;
      var list = document.getElementById('role-list');
      list.innerHTML = '';
      res.data.forEach(function(r, i){
        var div = document.createElement('div');
        div.className = 'role-item' + (i === 0 ? ' active' : '');
        div.setAttribute('data-rid', r.id);
        div.innerHTML = '<div class="r-name">' + r.name + '</div>' +
                        '<div class="r-count">' + r.user_count + ' 个用户</div>';
        list.appendChild(div);
        if (i === 0){
          curRoleId = r.id;
          loadRolePerms(r.id);
        }
      });
      bindRoleClicks();
    });
  }
  
  /* ========== 加载权限列表 ========== */
  function loadPerms(){
    apiGet(API + '/api/permissions').then(function(res){
      if (res.code !== 200) return;
      allPerms = res.data;
      renderPermTree(allPerms, []);
      if (curRoleId) loadRolePerms(curRoleId);
    });
  }
  
  /* ========== 渲染权限树 ========== */
  function renderPermTree(perms, grantedCodes){
    var tree = document.getElementById('perm-tree');
    tree.innerHTML = '';
    var modules = {};
    perms.forEach(function(p){
      var m = p.module || '其他';
      if (!modules[m]) modules[m] = [];
      modules[m].push(p);
    });
    Object.keys(modules).forEach(function(m){
      var bar = document.createElement('div');
      bar.className = 'perm-group-bar';
      bar.textContent = m;
      tree.appendChild(bar);
      modules[m].forEach(function(p){
        var row = document.createElement('div');
        row.className = 'perm-row';
        var checked = grantedCodes.indexOf(p.code) !== -1 ? ' checked' : '';
        row.innerHTML = '<input type="checkbox" class="cbx p-cbx" data-pid="' + p.id + '" data-code="' + p.code + '"' + checked + '>' +
          '<span class="p-name">' + p.name + '</span>' +
          '<span class="p-code">' + p.code + '</span>';
        tree.appendChild(row);
      });
    });
  }
  
  /* ========== 加载角色已分配的权限 ========== */
  function loadRolePerms(rid){
    apiGet(API + '/api/roles/' + rid + '/permissions')
      .then(function(res){
        if (res.code !== 200) return;
        var codes = res.data.map(function(p){ return p.code; });
        document.querySelectorAll('.p-cbx').forEach(function(cb){
          cb.checked = codes.indexOf(cb.getAttribute('data-code')) !== -1;
        });
      });
  }
  
  /* ========== 角色切换 ========== */
  function bindRoleClicks(){
    document.querySelectorAll('#role-list .role-item').forEach(function(item){
      item.addEventListener('click', function(){
        document.querySelectorAll('#role-list .role-item').forEach(function(x){ x.classList.remove('active'); });
        item.classList.add('active');
        curRoleId = item.getAttribute('data-rid');
        loadRolePerms(curRoleId);
      });
    });
  }
  
  /* ========== 左栏角色搜索过滤 ========== */
  document.getElementById('role-search').addEventListener('input', function(){
    var kw = this.value.trim();
    document.querySelectorAll('#role-list .role-item').forEach(function(item){
      var name = item.querySelector('.r-name').textContent;
      item.style.display = (!kw || name.indexOf(kw) !== -1) ? '' : 'none';
    });
  });
  
  /* ========== 刷新 ========== */
  document.getElementById('btn-role-refresh').addEventListener('click', function(){
    loadRoles();
    loadPerms();
    toast('已刷新');
  });
  
  /* ========== 保存权限 ========== */
  document.getElementById('btn-save-perms').addEventListener('click', function(){
    if (!curRoleId){ toast('请先选择角色'); return; }
    var ids = [];
    document.querySelectorAll('.p-cbx:checked').forEach(function(cb){
      ids.push(parseInt(cb.getAttribute('data-pid')));
    });
    apiPut(API + '/api/roles/' + curRoleId + '/permissions', { permission_ids: ids }).then(function(res){
      if (res.code === 200) toast('权限设置已保存');
      else toast('保存失败');
    });
  });
  
  /* ========== 初始化 ========== */
  loadRoles();
  loadPerms();
})
</script>
<style>
.assign-switch{ margin:14px 0 14px; font-size:14px; color:var(--text-2); display:flex; gap:10px; align-items:center; }
  .assign-switch .as-item{ cursor:pointer; background:none; border:none; font-size:14px; color:var(--text-2); padding:0; }
  .assign-switch .as-item:hover{ color:var(--primary); }
  .assign-switch .as-item.active{ color:var(--primary); font-weight:500; }
  .assign-switch .as-div{ color:var(--text-4); }
  /* 左右两栏 */
  .perm-cols{ display:flex; gap:16px; align-items:stretch; }
  .perm-left{ width:340px; flex-shrink:0; min-height:70vh; background:#fff; border:1px solid var(--border-light); border-radius:var(--radius); padding:18px 16px; }
  .perm-right{ flex:1; min-height:70vh; background:#fff; border:1px solid var(--border-light); border-radius:var(--radius); padding:6px 20px 20px; display:flex; flex-direction:column; }
  .pl-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
  .pl-head .t{ font-size:15px; font-weight:600; }
  /* 角色列表 */
  .role-item{ padding:10px 12px; border-radius:6px; cursor:pointer; margin-bottom:4px; }
  .role-item:hover{ background:#F7F8FA; }
  .role-item.active{ background:var(--primary-light); }
  .role-item .r-name{ font-size:14px; color:var(--text-1); }
  .role-item .r-count{ font-size:12px; color:var(--text-4); margin-top:2px; }
  /* 分组勾选树 */
  .perm-group-bar{ background:#F2F3F5; border-radius:4px; padding:8px 14px; font-size:14px; font-weight:600; color:var(--text-1); margin-top:10px; }
  .perm-row{ display:flex; align-items:center; gap:8px; padding:12px 14px; border-bottom:1px solid var(--border-light); }
  .perm-row .cbx{ width:16px; height:16px; accent-color:var(--primary); cursor:pointer; }
  .perm-row .p-name{ font-size:14px; }
  .perm-row .p-code{ margin-left:auto; font-size:13px; color:var(--text-3); }
</style>

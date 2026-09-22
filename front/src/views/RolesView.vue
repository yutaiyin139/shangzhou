<template>
  <AppShell id="page-root" active-key="roles" main-class="main-white">
    <div class="page-pad">
            <!-- 页内标签 -->
            <div class="tabs">
              <button class="tab" id="tab-users">用户管理</button>
              <button class="tab active">角色管理</button>
              <button class="tab" id="tab-funcs">功能管理</button>
            </div>
    
            <!-- 工具条 -->
            <div style="display:flex;gap:10px;margin-top:16px;align-items:center;flex-wrap:wrap">
              <button class="btn btn-primary" id="btn-add-role">＋ 新建角色</button>
              <div style="margin-left:auto;display:flex;gap:10px;align-items:center">
                <div class="search-input" style="background:#fff;border:1px solid var(--border)">
                  <input id="role-search" placeholder="角色名称">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
                </div>
                <button class="btn" style="padding:7px 10px" title="刷新" id="btn-refresh">
                  <svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 3v5h-5"/></svg>
                </button>
              </div>
            </div>
    
            <!-- 角色表格 -->
            <div class="table-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>角色名称</th><th>描述</th><th>用户数</th><th>状态</th><th>创建时间</th><th style="width:110px">操作</th>
                  </tr>
                </thead>
                <tbody id="role-tbody">
                  <tr>
                    <td>管理员</td>
                    <td>系统管理员，拥有所有权限</td>
                    <td>5</td>
                    <td><span class="st"><span class="st-dot"></span>启用</span></td>
                    <td>2026-07-24 16:43:56</td>
                    <td><div class="op-col">
                      <button class="link row-edit">编辑</button>
                      <button class="link link-red row-del">删除</button>
                    </div></td>
                  </tr>
                  <tr>
                    <td>普通用户</td>
                    <td>普通用户，拥有基本权限</td>
                    <td>2</td>
                    <td><span class="st"><span class="st-dot"></span>启用</span></td>
                    <td>2026-07-24 16:43:56</td>
                    <td><div class="op-col">
                      <button class="link row-edit">编辑</button>
                      <button class="link link-red row-del">删除</button>
                    </div></td>
                  </tr>
                  <tr>
                    <td>访客</td>
                    <td>访客用户，只有查看权限</td>
                    <td>1</td>
                    <td><span class="st"><span class="st-dot"></span>启用</span></td>
                    <td>2026-07-24 16:43:56</td>
                    <td><div class="op-col">
                      <button class="link row-edit">编辑</button>
                      <button class="link link-red row-del">删除</button>
                    </div></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
    <!-- 新建/编辑角色弹窗 -->
    <div class="modal-mask" id="modal-role">
      <div class="modal" style="width:440px">
        <div class="modal-head">
          <span class="modal-title" id="role-modal-title">新建角色</span>
          <button class="modal-close" data-action="closeModal(&#x27;modal-role&#x27;)">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <div class="form-label">角色名称 <span class="req">*</span></div>
            <input class="form-input" id="f-name" placeholder="请输入角色名称">
          </div>
          <div class="form-item" style="margin-bottom:4px">
            <div class="form-label">描述</div>
            <input class="form-input" id="f-desc" placeholder="请输入描述（选填）">
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-primary" id="f-btn-save">创建</button>
          <button class="btn" data-action="closeModal(&#x27;modal-role&#x27;)">取消</button>
        </div>
      </div>
    </div>
    
    <!-- 删除确认弹窗 -->
    <div class="modal-mask" id="modal-confirm">
      <div class="modal" style="width:400px">
        <div class="modal-head">
          <span class="modal-title">确认删除</span>
          <button class="modal-close" data-action="closeModal(&#x27;modal-confirm&#x27;)">✕</button>
        </div>
        <div class="confirm-body" id="confirm-text">确定删除该角色吗？</div>
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
  var tbody = document.getElementById('role-tbody');
  
  document.getElementById('tab-users').addEventListener('click', function(){ window.location.hash = '#/users'; });
  document.getElementById('tab-funcs').addEventListener('click', function(){ window.location.hash = '#/functions'; });
  
  /* ========== 加载角色列表 ========== */
  function loadRoles(){
    apiGet(API + '/api/roles').then(function(res){
      if (res.code !== 200) return;
      tbody.innerHTML = '';
      res.data.forEach(function(r){
        var tr = document.createElement('tr');
        tr.setAttribute('data-rid', r.id);
        tr.innerHTML =
          '<td>' + r.name + '</td>' +
          '<td>' + (r.description || '-') + '</td>' +
          '<td>' + r.user_count + '</td>' +
          '<td><span class="st"><span class="st-dot"></span>' + (r.status === 1 ? '启用' : '禁用') + '</span></td>' +
          '<td>' + r.created_at + '</td>' +
          '<td><div class="op-col">' +
            '<button class="link row-edit">编辑</button>' +
            '<button class="link link-red row-del">删除</button>' +
          '</div></td>';
        tbody.appendChild(tr);
      });
    });
  }
  
  /* 删除确认 */
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
  
  /* 新建 / 编辑 */
  var editingRid = null;
  document.getElementById('btn-add-role').addEventListener('click', function(){
    editingRid = null;
    document.getElementById('role-modal-title').textContent = '新建角色';
    document.getElementById('f-btn-save').textContent = '创建';
    var n = document.getElementById('f-name'); n.value = ''; n.classList.remove('err');
    document.getElementById('f-desc').value = '';
    openModal('modal-role');
  });
  
  tbody.addEventListener('click', function(e){
    var tr = e.target.closest('tr');
    if (!tr) return;
    if (e.target.classList.contains('row-del')){
      var rid = tr.getAttribute('data-rid');
      var name = tr.children[0].textContent;
      askConfirm('确定删除角色「' + name + '」吗？', function(){
        apiDelete(API + '/api/roles/' + rid)
          .then(function(res){
            if (res.code === 200){ tr.remove(); toast('已删除'); }
            else toast('删除失败');
          });
      });
    }
    if (e.target.classList.contains('row-edit')){
      editingRid = tr.getAttribute('data-rid');
      document.getElementById('role-modal-title').textContent = '编辑角色';
      document.getElementById('f-btn-save').textContent = '保存';
      var n = document.getElementById('f-name'); n.value = tr.children[0].textContent; n.classList.remove('err');
      var desc = tr.children[1].textContent;
      document.getElementById('f-desc').value = (desc === '-') ? '' : desc;
      openModal('modal-role');
    }
  });
  
  document.getElementById('f-btn-save').addEventListener('click', function(){
    var nameEl = document.getElementById('f-name');
    nameEl.classList.remove('err');
    if (!nameEl.value.trim()){
      nameEl.classList.add('err');
      nameEl.focus();
      toast('请输入角色名称');
      return;
    }
    var name = nameEl.value.trim();
    var desc = document.getElementById('f-desc').value.trim();
  
    if (editingRid){
      apiPut(API + '/api/roles/' + editingRid, { name: name, description: desc }).then(function(res){
        if (res.code === 200){
          closeModal('modal-role');
          toast('保存成功');
          loadRoles();
        } else toast('保存失败');
      });
    } else {
      apiPost(API + '/api/roles', { name: name, description: desc }).then(function(res){
        if (res.code === 200){
          closeModal('modal-role');
          toast('创建成功');
          loadRoles();
        } else toast('创建失败');
      });
    }
  });
  
  /* 搜索过滤 */
  document.getElementById('role-search').addEventListener('keydown', function(e){
    if (e.key !== 'Enter') return;
    var kw = this.value.trim();
    tbody.querySelectorAll('tr').forEach(function(tr){
      tr.style.display = (!kw || tr.children[0].textContent.indexOf(kw) !== -1) ? '' : 'none';
    });
  });
  
  /* 刷新 */
  document.getElementById('btn-refresh').addEventListener('click', function(){
    document.getElementById('role-search').value = '';
    loadRoles();
    toast('已刷新');
  });
  
  /* 初始化 */
  loadRoles();
})
</script>
<style>
.ico-svg{ width:15px; height:15px; vertical-align:-2px; }
  .st{ display:inline-flex; align-items:center; gap:6px; }
  .st-dot{ width:8px; height:8px; border-radius:50%; background:var(--green); display:inline-block; }
  .op-col{ display:flex; align-items:center; gap:10px; }
  .form-input.err{ border-color:var(--red); }
  .confirm-body{ padding:22px 24px 8px; font-size:14px; color:var(--text-2); line-height:1.7; }
</style>

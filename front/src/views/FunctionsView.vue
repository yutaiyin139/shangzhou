<template>
  <AppShell id="page-root" active-key="functions" main-class="main-white">
    <div class="page-pad">
            <!-- 页内标签 -->
            <div class="tabs">
              <button class="tab" id="tab-users">用户管理</button>
              <button class="tab" id="tab-roles">角色管理</button>
              <button class="tab active">功能管理</button>
            </div>
    
            <!-- 工具条 -->
            <div style="display:flex;gap:10px;margin-top:16px;align-items:center;flex-wrap:wrap">
              <div style="margin-left:auto;display:flex;gap:10px;align-items:center">
                <div class="search-input" style="background:#fff;border:1px solid var(--border)">
                  <input id="func-search" placeholder="功能名称">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
                </div>
                <button class="btn" style="padding:7px 10px" title="刷新" id="btn-refresh">
                  <svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 3v5h-5"/></svg>
                </button>
              </div>
            </div>
    
            <!-- 功能表格 -->
            <div class="table-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>功能名称</th><th>功能代码</th><th>所属模块</th><th>描述</th><th>创建时间</th>
                  </tr>
                </thead>
                <tbody id="func-tbody">
                </tbody>
              </table>
            </div>
          </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet } from '../api/client'

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
  var tbody = document.getElementById('func-tbody');
  
  document.getElementById('tab-users').addEventListener('click', function(){ window.location.hash = '#/users'; });
  document.getElementById('tab-roles').addEventListener('click', function(){ window.location.hash = '#/roles'; });
  
  /* ========== 加载功能列表 ========== */
  function loadFunctions(){
    apiGet('/api/permissions').then(function(res){
      tbody.innerHTML = '';
      res.data.forEach(function(p){
        var tr = document.createElement('tr');
        tr.innerHTML =
          '<td>' + p.name + '</td>' +
          '<td>' + p.code + '</td>' +
          '<td>' + (p.module || '-') + '</td>' +
          '<td>' + (p.description || '-') + '</td>' +
          '<td>' + (p.created_at || '-') + '</td>';
        tbody.appendChild(tr);
      });
    }).catch(function(err){ console.error('加载失败:', err); tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#f53f3f;padding:20px">加载失败，请检查后端服务是否启动</td></tr>'; });
  }
  
  loadFunctions();
  
  /* 搜索过滤 */
  document.getElementById('func-search').addEventListener('keydown', function(e){
    if (e.key !== 'Enter') return;
    var kw = this.value.trim().toLowerCase();
    tbody.querySelectorAll('tr').forEach(function(tr){
      tr.style.display = (!kw || tr.children[0].textContent.toLowerCase().indexOf(kw) !== -1) ? '' : 'none';
    });
  });
  
  /* 刷新 */
  document.getElementById('btn-refresh').addEventListener('click', function(){
    document.getElementById('func-search').value = '';
    loadFunctions();
    toast('已刷新');
  });
})
</script>
<style>
.ico-svg{ width:15px; height:15px; vertical-align:-2px; }
  .op-col{ display:flex; flex-direction:column; align-items:flex-start; gap:2px; }
  .form-input.err,.form-sel.err{ border-color:var(--red); }
  .form-sel{ width:100%; border:1px solid var(--border); border-radius:6px; padding:9px 12px; font-size:14px; background:#fff; appearance:none;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2386909C' stroke-width='2'><path d='M6 9l6 6 6-6'/></svg>");
    background-repeat:no-repeat; background-position:right 12px center; cursor:pointer; }
  .form-sel:focus{ border-color:var(--primary); box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  .confirm-body{ padding:22px 24px 8px; font-size:14px; color:var(--text-2); line-height:1.7; }
</style>

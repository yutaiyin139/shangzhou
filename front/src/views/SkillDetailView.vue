<template>
  <AppShell id="page-root" active-key="skill-detail" main-class="main-white">
    <div class="sd-topbar">
            <span class="sd-crumb"><a data-action="location.hash = '/skills'">Skills 广场</a> / <b id="crumbName">-</b></span>
            <div class="sd-tabs" id="sdTabs">
              <button class="active" data-v="overview">概览</button>
              <button data-v="history">更新记录</button>
            </div>
            <div class="sd-ops">
              <button class="btn btn-indigo" id="sdUninstallBtn" style="display:none;" data-action="uninstallSkill()">卸载</button>
              <button class="btn btn-indigo" id="sdInstallBtn" data-action="installSkill()">安装</button>
              <button class="btn" id="sdDelBtn" style="display:none;color:var(--red);border-color:var(--red);" data-action="delSkill()">删除</button>
            </div>
          </div>

          <!-- 概览 -->
          <div class="sd-body" id="viewOverview">
            <div class="sd-title">
              <div class="sd-icon" id="sdIcon">✨</div>
              <span class="sd-name" id="sdName">-</span>
              <span class="sd-ver">版本 V 1.0</span>
            </div>
            <div class="sd-desc" id="sdDesc"></div>
            <div class="sd-tags">
              <span class="sd-tag" id="sdKind">-</span>
              <span class="sd-tag" id="sdCate">-</span>
              <span class="sd-tag" id="sdTime">-</span>
            </div>

            <div class="sd-table">
              <div class="sd-tr"><div class="sd-th">name</div><div class="sd-td" id="tdName">-</div></div>
              <div class="sd-tr"><div class="sd-th">description</div><div class="sd-td" id="tdDesc"></div></div>
            </div>

            <div class="sd-md" id="sdMd"></div>
          </div>

          <!-- 更新记录 -->
          <div class="sd-body" id="viewHistory" style="display:none;">
            <div class="sd-empty">暂无更新记录</div>
          </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet, apiPost, apiDelete } from '../api/client'

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

  var skill = null;   // 当前技能详情

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* 简单 Markdown 渲染（标题/列表/段落/分割线） */
  function mdHtml(md){
    var html = '';
    var inList = false;
    function closeList(){ if (inList){ html += '</ul>'; inList = false; } }
    String(md || '').split(/\r?\n/).forEach(function(line){
      line = line.trim();
      if (!line){ closeList(); return; }
      var h3 = line.match(/^#\s+(.*)$/);
      var h4 = line.match(/^##\s+(.*)$/);
      var li = line.match(/^[-*]\s+(.*)$/);
      var liN = line.match(/^\d+[.、]\s*(.*)$/);
      if (/^-{3,}$/.test(line)){ closeList(); html += '<hr>'; return; }
      if (h3){ closeList(); html += '<h3>' + esc(h3[1]) + '</h3>'; return; }
      if (h4){ closeList(); html += '<h4>' + esc(h4[1]) + '</h4>'; return; }
      if (li || liN){
        if (!inList){ html += '<ul>'; inList = true; }
        html += '<li>' + esc(li ? li[1] : liN[1]) + '</li>';
        return;
      }
      closeList();
      html += '<p>' + esc(line) + '</p>';
    });
    closeList();
    return html;
  }

  /* 加载详情（hash 路由：query 在 hash 内） */
  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var key = params.get('key') || '';

  function loadDetail(){
    if (!key) return;
    apiGet('/api/skills/' + encodeURIComponent(key) + '/detail').then(function(data){
      if (data.code !== 200){ toast(data.msg || '加载失败'); return; }
      skill = data.data;
      document.getElementById('crumbName').textContent = skill.name;
      document.getElementById('sdName').textContent = skill.name;
      document.getElementById('tdName').textContent = skill.name;
      document.getElementById('sdDesc').textContent = skill.description || '';
      document.getElementById('tdDesc').textContent = skill.description || '';
      document.getElementById('sdIcon').textContent = skill.icon || '✨';
      document.getElementById('sdKind').textContent = skill.kind === 'custom' ? '自定义' : '内置';
      document.getElementById('sdCate').textContent = '分类：' + (skill.category || '其他');
      document.getElementById('sdTime').textContent = '更新于 ' + (skill.updated_at || '');
      document.getElementById('sdMd').innerHTML = mdHtml(skill.content) || '<p>（暂无正文）</p>';
      document.title = skill.name + ' - Skills 广场 - 熵舟·智能体工作台';
      updateOps();
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* 顶部操作按钮：内置 = 安装/卸载；自定义 = 删除 */
  function updateOps(){
    var isCustom = skill && skill.kind === 'custom';
    document.getElementById('sdDelBtn').style.display = isCustom ? '' : 'none';
    var on = !!(skill && skill.installed);
    document.getElementById('sdInstallBtn').style.display = isCustom || on ? 'none' : '';
    document.getElementById('sdUninstallBtn').style.display = isCustom || !on ? 'none' : '';
  }
  function installSkill(){
    if (!skill) return;
    apiPost('/api/skills/' + encodeURIComponent(skill.key) + '/install').then(function(data){
        if (data.code === 200){ skill.installed = true; updateOps(); toast('已安装，可在智能体编排中使用'); }
        else toast(data.msg || '安装失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function uninstallSkill(){
    if (!skill) return;
    apiDelete('/api/skills/' + encodeURIComponent(skill.key) + '/install').then(function(data){
        if (data.code === 200){ skill.installed = false; updateOps(); toast('已卸载'); }
        else toast(data.msg || '卸载失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function delSkill(){
    if (!skill || !confirm('确定删除自定义 Skill「' + skill.name + '」吗？')) return;
    apiDelete('/api/skills/' + skill.key.replace(/^custom_/, '')).then(function(data){
        if (data.code === 200){ toast('已删除'); location.hash = '/skills'; }
        else toast(data.msg || '删除失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* 概览 / 更新记录 切换 */
  document.querySelectorAll('#sdTabs button').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('#sdTabs button').forEach(function(x){ x.classList.remove('active'); });
      b.classList.add('active');
      var isHistory = b.dataset.v === 'history';
      document.getElementById('viewOverview').style.display = isHistory ? 'none' : '';
      document.getElementById('viewHistory').style.display = isHistory ? '' : 'none';
    });
  });

  window.installSkill = installSkill;
  window.uninstallSkill = uninstallSkill;
  window.delSkill = delSkill;

  loadDetail();
})
</script>
<style>
  .sd-topbar{ display:flex; align-items:center; gap:16px; padding:14px 24px; background:#fff;
    border-bottom:1px solid var(--border-light); position:sticky; top:0; z-index:10; }
  .sd-crumb{ font-size:14px; color:var(--text-3); }
  .sd-crumb a{ color:var(--text-3); cursor:pointer; }
  .sd-crumb a:hover{ color:var(--primary); }
  .sd-crumb b{ color:var(--text-1); font-weight:600; }
  .sd-tabs{ position:absolute; left:50%; transform:translateX(-50%); display:flex; gap:4px;
    background:#F2F3F5; border-radius:8px; padding:3px; }
  .sd-tabs button{ border:none; background:transparent; padding:5px 18px; border-radius:6px;
    font-size:13px; color:var(--text-2); cursor:pointer; }
  .sd-tabs button.active{ background:#fff; color:var(--text-1); font-weight:500; box-shadow:0 1px 4px rgba(29,33,41,.1); }
  .sd-ops{ margin-left:auto; display:flex; gap:10px; align-items:center; }
  .sd-ops .btn{ display:inline-flex; align-items:center; gap:6px; }
  .btn-indigo{ background:#5B5BD6; color:#fff; border:none; }
  .btn-indigo:hover{ background:#4A4AC4; }

  .sd-body{ max-width:1080px; margin:0 auto; padding:34px 40px 60px; }
  .sd-title{ display:flex; align-items:center; gap:14px; }
  .sd-icon{ width:52px; height:52px; border:1px solid var(--border); border-radius:10px;
    display:flex; align-items:center; justify-content:center; font-size:24px; color:var(--primary); background:#fff; }
  .sd-name{ font-size:22px; font-weight:700; }
  .sd-ver{ border:1px solid var(--border); border-radius:6px; font-size:12px; color:var(--text-2);
    padding:3px 10px; user-select:none; }
  .sd-desc{ font-size:14px; color:var(--text-2); line-height:1.8; margin-top:18px; }
  .sd-tags{ display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }
  .sd-tag{ background:#F2F3F5; color:var(--text-2); font-size:12px; border-radius:6px; padding:4px 12px;
    display:inline-flex; align-items:center; gap:5px; }

  .sd-table{ border:1px solid var(--border-light); border-radius:10px; overflow:hidden; margin-top:26px; }
  .sd-tr{ display:flex; }
  .sd-tr + .sd-tr{ border-top:1px solid var(--border-light); }
  .sd-th{ width:170px; flex-shrink:0; padding:14px 18px; font-size:13px; color:var(--text-1);
    border-right:1px solid var(--border-light); background:#fff; }
  .sd-td{ flex:1; padding:14px 18px; font-size:13px; color:var(--text-2); line-height:1.7; }

  .sd-md{ margin-top:34px; font-size:14px; color:var(--text-1); line-height:1.9; }
  .sd-md h3{ font-size:16px; font-weight:700; margin:0 0 18px; }
  .sd-md h4{ font-size:14px; font-weight:700; margin:26px 0 12px; }
  .sd-md p{ color:var(--text-2); margin:0 0 12px; }
  .sd-md hr{ border:none; border-top:1px solid var(--border-light); margin:26px 0; }
  .sd-md ul{ color:var(--text-2); padding-left:20px; margin:0; }
  .sd-md ul li{ margin-bottom:6px; }

  .sd-empty{ text-align:center; color:var(--text-3); font-size:13px; padding:80px 0; }
</style>

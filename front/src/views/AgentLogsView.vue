<template>
  <div id="page-root" class="page-root agent-logs-root">
    <div class="ad-shell">
      <!-- 左窄栏 -->
      <aside class="ad-side">
        <div class="ad-side-top">
          <button class="ad-back" title="返回" data-action="location.hash = '/my-agents'">‹</button>
          <span class="ad-home" title="首页" data-action="location.hash = '/home'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg></span>
          <span class="ad-crumb">/ AGENTS</span>
          <span class="sp">
            <button class="ad-icobtn" data-action="toast(&#x27;暂无新通知&#x27;)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2 2 0 0 0 4 0"/></svg><span class="dot"></span></button>
            <button class="ad-icobtn" data-action="toggleSidePanel()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg></button>
          </span>
        </div>
    
        <div class="ad-agent">
          <span class="ava">🧸</span>
          <span class="nm">客服助手</span>
          <button class="more" data-action="openMoreMenu()">…</button>
        </div>
    
        <nav class="ad-menu" id="adMenu">
          <div class="ad-mitem" data-action="navKeep('/agent-config')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg></span>配置</div>
          <div class="ad-mitem" data-action="navKeep('/agent-detail')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v18M3 12h18M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg></span>访问点</div>
          <div class="ad-mitem active"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg></span>日志</div>
          <div class="ad-mitem" data-action="navKeep('/agent-monitor')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 19V10M10 19V5M16 19v-8"/><path d="M2 19h20"/></svg></span>监控</div>
        </nav>
    
        <div class="ad-user">
          <span class="u-ava">于</span>
          <span class="u-nm">于太印</span>
          <button class="u-help" data-action="openHelpCenter()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.2a2.6 2.6 0 1 1 3.6 2.4c-.8.3-1.1.9-1.1 1.7"/><circle cx="12" cy="16.8" r=".6" fill="currentColor"/></svg></button>
        </div>
      </aside>
    
      <!-- 主区：日志 -->
      <main class="ad-main">
        <div class="ad-title">日志</div>
        <div class="ad-sub">完整日志记录应用运行状态，包括用户输入、Agent 回复、规划和工具使用。</div>
    
        <div class="log-filter">
          <span class="lf-chip" data-action="openTimeRange()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg><span id="timeRangeLabel">最近 7 天</span><span class="x" data-action="event.stopPropagation();clearTimeRange()">✕</span></span>
          <span class="lf-chip gray" data-action="openSourceFilter()">来源<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
          <span class="lf-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="logSearchInput" placeholder="搜索" onkeydown="if(event.key==='Enter')doSearch()"></span>
          <span class="lf-right">
            <span class="lf-sort" data-action="toggleSort()">排序：<b id="sortLabel">最近创建时间</b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
            <button class="lf-ico" data-action="toggleViewMode()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
          </span>
        </div>
    
        <div class="log-table">
          <table class="tbl">
            <thead><tr><th>标题</th><th>来源</th><th>终端用户</th><th>消息数</th><th>用户评分</th><th>操作率</th><th>更新时间</th><th>创建时间</th></tr></thead>
          </table>
          <div class="log-empty">暂无日志</div>
        </div>
    
        <div class="log-foot">
          <span class="pg"><button data-action="prevPage()">‹</button><span class="cur" id="pageInfo">1 / 1</span><button data-action="nextPage()">›</button></span>
          <span class="pg-num" id="pageNum">1</span>
          <span class="pg-size"><span data-action="setPageSize(10)">10</span><span class="on" data-action="setPageSize(25)">25</span><span data-action="setPageSize(50)">50</span></span>
        </div>
      </main>
    </div>
  </div>
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

  /* ================= P2 占位功能实现 ================= */

  /* 收起/展开侧边面板 */
  function toggleSidePanel(){
    var side = document.querySelector('.ad-side');
    var main = document.querySelector('.ad-main');
    if (side.style.display === 'none'){
      side.style.display = '';
      if (main) main.style.flex = '';
      toast('已展开侧边面板');
    } else {
      side.style.display = 'none';
      if (main) main.style.flex = '1';
      toast('已收起侧边面板');
    }
  }
  window.toggleSidePanel = toggleSidePanel;

  /* 更多操作菜单 */
  function openMoreMenu(){
    openModal('更多操作',
      '<div class="more-menu">' +
        '<button class="mm-btn" onclick="exportLogs()"><span class="mm-ico">📤</span>导出日志</button>' +
        '<button class="mm-btn" onclick="clearLogs()"><span class="mm-ico">🗑</span>清空日志</button>' +
      '</div>'
    );
  }
  function exportLogs(){
    closeModal();
    toast('日志已导出');
  }
  function clearLogs(){
    closeModal();
    if (confirm('确定清空所有日志？')){
      document.querySelector('.log-table .tbl').innerHTML = '<thead><tr><th>标题</th><th>来源</th><th>终端用户</th><th>消息数</th><th>用户评分</th><th>操作率</th><th>更新时间</th><th>创建时间</th></tr></thead>';
      document.querySelector('.log-empty').style.display = 'flex';
      toast('日志已清空');
    }
  }
  window.openMoreMenu = openMoreMenu;

  /* 帮助中心 */
  function openHelpCenter(){
    openModal('帮助中心',
      '<div class="help-list">' +
        '<div class="help-item"><b>📖 日志查看指南</b><p>了解如何筛选和查看对话日志</p></div>' +
        '<div class="help-item"><b>🔍 搜索与筛选</b><p>按时间、来源、关键词搜索日志</p></div>' +
        '<div class="help-item"><b>📊 日志字段说明</b><p>各字段含义和评分标准</p></div>' +
        '<div class="help-item"><b>📤 导出日志</b><p>将日志导出为 CSV 或 JSON</p></div>' +
      '</div>'
    );
  }
  window.openHelpCenter = openHelpCenter;

  /* 时间范围选择 */
  function openTimeRange(){
    openModal('选择时间范围',
      '<div class="time-range">' +
        '<button class="tr-btn" data-action="setTimeRange(\'今天\')">今天</button>' +
        '<button class="tr-btn" data-action="setTimeRange(\'最近 7 天\')">最近 7 天</button>' +
        '<button class="tr-btn" data-action="setTimeRange(\'最近 30 天\')">最近 30 天</button>' +
        '<button class="tr-btn" data-action="setTimeRange(\'最近 90 天\')">最近 90 天</button>' +
        '<button class="tr-btn" data-action="setTimeRange(\'全部\')">全部</button>' +
      '</div>'
    );
  }
  function setTimeRange(range){
    document.getElementById('timeRangeLabel').textContent = range;
    closeModal();
    toast('时间范围：' + range);
  }
  function clearTimeRange(){
    document.getElementById('timeRangeLabel').textContent = '全部';
    toast('已清除时间筛选');
  }
  window.openTimeRange = openTimeRange;

  /* 来源筛选 */
  function openSourceFilter(){
    openModal('来源筛选',
      '<div class="source-filter">' +
        '<label class="sf-item"><input type="checkbox" checked> Web app</label>' +
        '<label class="sf-item"><input type="checkbox" checked> API</label>' +
        '<label class="sf-item"><input type="checkbox" checked> 嵌入</label>' +
        '<label class="sf-item"><input type="checkbox" checked> 调试</label>' +
        '<button class="btn btn-primary" data-action="applySourceFilter()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applySourceFilter(){
    closeModal();
    toast('来源筛选已应用');
  }
  window.openSourceFilter = openSourceFilter;

  /* 搜索 */
  function doSearch(){
    var q = document.getElementById('logSearchInput').value.trim();
    toast('搜索：' + (q || '（空）'));
  }
  window.doSearch = doSearch;

  /* 排序切换 */
  var sortModes = ['最近创建时间', '最早创建时间', '消息数降序', '消息数升序'];
  var sortIdx = 0;
  function toggleSort(){
    sortIdx = (sortIdx + 1) % sortModes.length;
    document.getElementById('sortLabel').textContent = sortModes[sortIdx];
    toast('排序：' + sortModes[sortIdx]);
  }
  window.toggleSort = toggleSort;

  /* 视图模式切换（列表/卡片） */
  var viewMode = 'list';
  function toggleViewMode(){
    viewMode = viewMode === 'list' ? 'card' : 'list';
    toast(viewMode === 'list' ? '列表视图' : '卡片视图');
  }
  window.toggleViewMode = toggleViewMode;

  /* 分页 */
  var currentPage = 1, totalPages = 1, pageSize = 25;
  function prevPage(){
    if (currentPage > 1){
      currentPage--;
      refreshPageInfo();
      toast('第 ' + currentPage + ' 页');
    }
  }
  function nextPage(){
    if (currentPage < totalPages){
      currentPage++;
      refreshPageInfo();
      toast('第 ' + currentPage + ' 页');
    }
  }
  function setPageSize(size){
    pageSize = size;
    currentPage = 1;
    refreshPageInfo();
    document.querySelectorAll('.pg-size span').forEach(function(s){
      s.classList.toggle('on', parseInt(s.textContent, 10) === size);
    });
    toast('每页 ' + size + ' 条');
  }
  function refreshPageInfo(){
    document.getElementById('pageInfo').textContent = currentPage + ' / ' + totalPages;
    document.getElementById('pageNum').textContent = currentPage;
  }
  window.prevPage = prevPage;
  window.nextPage = nextPage;
  window.setPageSize = setPageSize;

})
</script>
<style>
.agent-logs-root{ background:#fff; }
  .ad-shell{ display:flex; height:100vh; overflow:hidden; background:#fff; }

  /* ---------- 左窄栏（与访问点页一致） ---------- */
  .ad-side{ width:250px; background:#F7F8FA; border-right:1px solid var(--border-light); display:flex; flex-direction:column; flex-shrink:0; }
  .ad-side-top{ display:flex; align-items:center; gap:4px; padding:12px 10px 4px 14px; }
  .ad-back{ width:24px; height:24px; border:none; background:none; font-size:18px; color:var(--text-1); display:inline-flex; align-items:center; justify-content:center; border-radius:6px; cursor:pointer; }
  .ad-back:hover{ background:#EEF0F3; }
  .ad-home{ width:24px; height:24px; color:var(--text-1); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; border-radius:6px; }
  .ad-home:hover{ background:#EEF0F3; }
  .ad-home svg{ width:17px; height:17px; }
  .ad-crumb{ font-size:14px; font-weight:700; letter-spacing:.5px; margin-left:2px; user-select:none; }
  .ad-side-top .sp{ margin-left:auto; display:flex; gap:4px; }
  .ad-icobtn{ width:26px; height:26px; border:none; background:none; color:var(--text-2); border-radius:6px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; position:relative; }
  .ad-icobtn:hover{ background:#EEF0F3; color:var(--text-1); }
  .ad-icobtn svg{ width:16px; height:16px; }
  .ad-icobtn .dot{ position:absolute; top:4px; right:5px; width:6px; height:6px; border-radius:50%; background:var(--red); }
  .ad-agent{ display:flex; align-items:center; gap:10px; margin:10px 14px 6px; padding:6px 4px; }
  .ad-agent .ava{ width:38px; height:38px; border-radius:50%; background:#F0EBFC; display:flex; align-items:center; justify-content:center; font-size:21px; flex-shrink:0; }
  .ad-agent .nm{ font-size:15px; font-weight:600; }
  .ad-agent .more{ margin-left:auto; border:none; background:none; color:var(--text-3); font-size:16px; cursor:pointer; border-radius:6px; width:24px; height:24px; }
  .ad-agent .more:hover{ background:#EEF0F3; color:var(--text-1); }
  .ad-menu{ padding:6px 10px; }
  .ad-mitem{ display:flex; align-items:center; gap:10px; padding:8px 10px; margin:2px 0; border-radius:8px; font-size:14px; color:var(--text-1); cursor:pointer; user-select:none; }
  .ad-mitem:hover{ background:#EEF0F3; }
  .ad-mitem.active{ background:var(--primary-light); color:var(--primary); font-weight:500; }
  .ad-mitem .mi{ width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center; color:inherit; }
  .ad-mitem .mi svg{ width:16px; height:16px; }
  .ad-user{ margin-top:auto; display:flex; align-items:center; gap:10px; padding:14px; border-top:1px solid var(--border-light); }
  .ad-user .u-ava{ width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#7BA7FF,#2E63F0); color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:12px; flex-shrink:0; }
  .ad-user .u-nm{ font-size:14px; }
  .ad-user .u-help{ margin-left:auto; border:none; background:none; color:var(--text-3); cursor:pointer; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; }
  .ad-user .u-help svg{ width:16px; height:16px; }
  .ad-user .u-help:hover{ color:var(--primary); }

  /* ---------- 主区 ---------- */
  .ad-main{ flex:1; overflow-y:auto; padding:26px 30px 40px; background:#fff; display:flex; flex-direction:column; }
  .ad-title{ font-size:18px; font-weight:600; }
  .ad-sub{ color:var(--text-3); font-size:13px; margin-top:6px; }

  .log-filter{ display:flex; align-items:center; gap:10px; margin-top:20px; }
  .lf-chip{ display:inline-flex; align-items:center; gap:8px; background:#F7F8FA; border:1px solid var(--border-light); border-radius:8px; padding:7px 12px; font-size:13px; color:var(--text-1); cursor:pointer; }
  .lf-chip svg{ width:14px; height:14px; color:var(--text-2); }
  .lf-chip .x{ width:14px; height:14px; border-radius:50%; background:#E4E6EA; color:var(--text-3); display:inline-flex; align-items:center; justify-content:center; font-size:10px; }
  .lf-chip.gray{ color:var(--text-3); }
  .lf-search{ display:flex; align-items:center; gap:8px; background:#F7F8FA; border:1px solid var(--border-light); border-radius:8px; padding:7px 12px; width:230px; }
  .lf-search svg{ width:14px; height:14px; color:var(--text-3); flex-shrink:0; }
  .lf-search input{ border:none; background:none; outline:none; font-size:13px; width:100%; }
  .lf-right{ margin-left:auto; display:flex; align-items:center; gap:10px; }
  .lf-sort{ display:inline-flex; align-items:center; gap:6px; background:#F7F8FA; border:1px solid var(--border-light); border-radius:8px; padding:7px 12px; font-size:13px; color:var(--text-2); cursor:pointer; white-space:nowrap; }
  .lf-sort svg{ width:12px; height:12px; }
  .lf-sort b{ color:var(--text-1); font-weight:500; }
  .lf-ico{ width:34px; height:34px; border:1px solid var(--border-light); border-radius:8px; background:#fff; color:var(--text-2); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; }
  .lf-ico svg{ width:16px; height:16px; }

  .log-table{ margin-top:14px; flex:1; display:flex; flex-direction:column; }
  .log-table .tbl thead th{ font-size:13px; color:var(--text-3); font-weight:500; }
  .log-empty{ flex:1; display:flex; align-items:flex-start; justify-content:center; padding-top:56px; color:var(--text-3); font-size:13px; }

  .log-foot{ display:flex; align-items:center; margin-top:14px; color:var(--text-2); font-size:13px; }
  .pg{ display:inline-flex; align-items:center; gap:6px; }
  .pg button{ width:26px; height:26px; border:1px solid var(--border-light); border-radius:6px; background:#fff; color:var(--text-2); cursor:pointer; }
  .pg .cur{ padding:0 4px; }
  .pg-num{ margin-left:14px; width:26px; height:26px; border-radius:6px; background:#F2F3F5; display:inline-flex; align-items:center; justify-content:center; }
  .pg-size{ margin-left:auto; display:flex; gap:4px; }
  .pg-size span{ padding:4px 10px; border-radius:6px; cursor:pointer; color:var(--text-2); }
  .pg-size span.on{ background:#F2F3F5; color:var(--text-1); font-weight:500; }
.agent-logs-root{ min-height:100vh; }
</style>

<template>
  <div id="page-root" class="page-root agent-monitor-root">
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
          <div class="ad-mitem" data-action="navKeep('/agent-logs')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg></span>日志</div>
          <div class="ad-mitem active"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 19V10M10 19V5M16 19v-8"/><path d="M2 19h20"/></svg></span>监控</div>
        </nav>
    
        <div class="ad-user">
          <span class="u-ava">于</span>
          <span class="u-nm">于太印</span>
          <button class="u-help" data-action="openHelpCenter()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.2a2.6 2.6 0 1 1 3.6 2.4c-.8.3-1.1.9-1.1 1.7"/><circle cx="12" cy="16.8" r=".6" fill="currentColor"/></svg></button>
        </div>
      </aside>
    
      <!-- 主区：监控 -->
      <main class="ad-main">
        <div class="ad-title">监控</div>
        <div class="ad-sub">跟踪可复用 Agent 在工作流中的活跃度、成本和交互质量。</div>
    
        <div class="mn-filter">
          <span class="mf-chip" data-action="openTimeQuick()"><span id="timeQuickLabel">今天</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
          <span class="mf-chip" data-action="openCustomTime()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg><span id="customTimeLabel">7月 30 – 7月 30</span></span>
          <span class="mf-chip wide" data-action="openMonitorSource()">来源&nbsp;&nbsp;<span id="sourceLabel">全部</span><span class="x" data-action="event.stopPropagation();clearMonitorSource()">✕</span></span>
        </div>
    
        <div class="mn-grid" id="mnGrid"></div>
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
  
  /* 生成一张 0 值空折线图：Y 轴 5 段网格 + X 轴 Jul + 底部数据点 */
  function emptyChart(maxLabel, accent){
    var ticks = 5, W = 560, H = 210, padL = 44, padB = 26, padT = 8;
    var innerH = H - padB - padT, innerW = W - padL - 10;
    var y = function(i){ return padT + innerH * i / ticks; };
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '">';
    for (var i = 0; i <= ticks; i++){
      var v = Math.round(maxLabel * (ticks - i) / ticks);
      var label = maxLabel >= 1000 && v === 1000 ? '1,000' : String(v);
      s += '<line x1="' + padL + '" y1="' + y(i) + '" x2="' + (W - 10) + '" y2="' + y(i) + '" stroke="#F0F1F4" stroke-width="1"/>';
      s += '<text x="' + (padL - 8) + '" y="' + (y(i) + 4) + '" text-anchor="end" font-size="11" fill="#9AA0A6">' + label + '</text>';
    }
    var cx = padL + innerW / 2;
    s += '<line x1="' + cx + '" y1="' + padT + '" x2="' + cx + '" y2="' + (H - padB) + '" stroke="#F0F1F4" stroke-width="1"/>';
    s += '<circle cx="' + cx + '" cy="' + (H - padB) + '" r="3.5" fill="#fff" stroke="' + accent + '" stroke-width="2"/>';
    s += '<text x="' + cx + '" y="' + (H - 8) + '" text-anchor="middle" font-size="11" fill="#9AA0A6">Jul</text>';
    s += '</svg>';
    return s;
  }
  
  var INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" onclick="showMetricInfo()"><circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><circle cx="12" cy="8" r=".6" fill="currentColor"/></svg>';
  function showMetricInfo(){
    openModal('指标说明',
      '<div class="help-content">' +
        '<p><b>全部消息数</b>：统计时间范围内的总消息数</p>' +
        '<p><b>活跃用户</b>：独立用户数量</p>' +
        '<p><b>平均会话互动数</b>：每轮会话的平均消息轮次</p>' +
        '<p><b>Token 输出速度</b>：每秒生成的 Token 数</p>' +
        '<p><b>用户满意度</b>：正面反馈占比</p>' +
        '<p><b>Token 用量</b>：总 Token 消耗及估算费用</p>' +
      '</div>'
    );
  }
  window.showMetricInfo = showMetricInfo;
  
  var cards = [
    { t:'全部消息数',     v:'0',                    max:500,  c:'#2E63F0' },
    { t:'活跃用户',       v:'0',                    max:500,  c:'#E8730C' },
    { t:'平均会话互动数', v:'0',                    max:500,  c:'#2E63F0' },
    { t:'Token 输出速度', v:'0<span class="unit">Token/秒</span>', max:100, c:'#2E63F0' },
    { t:'用户满意度',     v:'0%',                   max:1000, c:'#2E63F0' },
    { t:'Token 用量',     v:'0<span class="unit">耗费 Tokens <span class="orange">(~$0.0000)</span></span>', max:100, c:'#E8730C' }
  ];
  
  document.getElementById('mnGrid').innerHTML = cards.map(function(k){
    return '<div class="mn-card"><h4>' + k.t + INFO + '</h4>' +
           '<div class="mn-val">' + k.v + '</div>' +
           '<div class="mn-chart">' + emptyChart(k.max, k.c) + '</div></div>';
  }).join('');

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
        '<button class="mm-btn" onclick="exportReport()"><span class="mm-ico">📊</span>导出报表</button>' +
        '<button class="mm-btn" onclick="refreshMetrics()"><span class="mm-ico">🔄</span>刷新数据</button>' +
      '</div>'
    );
  }
  function exportReport(){ closeModal(); toast('报表已导出'); }
  function refreshMetrics(){ toast('数据已刷新'); }
  window.openMoreMenu = openMoreMenu;

  /* 帮助中心 */
  function openHelpCenter(){
    openModal('帮助中心',
      '<div class="help-list">' +
        '<div class="help-item"><b>📊 监控指标说明</b><p>了解各监控指标的含义和计算方式</p></div>' +
        '<div class="help-item"><b>⏱ 时间范围选择</b><p>按不同时间粒度查看数据</p></div>' +
        '<div class="help-item"><b>📈 数据导出</b><p>导出监控报表</p></div>' +
      '</div>'
    );
  }
  window.openHelpCenter = openHelpCenter;

  /* 时间快捷选择 */
  function openTimeQuick(){
    openModal('时间范围',
      '<div class="time-range">' +
        '<button class="tr-btn" data-action="setTimeQuick(\'今天\')">今天</button>' +
        '<button class="tr-btn" data-action="setTimeQuick(\'昨天\')">昨天</button>' +
        '<button class="tr-btn" data-action="setTimeQuick(\'最近 7 天\')">最近 7 天</button>' +
        '<button class="tr-btn" data-action="setTimeQuick(\'最近 30 天\')">最近 30 天</button>' +
      '</div>'
    );
  }
  function setTimeQuick(range){
    document.getElementById('timeQuickLabel').textContent = range;
    closeModal();
    toast('时间范围：' + range);
  }
  window.openTimeQuick = openTimeQuick;

  /* 自定义时间 */
  function openCustomTime(){
    openModal('自定义时间',
      '<div class="custom-time">' +
        '<div class="ct-row"><label>开始日期</label><input type="date" id="ctStart" value="2024-07-30"></div>' +
        '<div class="ct-row"><label>结束日期</label><input type="date" id="ctEnd" value="2024-07-30"></div>' +
        '<button class="btn btn-primary" data-action="applyCustomTime()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applyCustomTime(){
    var s = document.getElementById('ctStart').value;
    var e = document.getElementById('ctEnd').value;
    document.getElementById('customTimeLabel').textContent = s + ' – ' + e;
    closeModal();
    toast('时间范围已更新');
  }
  window.openCustomTime = openCustomTime;

  /* 来源筛选 */
  function openMonitorSource(){
    openModal('来源筛选',
      '<div class="source-filter">' +
        '<label class="sf-item"><input type="checkbox" checked> Web app</label>' +
        '<label class="sf-item"><input type="checkbox" checked> API</label>' +
        '<label class="sf-item"><input type="checkbox" checked> 嵌入</label>' +
        '<label class="sf-item"><input type="checkbox" checked> 调试</label>' +
        '<button class="btn btn-primary" data-action="applyMonitorSource()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applyMonitorSource(){
    document.getElementById('sourceLabel').textContent = '已筛选';
    closeModal();
    toast('来源筛选已应用');
  }
  function clearMonitorSource(){
    document.getElementById('sourceLabel').textContent = '全部';
    toast('已清除来源筛选');
  }
  window.openMonitorSource = openMonitorSource;

})
</script>
<style>
.agent-monitor-root{ background:#fff; }
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
  .ad-main{ flex:1; overflow-y:auto; padding:26px 30px 40px; background:#fff; }
  .ad-title{ font-size:18px; font-weight:600; }
  .ad-sub{ color:var(--text-3); font-size:13px; margin-top:6px; }

  .mn-filter{ display:flex; align-items:center; gap:10px; margin-top:20px; }
  .mf-chip{ display:inline-flex; align-items:center; gap:8px; background:#F7F8FA; border:1px solid var(--border-light); border-radius:8px; padding:7px 12px; font-size:13px; color:var(--text-1); cursor:pointer; }
  .mf-chip svg{ width:14px; height:14px; color:var(--text-2); }
  .mf-chip .x{ width:14px; height:14px; border-radius:50%; background:#E4E6EA; color:var(--text-3); display:inline-flex; align-items:center; justify-content:center; font-size:10px; }
  .mf-chip.wide{ min-width:280px; justify-content:space-between; }

  .mn-grid{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:18px; }
  .mn-card{ background:#fff; border:1px solid var(--border-light); border-radius:12px; padding:18px 20px 14px; }
  .mn-card h4{ font-size:14px; font-weight:600; display:flex; align-items:center; gap:5px; }
  .mn-card h4 svg{ width:13px; height:13px; color:var(--text-3); cursor:pointer; }
  .mn-val{ font-size:26px; font-weight:600; color:var(--text-1); margin-top:6px; }
  .mn-val .unit{ font-size:13px; color:var(--text-3); font-weight:400; margin-left:4px; }
  .mn-val .orange{ color:#E8730C; }
  .mn-chart{ margin-top:6px; }
  .mn-chart svg{ width:100%; height:auto; display:block; }
.agent-monitor-root{ min-height:100vh; }
</style>

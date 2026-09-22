<template>
  <AppShell id="page-root" active-key="tools">
    <div class="page-pad">

   
        <div class="page-title">工具插件</div>
        <div class="page-sub">工作区中所有可用的工具 —— 包括内置工具和从 Marketplace 安装的工具。</div>
      

      <div class="tools-bar">
        <button class="btn" id="toolTagBtn" data-action="openTagModal()">标签</button>
        <span class="search-input" style="min-width:260px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="toolSearch" placeholder="搜索"></span>
        <button class="btn" style="margin-left:auto;" id="autoUpdateBtn" data-action="openAutoModal()">🌀 <span id="autoModeText">自动更新 · 仅修复</span></button>
      </div>

      <!-- Tab 切换 -->
      <div class="tools-tabs">
        <button class="tools-tab active" data-tab="tools" onclick="switchToolsTab('tools')">工具列表</button>
        <button class="tools-tab" data-tab="logs" onclick="switchToolsTab('logs')">调用日志</button>
      </div>

      <!-- 工具日志面板 -->
      <div class="tools-logs-panel" id="toolsLogsPanel" style="display:none;">
        <div class="logs-bar">
          <span class="logs-total" id="logsTotal">共 0 条记录</span>
          <select id="logsStatusFilter" onchange="loadToolLogs()" class="logs-select">
            <option value="">全部状态</option>
            <option value="success">成功</option>
            <option value="error">失败</option>
          </select>
          <button class="btn btn-sm" onclick="loadToolLogs()">刷新</button>
          <button class="btn btn-sm btn-danger" onclick="clearToolLogs()">清空</button>
        </div>
        <div class="logs-list" id="toolLogsList">
          <div class="logs-empty">暂无调用记录</div>
        </div>
      </div>

      <!-- 内置工具网格（数据来自 /api/tools/builtin） -->
      <div class="tools-grid" id="builtinGrid"></div>

      <div class="collapse-line">⌃</div>

      <div class="mk-title">来自 Marketplace 的更多精彩内容</div>
      <div class="mk-sub">探索 <a class="link" href="#/marketplace">模型</a>, <a class="link" href="#/marketplace">工具</a>, <a class="link" href="#/marketplace">数据源</a>, <a class="link" href="#/marketplace">触发器</a>, <a class="link" href="#/marketplace">Agent 策略</a>, <a class="link" href="#/marketplace">扩展</a> 和 <a class="link" href="#/marketplace">集成包</a> 在 <a class="link" href="#/marketplace">应用市场 ↗</a></div>

      <!-- 精选（动态渲染：来自 /api/tools/builtin 已安装工具） -->
      <div class="sec-head"><span class="t">已安装工具</span><button class="more" data-action="showMoreTools(this)">查看更多 ›</button></div>
      <div class="mk-scroll" id="marketFeatured">
        <!-- 动态渲染：loadMarketTools() 会从 /api/tools/builtin 加载真实数据 -->
      </div>

      <!-- 最新（动态渲染：来自 tool_installs 最近安装记录） -->
      <div class="sec-head"><span class="t">最近安装</span><button class="more" data-action="showMoreTools(this)">查看更多 ›</button></div>
      <div class="mk-scroll" id="marketLatest">
        <!-- 动态渲染 -->
      </div>

    </div>

    <!-- 标签筛选弹窗（搜索 + 标签多选） -->
    <div class="modal-mask" id="tagModal">
      <div class="modal" style="width:560px;">
        <div class="modal-head"><div class="modal-title">标签</div>
          <button class="modal-close" data-action="closeModal(&#x27;tagModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="search-input" style="width:100%;background:#fff;border:1px solid var(--border);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="tagSearch" placeholder="搜索标签"></div>
          <div class="tag-grid" id="tagList"></div>
        </div>
        <div class="modal-foot">
          <button class="btn" data-action="closeModal(&#x27;tagModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="tagOkBtn">确定</button>
        </div>
      </div>
    </div>

    <!-- 自动更新设置弹窗（模式/时间/范围） -->
    <div class="modal-mask" id="autoModal">
      <div class="modal" style="width:520px;">
        <div class="modal-head"><div class="modal-title">自动更新设置</div>
          <button class="modal-close" data-action="closeModal(&#x27;autoModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="au-label">自动更新</div>
          <div class="au-opts">
            <label class="au-opt"><input type="radio" name="auMode" value="disabled"><span class="au-t">禁用</span></label>
            <label class="au-opt"><input type="radio" name="auMode" value="patch"><span class="au-t">仅修复<span class="au-hint">仅自动更新补丁版本 1.0.1→1.0.2</span></span></label>
            <label class="au-opt"><input type="radio" name="auMode" value="latest"><span class="au-t">最新</span></label>
          </div>
          <div class="au-label">更新时间</div>
          <input type="time" id="auTime" value="19:45" style="border:1px solid var(--border);border-radius:8px;padding:8px 12px;font-size:14px;">
          <div class="au-label">范围</div>
          <div class="au-opts">
            <label class="au-opt"><input type="radio" name="auScope" value="all"><span class="au-t">全部</span></label>
            <label class="au-opt"><input type="radio" name="auScope" value="exclude"><span class="au-t">排除选定</span></label>
            <label class="au-opt"><input type="radio" name="auScope" value="only"><span class="au-t">仅选定</span></label>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" data-action="closeModal(&#x27;autoModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="autoSaveBtn">保存</button>
        </div>
      </div>
    </div>

    <!-- 工具详情抽屉（点击卡片右侧滑出，展示 ACTIONS 列表） -->
    <div class="tool-drawer" id="toolDrawer">
      <div class="td-head">
        <span class="td-ico" id="tdIcon">🎙️</span>
        <span>
          <div class="td-name" id="tdName">Audio</div>
          <div class="td-sub" id="tdSub">hjlarry / audio</div>
        </span>
        <button class="td-close" data-action="closeToolDrawer()">✕</button>
      </div>
      <div class="td-desc" id="tdDesc">一个用于文本转语音和语音转文本的工具。</div>
      <div class="td-body">
        <div class="td-act-t" id="tdActTitle">包含 2 个 ACTIONS</div>
        <div id="tdActs"></div>
      </div>
      <div class="td-foot">
        <button class="btn" id="tdUninstallBtn" data-action="uninstallTool()">卸载</button>
        <button class="btn btn-primary" id="tdInstallBtn" data-action="installTool()">安装</button>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onUnmounted } from 'vue'
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

  var tools = [];            // 内置工具（来自 /api/tools/builtin）
  var loaded = false;        // 是否已加载完成
  var curQ = '';             // 搜索词
  var selTags = [];          // 选中的标签（空 = 全部）
  var acts = [];             // 当前抽屉展示的 actions
  var actOpen = {};          // action 参数展开状态
  var curTool = null;        // 当前抽屉的工具对象

  /* 标签体系：18 个标签 */
  var TAG_LIST = ['Agent', 'RAG', '搜索', '图片', '视频', '天气', '金融', '设计', '旅行',
                  '社交', '新闻', '医疗', '生产力', '教育', '商业', '娱乐', '工具', '其他'];
  var AUTO_MODE_TEXT = { disabled: '自动更新', patch: '自动更新 · 仅修复', latest: '自动更新 · 最新' };

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* ========== 加载内置工具列表 ========== */
  function loadTools(){
    apiGet('/api/tools/builtin').then(function(data){
      loaded = true;
      if (data.code === 200){
        tools = data.data || [];
        render();
      } else {
        document.getElementById('builtinGrid').innerHTML = '<div class="tools-none">加载失败：' + esc(data.msg || '未知错误') + '</div>';
      }
    }).catch(function(){ loaded = true; render(); });
  }

  /* ========== 渲染卡片网格（搜索 + 标签过滤，纯前端过滤） ========== */
  function render(){
    var q = curQ.trim().toLowerCase();
    var list = tools.filter(function(t){
      var okQ = !q ||
        t.name.toLowerCase().indexOf(q) > -1 ||
        t.description.toLowerCase().indexOf(q) > -1 ||
        t.author.toLowerCase().indexOf(q) > -1 ||
        t.package.toLowerCase().indexOf(q) > -1;
      var okT = !selTags.length || (t.labels || []).some(function(l){ return selTags.indexOf(l) > -1; });
      return okQ && okT;
    });
    var grid = document.getElementById('builtinGrid');
    if (!list.length){
      grid.innerHTML = loaded
        ? '<div class="tools-none">未找到集成</div>'
        : '<div class="tools-none">加载中…</div>';
      return;
    }
    grid.innerHTML = list.map(function(t, i){
      var realIdx = tools.indexOf(t);
      var ic = t.icon || '🔧';
      return '<div class="tcard tool-card" data-idx="' + realIdx + '" onclick="openToolDrawer(' + realIdx + ')">' +
        (t.installed ? '<span class="corner-gray inst">已安装</span>' : '<span class="corner-gray">内置</span>') +
        '<div class="t-main">' +
          '<div class="t-ico" style="background:' + esc(t.icon_bg || '#F2F3F5') + ';' + (t.icon_fg ? 'color:' + esc(t.icon_fg) + ';' : '') + '">' + ic + '</div>' +
          '<div><div class="t-name">' + esc(t.name) + '</div><div class="t-desc">' + esc(t.description) + '</div></div>' +
        '</div>' +
        '<div class="t-foot"><span class="tf-author">' + esc(t.author) + '</span><span class="tf-slash">/</span><span class="tf-pkg">' + esc(t.package) + '</span></div>' +
      '</div>';
    }).join('');
  }

  /* ========== Marketplace 动态渲染（接真实 API 数据） ========== */
  function loadMarketTools(){
    // 从已安装的内置工具中选取展示在 Marketplace 区域
    var featured = document.getElementById('marketFeatured');
    var latest = document.getElementById('marketLatest');
    if (!featured || !latest) return;
    featured.innerHTML = '<div style="padding:20px;color:#999;font-size:13px;">加载中…</div>';
    latest.innerHTML = '<div style="padding:20px;color:#999;font-size:13px;">加载中…</div>';
    apiGet('/api/tools/builtin').then(function(res){
      var allTools = (res.data || []).filter(function(t){ return t.installed; });
      if (!allTools.length) {
        var emptyMsg = '<div style="padding:20px;color:#999;font-size:13px;">暂无已安装工具，请先在左侧安装</div>';
        featured.innerHTML = emptyMsg;
        latest.innerHTML = emptyMsg;
        return;
      }
      // 精选：展示前 4 个已安装工具
      var featuredTools = allTools.slice(0, 4);
      // 最新：展示最近安装的 3 个（按安装时间倒序，若无时间则取后 3 个）
      var latestTools = allTools.slice().reverse().slice(0, 3);
      featured.innerHTML = featuredTools.map(function(t){
        return renderMarketCard(t);
      }).join('');
      latest.innerHTML = latestTools.map(function(t){
        return renderMarketCard(t);
      }).join('');
    }).catch(function(){
      var errMsg = '<div style="padding:20px;color:#999;font-size:13px;">加载失败</div>';
      featured.innerHTML = errMsg;
      latest.innerHTML = errMsg;
    });
  }

  function renderMarketCard(t){
    var ic = t.icon || '🔧';
    var iconBg = t.icon_bg || '#F2F3F5';
    var iconFg = t.icon_fg ? 'color:' + esc(t.icon_fg) : '';
    return '<div class="mcard tool-card" data-name="' + esc(t.name) + '">' +
      '<span class="corner">工具</span>' +
      '<div class="m-head"><div class="m-icon" style="background:' + esc(iconBg) + ';' + iconFg + ';">' + esc(String(ic).substring(0, 4)) + '</div>' +
        '<div><div class="m-name">' + esc(t.name) + '</div><div class="m-meta">' + esc(t.author || '内置') + ' · ' + esc(t.package || '') + '</div></div></div>' +
      '<div class="m-desc">' + esc((t.description || '').substring(0, 80)) + (t.description && t.description.length > 80 ? '…' : '') + '</div>' +
      '<div class="m-tags">' + (t.labels && t.labels.length ? '<span class="tag tag-blue">' + esc(t.labels[0]) + '</span>' : '<span class="tag">🔧 工具</span>') + '</div>' +
      '<div class="m-acts"><button class="btn btn-sm" disabled>已安装</button><button class="btn btn-sm" data-action="showMarketToolDetail(this)">详情</button></div>' +
    '</div>';
  }

  /* ========== 详情抽屉（点击卡片 → GET /api/tools/builtin/<id>/tools） ========== */
  function openToolDrawer(idx){
    var t = tools[idx];
    if (!t) return;
    curTool = t;
    updateInstallBtns();
    document.querySelectorAll('.tool-card').forEach(function(c){ c.classList.remove('sel'); });
    var card = document.querySelector('.tool-card[data-idx="' + idx + '"]');
    if (card) card.classList.add('sel');
    var tdIcon = document.getElementById('tdIcon');
    tdIcon.innerHTML = t.icon || '🔧';
    tdIcon.style.background = t.icon_bg || '#F2F3F5';
    tdIcon.style.color = t.icon_fg || '';
    document.getElementById('tdName').textContent = t.name;
    document.getElementById('tdSub').textContent = t.author + ' / ' + t.package;
    document.getElementById('tdDesc').textContent = t.description;
    document.getElementById('tdActTitle').textContent = '包含 ' + (t.tools || []).length + ' 个 ACTIONS';
    document.getElementById('tdActs').innerHTML = '<div class="td-loading">加载中…</div>';
    actOpen = {};
    openModal('toolDrawer');
    apiGet('/api/tools/builtin/' + encodeURIComponent(t.id) + '/tools').then(function(data){
      if (data.code === 200){
        acts = data.data || [];
        renderActs();
      } else {
        document.getElementById('tdActs').innerHTML = '<div class="td-loading">' + esc(data.msg || '加载失败') + '</div>';
      }
    }).catch(function(){
      document.getElementById('tdActs').innerHTML = '<div class="td-loading">网络异常，请稍后重试</div>';
    });
  }
  function renderActs(){
    document.getElementById('tdActTitle').textContent = '包含 ' + acts.length + ' 个 ACTIONS';
    document.getElementById('tdActs').innerHTML = acts.map(function(a, i){
      var params = a.parameters || [];
      var open = actOpen[i];
      return '<div class="td-act" onclick="toggleAct(' + i + ')">' +
        '<div class="a-n">' + esc(a.label || a.name) + '</div>' +
        '<div class="a-d">' + esc(a.description) + '</div>' +
        (params.length ? '<div class="a-params"' + (open ? '' : ' style="display:none"') + '>' +
          params.map(function(p){
            return '<div class="tp-row">' +
              '<span class="tp-name">' + esc(p.name) + (p.required ? ' <em class="tp-req">必填</em>' : '') + '</span>' +
              '<span class="tp-type">' + esc(p.type) + '</span>' +
              '<span class="tp-desc">' + esc(p.description) + '</span>' +
            '</div>';
          }).join('') + '</div>' : '') +
      '</div>';
    }).join('');
  }
  function toggleAct(i){
    actOpen[i] = !actOpen[i];
    renderActs();
  }

  /* ========== 安装 / 卸载（安装后可在智能体编排「添加工具」中选择使用） ========== */
  function updateInstallBtns(){
    var on = !!(curTool && curTool.installed);
    document.getElementById('tdInstallBtn').style.display = on ? 'none' : '';
    document.getElementById('tdUninstallBtn').style.display = on ? '' : 'none';
  }
  function installTool(){
    if (!curTool) return;
    apiPost('/api/tools/builtin/' + encodeURIComponent(curTool.id) + '/install')
      .then(function(data){
        if (data.code === 200){
          curTool.installed = true;
          var idx = tools.indexOf(curTool);
          if (idx > -1) tools[idx].installed = true;
          updateInstallBtns();
          render();
          toast('已安装，可在智能体编排中使用');
        } else {
          toast(data.msg || '安装失败');
        }
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function uninstallTool(){
    if (!curTool) return;
    apiDelete('/api/tools/builtin/' + encodeURIComponent(curTool.id) + '/install')
      .then(function(data){
        if (data.code === 200){
          curTool.installed = false;
          var idx = tools.indexOf(curTool);
          if (idx > -1) tools[idx].installed = false;
          updateInstallBtns();
          render();
          toast('已卸载');
        } else {
          toast(data.msg || '卸载失败');
        }
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function closeToolDrawer(){
    document.getElementById('toolDrawer').classList.remove('show');
    document.querySelectorAll('.tool-card').forEach(function(c){ c.classList.remove('sel'); });
  }

  /* ========== 标签筛选弹窗（搜索 + 18 标签多选） ========== */
  function openTagModal(){
    renderTagList();
    openModal('tagModal');
  }
  function renderTagList(){
    var kw = document.getElementById('tagSearch').value.trim().toLowerCase();
    document.getElementById('tagList').innerHTML = TAG_LIST.map(function(t){
      if (kw && t.toLowerCase().indexOf(kw) === -1) return '';
      var on = selTags.indexOf(t) > -1;
      return '<label class="tag-item' + (on ? ' on' : '') + '"><input type="checkbox" value="' + esc(t) + '"' + (on ? ' checked' : '') + '><span>' + esc(t) + '</span></label>';
    }).join('');
  }
  document.getElementById('tagSearch').addEventListener('input', renderTagList);
  document.getElementById('tagOkBtn').addEventListener('click', function(){
    selTags = Array.prototype.map.call(document.querySelectorAll('#tagList input:checked'), function(cb){ return cb.value; });
    document.getElementById('toolTagBtn').textContent = selTags.length ? '标签(' + selTags.length + ')' : '标签';
    closeModal('tagModal');
    render();
  });

  /* ========== 自动更新设置弹窗（模式/更新时间/范围） ========== */
  function loadAutoMode(){
    apiGet('/api/tools/auto-update').then(function(data){
      if (data.code === 200){
        document.getElementById('autoModeText').textContent = AUTO_MODE_TEXT[data.data.mode] || '自动更新';
      }
    }).catch(function(){});
  }
  function openAutoModal(){
    apiGet('/api/tools/auto-update').then(function(data){
      if (data.code === 200){
        var s = data.data || {};
        document.querySelectorAll('input[name="auMode"]').forEach(function(rb){ rb.checked = rb.value === (s.mode || 'patch'); });
        document.getElementById('auTime').value = s.update_time || '19:45';
        document.querySelectorAll('input[name="auScope"]').forEach(function(rb){ rb.checked = rb.value === (s.scope || 'all'); });
      }
      openModal('autoModal');
    }).catch(function(){ openModal('autoModal'); });
  }
  document.getElementById('autoSaveBtn').addEventListener('click', function(){
    var mode = document.querySelector('input[name="auMode"]:checked');
    var scope = document.querySelector('input[name="auScope"]:checked');
    apiPut('/api/tools/auto-update', {
      mode: mode ? mode.value : 'patch',
      update_time: document.getElementById('auTime').value || '19:45',
      scope: scope ? scope.value : 'all'
    }).then(function(data){
      if (data.code === 200){
        document.getElementById('autoModeText').textContent = AUTO_MODE_TEXT[data.data.mode] || '自动更新';
        closeModal('autoModal');
        toast('自动更新设置已保存');
      } else {
        toast(data.msg || '保存失败');
      }
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  });

  /* ========== 搜索过滤（纯前端） ========== */
  document.getElementById('toolSearch').addEventListener('input', function(){
    curQ = this.value;
    render();
  });

  /* ========== Tab 切换 ========== */
  window.switchToolsTab = function(tab) {
    document.querySelectorAll('.tools-tab').forEach(function(t) {
      t.classList.toggle('active', t.getAttribute('data-tab') === tab);
    });
    var toolsGrid = document.getElementById('builtinGrid');
    var collapseLine = document.querySelector('.collapse-line');
    var mkTitle = document.querySelector('.mk-title');
    var mkSub = document.querySelector('.mk-sub');
    var secHeads = document.querySelectorAll('.sec-head');
    var mkScrolls = document.querySelectorAll('.mk-scroll');
    var logsPanel = document.getElementById('toolsLogsPanel');

    if (tab === 'logs') {
      if (toolsGrid) toolsGrid.style.display = 'none';
      if (collapseLine) collapseLine.style.display = 'none';
      if (mkTitle) mkTitle.style.display = 'none';
      if (mkSub) mkSub.style.display = 'none';
      secHeads.forEach(function(h) { h.style.display = 'none'; });
      mkScrolls.forEach(function(s) { s.style.display = 'none'; });
      if (logsPanel) logsPanel.style.display = 'block';
      loadToolLogs();
    } else {
      if (toolsGrid) toolsGrid.style.display = '';
      if (collapseLine) collapseLine.style.display = '';
      if (mkTitle) mkTitle.style.display = '';
      if (mkSub) mkSub.style.display = '';
      secHeads.forEach(function(h) { h.style.display = ''; });
      mkScrolls.forEach(function(s) { s.style.display = ''; });
      if (logsPanel) logsPanel.style.display = 'none';
    }
  };

  /* ========== 工具调用日志 ========== */
  window.loadToolLogs = function() {
    var status = document.getElementById('logsStatusFilter') ? document.getElementById('logsStatusFilter').value : '';
    apiGet('/api/tools/logs', { params: { page_size: 50, status: status || undefined } }).then(function(data){
      if (data.code === 200){
        renderToolLogs(data.data.items);
        var totalEl = document.getElementById('logsTotal');
        if (totalEl) totalEl.textContent = '共 ' + (data.data.total || 0) + ' 条记录';
      } else {
        document.getElementById('toolLogsList').innerHTML = '<div class="logs-empty">加载失败</div>';
      }
    }).catch(function(){
      document.getElementById('toolLogsList').innerHTML = '<div class="logs-empty">网络异常</div>';
    });
  };

  window.renderToolLogs = function(items) {
    var container = document.getElementById('toolLogsList');
    if (!items || !items.length){
      container.innerHTML = '<div class="logs-empty">暂无调用记录</div>';
      return;
    }
    container.innerHTML = items.map(function(log){
      var statusIcon = log.status === 'success' ? '✓' : '✗';
      var statusClass = log.status === 'success' ? 'ok' : 'err';
      return '<div class="log-item">' +
        '<span class="log-status ' + statusClass + '">' + statusIcon + '</span>' +
        '<span class="log-type">' + esc(log.node_type) + '</span>' +
        '<span class="log-name">' + esc(log.provider_id) + '.' + esc(log.tool_name) + '</span>' +
        '<span class="log-node">' + esc(log.node_id) + '</span>' +
        '<span class="log-time">' + esc(log.created_at) + '</span>' +
        '<span class="log-ms">' + (log.elapsed_ms || 0) + 'ms</span>' +
        '<button class="log-detail-btn" onclick="showLogDetail(\'' + log.id + '\')">详情</button>' +
      '</div>';
    }).join('');
  };

  window.showLogDetail = function(logId) {
    apiGet('/api/tools/logs/' + encodeURIComponent(logId)).then(function(data){
      if (data.code === 200) {
        var d = data.data;
        var params = JSON.stringify(d.parameters || {}, null, 2);
        var result = d.result || '(无)';
        alert('参数:\n' + params + '\n\n结果:\n' + result.substring(0, 500));
      }
    });
  };

  window.clearToolLogs = function() {
    if (!confirm('确定要清空所有调用日志吗？')) return;
    apiDelete('/api/tools/logs').then(function(data){
      if (data.code === 200){
        loadToolLogs();
        toast('日志已清空');
      } else {
        toast(data.msg || '操作失败');
      }
    }).catch(function(){ toast('网络异常'); });
  };

  /* 内联 onclick 全局可调用：挂载到 window */
  window.openToolDrawer = openToolDrawer;
  window.toggleAct = toggleAct;
  window.installTool = installTool;
  window.uninstallTool = uninstallTool;
  window.closeToolDrawer = closeToolDrawer;
  window.openTagModal = openTagModal;
  window.openAutoModal = openAutoModal;

  render();
  loadTools();
  loadMarketTools();
  loadAutoMode();

  /* ================= P3 占位功能实现 ================= */

  /* 查看更多工具 */
  window.showMoreTools = function(btn){
    var section = btn.closest('.sec-head').nextElementSibling;
    if (section){
      section.style.overflowX = 'visible';
      section.style.flexWrap = 'wrap';
      toast('已展示全部工具');
    }
  };

  /* 安装 Marketplace 工具（接真实 API） */
  window.installMarketTool = function(btn){
    var card = btn.closest('.mcard');
    var name = card ? card.getAttribute('data-name') : '工具';
    // 查找对应的工具 ID（通过 tools 数组匹配名称）
    var toolId = null;
    for (var i = 0; i < tools.length; i++){
      if (tools[i].name === name){ toolId = tools[i].id; break; }
    }
    if (!toolId){
      toast('未找到工具：' + name);
      return;
    }
    toast('正在安装：' + name);
    btn.textContent = '安装中…';
    btn.disabled = true;
    apiPost('/api/tools/builtin/' + encodeURIComponent(toolId) + '/install')
      .then(function(){
        btn.textContent = '已安装';
        btn.classList.add('btn-primary');
        toast(name + ' 安装成功');
        loadMarketTools();  // 刷新 Marketplace 区域
      })
      .catch(function(){
        btn.textContent = '安装';
        btn.disabled = false;
        toast(name + ' 安装失败');
      });
  };

  /* 查看 Marketplace 工具详情 */
  window.showMarketToolDetail = function(btn){
    var card = btn.closest('.mcard');
    if (!card) return;
    var name = card.getAttribute('data-name') || '工具';
    var desc = card.querySelector('.m-desc');
    var meta = card.querySelector('.m-meta');
    openModal('工具详情 - ' + name,
      '<div class="tool-detail">' +
        '<p>' + (desc ? desc.textContent : '') + '</p>' +
        '<p style="color:var(--text-3);font-size:12px;margin-top:8px;">' + (meta ? meta.textContent : '') + '</p>' +
      '</div>'
    );
  };

})
</script>
<style>
.tools-bar{display:flex;align-items:center;gap:14px;margin:16px 0 4px;}
  .tools-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:16px;}
  @media (max-width:1200px){ .tools-grid{grid-template-columns:repeat(1,1fr);} }
  .tools-none{grid-column:1/-1;text-align:center;padding:60px 0;color:var(--text-3);font-size:14px;background:#fff;border:1px solid var(--border-light);border-radius:10px;}
  /* 内置工具卡片（整卡可点，图标+名称+描述+作者/包名+右上角"内置"标记） */
  .tcard{background:#fff;border:1px solid var(--border-light);border-radius:10px;cursor:pointer;transition:box-shadow .15s;position:relative;display:flex;flex-direction:column;overflow:hidden;}
  .tcard:hover{box-shadow:0 4px 16px rgba(29,33,41,.08);}
  .tcard.sel{border-color:var(--primary);box-shadow:0 0 0 2px rgba(46,99,240,.14);}
  .tcard .t-main{display:flex;gap:12px;padding:18px 18px 14px;align-items:flex-start;flex:1;}
  .tcard .t-ico{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;}
  .tcard .t-name{font-size:15px;font-weight:600;}
  .tcard .t-desc{font-size:13px;color:var(--text-2);margin-top:4px;line-height:1.6;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .tcard .t-foot{background:#F7F8FA;padding:9px 18px;font-size:12px;display:flex;gap:6px;}
  .tcard .tf-author,.tcard .tf-pkg{color:var(--text-3);}
  .tcard .tf-slash{color:var(--text-4);}
  .corner-gray{position:absolute;top:0;right:0;background:#F2F3F5;color:var(--text-3);font-size:11px;padding:3px 10px;border-radius:0 10px 0 8px;z-index:2;}
  .corner-gray.inst{background:#E8F7EE;color:#12A150;}
  .collapse-line{display:flex;justify-content:center;margin:28px 0 8px;color:var(--text-4);font-size:14px;}
  .mk-title{font-size:17px;font-weight:700;color:#1C64F2;}
  .mk-sub{font-size:13px;color:var(--text-2);margin-top:8px;}
  .sec-head{display:flex;align-items:center;margin:26px 0 2px;}
  .sec-head .t{font-size:15px;font-weight:600;}
  .sec-head .more{margin-left:auto;font-size:13px;color:var(--text-3);cursor:pointer;background:none;border:none;}
  .sec-head .more:hover{color:var(--primary);}
  /* Marketplace 横向轮播 */
  .mk-scroll{display:flex;gap:16px;margin-top:14px;overflow-x:auto;padding-bottom:6px;scroll-snap-type:x proximity;}
  .mk-scroll::-webkit-scrollbar{height:6px;}
  .mk-scroll::-webkit-scrollbar-thumb{background:#E2E4E8;border-radius:3px;}
  .mcard{background:#fff;border:1px solid var(--border-light);border-radius:10px;padding:16px;min-width:300px;max-width:340px;flex-shrink:0;position:relative;display:flex;flex-direction:column;gap:10px;}
  .mcard .corner{position:absolute;top:0;right:0;background:var(--primary-light);color:var(--primary);font-size:11px;padding:3px 10px;border-radius:0 10px 0 8px;}
  .m-head{display:flex;align-items:center;gap:12px;}
  .m-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;}
  .m-name{font-size:15px;font-weight:600;}
  .m-meta{font-size:12px;color:var(--text-3);margin-top:3px;}
  .m-desc{font-size:13px;color:var(--text-2);line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
  .m-tags{display:flex;gap:6px;}
  .tag{font-size:11px;padding:2px 8px;border-radius:4px;background:#F2F3F5;color:var(--text-3);}
  .tag-blue{background:#EAF1FE;color:#1C64F2;}
  .m-acts{display:flex;gap:8px;margin-top:2px;}
  .m-acts .btn{padding:5px 14px;font-size:13px;}
  /* 标签弹窗 */
  .tag-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px;max-height:300px;overflow-y:auto;}
  .tag-item{display:flex;align-items:center;gap:8px;border:1px solid var(--border-light);border-radius:8px;padding:9px 12px;cursor:pointer;font-size:13px;transition:all .12s;}
  .tag-item:hover{border-color:var(--primary);}
  .tag-item.on{border-color:var(--primary);background:var(--primary-light);color:var(--primary);font-weight:500;}
  .tag-item input{accent-color:var(--primary);}
  /* 自动更新弹窗 */
  .au-label{font-size:14px;font-weight:600;margin:16px 0 10px;}
  .au-label:first-child{margin-top:0;}
  .au-opts{display:flex;flex-direction:column;gap:10px;}
  .au-opt{display:flex;align-items:flex-start;gap:8px;cursor:pointer;font-size:14px;}
  .au-opt input{accent-color:var(--primary);margin-top:2px;}
  .au-hint{display:block;font-size:12px;color:var(--text-3);margin-top:2px;}
  /* 详情抽屉 */
  .tool-drawer{position:fixed;top:0;right:0;height:100vh;width:520px;max-width:92vw;background:#fff;border-left:1px solid var(--border-light);box-shadow:-8px 0 30px rgba(29,33,41,.10);z-index:80;transform:translateX(100%);transition:transform .25s ease;display:flex;flex-direction:column;}
  .tool-drawer.show{transform:translateX(0);}
  .td-head{display:flex;align-items:flex-start;gap:12px;padding:22px 22px 14px;}
  .td-ico{width:46px;height:46px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}
  .td-name{font-size:17px;font-weight:700;}
  .td-sub{font-size:13px;color:var(--text-3);margin-top:4px;}
  .td-close{margin-left:auto;width:28px;height:28px;border:none;background:none;border-radius:6px;color:var(--text-2);cursor:pointer;font-size:14px;flex-shrink:0;}
  .td-close:hover{background:#F2F3F5;color:var(--text-1);}
  .td-desc{padding:0 22px;font-size:13.5px;color:var(--text-2);line-height:1.7;}
  .td-body{flex:1;overflow-y:auto;margin-top:18px;background:#F7F8FA;border-top:1px solid var(--border-light);padding:18px 22px;}
  .td-act-t{font-size:13px;font-weight:700;letter-spacing:.4px;margin-bottom:12px;}
  .td-foot{display:flex;justify-content:flex-end;gap:10px;padding:14px 22px;border-top:1px solid var(--border-light);background:#fff;flex-shrink:0;}
  .td-loading{color:var(--text-3);font-size:13px;padding:20px 0;text-align:center;}
  .td-act{background:#fff;border:1px solid var(--border-light);border-radius:10px;padding:14px 16px;margin-bottom:10px;cursor:pointer;transition:box-shadow .15s;}
  .td-act:hover{box-shadow:0 2px 8px rgba(29,33,41,.06);}
  .td-act .a-n{font-size:14px;font-weight:600;}
  .td-act .a-d{font-size:12.5px;color:var(--text-3);margin-top:4px;}
  .a-params{margin-top:10px;border-top:1px solid var(--border-light);padding-top:10px;display:flex;flex-direction:column;gap:8px;}
  .tp-row{display:flex;align-items:center;gap:10px;font-size:12.5px;}
  .tp-name{font-weight:600;color:var(--text-1);}
  .tp-req{font-style:normal;color:#E5484D;font-size:11px;border:1px solid #F3C1C3;background:#FEF1F2;border-radius:4px;padding:0 5px;margin-left:4px;}
  .tp-type{color:var(--primary);background:var(--primary-light);border-radius:4px;padding:1px 6px;font-size:11px;}
  .tp-desc{color:var(--text-3);}
  /* Tab 切换 */
  .tools-tabs{display:flex;gap:4px;margin:16px 0 0;border-bottom:1px solid var(--border-light);}
  .tools-tab{padding:10px 20px;font-size:14px;font-weight:500;color:var(--text-2);background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;transition:all .15s;}
  .tools-tab:hover{color:var(--text-1);}
  .tools-tab.active{color:var(--primary);border-bottom-color:var(--primary);}
  /* 工具日志面板 */
  .tools-logs-panel{margin-top:16px;}
  .logs-bar{display:flex;align-items:center;gap:12px;margin-bottom:12px;}
  .logs-total{font-size:13px;color:var(--text-2);flex:1;}
  .logs-select{border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:13px;outline:none;background:#fff;}
  .logs-list{display:flex;flex-direction:column;gap:8px;}
  .logs-empty{text-align:center;padding:40px 0;color:var(--text-3);font-size:14px;background:#fff;border:1px solid var(--border-light);border-radius:10px;}
  .log-item{display:flex;align-items:center;gap:12px;padding:12px 16px;background:#fff;border:1px solid var(--border-light);border-radius:8px;font-size:13px;}
  .log-status{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;}
  .log-status.ok{background:#E8F7EE;color:#12A150;}
  .log-status.err{background:#FEF1F2;color:#E5484D;}
  .log-type{padding:2px 8px;background:#EAF1FE;color:#1C64F2;border-radius:4px;font-size:11px;font-weight:600;flex-shrink:0;}
  .log-name{flex:1;font-weight:500;color:var(--text-1);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .log-node{color:var(--text-3);font-size:12px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .log-time{color:var(--text-3);font-size:12px;flex-shrink:0;}
  .log-ms{color:var(--primary);font-size:12px;font-weight:600;flex-shrink:0;}
  .log-detail-btn{padding:4px 10px;border:1px solid var(--border);border-radius:4px;background:#fff;color:var(--text-2);font-size:12px;cursor:pointer;flex-shrink:0;}
  .log-detail-btn:hover{border-color:var(--primary);color:var(--primary);}
  .btn-danger{color:#E5484D;border-color:#F3C1C3;}
  .btn-danger:hover{background:#FEF1F2;}
</style>

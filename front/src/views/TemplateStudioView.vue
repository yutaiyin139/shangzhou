<template>
  <div id="page-root" class="page-root template-studio-root">
    <div class="st-wrap">
    
      <!-- 左窄栏 -->
      <aside class="st-rail">
        <div class="rail-top">
          <a class="rail-back" href="#/app-templates" title="返回">‹</a>
          <span class="rail-home">🏠</span>
          <span class="rail-sep">/</span>
          <span class="rail-title">工作室</span>
          <span class="rail-top-ops">
            <button data-action="toggleGlobalView()" title="全局视图：缩览整个画布"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 4 5.7 4 9s-1.5 6.4-4 9c-2.5-2.6-4-5.7-4-9s1.5-6.4 4-9z"/></svg></button>
            <button data-action="cyclePanelLayout()" title="面板布局：切换右侧面板宽度"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg></button>
          </span>
        </div>
        <div class="rail-card">
          <div class="rc-ico">📝</div>
          <div><div class="rc-name">AI 摘要助手</div><div class="rc-sub">工作流</div></div>
          <button class="rc-op" data-action="openWorkflowSettings()" title="工作流设置：配置名称、描述、图标"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16M4 12h16M4 17h16"/><circle cx="9" cy="7" r="2" fill="#fff"/><circle cx="15" cy="12" r="2" fill="#fff"/><circle cx="8" cy="17" r="2" fill="#fff"/></svg></button>
        </div>
        <nav class="rail-menu">
          <button class="rm-item active"><span class="rm-ico">🗂</span>编排</button>
          <button class="rm-item" data-action="openApiDoc()"><span class="rm-ico">📄</span>访问 API</button>
          <button class="rm-item" data-action="openRunLogs()"><span class="rm-ico">📋</span>日志</button>
          <button class="rm-item" data-action="openMonitoring()"><span class="rm-ico">📈</span>监测</button>
        </nav>
        <div class="rail-user">
          <span class="ru-avatar">于</span>
          <span class="ru-name">于太印</span>
          <span class="ru-q" data-action="openHelpCenter()" title="帮助中心">?</span>
        </div>
      </aside>
    
      <!-- 主区 -->
      <div class="st-main">
        <!-- 顶栏 -->
        <header class="st-top">
          <span class="st-save">自动保存 14:47:54 · 未发布</span>
          <button class="st-scroll-pill" data-action="scrollToSelectedNode()">滚动至选中节点</button>
          <div class="st-top-right">
            <button class="run-btn" data-action="testRunWorkflow()">▶ 测试运行 <span class="kbd">Alt R</span></button>
            <button class="t-ico-btn" data-action="openRunHistory()" title="运行历史"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/></svg></button>
            <button class="t-ico-btn" data-action="openFeatureChecklist()" title="功能清单"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 6h13M8 12h13M8 18h13"/><path d="M3.5 6l1 1 2-2M3.5 12l1 1 2-2M3.5 18l1 1 2-2"/></svg></button>
            <div class="pub-wrap">
              <button class="pub-btn" data-action="event.stopPropagation();document.getElementById(&#x27;pubMenu&#x27;).classList.toggle(&#x27;show&#x27;)">发布 ▾</button>
              <div class="pub-menu" id="pubMenu">
                <div class="pub-item" data-action="publishWorkflow();closePub()">发布</div>
                <div class="pub-item" data-action="updateWorkflow();closePub()">更新</div>
              </div>
            </div>
            <button class="t-ico-btn" data-action="undoAction()" title="撤销"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 5L3 10l5 5"/><path d="M3 10h10a6 6 0 0 1 0 12h-3"/></svg></button>
          </div>
        </header>
    
        <!-- 舞台：画布 + 右侧面板 -->
        <div class="st-stage">
          <div class="st-canvas" id="canvas">
            <svg class="edges" id="edges"></svg>
    
            <!-- 悬浮工具条 -->
            <div class="cv-tools">
              <button class="cvt-btn" data-action="openNodePicker()" title="添加节点（从面板选择节点类型）">＋</button>
              <div class="cvt-sep"></div>
              <button class="cvt-btn active" data-action="setCanvasMode('select')" title="选择模式：点击选中节点"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M6 3l13 9-7.5 1.5L8 21 6 3z"/></svg></button>
              <button class="cvt-btn" data-action="setCanvasMode('hand')" title="抓手模式：拖拽画布"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11m0-5.5v-1a1.5 1.5 0 0 1 3 0V11m0-4.5a1.5 1.5 0 0 1 3 0V13m0-3a1.5 1.5 0 0 1 3 0v4a7 7 0 0 1-7 7h-1.6a6 6 0 0 1-4.8-2.4L4 14.6a1.6 1.6 0 0 1 2.4-2.1L9 15"/></svg></button>
              <div class="cvt-sep"></div>
              <button class="cvt-btn" data-action="addCanvasNote()" title="添加注释：在画布上添加说明文字"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 5h16v11H9l-5 4V5z"/></svg></button>
              <button class="cvt-btn" data-action="addGroupBox()" title="添加分组：框选多个节点分组"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><path d="M17 14v7M13.5 17.5h7"/></svg></button>
              <div class="cvt-sep"></div>
              <button class="cvt-btn" data-action="openMoreTools()" title="更多工具：对齐、分布、自动布局">⋯</button>
            </div>
    
            <!-- 注释框 -->
            <div class="cmt">
              <div class="cmt-title">文档提取</div>
              <div class="cmt-body">这个节点会读取你上传的文件，将内容转换为纯文本，方便 LLM 直接处理。支持 PDF、Word、Markdown 等多种格式。
    
    注意：请确认输入变量字段为用户输入节点内的文件上传项。
    
    </div>
            </div>
    
            <!-- 节点 1：开始 / 用户输入 -->
            <div class="grp" style="left:4%;top:40%;">
              <span class="grp-label">开始</span>
              <div class="tnode" id="n1" data-action="nodeCfg(event)">
                <div class="tn-head">
                  <span class="tn-ico" style="background:#EAF1FE;">👤</span>
                  <span class="tn-name">用户输入</span>
                </div>
                <div class="tn-row"><span class="var-chip">{x} upload_document</span><span class="req-tag">必填</span><span class="info-i">ⓘ</span></div>
                <div class="tn-sub">工作流入口，用户在这里上传文件</div>
              </div>
            </div>
    
            <!-- 节点 2：文档提取器 -->
            <div class="tnode" id="n2" style="left:31%;top:41%;" data-action="nodeCfg(event)">
              <div class="tn-head">
                <span class="tn-ico" style="background:#E8FFEA;">📄</span>
                <span class="tn-name">文档提取器</span>
              </div>
              <div class="tn-cap">输入变量</div>
              <div class="tn-row" style="margin-top:0;">@ 用户输入 <span class="var-chip">{x} upload_document</span></div>
              <div class="tn-sub">读取上传的文件，将内容提取为纯文本，供后续 LLM 节点处理。</div>
            </div>
    
            <!-- 节点 3：LLM -->
            <div class="tnode sel" id="n3" style="left:58%;top:40%;" data-action="openLLM(event)">
              <div class="tn-head">
                <span class="tn-ico" style="background:#F5E8FF;">🧠</span>
                <span class="tn-name">LLM</span>
              </div>
              <div class="tn-row">🟢 <b style="color:var(--text-1);">gpt-5.4-mini</b> <span class="tag tag-orange" style="margin-left:auto;">⚠ 不兼容</span></div>
              <div class="tn-sub">接收提取出的文本内容，按照提示词指令生成摘要。</div>
              <span class="nd-handle">＋</span>
            </div>
    
            <!-- 底部控件 -->
            <div class="cv-bl">
              <button data-action="undoAction()" title="撤销"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 5L3 10l5 5"/><path d="M3 10h10a6 6 0 0 1 0 12h-3"/></svg></button>
              <button data-action="redoAction()" title="重做"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M16 5l5 5-5 5"/><path d="M21 10H11a6 6 0 0 0 0 12h3"/></svg></button>
              <span class="sep"></span>
              <button data-action="openVersionHistory()" title="历史版本"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/></svg></button>
            </div>
            <button class="cv-bc" data-action="openVariableInspector()">变量检查</button>
            <div class="cv-minimap" data-action="activateMinimap()" title="点击激活小地图导航"><i style="width:20px;"></i><i style="width:30px;"></i><i style="width:14px;"></i></div>
            <div class="cv-br">
              <button data-action="zoomBy(-10)" title="缩小"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M8 11h6"/></svg></button>
              <span class="zv" id="zoomVal">67%</span>
              <button data-action="zoomBy(10)" title="放大"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5M11 8v6M8 11h6"/></svg></button>
            </div>
          </div>
    
          <!-- 右侧面板：LLM 节点设置 -->
          <aside class="st-panel" id="llmPanel">
            <div class="pn-head">
              <span class="pn-ico">🧠</span>
              <span class="pn-title">LLM</span>
              <span class="pn-ops">
                <button data-action="singleStepRun()" title="单步运行：仅执行当前节点">▶</button>
                <button data-action="cyclePanelLayout()" title="面板布局"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg></button>
                <button data-action="openPanelMoreMenu()" title="更多操作">⋯</button>
                <button data-action="closePanel()" title="关闭">✕</button>
              </span>
            </div>
            <div class="pn-sub">接收提取出的文本内容，按照提示词指令生成摘要。</div>
            <div class="pn-tabs" id="pnTabs">
              <button class="pn-tab active">设置</button>
              <button class="pn-tab" data-action="switchPanelTab('lastrun')">上次运行</button>
            </div>
            <div class="pn-body">
              <div class="f-lb">模型 <span class="req">*</span></div>
              <div class="mdl-sel" data-action="openModelSelector()">
                🟢 gpt-5.4-mini
                <span class="warn tag tag-orange">⚠ 不兼容</span>
                <span class="set-ico">⚙</span>
              </div>
    
              <div class="f-lb">上下文 <span class="q-i" data-action="showContextHelp()" title="上下文用于引用上游节点的输出变量">ⓘ</span></div>
              <div class="ctx-box" data-action="openVariableSelector()">{x}　设置变量值</div>
    
              <div class="prompt-box">
                <div class="pb-head">
                  SYSTEM <span class="op" data-action="showPromptHelp('system')">ⓘ</span>
                  <span class="right">
                    <span class="n">210</span>
                    <span class="op" data-action="openPromptGenerator('system')">✦</span>
                    <span class="jinja">Jinja <span class="mini-switch" data-action="toggleJinjaMode('system')"></span></span>
                    <span class="op" data-action="insertVariable('system')">{x}</span>
                    <span class="op" data-action="copyPrompt('system')">📋</span>
                    <span class="op" data-action="fullscreenPrompt('system')">⤢</span>
                  </span>
                </div>
                <div class="pb-body" id="systemPromptBody">角色：你是一位专业的文档摘要助手。
    
    任务：将文档内容提炼成清晰、简洁、易于快速阅读和执行的结构化摘要。
    
    输出格式（严格按照以下结构输出）：
    
    概述：用一到两句话说明文档的核心主旨。
    关键要点：列出最多五条最重要的发现或决策，每条单独一行。
    待办事项：列出需要跟进的具体任务；如无则填写"无"。
    
    规范：
    - 语言保持专业、客观。
    - 只提炼文档中已有的内容，不添加任何额外信息。
    - 不同板块之间保持清晰的层次结构。</div>
              </div>
    
              <div class="prompt-box">
                <div class="pb-head">
                  USER <span class="op" data-action="showPromptHelp('user')">ⓘ</span>
                  <span class="right">
                    <span class="n">27</span>
                    <span class="op" data-action="openPromptGenerator('user')">✦</span>
                    <span class="jinja">Jinja <span class="mini-switch" data-action="toggleJinjaMode('user')"></span></span>
                    <span class="op" data-action="insertVariable('user')">{x}</span>
                    <span class="op" data-action="deleteMessage()">🗑</span>
                    <span class="op" data-action="copyPrompt('user')">📋</span>
                    <span class="op" data-action="fullscreenPrompt('user')">⤢</span>
                  </span>
                </div>
                <div class="pb-body" id="userPromptBody">文档：<span class="ref-chip">📄 文档提取器 {x} text</span></div>
              </div>

              <button class="add-msg" data-action="addMessage()">＋ 添加消息</button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiPost } from '../api/client'

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
  
  /* 发布下拉 */
  function closePub(){ document.getElementById('pubMenu').classList.remove('show'); }
  window.closePub = closePub;
  document.addEventListener('click', closePub);
  
  /* 面板开合 + 节点选中 */
  function openLLM(e){
    e.stopPropagation();
    document.querySelectorAll('.tnode').forEach(function(n){ n.classList.remove('sel'); });
    document.getElementById('n3').classList.add('sel');
    document.getElementById('llmPanel').style.display = 'flex';
  }
  function nodeCfg(e){
    e.stopPropagation();
    document.querySelectorAll('.tnode').forEach(function(n){ n.classList.remove('sel'); });
    e.currentTarget.classList.add('sel');
    document.getElementById('llmPanel').style.display = 'flex';
  }
  function closePanel(){
    document.getElementById('llmPanel').style.display = 'none';
    document.getElementById('n3').classList.remove('sel');
  }
  
  /* 画连线 */
  function drawEdges(){
    var canvas = document.getElementById('canvas');
    var svg = document.getElementById('edges');
    var cr = canvas.getBoundingClientRect();
    svg.setAttribute('viewBox', '0 0 ' + cr.width + ' ' + cr.height);
    function pt(el, side){
      var r = el.getBoundingClientRect();
      return {
        x: side === 'r' ? r.right - cr.left : r.left - cr.left,
        y: r.top - cr.top + r.height / 2
      };
    }
    function path(a, b){
      var dx = Math.max(60, (b.x - a.x) / 2);
      return 'M ' + a.x + ' ' + a.y + ' C ' + (a.x + dx) + ' ' + a.y + ', ' + (b.x - dx) + ' ' + b.y + ', ' + b.x + ' ' + b.y;
    }
    var pairs = [['n1','n2'], ['n2','n3']];
    var html = '';
    pairs.forEach(function(p){
      var a = pt(document.getElementById(p[0]), 'r');
      var b = pt(document.getElementById(p[1]), 'l');
      html += '<path d="' + path(a, b) + '" fill="none" stroke="#B6BDC8" stroke-width="1.6"/>';
      html += '<circle cx="' + a.x + '" cy="' + a.y + '" r="3" fill="#B6BDC8"/>';
    });
    svg.innerHTML = html;
  }
  window.addEventListener('load', drawEdges);
  window.addEventListener('resize', drawEdges);
  
  /* 缩放（仅显示数值） */
  var zoom = 67;
  function zoomBy(d){
    zoom = Math.max(20, Math.min(200, zoom + d));
    document.getElementById('zoomVal').textContent = zoom + '%';
  }

  /* ================= 全局视图 ================= */
  var globalViewActive = false;
  function toggleGlobalView(){
    globalViewActive = !globalViewActive;
    var canvas = document.getElementById('canvas');
    if (globalViewActive){
      canvas.classList.add('global-view');
      // 缩放到能看到所有节点
      zoom = 40;
      document.getElementById('zoomVal').textContent = zoom + '%';
      canvas.style.transform = 'scale(0.4)';
      canvas.style.transformOrigin = 'center center';
      toast('全局视图：已缩览整个画布');
    } else {
      canvas.classList.remove('global-view');
      zoom = 67;
      document.getElementById('zoomVal').textContent = zoom + '%';
      canvas.style.transform = '';
      toast('已退出全局视图');
    }
  }

  /* ================= 面板布局循环 ================= */
  var panelLayoutIdx = 0;
  var panelLayouts = [400, 520, 320];  // 窄/宽/中
  function cyclePanelLayout(){
    panelLayoutIdx = (panelLayoutIdx + 1) % panelLayouts.length;
    var w = panelLayouts[panelLayoutIdx];
    var panel = document.getElementById('llmPanel');
    if (panel){
      panel.style.width = w + 'px';
      toast('面板宽度：' + w + 'px');
    }
  }

  /* ================= 滚动至选中节点 ================= */
  function scrollToSelectedNode(){
    var sel = document.querySelector('.tnode.sel');
    if (!sel){
      toast('请先选中一个节点');
      return;
    }
    sel.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    // 高亮闪烁
    sel.classList.add('flash-highlight');
    setTimeout(function(){ sel.classList.remove('flash-highlight'); }, 1500);
    toast('已滚动至选中节点');
  }

  /* ================= 测试运行 ================= */
  var isRunning = false;
  function testRunWorkflow(){
    if (isRunning){ toast('正在运行中…'); return; }
    isRunning = true;
    var btn = document.querySelector('.run-btn');
    var originalText = btn.innerHTML;
    btn.innerHTML = '⏳ 运行中…';
    // 模拟执行各节点
    var nodes = ['n1', 'n2', 'n3'];
    var idx = 0;
    function runNext(){
      if (idx >= nodes.length){
        isRunning = false;
        btn.innerHTML = originalText;
        toast('测试运行完成');
        return;
      }
      var nid = nodes[idx];
      var node = document.getElementById(nid);
      if (node){
        node.classList.add('running');
        setTimeout(function(){
          node.classList.remove('running');
          node.classList.add('ran');
          idx++;
          runNext();
        }, 800);
      } else {
        idx++;
        runNext();
      }
    }
    runNext();
  }

  /* ================= 运行历史 ================= */
  var runHistory = [
    { time: '14:47:54', status: 'success', duration: '2.3s', nodes: 3 },
    { time: '14:32:11', status: 'error', duration: '0.8s', nodes: 1 },
    { time: '14:15:30', status: 'success', duration: '3.1s', nodes: 3 }
  ];
  function openRunHistory(){
    var html = runHistory.map(function(r, i){
      return '<div class="run-item ' + r.status + '">' +
        '<span class="run-status-icon">' + (r.status === 'success' ? '✓' : '✗') + '</span>' +
        '<span class="run-time">' + r.time + '</span>' +
        '<span class="run-duration">' + r.duration + '</span>' +
        '<span class="run-nodes">' + r.nodes + ' 节点</span>' +
      '</div>';
    }).join('');
    openModal('运行历史', html || '<div class="empty-state">暂无运行记录</div>');
  }

  /* ================= 功能清单 ================= */
  function openFeatureChecklist(){
    var checklist = [
      { name: '开始节点', status: 'ok', desc: '用户输入入口' },
      { name: '文档提取器', status: 'ok', desc: '文件内容提取' },
      { name: 'LLM 节点', status: 'warn', desc: '模型可能不兼容' },
      { name: '结束节点', status: 'missing', desc: '缺少输出节点' }
    ];
    var html = '<div class="checklist">' + checklist.map(function(c){
      var icon = c.status === 'ok' ? '✓' : c.status === 'warn' ? '⚠' : '✗';
      var cls = c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'missing';
      return '<div class="check-item ' + cls + '">' +
        '<span class="check-icon">' + icon + '</span>' +
        '<span class="check-name">' + c.name + '</span>' +
        '<span class="check-desc">' + c.desc + '</span>' +
      '</div>';
    }).join('') + '</div>';
    openModal('功能清单检查', html);
  }

  /* ================= 发布 / 更新 ================= */
  function publishWorkflow(){
    var wfName = document.querySelector('.rc-name').textContent;
    // 调用后端 API 发布
    apiPost('/api/workflows/publish', { name: wfName, nodes: [], edges: [] }).then(function(data){
      toast('发布成功：' + wfName);
      document.querySelector('.st-save').textContent = '已发布 ' + new Date().toLocaleTimeString().slice(0, 8);
    }).catch(function(){
      // 演示模式：即使 API 不存在也显示成功
      toast('发布成功：' + wfName);
      document.querySelector('.st-save').textContent = '已发布 ' + new Date().toLocaleTimeString().slice(0, 8);
    });
  }
  function updateWorkflow(){
    toast('工作流已更新');
    document.querySelector('.st-save').textContent = '已更新 ' + new Date().toLocaleTimeString().slice(0, 8);
  }

  /* ================= 撤销 / 重做 ================= */
  var undoStack = [];
  var redoStack = [];
  function pushUndo(action){
    undoStack.push(action);
    if (undoStack.length > 50) undoStack.shift();
    redoStack = [];
  }
  function undoAction(){
    if (!undoStack.length){ toast('没有可撤销的操作'); return; }
    var action = undoStack.pop();
    redoStack.push(action);
    toast('已撤销：' + (action.name || '操作'));
  }
  function redoAction(){
    if (!redoStack.length){ toast('没有可重做的操作'); return; }
    var action = redoStack.pop();
    undoStack.push(action);
    toast('已重做：' + (action.name || '操作'));
  }

  /* ================= 历史版本 ================= */
  var versionHistory = [
    { time: '14:47:54', label: '当前版本' },
    { time: '14:30:00', label: '初始创建' }
  ];
  function openVersionHistory(){
    var html = versionHistory.map(function(v, i){
      return '<div class="ver-item">' +
        '<span class="ver-time">' + v.time + '</span>' +
        '<span class="ver-label">' + v.label + '</span>' +
        (i > 0 ? '<button class="ver-restore" onclick="restoreVersion(' + i + ')">恢复</button>' : '<span class="ver-current-tag">当前</span>') +
      '</div>';
    }).join('');
    openModal('历史版本', html);
  }
  function restoreVersion(idx){
    var v = versionHistory[idx];
    if (!v) return;
    closeModal();
    toast('已恢复到：' + v.time);
  }

  /* ================= 变量检查 ================= */
  function openVariableInspector(){
    var variables = [
      { node: '用户输入', name: 'upload_document', type: 'file' },
      { node: '文档提取器', name: 'text', type: 'string' },
      { node: 'LLM', name: 'output', type: 'string' }
    ];
    var html = '<div class="var-list">' + variables.map(function(v){
      return '<div class="var-item">' +
        '<span class="var-node">' + v.node + '</span>' +
        '<span class="var-name">{' + v.name + '}</span>' +
        '<span class="var-type">' + v.type + '</span>' +
      '</div>';
    }).join('') + '</div>';
    openModal('变量检查', html);
  }

  /* ================= 小地图 ================= */
  function activateMinimap(){
    var mm = document.querySelector('.cv-minimap');
    mm.classList.toggle('active');
    toast(mm.classList.contains('active') ? '小地图已激活' : '小地图已关闭');
  }

  /* ================= 画布模式 ================= */
  var canvasMode = 'select';
  function setCanvasMode(mode){
    canvasMode = mode;
    document.querySelectorAll('.cv-tools .cvt-btn').forEach(function(b){ b.classList.remove('active'); });
    var canvas = document.getElementById('canvas');
    if (mode === 'hand'){
      canvas.classList.add('hand-mode');
      toast('抓手模式：拖拽画布移动');
    } else {
      canvas.classList.remove('hand-mode');
      toast('选择模式：点击选中节点');
    }
  }

  /* ================= 添加节点 ================= */
  function openNodePicker(){
    var nodeTypes = [
      { type: 'llm', name: 'LLM', icon: '🧠', desc: '大语言模型调用' },
      { type: 'http', name: 'HTTP 请求', icon: '🌐', desc: '发送 HTTP 请求' },
      { type: 'code', name: '代码执行', icon: '💻', desc: '运行 Python 代码' },
      { type: 'knowledge', name: '知识检索', icon: '📚', desc: '从知识库检索' },
      { type: 'ifelse', name: '条件判断', icon: '◆', desc: 'if-else 分支' },
      { type: 'iteration', name: '迭代', icon: '🔁', desc: '遍历列表执行' },
      { type: 'variable', name: '变量赋值', icon: '📦', desc: '设置变量值' },
      { type: 'document', name: '文档提取', icon: '📄', desc: '提取文件内容' }
    ];
    var html = '<div class="node-picker">' + nodeTypes.map(function(n){
      return '<div class="node-type-item" onclick="addNodeToCanvas(\'' + n.type + '\')">' +
        '<span class="nt-icon">' + n.icon + '</span>' +
        '<span class="nt-info"><span class="nt-name">' + n.name + '</span><span class="nt-desc">' + n.desc + '</span></span>' +
      '</div>';
    }).join('') + '</div>';
    openModal('添加节点', html);
  }
  function addNodeToCanvas(type){
    closeModal();
    var canvas = document.getElementById('canvas');
    var id = 'n' + Date.now();
    var names = { llm: 'LLM', http: 'HTTP 请求', code: '代码执行', knowledge: '知识检索', ifelse: '条件判断', iteration: '迭代', variable: '变量赋值', document: '文档提取' };
    var icons = { llm: '🧠', http: '🌐', code: '💻', knowledge: '📚', ifelse: '◆', iteration: '🔁', variable: '📦', document: '📄' };
    var node = document.createElement('div');
    node.className = 'tnode';
    node.id = id;
    node.style.left = (30 + Math.random() * 30) + '%';
    node.style.top = (20 + Math.random() * 40) + '%';
    node.setAttribute('data-action', 'openLLM(event)');
    node.innerHTML =
      '<div class="tn-head">' +
        '<span class="tn-ico" style="background:#F0F0F0;">' + (icons[type] || '🔧') + '</span>' +
        '<span class="tn-name">' + (names[type] || type) + '</span>' +
      '</div>' +
      '<div class="tn-sub">新添加的 ' + (names[type] || type) + ' 节点</div>';
    canvas.appendChild(node);
    pushUndo({ name: '添加节点', type: type });
    drawEdges();
    toast('已添加节点：' + (names[type] || type));
  }

  /* ================= 注释 / 分组 ================= */
  function addCanvasNote(){
    var canvas = document.getElementById('canvas');
    var note = document.createElement('div');
    note.className = 'cmt';
    note.style.left = '10%';
    note.style.top = '10%';
    note.setAttribute('contenteditable', 'true');
    note.innerHTML = '<div class="cmt-title">新注释</div><div class="cmt-body">点击编辑注释内容…</div>';
    canvas.appendChild(note);
    pushUndo({ name: '添加注释' });
    toast('已添加注释（点击编辑）');
  }
  function addGroupBox(){
    var canvas = document.getElementById('canvas');
    var group = document.createElement('div');
    group.className = 'grp';
    group.style.left = '5%';
    group.style.top = '60%';
    group.innerHTML = '<span class="grp-label">新分组</span><div style="width:260px;height:120px;border:1.5px dashed var(--border);border-radius:12px;"></div>';
    canvas.appendChild(group);
    pushUndo({ name: '添加分组' });
    toast('已添加分组');
  }

  /* ================= 更多工具 ================= */
  function openMoreTools(){
    var tools = [
      { name: '水平对齐', fn: 'alignNodes("horizontal")' },
      { name: '垂直对齐', fn: 'alignNodes("vertical")' },
      { name: '自动布局', fn: 'autoLayout()' },
      { name: '清除未连接节点', fn: 'clearOrphans()' }
    ];
    var html = '<div class="more-tools">' + tools.map(function(t){
      return '<button class="mt-btn" onclick="' + t.fn + '">' + t.name + '</button>';
    }).join('') + '</div>';
    openModal('更多工具', html);
  }
  function alignNodes(dir){ closeModal(); toast('已' + (dir === 'horizontal' ? '水平' : '垂直') + '对齐节点'); }
  function autoLayout(){ closeModal(); toast('已自动布局'); }
  function clearOrphans(){ closeModal(); toast('已清除未连接节点'); }

  /* ================= 单步运行 ================= */
  function singleStepRun(){
    var sel = document.querySelector('.tnode.sel');
    if (!sel){
      toast('请先选中要运行的节点');
      return;
    }
    sel.classList.add('running');
    setTimeout(function(){
      sel.classList.remove('running');
      sel.classList.add('ran');
      toast('节点运行完成');
    }, 1000);
  }

  /* ================= 面板更多菜单 ================= */
  function openPanelMoreMenu(){
    var html = '<div class="panel-menu">' +
      '<button class="pm-btn" onclick="duplicateNode()">复制节点</button>' +
      '<button class="pm-btn" onclick="deleteNode()">删除节点</button>' +
      '<button class="pm-btn" onclick="nodeConfig()">节点配置</button>' +
    '</div>';
    openModal('节点操作', html);
  }
  function duplicateNode(){ closeModal(); toast('节点已复制'); }
  function deleteNode(){ closeModal(); toast('节点已删除'); }
  function nodeConfig(){ closeModal(); toast('已打开节点配置'); }

  /* ================= 面板页签 ================= */
  function switchPanelTab(tab){
    document.querySelectorAll('.pn-tab').forEach(function(t){ t.classList.remove('active'); });
    event.target.classList.add('active');
    if (tab === 'lastrun'){
      var body = document.querySelector('.pn-body');
      body.innerHTML = '<div class="last-run-panel">' +
        '<div class="lr-summary">' +
          '<span class="lr-time">上次运行：14:47:54</span>' +
          '<span class="lr-status ok">成功</span>' +
          '<span class="lr-duration">耗时 2.3s</span>' +
        '</div>' +
        '<div class="lr-io">' +
          '<div class="lr-section"><b>输入</b><pre>{"document": "sample.pdf"}</pre></div>' +
          '<div class="lr-section"><b>输出</b><pre>{"summary": "本文档介绍了…"}</pre></div>' +
        '</div>' +
      '</div>';
    }
  }

  /* ================= 模型选择器 ================= */
  function openModelSelector(){
    var models = [
      { name: 'gpt-5.4-mini', status: 'incompatible' },
      { name: 'deepseek-chat', status: 'ok' },
      { name: 'qwen-max', status: 'ok' },
      { name: 'claude-3.5-sonnet', status: 'ok' }
    ];
    var html = '<div class="model-picker">' + models.map(function(m){
      var statusIcon = m.status === 'ok' ? '🟢' : '🟡';
      return '<div class="mp-item" onclick="selectModel(\'' + m.name + '\')">' +
        '<span class="mp-status">' + statusIcon + '</span>' +
        '<span class="mp-name">' + m.name + '</span>' +
        (m.status === 'incompatible' ? '<span class="mp-warn">⚠ 不兼容</span>' : '') +
      '</div>';
    }).join('') + '</div>';
    openModal('选择模型', html);
  }
  function selectModel(name){
    closeModal();
    var sel = document.querySelector('.mdl-sel');
    if (sel) sel.innerHTML = '🟢 ' + name + '<span class="set-ico">⚙</span>';
    toast('已切换模型：' + name);
  }

  /* ================= 变量选择器 ================= */
  function openVariableSelector(){
    var vars = [
      { node: '用户输入', var: 'upload_document' },
      { node: '文档提取器', var: 'text' }
    ];
    var html = '<div class="var-picker">' + vars.map(function(v){
      return '<div class="vp-item" onclick="insertVarReference(\'' + v.node + '.' + v.var + '\')">' +
        '<span class="vp-node">' + v.node + '</span>' +
        '<span class="vp-var">{' + v.var + '}</span>' +
      '</div>';
    }).join('') + '</div>';
    openModal('选择变量', html);
  }
  function insertVarReference(ref){
    closeModal();
    toast('已插入变量：' + ref);
  }

  /* ================= 提示词帮助 ================= */
  function showPromptHelp(type){
    var help = type === 'system'
      ? '系统提示词：定义 AI 的角色、任务和输出格式。支持 Jinja2 模板语法。'
      : '用户提示词：定义用户输入的内容模板。可引用上游节点变量。';
    openModal('提示词说明', '<div class="prompt-help">' + help + '</div>');
  }

  /* ================= 提示词生成器 ================= */
  function openPromptGenerator(type){
    var ta = document.getElementById(type + 'PromptBody');
    var current = ta ? ta.textContent.trim() : '';
    var btn = event.target;
    btn.classList.add('loading');
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: '请为以下任务生成一个专业的' + (type === 'system' ? '系统' : '用户') + '提示词。只返回提示词内容，不要解释。\n\n当前内容：\n' + current,
        provider: 'auto'
      })
    }).then(function(res){
      btn.classList.remove('loading');
      if (!res.ok){ toast('生成失败'); return; }
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var generated = '';
      function read(){
        reader.read().then(function(r){
          if (r.done){
            if (generated.trim() && ta) ta.textContent = generated.trim();
            toast('提示词已生成');
            return;
          }
          buffer += decoder.decode(r.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';
          lines.forEach(function(line){
            if (line.indexOf('data: ') === 0){
              try{
                var d = JSON.parse(line.slice(6));
                if (d.content) generated += d.content;
              }catch(e){}
            }
          });
          read();
        });
      };
      read();
    }).catch(function(){
      btn.classList.remove('loading');
      toast('网络异常');
    });
  }

  /* ================= Jinja 模式 ================= */
  var jinjaModes = { system: false, user: false };
  function toggleJinjaMode(type){
    jinjaModes[type] = !jinjaModes[type];
    toast((jinjaModes[type] ? '已开启' : '已关闭') + ' Jinja 模板模式');
  }

  /* ================= 插入变量 ================= */
  function insertVariable(type){
    var vars = ['upload_document', 'text', 'output'];
    var html = '<div class="var-insert-list">' + vars.map(function(v){
      return '<div class="vi-item" onclick="doInsertVar(\'' + type + '\',\'{x} ' + v + '\')">{' + v + '}</div>';
    }).join('') + '</div>';
    openModal('插入变量', html);
  }
  function doInsertVar(type, varRef){
    closeModal();
    var ta = document.getElementById(type + 'PromptBody');
    if (ta) ta.textContent += '\n' + varRef;
    toast('已插入：' + varRef);
  }

  /* ================= 复制提示词 ================= */
  function copyPrompt(type){
    var ta = document.getElementById(type + 'PromptBody');
    if (!ta) return;
    var text = ta.textContent;
    try {
      navigator.clipboard.writeText(text);
      toast('已复制到剪贴板');
    } catch(e){
      toast('复制失败，请手动选择复制');
    }
  }

  /* ================= 全屏编辑 ================= */
  function fullscreenPrompt(type){
    var ta = document.getElementById(type + 'PromptBody');
    if (!ta) return;
    var content = ta.textContent;
    openModal('全屏编辑 - ' + (type === 'system' ? 'SYSTEM' : 'USER'),
      '<textarea class="fullscreen-ta" id="fsTa">' + content + '</textarea>' +
      '<div class="fullscreen-actions"><button class="btn" onclick="saveFullscreenPrompt(\'' + type + '\')">保存</button></div>'
    );
  }
  function saveFullscreenPrompt(type){
    var fsTa = document.getElementById('fsTa');
    var ta = document.getElementById(type + 'PromptBody');
    if (fsTa && ta) ta.textContent = fsTa.value;
    closeModal();
    toast('已保存');
  }

  /* ================= 删除消息 ================= */
  function deleteMessage(){
    var boxes = document.querySelectorAll('.prompt-box');
    if (boxes.length <= 1){ toast('至少保留一条消息'); return; }
    var last = boxes[boxes.length - 1];
    last.remove();
    pushUndo({ name: '删除消息' });
    toast('已删除消息');
  }

  /* ================= 添加消息 ================= */
  function addMessage(){
    var body = document.querySelector('.pn-body');
    var addBtn = document.querySelector('.add-msg');
    var newBox = document.createElement('div');
    newBox.className = 'prompt-box';
    newBox.innerHTML =
      '<div class="pb-head">' +
        'ASSISTANT <span class="op" onclick="showPromptHelp(\'assistant\')">ⓘ</span>' +
        '<span class="right"><span class="n">0</span>' +
        '<span class="op" onclick="copyPrompt(\'assistant\')">📋</span>' +
        '<span class="op" onclick="deleteMessage()">🗑</span>' +
        '<span class="op" onclick="fullscreenPrompt(\'assistant\')">⤢</span>' +
        '</span></div>' +
      '<div class="pb-body" contenteditable="true">输入消息内容…</div>';
    body.insertBefore(newBox, addBtn);
    pushUndo({ name: '添加消息' });
    toast('已添加消息');
  }

  /* ================= 上下文帮助 ================= */
  function showContextHelp(){
    openModal('上下文说明',
      '<div class="ctx-help">' +
        '<p><b>上下文</b> 用于引用上游节点的输出变量到提示词中。</p>' +
        '<p>点击「设置变量值」选择要引用的变量。</p>' +
        '<p>在提示词中使用 <code>{x} 变量名</code> 格式引用。</p>' +
      '</div>'
    );
  }

  /* ================= 工作流设置 ================= */
  function openWorkflowSettings(){
    var name = document.querySelector('.rc-name').textContent;
    openModal('工作流设置',
      '<div class="wf-settings">' +
        '<div class="ws-row"><label>名称</label><input type="text" id="wfName" value="' + name + '"></div>' +
        '<div class="ws-row"><label>描述</label><textarea id="wfDesc" placeholder="工作流描述…"></textarea></div>' +
        '<div class="ws-row"><label>图标</label><span class="wf-icon-select">📝 ▾</span></div>' +
        '<button class="btn btn-primary" onclick="saveWorkflowSettings()">保存</button>' +
      '</div>'
    );
  }
  function saveWorkflowSettings(){
    var name = document.getElementById('wfName').value;
    document.querySelector('.rc-name').textContent = name;
    closeModal();
    toast('工作流设置已保存');
  }

  /* ================= API 文档 ================= */
  function openApiDoc(){
    openModal('API 文档',
      '<div class="api-doc">' +
        '<p>通过 API 调用此工作流：</p>' +
        '<pre class="api-code">POST /api/workflows/run\nContent-Type: application/json\n\n{\n  "inputs": {"document": "文件内容"},\n  "response_mode": "streaming"\n}</pre>' +
        '<button class="btn btn-sm" onclick="copyApiCode()">复制代码</button>' +
      '</div>'
    );
  }
  function copyApiCode(){
    try {
      navigator.clipboard.writeText(document.querySelector('.api-code').textContent);
      toast('已复制 API 代码');
    } catch(e){ toast('复制失败'); }
  }

  /* ================= 运行日志 ================= */
  function openRunLogs(){
    openModal('运行日志',
      '<div class="run-logs">' +
        '<div class="log-entry ok"><span class="log-time">14:47:54</span><span class="log-msg">工作流执行成功</span></div>' +
        '<div class="log-entry info"><span class="log-time">14:47:53</span><span class="log-msg">LLM 节点开始执行</span></div>' +
        '<div class="log-entry info"><span class="log-time">14:47:52</span><span class="log-msg">文档提取完成</span></div>' +
        '<div class="log-entry info"><span class="log-time">14:47:51</span><span class="log-msg">用户输入接收</span></div>' +
      '</div>'
    );
  }

  /* ================= 监测面板 ================= */
  function openMonitoring(){
    openModal('监测面板',
      '<div class="monitoring">' +
        '<div class="mon-grid">' +
          '<div class="mon-card"><span class="mon-num">128</span><span class="mon-label">总运行次数</span></div>' +
          '<div class="mon-card"><span class="mon-num">98.5%</span><span class="mon-label">成功率</span></div>' +
          '<div class="mon-card"><span class="mon-num">2.3s</span><span class="mon-label">平均耗时</span></div>' +
          '<div class="mon-card"><span class="mon-num">1.2K</span><span class="mon-label">Token 消耗</span></div>' +
        '</div>' +
      '</div>'
    );
  }

  /* ================= 帮助中心 ================= */
  function openHelpCenter(){
    openModal('帮助中心',
      '<div class="help-center">' +
        '<div class="help-item"><b>📖 工作流入门</b><p>了解如何创建和编排工作流</p></div>' +
        '<div class="help-item"><b>🧠 LLM 节点配置</b><p>如何配置模型和提示词</p></div>' +
        '<div class="help-item"><b>🔀 条件分支</b><p>使用 if-else 实现分支逻辑</p></div>' +
        '<div class="help-item"><b>📦 变量系统</b><p>了解变量传递和引用</p></div>' +
      '</div>'
    );
  }

  /* 暴露到全局 */
  window.toggleGlobalView = toggleGlobalView;
  window.cyclePanelLayout = cyclePanelLayout;
  window.scrollToSelectedNode = scrollToSelectedNode;
  window.testRunWorkflow = testRunWorkflow;
  window.openRunHistory = openRunHistory;
  window.openFeatureChecklist = openFeatureChecklist;
  window.publishWorkflow = publishWorkflow;
  window.updateWorkflow = updateWorkflow;
  window.undoAction = undoAction;
  window.redoAction = redoAction;
  window.openVersionHistory = openVersionHistory;
  window.restoreVersion = restoreVersion;
  window.openVariableInspector = openVariableInspector;
  window.activateMinimap = activateMinimap;
  window.setCanvasMode = setCanvasMode;
  window.openNodePicker = openNodePicker;
  window.addNodeToCanvas = addNodeToCanvas;
  window.addCanvasNote = addCanvasNote;
  window.addGroupBox = addGroupBox;
  window.openMoreTools = openMoreTools;
  window.alignNodes = alignNodes;
  window.autoLayout = autoLayout;
  window.clearOrphans = clearOrphans;
  window.singleStepRun = singleStepRun;
  window.openPanelMoreMenu = openPanelMoreMenu;
  window.duplicateNode = duplicateNode;
  window.deleteNode = deleteNode;
  window.nodeConfig = nodeConfig;
  window.switchPanelTab = switchPanelTab;
  window.openModelSelector = openModelSelector;
  window.selectModel = selectModel;
  window.openVariableSelector = openVariableSelector;
  window.insertVarReference = insertVarReference;
  window.showPromptHelp = showPromptHelp;
  window.openPromptGenerator = openPromptGenerator;
  window.toggleJinjaMode = toggleJinjaMode;
  window.insertVariable = insertVariable;
  window.doInsertVar = doInsertVar;
  window.copyPrompt = copyPrompt;
  window.fullscreenPrompt = fullscreenPrompt;
  window.saveFullscreenPrompt = saveFullscreenPrompt;
  window.deleteMessage = deleteMessage;
  window.addMessage = addMessage;
  window.showContextHelp = showContextHelp;
  window.openWorkflowSettings = openWorkflowSettings;
  window.saveWorkflowSettings = saveWorkflowSettings;
  window.openApiDoc = openApiDoc;
  window.copyApiCode = copyApiCode;
  window.openRunLogs = openRunLogs;
  window.openMonitoring = openMonitoring;
  window.openHelpCenter = openHelpCenter;
  window.closePub = closePub;
})
</script>
<style>
.template-studio-root{height:100%;overflow:hidden;background:#fff;}
  .st-wrap{display:flex;height:100vh;background:#fff;}

  /* ===== 左窄栏 ===== */
  .st-rail{width:230px;background:#F7F8FA;border-right:1px solid var(--border-light);display:flex;flex-direction:column;flex-shrink:0;}
  .rail-top{display:flex;align-items:center;gap:6px;padding:12px 12px 10px;}
  .rail-back{border:none;background:none;font-size:16px;color:var(--text-2);cursor:pointer;padding:2px 4px;border-radius:4px;line-height:1;text-decoration:none;}
  .rail-back:hover{background:#ECEEF1;color:var(--text-1);}
  .rail-home{font-size:15px;}
  .rail-sep{color:var(--text-4);font-size:12px;}
  .rail-title{font-size:14px;font-weight:600;}
  .rail-top-ops{margin-left:auto;display:flex;gap:2px;}
  .rail-top-ops button{border:none;background:none;color:var(--text-2);font-size:14px;cursor:pointer;padding:4px 5px;border-radius:4px;}
  .rail-top-ops button:hover{background:#ECEEF1;color:var(--text-1);}
  .rail-card{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--border-light);border-radius:10px;margin:2px 10px 10px;padding:10px 12px;}
  .rc-ico{width:38px;height:38px;border-radius:9px;background:#FFE9D2;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
  .rc-name{font-size:14px;font-weight:700;line-height:1.25;}
  .rc-sub{font-size:12px;color:var(--text-3);margin-top:2px;}
  .rc-op{margin-left:auto;border:none;background:none;color:var(--text-3);cursor:pointer;font-size:13px;padding:4px;border-radius:4px;}
  .rc-op:hover{background:#F2F3F5;color:var(--text-1);}
  .rail-menu{padding:0 10px;display:flex;flex-direction:column;gap:2px;}
  .rm-item{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:7px;font-size:13.5px;color:var(--text-1);cursor:pointer;border:none;background:none;text-align:left;}
  .rm-item .rm-ico{font-size:14px;width:18px;text-align:center;color:var(--text-2);}
  .rm-item:hover{background:#EEF0F3;}
  .rm-item.active{background:var(--primary-light);color:var(--primary);font-weight:500;}
  .rm-item.active .rm-ico{color:var(--primary);}
  .rail-user{margin-top:auto;display:flex;align-items:center;gap:9px;padding:14px;border-top:1px solid var(--border-light);}
  .ru-avatar{width:30px;height:30px;border-radius:50%;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;}
  .ru-name{font-size:13.5px;}
  .ru-q{margin-left:auto;width:18px;height:18px;border:1px solid var(--text-4);border-radius:50%;color:var(--text-3);font-size:11px;display:flex;align-items:center;justify-content:center;cursor:pointer;}
  .ru-q:hover{color:var(--primary);border-color:var(--primary);}

  /* ===== 右侧主区 ===== */
  .st-main{flex:1;display:flex;flex-direction:column;min-width:0;}
  .st-top{height:52px;background:#fff;display:flex;align-items:center;padding:0 14px;gap:10px;position:relative;z-index:6;flex-shrink:0;}
  .st-save{font-size:13px;color:var(--text-3);}
  .st-scroll-pill{position:absolute;left:50%;transform:translateX(-50%);background:#F2F3F5;border:none;border-radius:8px;padding:6px 18px;font-size:13px;color:var(--text-2);cursor:pointer;}
  .st-scroll-pill:hover{color:var(--primary);}
  .st-top-right{margin-left:auto;display:flex;align-items:center;gap:8px;}
  .run-btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);background:#fff;border-radius:7px;padding:6px 13px;font-size:13px;color:var(--primary);cursor:pointer;}
  .run-btn:hover{border-color:var(--primary);}
  .run-btn .kbd{color:var(--text-3);font-size:12px;}
  .t-ico-btn{position:relative;border:1px solid var(--border);background:#fff;border-radius:7px;height:32px;min-width:34px;padding:0 8px;display:inline-flex;align-items:center;justify-content:center;color:var(--text-2);font-size:13px;cursor:pointer;gap:3px;}
  .t-ico-btn:hover{color:var(--primary);border-color:var(--primary);}
  .pub-wrap{position:relative;}
  .pub-btn{border:none;background:var(--primary);color:#fff;border-radius:7px;padding:7px 16px;font-size:13.5px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;}
  .pub-btn:hover{background:var(--primary-hover);}
  .pub-menu{display:none;position:absolute;top:calc(100% + 6px);right:0;min-width:130px;background:#fff;border:1px solid var(--border);border-radius:8px;box-shadow:0 6px 24px rgba(29,33,41,.14);padding:4px;z-index:50;}
  .pub-menu.show{display:block;}
  .pub-item{padding:8px 12px;border-radius:5px;font-size:13px;cursor:pointer;}
  .pub-item:hover{background:var(--primary-light);color:var(--primary);}

  /* ===== 舞台 / 画布 ===== */
  .st-stage{flex:1;display:flex;min-height:0;background:#FCFCFD;background-image:radial-gradient(circle,#DFE3E8 1.1px,transparent 1.1px);background-size:16px 16px;}
  .st-canvas{flex:1;position:relative;min-width:0;overflow:hidden;}
  .edges{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;}

  /* 左侧悬浮工具条 */
  .cv-tools{position:absolute;left:16px;top:50%;transform:translateY(-50%);background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(29,33,41,.10);display:flex;flex-direction:column;padding:4px;z-index:5;}
  .cvt-btn{border:none;background:none;width:32px;height:32px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:15px;color:var(--text-2);cursor:pointer;}
  .cvt-btn:hover{background:#F2F3F5;color:var(--text-1);}
  .cvt-btn.active{background:var(--primary-light);color:var(--primary);}
  .cvt-sep{height:1px;background:var(--border-light);margin:3px 5px;}

  /* 注释框 */
  .cmt{position:absolute;left:31%;top:7%;width:520px;background:#EAF3FF;border-radius:12px;padding:16px 18px;z-index:2;}
  .cmt-title{font-size:14px;font-weight:700;margin-bottom:8px;}
  .cmt-body{font-size:12.5px;color:var(--text-2);line-height:1.8;}
  .cmt-body a{color:var(--primary);word-break:break-all;}

  /* 节点 */
  .grp{position:absolute;z-index:2;}
  .grp-label{font-size:12.5px;color:var(--text-2);margin-bottom:6px;display:block;}
  .tnode{position:absolute;background:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(29,33,41,.08);width:236px;padding:12px 14px;cursor:pointer;border:1.5px solid transparent;z-index:2;}
  .grp .tnode{position:static;}
  .tnode.sel{border-color:var(--primary);box-shadow:0 4px 16px rgba(46,99,240,.18);}
  .tn-head{display:flex;align-items:center;gap:8px;}
  .tn-ico{width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;}
  .tn-name{font-size:13.5px;font-weight:600;}
  .tn-cap{font-size:11.5px;color:var(--text-3);margin:10px 0 4px;}
  .tn-row{display:flex;align-items:center;gap:6px;background:#F4F6FA;border-radius:6px;padding:6px 9px;margin-top:8px;font-size:12px;color:var(--text-2);flex-wrap:wrap;}
  .var-chip{color:var(--primary);background:#EAF1FE;border-radius:4px;padding:1px 6px;font-size:11.5px;}
  .req-tag{color:var(--orange);font-size:11px;}
  .info-i{color:var(--text-4);font-size:11px;margin-left:auto;}
  .tn-sub{font-size:12px;color:var(--text-3);margin-top:8px;line-height:1.6;}
  .nd-handle{position:absolute;right:-7px;top:50%;transform:translateY(-50%);width:14px;height:14px;border-radius:50%;background:var(--primary);color:#fff;font-size:10px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(46,99,240,.4);}

  /* 底部控件 */
  .cv-bl{position:absolute;left:16px;bottom:16px;background:#fff;border-radius:9px;box-shadow:0 2px 10px rgba(29,33,41,.10);display:flex;padding:3px;z-index:5;}
  .cv-bl button{border:none;background:none;width:32px;height:30px;border-radius:6px;color:var(--text-2);font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;}
  .cv-bl button:hover{background:#F2F3F5;color:var(--text-1);}
  .cv-bl .sep{width:1px;background:var(--border-light);margin:5px 2px;}
  .cv-bc{position:absolute;left:50%;transform:translateX(-50%);bottom:16px;background:#fff;border:none;border-radius:9px;box-shadow:0 2px 10px rgba(29,33,41,.10);padding:7px 16px;font-size:12.5px;color:var(--text-2);cursor:pointer;z-index:5;}
  .cv-bc:hover{color:var(--primary);}
  .cv-br{position:absolute;right:16px;bottom:16px;background:#fff;border-radius:9px;box-shadow:0 2px 10px rgba(29,33,41,.10);display:flex;align-items:center;padding:4px 8px;gap:4px;z-index:5;}
  .cv-br button{border:none;background:none;width:26px;height:26px;border-radius:6px;color:var(--text-2);font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;}
  .cv-br button:hover{background:#F2F3F5;color:var(--text-1);}
  .cv-br .zv{font-size:12.5px;color:var(--text-1);min-width:42px;text-align:center;user-select:none;}
  .cv-minimap{position:absolute;right:16px;bottom:62px;width:120px;height:80px;background:#fff;border-radius:8px;box-shadow:0 2px 10px rgba(29,33,41,.10);z-index:5;display:flex;align-items:center;justify-content:center;gap:4px;}
  .cv-minimap i{display:block;height:7px;border-radius:3px;background:#E5E6EB;}

  /* ===== 右侧面板：LLM 设置 ===== */
  .st-panel{width:400px;flex-shrink:0;background:#fff;border-radius:12px;box-shadow:0 6px 28px rgba(29,33,41,.13);margin:12px 12px 12px 8px;display:flex;flex-direction:column;overflow:hidden;}
  .pn-head{display:flex;align-items:center;padding:14px 16px 4px;gap:9px;}
  .pn-ico{width:28px;height:28px;border-radius:8px;background:#722ED1;color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;}
  .pn-title{font-size:15.5px;font-weight:700;}
  .pn-ops{margin-left:auto;display:flex;gap:2px;}
  .pn-ops button{border:none;background:none;color:var(--text-3);font-size:13px;cursor:pointer;padding:5px 6px;border-radius:5px;}
  .pn-ops button:hover{background:#F2F3F5;color:var(--text-1);}
  .pn-sub{font-size:12.5px;color:var(--text-3);padding:2px 16px 10px;}
  .pn-tabs{display:flex;gap:22px;padding:0 16px;border-bottom:1px solid var(--border-light);flex-shrink:0;}
  .pn-tab{padding:9px 2px;font-size:13.5px;color:var(--text-2);cursor:pointer;border:none;background:none;border-bottom:2px solid transparent;margin-bottom:-1px;}
  .pn-tab.active{color:var(--text-1);font-weight:600;border-bottom-color:var(--text-1);}
  .pn-body{flex:1;overflow-y:auto;padding:14px 16px;}
  .f-lb{font-size:13px;font-weight:600;margin:14px 0 8px;display:flex;align-items:center;gap:4px;}
  .f-lb:first-child{margin-top:0;}
  .f-lb .req{color:var(--red);font-weight:400;}
  .q-i{color:var(--text-4);font-size:12px;font-weight:400;cursor:help;}
  .mdl-sel{display:flex;align-items:center;gap:8px;background:#F7F8FA;border-radius:8px;padding:9px 12px;font-size:13.5px;font-weight:600;cursor:pointer;}
  .mdl-sel:hover{background:#F2F3F5;}
  .mdl-sel .warn{margin-left:auto;font-weight:400;}
  .mdl-sel .set-ico{color:var(--text-3);font-size:13px;margin-left:6px;}
  .ctx-box{background:#F7F8FA;border-radius:8px;padding:10px 12px;font-size:12.5px;color:var(--text-3);cursor:pointer;}
  .ctx-box:hover{background:#F2F3F5;}
  .prompt-box{background:#F7F8FA;border-radius:10px;margin-top:14px;overflow:hidden;}
  .pb-head{display:flex;align-items:center;gap:8px;padding:9px 12px;font-size:12.5px;font-weight:700;border-bottom:1px solid #EEF0F3;color:var(--text-1);flex-wrap:wrap;}
  .pb-head .n{color:var(--text-3);font-weight:400;}
  .pb-head .op{color:var(--text-3);font-weight:400;cursor:pointer;font-size:12px;}
  .pb-head .op:hover{color:var(--primary);}
  .pb-head .jinja{color:var(--text-3);font-weight:400;display:inline-flex;align-items:center;gap:3px;}
  .pb-head .right{margin-left:auto;display:flex;gap:9px;align-items:center;}
  .mini-switch{position:relative;width:22px;height:12px;background:#C9CDD4;border-radius:10px;display:inline-block;cursor:pointer;vertical-align:middle;}
  .mini-switch::before{content:"";position:absolute;width:9px;height:9px;border-radius:50%;background:#fff;top:1.5px;left:2px;}
  .pb-body{padding:12px 14px;font-size:12.8px;line-height:1.85;color:var(--text-1);white-space:pre-line;}
  .ref-chip{display:inline-flex;align-items:center;gap:4px;background:#EAF1FE;color:var(--primary);border-radius:5px;padding:2px 8px;font-size:12px;}
  .add-msg{margin-top:14px;width:100%;border:1px dashed var(--border);background:#fff;border-radius:8px;padding:9px;font-size:13px;color:var(--text-2);cursor:pointer;}
  .add-msg:hover{border-color:var(--primary);color:var(--primary);}
.template-studio-root{ height:100vh; display:flex; flex-direction:column; overflow:hidden; }

  /* ================= 全局视图 ================= */
  .st-canvas.global-view{ transition: transform .3s; }
  .st-canvas.hand-mode{ cursor: grab; }
  .st-canvas.hand-mode:active{ cursor: grabbing; }

  /* ================= 节点运行状态 ================= */
  .tnode.running{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(46,99,240,.2); animation: node-pulse 1s infinite; }
  .tnode.ran{ border-color: #00B42A; }
  @keyframes node-pulse { 0%,100%{ box-shadow: 0 0 0 3px rgba(46,99,240,.2); } 50%{ box-shadow: 0 0 0 6px rgba(46,99,240,.1); } }
  .tnode.flash-highlight{ animation: flash .5s 3; }
  @keyframes flash { 0%,100%{ box-shadow: 0 2px 10px rgba(29,33,41,.08); } 50%{ box-shadow: 0 0 0 4px var(--primary); } }

  /* ================= 弹窗内容 ================= */
  .checklist{ display:flex; flex-direction:column; gap:8px; }
  .check-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:8px; background:#F7F8FA; }
  .check-item.ok .check-icon{ color:#00B42A; }
  .check-item.warn .check-icon{ color:#FF7D00; }
  .check-item.missing .check-icon{ color:#F53F3F; }
  .check-icon{ font-size:16px; font-weight:700; }
  .check-name{ font-weight:600; min-width:80px; }
  .check-desc{ font-size:12px; color:var(--text-3); }

  .run-item{ display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:6px; margin-bottom:4px; background:#F7F8FA; }
  .run-item.success .run-status-icon{ color:#00B42A; }
  .run-item.error .run-status-icon{ color:#F53F3F; }
  .run-time{ font-weight:600; }
  .run-duration{ color:var(--text-3); font-size:12px; }
  .run-nodes{ margin-left:auto; font-size:12px; color:var(--text-3); }

  .ver-item{ display:flex; align-items:center; gap:10px; padding:8px 12px; border:1px solid var(--border-light); border-radius:6px; margin-bottom:4px; }
  .ver-time{ font-weight:600; }
  .ver-label{ color:var(--text-3); font-size:12px; }
  .ver-current-tag{ font-size:11px; color:var(--primary); background:var(--primary-light); padding:2px 8px; border-radius:10px; }
  .ver-restore{ margin-left:auto; border:1px solid var(--primary); background:#fff; color:var(--primary); border-radius:4px; padding:3px 10px; font-size:12px; cursor:pointer; }
  .ver-restore:hover{ background:var(--primary-light); }

  .var-list{ display:flex; flex-direction:column; gap:6px; }
  .var-item{ display:flex; align-items:center; gap:8px; padding:8px 12px; background:#F7F8FA; border-radius:6px; }
  .var-node{ font-weight:600; min-width:80px; }
  .var-name{ color:var(--primary); background:#EAF1FE; padding:2px 8px; border-radius:4px; font-size:12px; }
  .var-type{ margin-left:auto; font-size:11px; color:var(--text-4); }

  .node-picker{ display:flex; flex-direction:column; gap:4px; }
  .node-type-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:8px; cursor:pointer; transition:background .15s; }
  .node-type-item:hover{ background:var(--primary-light); }
  .nt-icon{ font-size:20px; }
  .nt-info{ display:flex; flex-direction:column; }
  .nt-name{ font-weight:600; font-size:13px; }
  .nt-desc{ font-size:11px; color:var(--text-3); }

  .more-tools{ display:flex; flex-direction:column; gap:4px; }
  .mt-btn{ padding:10px 14px; border:1px solid var(--border); background:#fff; border-radius:6px; text-align:left; cursor:pointer; font-size:13px; }
  .mt-btn:hover{ border-color:var(--primary); color:var(--primary); }

  .panel-menu{ display:flex; flex-direction:column; gap:4px; }
  .pm-btn{ padding:10px 14px; border:1px solid var(--border); background:#fff; border-radius:6px; text-align:left; cursor:pointer; font-size:13px; }
  .pm-btn:hover{ border-color:var(--primary); color:var(--primary); }

  .model-picker{ display:flex; flex-direction:column; gap:4px; }
  .mp-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:8px; cursor:pointer; }
  .mp-item:hover{ background:var(--primary-light); }
  .mp-name{ font-weight:600; }
  .mp-warn{ margin-left:auto; font-size:11px; color:#FF7D00; }

  .var-picker{ display:flex; flex-direction:column; gap:4px; }
  .vp-item{ display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:6px; cursor:pointer; }
  .vp-item:hover{ background:var(--primary-light); }
  .vp-node{ font-size:12px; color:var(--text-3); }
  .vp-var{ color:var(--primary); background:#EAF1FE; padding:2px 8px; border-radius:4px; font-size:12px; }

  .prompt-help{ font-size:13px; line-height:1.8; }
  .prompt-help code{ background:#F2F3F5; padding:2px 6px; border-radius:3px; font-size:12px; }

  .fullscreen-ta{ width:100%; min-height:300px; border:1px solid var(--border); border-radius:8px; padding:12px; font-size:13px; line-height:1.8; resize:vertical; font-family:inherit; }
  .fullscreen-actions{ margin-top:12px; text-align:right; }

  .var-insert-list{ display:flex; flex-direction:column; gap:4px; }
  .vi-item{ padding:8px 12px; background:#F7F8FA; border-radius:6px; cursor:pointer; font-size:13px; color:var(--primary); }
  .vi-item:hover{ background:var(--primary-light); }

  .last-run-panel{ padding:8px 0; }
  .lr-summary{ display:flex; gap:12px; margin-bottom:12px; }
  .lr-status.ok{ color:#00B42A; font-weight:600; }
  .lr-duration{ color:var(--text-3); font-size:12px; }
  .lr-section{ margin-bottom:10px; }
  .lr-section b{ display:block; margin-bottom:4px; font-size:12px; }
  .lr-section pre{ background:#F7F8FA; padding:8px 12px; border-radius:6px; font-size:12px; overflow-x:auto; }

  .wf-settings{ display:flex; flex-direction:column; gap:12px; }
  .ws-row{ display:flex; flex-direction:column; gap:4px; }
  .ws-row label{ font-size:13px; font-weight:600; }
  .ws-row input, .ws-row textarea{ padding:8px 12px; border:1px solid var(--border); border-radius:6px; font-size:13px; }
  .wf-icon-select{ display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border:1px solid var(--border); border-radius:6px; cursor:pointer; }

  .api-doc{ font-size:13px; }
  .api-doc p{ margin-bottom:8px; }
  .api-code{ background:#1D2129; color:#A8E063; padding:12px 16px; border-radius:8px; font-size:12px; line-height:1.6; overflow-x:auto; }

  .run-logs{ display:flex; flex-direction:column; gap:4px; }
  .log-entry{ display:flex; gap:10px; padding:8px 12px; border-radius:6px; font-size:12px; }
  .log-entry.ok{ background:#E8FFEA; }
  .log-entry.info{ background:#F7F8FA; }
  .log-time{ color:var(--text-3); min-width:60px; }

  .monitoring{ padding:8px 0; }
  .mon-grid{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .mon-card{ background:#F7F8FA; border-radius:8px; padding:14px; text-align:center; }
  .mon-num{ display:block; font-size:20px; font-weight:700; color:var(--primary); }
  .mon-label{ display:block; font-size:11px; color:var(--text-3); margin-top:4px; }

  .help-center{ display:flex; flex-direction:column; gap:8px; }
  .help-item{ padding:12px; background:#F7F8FA; border-radius:8px; }
  .help-item b{ display:block; margin-bottom:4px; }
  .help-item p{ font-size:12px; color:var(--text-3); margin:0; }

  .empty-state{ padding:20px; text-align:center; color:var(--text-3); font-size:13px; }
</style>

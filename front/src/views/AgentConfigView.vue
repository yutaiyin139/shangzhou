<template>
  <div id="page-root" class="page-root agent-config-root">
    <div class="cf-shell">
      <!-- 左窄栏 -->
      <aside class="ad-side">
        <div class="ad-side-top">
          <button class="ad-back" title="返回" data-action="goBack()">‹</button>
          <span class="ad-home" title="首页" data-action="location.hash = '/home'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg></span>
          <span class="ad-crumb">/ AGENTS</span>
          <span class="sp">
            <button class="ad-icobtn" data-action="toast(&#x27;暂无新通知&#x27;)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2 2 0 0 0 4 0"/></svg></button>
            <button class="ad-icobtn" data-action="toggleSidePanel()" title="收起/展开侧边面板"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg></button>
          </span>
        </div>
    
        <div class="ad-agent">
          <span class="ava">🤖</span>
          <span class="nm" id="sideName">加载中…</span>
          <button class="more" data-action="openMoreMenu()" title="更多操作：复制、删除、导出">…</button>
        </div>
    
        <nav class="ad-menu">
          <div class="ad-mitem active"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg></span>配置</div>
          <div class="ad-mitem" data-action="navKeep('/agent-detail')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v18M3 12h18M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg></span>访问点</div>
          <div class="ad-mitem" data-action="navKeep('/agent-logs')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg></span>日志</div>
          <div class="ad-mitem" data-action="navKeep('/agent-monitor')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 19V10M10 19V5M16 19v-8"/><path d="M2 19h20"/></svg></span>监控</div>
        </nav>
    
        <div class="ad-user">
          <span class="u-ava">于</span>
          <span class="u-nm">于太印</span>
          <button class="u-help" data-action="openHelpCenter()" title="帮助中心"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.2a2.6 2.6 0 1 1 3.6 2.4c-.8.3-1.1.9-1.1 1.7"/><circle cx="12" cy="16.8" r=".6" fill="currentColor"/></svg></button>
        </div>
      </aside>
    
      <!-- 右侧：顶栏 + 中栏 + 右栏 -->
      <div class="cf-right">
        <div class="cf-topbar">
          <button class="back" data-action="goBack()">‹ 返回</button>
          <span class="nm" id="topName">加载中…</span>
          <span class="tag" id="statusTag">草稿</span>
          <div class="ops">
            <div class="dd-wrap">
              <button class="btn btn-primary" id="pubBtn">发布 ▾</button>
              <div class="dd-menu" id="pubMenu">
                <div class="dd-item" id="ddPublish">发布</div>
                <div class="dd-item" data-action="openPublishHistory()">发布记录</div>
              </div>
            </div>
          </div>
        </div>
    
        <div class="cf-cols">
          <!-- 中栏：配置 -->
          <div class="cf-mid">
            <div class="seg-row">
              <div class="seg" id="seg">
                <button class="active" data-v="build">构建</button>
                <button data-v="preview">预览</button>
              </div>
            </div>
    
            <div class="cf-scroll">
              <div class="cf-h">配置 <span class="mode-badge">⚠ 构建模式</span></div>
              <div class="mode-tip">你正在使用构建模式。在此模式下，Configure 只能由 Agent 更新。通过右侧聊天调整此配置，然后应用。</div>
    
              <!-- 模型 -->
              <div class="sec">
                <div class="sec-head"><span class="t">模型</span></div>
                <div class="model-wrap">
                  <div class="model-select" id="modelSel">
                    <span id="modelName">qwen3.7-max</span>
                    <span style="color:var(--text-3);font-size:12px;">▾</span>
                  </div>
                  <div class="model-menu" id="modelMenu"></div>
                </div>
              </div>
    
              <!-- 提示词 -->
              <div class="sec">
                <div class="sec-head"><span class="t">提示词</span><span class="q" data-action="showPromptHelp()" title="提示词用于定义 Agent 的角色、任务和输出要求">?</span></div>
                <div class="prompt-box">
                  <textarea id="promptTa" placeholder="在此编写指令…"></textarea>
                  <div class="prompt-tools">
                    <button class="tl" data-action="insertPromptVariable()" title="插入变量到提示词">/ 插入</button>
                  </div>
                </div>
              </div>
    
              <!-- SKILL -->
              <div class="sec">
                <div class="sec-head"><span class="t">SKILL</span><span class="q" data-action="toast(&#x27;Skill 为 Agent 提供专业能力，对话时自动注入使用说明&#x27;)">?</span>
                  <button class="add" data-action="openSkillPick()">＋ 添加</button></div>
                <div id="skillBox">
                  <div class="sec-empty"><div class="e1">暂无 Skill</div><div class="e2">点击「＋ 添加」为 Agent 绑定技能，对话时自动注入使用说明</div></div>
                </div>
              </div>
    
              <!-- 文件 -->
              <div class="sec">
                <div class="sec-head"><span class="t">文件</span><span class="q" data-action="showFileHelp()" title="上传 Agent 可读取的文档，如规格、模板或指南">?</span>
                  <button class="add" data-action="addMock(&#x27;fileBox&#x27;,&#x27;📄&#x27;,&#x27;产品说明书.pdf&#x27;,&#x27;文件&#x27;)">＋ 添加</button></div>
                <div id="fileBox">
                  <div class="sec-empty"><div class="e1">暂无文件</div><div class="e2">上传 Agent 可读取的文档，例如规格、模板或指南</div></div>
                </div>
              </div>
    
              <!-- 工具 -->
              <div class="sec">
                <div class="sec-head"><span class="t">工具</span><span class="q" data-action="showToolHelp()" title="工具让 Agent 可以执行操作，如搜索网页或调用应用">?</span>
                  <button class="add" data-action="addMock(&#x27;toolBox&#x27;,&#x27;🔧&#x27;,&#x27;网页搜索&#x27;,&#x27;工具&#x27;)">＋ 添加</button></div>
                <div id="toolBox">
                  <div class="sec-empty"><div class="e1">暂无工具</div><div class="e2">工具让 Agent 可以执行操作，例如搜索网页或调用你的应用</div></div>
                </div>
              </div>
    
              <!-- 知识检索 -->
              <div class="sec">
                <div class="sec-head"><span class="t">知识检索</span><span class="q" data-action="showKnowledgeHelp()" title="连接 Agent 回答时可搜索的知识库">?</span>
                  <button class="add" data-action="addMock(&#x27;kbBox&#x27;,&#x27;📚&#x27;,&#x27;产品知识库&#x27;,&#x27;知识&#x27;)">＋ 添加</button></div>
                <div id="kbBox">
                  <div class="sec-empty"><div class="e1">暂无知识</div><div class="e2">连接 Agent 回答时可搜索的知识库</div></div>
                </div>
              </div>
    
              <!-- 高级设置 -->
              <div class="cfg-section closed" id="advSec" style="border-bottom:none;">
                <div class="cfg-head" style="padding-left:0;padding-right:0;" data-action="document.getElementById(&#x27;advSec&#x27;).classList.toggle(&#x27;closed&#x27;)">
                  <span class="t">高级设置</span>
                  <span class="arrow">▾</span>
                </div>
                <div class="cfg-body adv-body" style="padding-left:0;padding-right:0;">
                  <div class="cfg-row">
                    <label>温度 <span id="tempVal" style="color:var(--text-3);">0.7</span></label>
                    <input type="range" id="tempRange" min="0" max="100" value="70" oninput="document.getElementById('tempVal').textContent=(this.value/100).toFixed(1)">
                  </div>
                  <div class="cfg-row">
                    <label>最大令牌数</label>
                    <input class="form-input" type="number" id="maxTokens" value="4096" style="width:140px;">
                  </div>
                  <div class="cfg-row">
                    <label>最大迭代次数</label>
                    <input class="form-input" type="number" id="maxIter" value="5" min="1" max="20" style="width:140px;">
                  </div>
                </div>
              </div>

              <!-- Agent 策略 -->
              <div class="cfg-section" id="strategySec">
                <div class="cfg-head" style="padding-left:0;padding-right:0;" data-action="document.getElementById(&#x27;strategySec&#x27;).classList.toggle(&#x27;closed&#x27;)">
                  <span class="t">⚡ Agent 策略</span>
                  <span class="arrow">▾</span>
                </div>
                <div class="cfg-body strategy-body" style="padding-left:0;padding-right:0;">
                  <div class="cfg-row">
                    <label>策略类型</label>
                    <select class="form-input" id="strategySel" style="width:100%;">
                      <option value="react">ReAct（推理+行动）</option>
                      <option value="function_call">Function Call（函数调用）</option>
                      <option value="plan_execute">Plan & Execute（规划+执行）</option>
                    </select>
                  </div>
                  <div class="strategy-desc" id="strategyDesc">Reasoning + Acting 循环，LLM 通过文本格式决定调用工具或直接回答</div>

                  <!-- 策略配置（动态显示） -->
                  <div class="strategy-options" id="strategyOptions" style="display:none;">
                    <div class="cfg-row" id="optOutputFormat" style="display:none;">
                      <label>输出格式</label>
                      <select class="form-input" id="outputFormatSel">
                        <option value="text">纯文本</option>
                        <option value="json">JSON</option>
                        <option value="markdown">Markdown</option>
                      </select>
                    </div>
                    <div class="cfg-row" id="optFallbackModel" style="display:none;">
                      <label>回退模型</label>
                      <input class="form-input" type="text" id="fallbackModel" placeholder="可选，如 gpt-4o-mini" style="width:100%;">
                    </div>
                  </div>

                  <!-- 配置版本历史 -->
                  <div class="cfg-revisions" id="cfgRevisions" style="display:none;">
                    <div class="cfg-rev-toolbar">
                      <span class="cfg-rev-title">配置版本</span>
                      <button class="btn btn-sm" id="revRefreshBtn" data-action="loadConfigRevisions()">刷新</button>
                    </div>
                    <div class="cfg-rev-list" id="revList">
                      <div class="cfg-rev-empty">暂无版本记录</div>
                    </div>
                  </div>
                  <button class="btn btn-sm mem-toggle-manage" id="toggleRevisions" data-action="toggleRevisions()">版本历史 ▾</button>
                </div>
              </div>

              <!-- 长期记忆 -->
              <div class="cfg-section" id="memSec">
                <div class="cfg-head" style="padding-left:0;padding-right:0;" data-action="document.getElementById(&#x27;memSec&#x27;).classList.toggle(&#x27;closed&#x27;)">
                  <span class="t">🧠 长期记忆</span>
                  <span class="arrow">▾</span>
                </div>
                <div class="cfg-body mem-body" style="padding-left:0;padding-right:0;">
                  <div class="cfg-row" style="justify-content:space-between;">
                    <label style="margin:0;">启用长期记忆</label>
                    <label class="switch">
                      <input type="checkbox" id="memEnabled" checked>
                      <span class="switch-slider"></span>
                    </label>
                  </div>
                  <div class="mem-desc">开启后，对话时自动检索历史记忆辅助回答，并将新对话自动写入记忆。</div>
                  <div class="mem-manage" id="memManage" style="display:none;">
                    <div class="mem-toolbar">
                      <span class="mem-count" id="memCount">0 条记忆</span>
                      <button class="btn btn-sm" id="memRefreshBtn" data-action="loadMemories()">刷新</button>
                      <button class="btn btn-sm btn-danger" id="memClearBtn" data-action="clearAllMemories()">清空</button>
                    </div>
                    <div class="mem-list" id="memList">
                      <div class="mem-empty">暂无记忆</div>
                    </div>
                  </div>
                  <button class="btn btn-sm mem-toggle-manage" id="memToggleManage" data-action="toggleMemManage()">管理记忆 ▾</button>
                </div>
              </div>
            </div>
    
            <div class="cf-footbar" id="draftBar" style="display:none;">
              <span class="st"><b>Build</b> <span class="tag" style="margin-left:4px;">草稿</span><span class="draft-info" data-action="showDraftChanges()" style="cursor:pointer;color:var(--primary);">1 项变更待应用 ›</span></span>
              <span class="draft-ops">
                <button class="btn" data-action="discardDraft()">放弃</button>
                <button class="btn btn-primary" data-action="applyDraft()">应用</button>
              </span>
            </div>
          </div>
    
          <!-- 右栏：通过对话构建 / 预览 -->
          <div class="cf-side" id="sideBuild">
            <div class="bd-body">
              <div class="bd-ico">🛠️</div>
              <div class="bd-title">通过对话构建 Agent</div>
              <div class="bd-sub">描述你的需求，它会随着对话填写左侧表单。</div>
              <div class="bd-msgs" id="bdMsgs">
                <div class="msg ai">告诉我你想要什么样的 Agent，我来帮你构建</div>
              </div>
            </div>
            <div class="bd-inputwrap">
              <div class="bd-inputbox">
                <input id="bdInput" placeholder="描述你的 Agent 应该做什么…">
                <button class="btn btn-primary btn-sm" data-action="sendBuild()">开始构建</button>
              </div>
            </div>
            <div class="bd-note">Agent 运行在 Linux 沙盒中。</div>
          </div>
    
          <div class="cf-side" id="sidePreview" style="display:none;">
            <div class="pv-body">
              <div class="pv-ico">🤖</div>
              <div style="font-size:15px;font-weight:600;color:var(--text-1);">预览</div>
              <div style="margin-top:8px;font-size:13px;color:var(--text-3);">在「构建」页签中通过对话构建 Agent，或点击下方按钮开始体验</div>
            <div class="pv-msgs" id="pvMsgs" style="margin-top:12px;"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 选择 Skill 弹窗（可选已安装的内置 Skill / 自定义 Skill） -->
    <div class="modal-mask" id="skillPickModal">
      <div class="modal" style="width:640px;">
        <div class="modal-head"><div class="modal-title">添加 Skill</div>
          <button class="modal-close" data-action="closeModal(&#x27;skillPickModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="pk-search"><input id="skillPickQ" placeholder="搜索 Skill"><button class="btn btn-primary btn-sm" id="skillPickOk">确认添加</button></div>
          <div class="pk-list" id="skillPickBox"></div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { onMounted, onUnmounted } from 'vue'

/* 顶栏下拉菜单的全局点击关闭（提升为顶层：离开页面时可移除监听器，避免泄漏报错） */
function onDocClick(){
  var mm = document.getElementById('modelMenu');
  if (mm) mm.classList.remove('show');
  var pm = document.getElementById('pubMenu');
  if (pm) pm.classList.remove('show');
}
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
  
  /* hash 路由下的 query 解析（?id= / ?from= 都在 hash 内） */
  function hashQuery(){
    var h = location.hash.split('?')[1] || '';
    return new URLSearchParams(h);
  }
  var params = hashQuery();
  var agentId = params.get('id');

  /* 来源返回：默认单智能体应用列表，?from=multi 时返回多智能体应用列表 */
  var BACK_URL = params.get('from') === 'multi' ? '/multi-agent' : '/single-agent';
  function goBack(){ location.hash = BACK_URL; }

  /* =============== 智能体加载与表单回填 =============== */
  var appliedConfig = null;  // 已应用（保存到后端）的配置
  var agentData = null;      // 当前智能体详情

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* 渲染条目列表（Skill/文件/工具/知识） */
  function renderItems(boxId, items, type){
    var box = document.getElementById(boxId);
    if (!items || !items.length){
      box.innerHTML = '<div class="sec-empty"><div class="e1">暂无' + type + '</div></div>';
      return;
    }
    box.innerHTML = items.map(function(it){
      return '<div class="sec-item"><span class="ic">' + (it.icon || '📄') + '</span>' + esc(it.name) +
        '<button class="rm" onclick="removeMock(this,\'' + boxId + '\',\'' + type + '\')">✕</button></div>';
    }).join('');
  }

  /* 渲染已绑定技能列表 */
  function renderBoundSkills(skills){
    var box = document.getElementById('skillBox');
    if (!skills || !skills.length){
      box.innerHTML = '<div class="sec-empty"><div class="e1">暂无 Skill</div><div class="e2">点击「＋ 添加」为 Agent 绑定技能，对话时自动注入使用说明</div></div>';
      return;
    }
    box.innerHTML = skills.map(function(s){
      return '<div class="sec-item bound-skill" data-key="' + esc(s.skill_key) + '">' +
        '<span class="ic">' + (s.skill_icon || '✨') + '</span>' +
        '<span class="skill-name">' + esc(s.skill_name || s.skill_key) + '</span>' +
        '<span class="skill-kind">' + (s.skill_kind === 'custom' ? '自定义' : '内置') + '</span>' +
        '<button class="rm" onclick="unbindSkill(\'' + esc(s.skill_key) + '\')" title="解除绑定">✕</button>' +
      '</div>';
    }).join('');
  }

  /* 从 DOM 收集条目列表 */
  function collectItems(boxId){
    return Array.prototype.map.call(document.querySelectorAll('#' + boxId + ' .sec-item'), function(el){
      var ic = el.querySelector('.ic');
      var nm = el.childNodes[1];
      return { icon: ic ? ic.textContent : '', name: nm ? nm.textContent.trim() : '' };
    });
  }

  /* 收集左侧表单全部配置 */
  function collectConfig(){
    var strategy = document.getElementById('strategySel');
    var maxIter = document.getElementById('maxIter');
    var outputFmt = document.getElementById('outputFormatSel');
    var fallbackModel = document.getElementById('fallbackModel');
    return {
      model: document.getElementById('modelName').textContent,
      prompt: document.getElementById('promptTa').value,
      temperature: parseInt(document.getElementById('tempRange').value, 10) / 100,
      max_tokens: parseInt(document.getElementById('maxTokens').value, 10) || 4096,
      skills: collectItems('skillBox'),
      tools: collectItems('toolBox'),
      files: collectItems('fileBox'),
      kbs: collectItems('kbBox'),
      memory_enabled: document.getElementById('memEnabled') ? document.getElementById('memEnabled').checked : true,
      strategy: strategy ? strategy.value : 'react',
      max_iterations: maxIter ? (parseInt(maxIter.value, 10) || 5) : 5,
      output_format: outputFmt ? outputFmt.value : 'text',
      fallback_model: fallbackModel ? fallbackModel.value : ''
    };
  }

  /* 用 LLM 生成的配置自动填充左侧表单（不覆盖名称，名称以 agents 表为准） */
  function fillConfig(cfg){
    cfg = cfg || {};
    if (cfg.model) document.getElementById('modelName').textContent = cfg.model;
    if (cfg.prompt) document.getElementById('promptTa').value = cfg.prompt;
    if (typeof cfg.temperature === 'number'){
      document.getElementById('tempRange').value = Math.round(cfg.temperature * 100);
      document.getElementById('tempVal').textContent = cfg.temperature.toFixed(1);
    }
    if (cfg.max_tokens) document.getElementById('maxTokens').value = cfg.max_tokens;
    renderItems('skillBox', cfg.skills, 'Skill');
    renderItems('toolBox', cfg.tools, '工具');
    renderItems('fileBox', cfg.files, '文件');
    renderItems('kbBox', cfg.kbs, '知识');
    /* 长期记忆开关 */
    var memEl = document.getElementById('memEnabled');
    if (memEl && typeof cfg.memory_enabled === 'boolean'){
      memEl.checked = cfg.memory_enabled;
    }
    /* Agent 策略回填 */
    if (cfg.strategy){
      var stratEl = document.getElementById('strategySel');
      if (stratEl) stratEl.value = cfg.strategy;
      updateStrategyDesc(cfg.strategy);
    }
    if (cfg.max_iterations){
      var maxIterEl = document.getElementById('maxIter');
      if (maxIterEl) maxIterEl.value = cfg.max_iterations;
    }
    if (cfg.output_format){
      var fmtEl = document.getElementById('outputFormatSel');
      if (fmtEl) fmtEl.value = cfg.output_format;
    }
    if (cfg.fallback_model){
      var fbEl = document.getElementById('fallbackModel');
      if (fbEl) fbEl.value = cfg.fallback_model;
    }
    /* 不覆盖名称：名称以 agents 表中的 name 字段为准，LLM 生成的 name 仅作参考 */
  }

  /* 加载智能体详情并回填已保存配置 */
  function loadAgent(){
    if (!agentId){
      toast('请从单智能体列表进入');
      return;
    }
    apiGet('/api/agents/' + agentId).then(function(data){
      if (data.code === 200){
        agentData = data.data;
        document.getElementById('topName').textContent = agentData.name;
        document.getElementById('sideName').textContent = agentData.name;
        setStatusTag(agentData.status);
        if (agentData.config && agentData.config.prompt){
          fillConfig(agentData.config);
          appliedConfig = agentData.config;
        }
      } else {
        toast(data.msg || '智能体加载失败');
      }
    });
  }

  function setStatusTag(status){
    var tag = document.getElementById('statusTag');
    if (status === 'published'){
      tag.textContent = '已发布';
      tag.classList.add('published');
      document.getElementById('pubBtn').innerHTML = '已发布 ▾';
      document.getElementById('pubBtn').classList.add('disabled');
    } else {
      tag.textContent = '草稿';
      tag.classList.remove('published');
    }
  }

  function markDirty(){
    document.getElementById('draftBar').style.display = '';
  }

  /* Build 草稿条：应用（保存配置到后端并发布）/ 放弃 */
  function applyDraft(){
    if (!agentId){
      toast('未找到智能体');
      return;
    }
    var cfg = collectConfig();
    var body = { config: JSON.stringify(cfg), status: 'published' };
    var nm = document.getElementById('topName').textContent;
    if (agentData && nm && nm !== agentData.name) body.name = nm;
    apiPut('/api/agents/' + agentId, body).then(function(data){
      if (data.code === 200){
        document.getElementById('draftBar').style.display = 'none';
        appliedConfig = cfg;
        setStatusTag('published');
        if (agentData) agentData.status = 'published';
        toast('已应用并发布，智能体已上线');
      } else {
        toast('发布失败：' + (data.msg || '未知错误'));
      }
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function discardDraft(){
    document.getElementById('draftBar').style.display = 'none';
    if (appliedConfig) fillConfig(appliedConfig);
    else if (agentData){
      document.getElementById('topName').textContent = agentData.name;
      document.getElementById('sideName').textContent = agentData.name;
      fillConfig({ prompt: '', skills: [], tools: [], files: [], kbs: [] });
      document.getElementById('tempRange').value = 70;
      document.getElementById('tempVal').textContent = '0.7';
    }
    toast('已放弃变更');
  }

  /* =============== 长期记忆管理 =============== */
  function toggleMemManage(){
    var el = document.getElementById('memManage');
    var btn = document.getElementById('memToggleManage');
    if (el && el.style.display === 'none'){
      el.style.display = '';
      btn.textContent = '管理记忆 ▴';
      loadMemories();
    } else if (el){
      el.style.display = 'none';
      btn.textContent = '管理记忆 ▾';
    }
  }

  function loadMemories(){
    if (!agentId) return;
    var list = document.getElementById('memList');
    var count = document.getElementById('memCount');
    list.innerHTML = '<div class="mem-empty">加载中…</div>';
    apiGet('/api/agents/' + agentId + '/memories', { params: { page_size: 50 } }).then(function(data){
      if (data.code === 200){
        var items = data.data.items || [];
        var total = data.data.total || 0;
        if (count) count.textContent = total + ' 条记忆';
        if (!items.length){
          list.innerHTML = '<div class="mem-empty">暂无记忆，对话后自动生成</div>';
          return;
        }
        list.innerHTML = items.map(function(m){
          var statusIcon = m.embedding_status === 'completed' ? '✅' : (m.embedding_status === 'failed' ? '⚠️' : '⏳');
          return '<div class="mem-item">' +
            '<div class="mem-item-text">' + esc(m.content) + '</div>' +
            '<div class="mem-item-meta">' +
              '<span class="mem-status">' + statusIcon + '</span>' +
              '<button class="mem-del-btn" onclick="deleteMemory(' + m.id + ')">✕</button>' +
            '</div>' +
          '</div>';
        }).join('');
      } else {
        list.innerHTML = '<div class="mem-empty">加载失败</div>';
      }
    }).catch(function(){
      list.innerHTML = '<div class="mem-empty">加载失败</div>';
    });
  }

  function deleteMemory(memId){
    if (!agentId || !memId) return;
    if (!confirm('确定删除这条记忆？')) return;
    apiDelete('/api/agents/' + agentId + '/memories/' + memId)
      .then(function(data){
        if (data.code === 200){
          toast('已删除');
          loadMemories();
        } else {
          toast(data.msg || '删除失败');
        }
      }).catch(function(){ toast('删除失败'); });
  }

  function clearAllMemories(){
    if (!agentId) return;
    if (!confirm('确定清空全部记忆？此操作不可恢复。')) return;
    apiDelete('/api/agents/' + agentId + '/memories')
      .then(function(data){
        if (data.code === 200){
          toast('已清空 ' + (data.data.deleted || 0) + ' 条记忆');
          loadMemories();
        } else {
          toast(data.msg || '清空失败');
        }
      }).catch(function(){ toast('清空失败'); });
  }
  
  /* 构建 / 预览 分段切换 */
  var segBtns = document.querySelectorAll('#seg button');
  segBtns.forEach(function(b){
    b.addEventListener('click', function(){
      segBtns.forEach(function(x){ x.classList.remove('active'); });
      b.classList.add('active');
      var isPreview = b.dataset.v === 'preview';
      document.getElementById('sideBuild').style.display = isPreview ? 'none' : '';
      document.getElementById('sidePreview').style.display = isPreview ? '' : 'none';
    });
  });
  
  /* 模型选择自定义下拉：读取 model_configs 表（/api/model-configs，仅启用中） */
  var MODELS = [];  // { name, provider }
  function loadModels(){
    apiGet('/api/model-configs').then(function(data){
      MODELS = (data.code === 200 ? (data.data || []) : []).filter(function(m){
        return m.status === 1;
      }).map(function(m){
        return { name: m.model_name, provider: m.provider || '' };
      });
      var cur = document.getElementById('modelName').textContent;
      /* 列表无当前已配置模型时：有已保存配置则保留显示，否则默认选第一个 */
      if (!MODELS.some(function(m){ return m.name === cur; })){
        if (!appliedConfig && MODELS.length) document.getElementById('modelName').textContent = MODELS[0].name;
      }
    }).catch(function(){ MODELS = []; });
  }
  var modelMenu = document.getElementById('modelMenu');
  function renderModelMenu(){
    var cur = document.getElementById('modelName').textContent;
    if (!MODELS.length){
      modelMenu.innerHTML = '<div class="model-opt none">暂无可用模型，请先到「模型」页面配置</div>';
      return;
    }
    modelMenu.innerHTML = MODELS.map(function(m){
      var on = m.name === cur;
      return '<div class="model-opt' + (on ? ' cur' : '') + '" data-m="' + esc(m.name) + '"><span class="mo-name">' + esc(m.name) + '</span><span class="mo-prov">' + esc(m.provider) + (on ? ' ✓' : '') + '</span></div>';
    }).join('');
    modelMenu.querySelectorAll('.model-opt').forEach(function(o){
      o.addEventListener('click', function(e){
        e.stopPropagation();
        document.getElementById('modelName').textContent = o.dataset.m;
        modelMenu.classList.remove('show');
        markDirty();
        toast('已切换模型：' + o.dataset.m);
      });
    });
  }
  document.getElementById('modelSel').addEventListener('click', function(e){
    e.stopPropagation();
    renderModelMenu();
    modelMenu.classList.toggle('show');
  });
  document.addEventListener('click', onDocClick);
  
  /* 添加 Skill / 文件 / 工具 / 知识（条目追加） */
  function addMock(boxId, ico, name, type){
    var items = collectItems(boxId);
    items.push({ icon: ico, name: name });
    renderItems(boxId, items, type);
    markDirty();
    toast('已添加：' + name);
  }
  function removeMock(btn, boxId, type){
    var item = btn.closest('.sec-item');
    if (item) item.remove();
    var box = document.getElementById(boxId);
    if (box && !box.querySelector('.sec-item')){
      box.innerHTML = '<div class="sec-empty"><div class="e1">暂无' + type + '</div></div>';
    }
    markDirty();
  }
  /* 内联 onclick 全局可调用 */
  window.removeMock = removeMock;

  /* =============== 技能选择（已安装的内置 Skill / 自定义 Skill） =============== */
  var skillCands = [];
  var boundSkills = [];  // 当前已绑定的技能

  function loadSkillCands(){
    return apiGet('/api/skills').then(function(d){
      skillCands = (d.code === 200) ? (d.data || []).filter(function(s){ return s.installed; }) : [];
    }).catch(function(){ skillCands = []; });
  }

  function loadBoundSkills(){
    if (!agentId) return;
    return apiGet('/api/agents/' + agentId + '/skills').then(function(d){
      if (d.code === 200){
        boundSkills = d.data || [];
        renderBoundSkills(boundSkills);
      }
    }).catch(function(){ boundSkills = []; });
  }

  function renderSkillPick(){
    var q = document.getElementById('skillPickQ').value.trim().toLowerCase();
    var box = document.getElementById('skillPickBox');
    var list = skillCands.filter(function(s){
      return !q || (s.name || '').toLowerCase().indexOf(q) > -1 || (s.key || '').toLowerCase().indexOf(q) > -1;
    });
    if (!list.length){
      box.innerHTML = '<div class="pk-empty">暂无可用 Skill，请先到「Skills 广场」安装</div>';
      return;
    }
    var boundKeys = boundSkills.map(function(s){ return s.skill_key; });
    box.innerHTML = list.map(function(s){
      var on = boundKeys.indexOf(s.key) > -1;
      return '<label class="pk-item' + (on ? ' on' : '') + '"><input type="checkbox" data-key="' + esc(s.key) + '" data-name="' + esc(s.name) + '" data-icon="' + esc(s.icon || '✨') + '" data-kind="' + esc(s.kind || 'builtin') + '"' + (on ? ' checked' : '') + '> <span class="pk-ico">' + (s.icon || '✨') + '</span> <span class="pk-name">' + esc(s.name) + '</span> <span class="pk-src">' + (s.kind === 'custom' ? '自定义' : '内置') + '</span></label>';
    }).join('');
  }

  function openSkillPick(){
    document.getElementById('skillPickBox').innerHTML = '<div class="pk-empty">加载中…</div>';
    openModal('skillPickModal');
    loadSkillCands().then(function(){
      // 先加载已绑定技能，确保弹窗中正确显示勾选状态
      loadBoundSkills().then(renderSkillPick);
    });
  }

  document.getElementById('skillPickQ').addEventListener('input', renderSkillPick);
  document.getElementById('skillPickOk').addEventListener('click', function(){
    var checked = document.querySelectorAll('#skillPickBox input:checked');
    var toBind = Array.prototype.map.call(checked, function(cb){
      return {
        skill_key: cb.dataset.key,
        skill_name: cb.dataset.name,
        skill_icon: cb.dataset.icon,
        skill_kind: cb.dataset.kind
      };
    });
    // 找出需要解绑的技能
    var toBindKeys = toBind.map(function(s){ return s.skill_key; });
    var toUnbind = boundSkills.filter(function(s){ return toBindKeys.indexOf(s.skill_key) === -1; });

    // 执行绑定/解绑
    var promises = [];
    toBind.forEach(function(s){
      // 检查是否已绑定
      if (!boundSkills.some(function(b){ return b.skill_key === s.skill_key; })){
        promises.push(
          apiPost('/api/agents/' + agentId + '/skills', s)
        );
      }
    });
    toUnbind.forEach(function(s){
      promises.push(
        apiDelete('/api/agents/' + agentId + '/skills/' + encodeURIComponent(s.skill_key))
      );
    });

    Promise.all(promises).then(function(){
      closeModal('skillPickModal');
      loadBoundSkills();
      markDirty();
      toast('已更新 Skill 绑定');
    }).catch(function(){
      toast('操作失败，请重试');
    });
  });
  window.openSkillPick = openSkillPick;

  /* 解除技能绑定 */
  function unbindSkill(skillKey){
    if (!agentId || !skillKey) return;
    if (!confirm('确定解除该技能绑定？')) return;
    apiDelete('/api/agents/' + agentId + '/skills/' + encodeURIComponent(skillKey)).then(function(data){
      if (data.code === 200){
        toast('已解除绑定');
        loadBoundSkills();
        markDirty();
      } else {
        toast(data.msg || '解除失败');
      }
    }).catch(function(){ toast('操作失败'); });
  }
  window.unbindSkill = unbindSkill;
  
  /* 发布下拉：发布后状态生效并可跳转对话 */
  var pubMenu = document.getElementById('pubMenu');
  document.getElementById('pubBtn').addEventListener('click', function(e){
    if (this.classList.contains('disabled')){ toast('该智能体已发布'); return; }
    e.stopPropagation();
    pubMenu.classList.toggle('show');
  });
  document.getElementById('ddPublish').addEventListener('click', function(){
    pubMenu.classList.remove('show');
    if (!agentId){ toast('未找到智能体'); return; }
    if (!appliedConfig){
      toast('请先在底部点击「应用」保存配置，再发布');
      return;
    }
    apiPut('/api/agents/' + agentId, { status: 'published' }).then(function(data){
      if (data.code === 200){
        setStatusTag('published');
        toast('发布成功，智能体已上线');
        var nm = encodeURIComponent(document.getElementById('topName').textContent);
        setTimeout(function(){ location.hash = '/agent-chat?id=' + agentId + '&name=' + nm; }, 900);
      } else {
        toast('发布失败：' + (data.msg || '未知错误'));
      }
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  });
  
  /* 通过对话构建：一句话需求 → LLM 生成配置 → 自动填充左侧表单 */
  function sendBuild(){
    var input = document.getElementById('bdInput');
    var v = input.value.trim();
    if (!v){ toast('请先描述你的 Agent'); input.focus(); return; }
    var msgs = document.getElementById('bdMsgs');
    var u = document.createElement('div');
    u.className = 'msg user';
    u.textContent = v;
    msgs.appendChild(u);
    input.value = '';
    var a = document.createElement('div');
    a.className = 'msg ai';
    a.textContent = '正在根据你的描述生成配置…';
    msgs.appendChild(a);
    msgs.scrollTop = msgs.scrollHeight;
    apiPost('/api/agent/build', { requirement: v }).then(function(data){
      if (data.code === 200 && data.data){
        fillConfig(data.data);
        markDirty();
        a.textContent = '已根据你的描述完成左侧配置（模型、提示词、技能、工具等），请点击底部「应用」保存，然后即可「发布」。';
      } else {
        a.textContent = '构建失败：' + (data.msg || '未知错误') + '，请重试或调整描述。';
      }
      msgs.scrollTop = msgs.scrollHeight;
    }).catch(function(){
      a.textContent = '网络异常，构建失败，请稍后重试。';
      msgs.scrollTop = msgs.scrollHeight;
    });
  }
  document.getElementById('bdInput').addEventListener('keydown', function(e){
    if (e.key === 'Enter') sendBuild();
  });

  /* 提示词输入 → 标记变更 */
  document.getElementById('promptTa').addEventListener('input', markDirty);
  document.getElementById('maxTokens').addEventListener('input', markDirty);

  /* =============== Agent 策略管理 =============== */
  var STRATEGY_DESCS = {
    'react': 'Reasoning + Acting 循环，LLM 通过文本格式决定调用工具或直接回答',
    'function_call': '使用 OpenAI tools 协议，LLM 原生函数调用能力，适合支持工具调用的模型',
    'plan_execute': '先规划完整步骤，再逐步执行，适合复杂多步任务'
  };

  function updateStrategyDesc(strategy){
    var descEl = document.getElementById('strategyDesc');
    if (descEl && STRATEGY_DESCS[strategy]){
      descEl.textContent = STRATEGY_DESCS[strategy];
    }
    // 显示/隐藏策略特定配置
    var opts = document.getElementById('strategyOptions');
    if (opts){
      opts.style.display = strategy === 'react' ? 'none' : '';
    }
  }

  var strategySel = document.getElementById('strategySel');
  if (strategySel){
    strategySel.addEventListener('change', function(){
      updateStrategyDesc(this.value);
      markDirty();
    });
  }

  /* =============== 配置版本管理 =============== */
  function toggleRevisions(){
    var el = document.getElementById('cfgRevisions');
    var btn = document.getElementById('toggleRevisions');
    if (el && el.style.display === 'none'){
      el.style.display = '';
      btn.textContent = '版本历史 ▴';
      loadConfigRevisions();
    } else if (el){
      el.style.display = 'none';
      btn.textContent = '版本历史 ▾';
    }
  }
  window.toggleRevisions = toggleRevisions;

  function loadConfigRevisions(){
    if (!agentId) return;
    var list = document.getElementById('revList');
    list.innerHTML = '<div class="cfg-rev-empty">加载中…</div>';
    apiGet('/api/agents/' + agentId + '/config-revisions').then(function(data){
      if (data.code === 200){
        var items = data.data || [];
        if (!items.length){
          list.innerHTML = '<div class="cfg-rev-empty">暂无版本记录</div>';
          return;
        }
        list.innerHTML = items.map(function(rev){
          var cfg = rev.config || {};
          var strategyLabel = cfg.strategy || rev.strategy || 'react';
          var summary = (cfg.prompt || '').substring(0, 40) || '配置快照';
          return '<div class="cfg-rev-item" data-id="' + rev.id + '">' +
            '<div class="cfg-rev-info">' +
              '<span class="cfg-rev-time">' + (rev.created_at || '') + '</span>' +
              '<span class="cfg-rev-strategy">' + esc(strategyLabel) + '</span>' +
            '</div>' +
            '<div class="cfg-rev-summary">' + esc(summary) + '</div>' +
            '<button class="cfg-rev-rollback" onclick="rollbackRevision(' + rev.id + ')">回滚到此版本</button>' +
          '</div>';
        }).join('');
      } else {
        list.innerHTML = '<div class="cfg-rev-empty">加载失败</div>';
      }
    }).catch(function(){
      list.innerHTML = '<div class="cfg-rev-empty">加载失败</div>';
    });
  }

  function rollbackRevision(revId){
    if (!agentId || !revId) return;
    if (!confirm('确定回滚到此版本？当前配置将被覆盖。')) return;
    apiPost('/api/agents/' + agentId + '/config-revisions/' + revId + '/rollback').then(function(data){
      if (data.code === 200){
        toast('已回滚到指定版本');
        // 重新加载配置
        if (data.data) fillConfig(data.data);
        loadAgent();
        loadConfigRevisions();
      } else {
        toast(data.msg || '回滚失败');
      }
    }).catch(function(){ toast('回滚失败'); });
  }
  window.rollbackRevision = rollbackRevision;

  /* ================= P2 占位功能实现 ================= */

  /* 收起/展开侧边面板 */
  function toggleSidePanel(){
    var side = document.querySelector('.ad-side');
    var right = document.querySelector('.cf-right');
    if (side.style.display === 'none'){
      side.style.display = '';
      if (right) right.style.flex = '';
      toast('已展开侧边面板');
    } else {
      side.style.display = 'none';
      if (right) right.style.flex = '1';
      toast('已收起侧边面板');
    }
  }
  window.toggleSidePanel = toggleSidePanel;

  /* 更多操作菜单 */
  function openMoreMenu(){
    var name = document.getElementById('topName').textContent;
    openModal('更多操作',
      '<div class="more-menu">' +
        '<button class="mm-btn" onclick="duplicateAgent()"><span class="mm-ico">📑</span>复制智能体</button>' +
        '<button class="mm-btn" onclick="exportConfig()"><span class="mm-ico">📤</span>导出配置</button>' +
        '<button class="mm-btn" onclick="resetAgent()"><span class="mm-ico">🔄</span>重置配置</button>' +
        '<button class="mm-btn danger" onclick="deleteAgent()"><span class="mm-ico">🗑</span>删除智能体</button>' +
      '</div>'
    );
  }
  function duplicateAgent(){ closeModal(); toast('智能体已复制：' + document.getElementById('topName').textContent + ' 副本'); }
  function exportConfig(){
    var cfg = collectConfig();
    var blob = new Blob([JSON.stringify(cfg, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = document.getElementById('topName').textContent + '_config.json';
    a.click();
    URL.revokeObjectURL(url);
    closeModal();
    toast('配置已导出');
  }
  function resetAgent(){
    closeModal();
    if (confirm('确定重置所有配置？')){
      document.getElementById('promptTa').value = '';
      renderItems('skillBox', [], 'Skill');
      renderItems('toolBox', [], '工具');
      renderItems('fileBox', [], '文件');
      renderItems('kbBox', [], '知识');
      markDirty();
      toast('配置已重置');
    }
  }
  function deleteAgent(){
    closeModal();
    if (confirm('确定删除此智能体？此操作不可恢复。')){
      if (agentId){
        apiDelete('/api/agents/' + agentId).then(function(data){
          if (data.code === 200){ location.hash = '/single-agent'; toast('已删除'); }
          else { toast('删除失败'); }
        }).catch(function(){ toast('删除失败'); });
      } else {
        location.hash = '/single-agent';
      }
    }
  }
  window.openMoreMenu = openMoreMenu;

  /* 帮助中心 */
  function openHelpCenter(){
    openModal('帮助中心',
      '<div class="help-list">' +
        '<div class="help-item"><b>📖 智能体配置入门</b><p>了解如何配置模型、提示词和技能</p></div>' +
        '<div class="help-item"><b>🧠 模型选择指南</b><p>不同模型的特点和适用场景</p></div>' +
        '<div class="help-item"><b>✨ 技能绑定说明</b><p>如何为 Agent 绑定内置或自定义技能</p></div>' +
        '<div class="help-item"><b>📚 知识库连接</b><p>连接知识库让 Agent 回答更准确</p></div>' +
        '<div class="help-item"><b>🔧 工具使用指南</b><p>配置工具让 Agent 能执行操作</p></div>' +
        '<div class="help-item"><b>💾 版本管理</b><p>查看和回滚配置历史版本</p></div>' +
      '</div>'
    );
  }
  window.openHelpCenter = openHelpCenter;

  /* 发布记录 */
  function openPublishHistory(){
    var history = [
      { time: '2024-01-15 14:30', version: 'v3', status: 'published' },
      { time: '2024-01-14 10:20', version: 'v2', status: 'published' },
      { time: '2024-01-10 09:00', version: 'v1', status: 'published' }
    ];
    var html = '<div class="pub-history">' + history.map(function(h){
      return '<div class="ph-item">' +
        '<span class="ph-version">' + h.version + '</span>' +
        '<span class="ph-time">' + h.time + '</span>' +
        '<span class="ph-status">已发布</span>' +
      '</div>';
    }).join('') + '</div>';
    openModal('发布记录', html);
  }
  window.openPublishHistory = openPublishHistory;

  /* 提示词帮助 */
  function showPromptHelp(){
    openModal('提示词说明',
      '<div class="help-content">' +
        '<p><b>提示词</b> 用于定义 Agent 的角色、任务和输出要求。</p>' +
        '<p>一个好的提示词应包含：</p>' +
        '<ul>' +
          '<li><b>角色定义</b>：AI 是谁，有什么背景</li>' +
          '<li><b>任务描述</b>：需要完成什么工作</li>' +
          '<li><b>输出格式</b>：期望的输出结构</li>' +
          '<li><b>约束条件</b>：不要做什么</li>' +
        '</ul>' +
      '</div>'
    );
  }
  window.showPromptHelp = showPromptHelp;

  /* 插入变量 */
  function insertPromptVariable(){
    var vars = ['用户输入', '当前时间', '会话ID', '用户名称'];
    openModal('插入变量',
      '<div class="var-insert">' +
        '<p>选择要插入的变量：</p>' +
        vars.map(function(v, i){
          return '<button class="var-btn" onclick="doInsertVar(\'{{' + v + '}}\')">' + v + '</button>';
        }).join('') +
      '</div>'
    );
  }
  function doInsertVar(v){
    var ta = document.getElementById('promptTa');
    ta.value += (ta.value ? '\n' : '') + v;
    closeModal();
    toast('已插入变量');
  }
  window.insertPromptVariable = insertPromptVariable;

  /* 文件说明 */
  function showFileHelp(){
    openModal('文件说明',
      '<div class="help-content">' +
        '<p>上传 Agent 可读取的文档，如产品规格、模板或指南。</p>' +
        '<p>支持格式：PDF、Word、Markdown、TXT</p>' +
      '</div>'
    );
  }
  window.showFileHelp = showFileHelp;

  /* 工具说明 */
  function showToolHelp(){
    openModal('工具说明',
      '<div class="help-content">' +
        '<p>工具让 Agent 可以执行操作，例如：</p>' +
        '<ul>' +
          '<li>网页搜索</li>' +
          '<li>数据库查询</li>' +
          '<li>API 调用</li>' +
          '<li>代码执行</li>' +
        '</ul>' +
      '</div>'
    );
  }
  window.showToolHelp = showToolHelp;

  /* 知识检索说明 */
  function showKnowledgeHelp(){
    openModal('知识检索说明',
      '<div class="help-content">' +
        '<p>连接 Agent 回答时可搜索的知识库。</p>' +
        '<p>对话时，系统会自动从知识库检索相关内容作为参考。</p>' +
      '</div>'
    );
  }
  window.showKnowledgeHelp = showKnowledgeHelp;

  /* 查看变更详情 */
  function showDraftChanges(){
    var cfg = collectConfig();
    openModal('变更详情',
      '<div class="draft-changes">' +
        '<div class="dc-item"><span class="dc-key">模型</span><span class="dc-val">' + esc(cfg.model) + '</span></div>' +
        '<div class="dc-item"><span class="dc-key">提示词长度</span><span class="dc-val">' + cfg.prompt.length + ' 字符</span></div>' +
        '<div class="dc-item"><span class="dc-key">Temperature</span><span class="dc-val">' + cfg.temperature + '</span></div>' +
        '<div class="dc-item"><span class="dc-key">Max Tokens</span><span class="dc-val">' + cfg.max_tokens + '</span></div>' +
        '<div class="dc-item"><span class="dc-key">Skill</span><span class="dc-val">' + cfg.skills.length + ' 个</span></div>' +
        '<div class="dc-item"><span class="dc-key">工具</span><span class="dc-val">' + cfg.tools.length + ' 个</span></div>' +
        '<div class="dc-item"><span class="dc-key">文件</span><span class="dc-val">' + cfg.files.length + ' 个</span></div>' +
        '<div class="dc-item"><span class="dc-key">知识库</span><span class="dc-val">' + cfg.kbs.length + ' 个</span></div>' +
      '</div>'
    );
  }
  window.showDraftChanges = showDraftChanges;

  /* 初始加载：拉取智能体详情、可选模型列表、已绑定技能 */
  loadAgent();
  loadModels();
  loadBoundSkills();
})

onUnmounted(function(){
  /* 组件卸载时移除全局监听器，防止在其他页面点击时反复报错 */
  document.removeEventListener('click', onDocClick);
});
</script>
<style>
.agent-config-root{ background:#fff; }
  .cf-shell{ display:flex; height:100vh; overflow:hidden; background:#fff; }

  /* ---------- 左窄栏（结构同 agent-detail.html） ---------- */
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
  .ad-agent{ display:flex; align-items:center; gap:10px; margin:10px 14px 6px; padding:6px 4px; }
  .ad-agent .ava{ width:38px; height:38px; border-radius:50%; background:var(--primary-light); display:flex; align-items:center; justify-content:center; font-size:21px; flex-shrink:0; }
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

  /* ---------- 右侧整体 ---------- */
  .cf-right{ flex:1; display:flex; flex-direction:column; min-width:0; }

  /* 顶栏（横跨中右栏） */
  .cf-topbar{ height:52px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; padding:0 16px; gap:10px; flex-shrink:0; background:#fff; }
  .cf-topbar .back{ display:inline-flex; align-items:center; gap:4px; border:none; background:none; font-size:14px; color:var(--text-1); cursor:pointer; padding:5px 8px; border-radius:6px; }
  .cf-topbar .back:hover{ background:#F2F3F5; }
  .cf-topbar .nm{ font-size:15px; font-weight:600; }
  .cf-topbar .ops{ margin-left:auto; display:flex; align-items:center; gap:10px; }

  .cf-cols{ flex:1; display:flex; overflow:hidden; }

  /* ---------- 中栏 ---------- */
  .cf-mid{ width:420px; border-right:1px solid var(--border-light); display:flex; flex-direction:column; flex-shrink:0; background:#fff; }
  .seg-row{ padding:12px 18px 0; flex-shrink:0; }
  .seg{ display:inline-flex; background:#F2F3F5; border-radius:8px; padding:3px; gap:2px; }
  .seg button{ border:none; background:transparent; padding:5px 18px; border-radius:6px; font-size:13px; color:var(--text-2); cursor:pointer; }
  .seg button.active{ background:#fff; color:var(--primary); font-weight:500; box-shadow:0 1px 4px rgba(29,33,41,.1); }

  .cf-scroll{ flex:1; overflow-y:auto; padding:16px 18px 24px; }
  .cf-h{ font-size:16px; font-weight:600; margin-bottom:14px; }
  .sec{ border-bottom:1px solid var(--border-light); padding:16px 0; }
  .sec:last-child{ border-bottom:none; }
  .sec-head{ display:flex; align-items:center; gap:6px; margin-bottom:12px; }
  .sec-head .t{ font-size:14px; font-weight:600; }
  .sec-head .q{ color:var(--text-3); font-size:12px; cursor:pointer; }
  .sec-head .add{ margin-left:auto; border:none; background:none; color:var(--text-1); font-size:13px; cursor:pointer; padding:4px 6px; border-radius:6px; }
  .sec-head .add:hover{ color:var(--primary); background:var(--primary-light); }
  .sec-empty{ background:#F7F8FA; border-radius:8px; padding:14px 16px; }
  .sec-empty .e1{ font-size:13px; color:var(--text-1); }
  .sec-empty .e2{ font-size:12px; color:var(--text-3); margin-top:4px; }
  .sec-item{ display:flex; align-items:center; gap:10px; border:1px solid var(--border-light); border-radius:8px; padding:10px 12px; font-size:13px; }
  .sec-item .ic{ width:28px; height:28px; border-radius:6px; background:var(--primary-light); display:inline-flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
  .sec-item .rm{ margin-left:auto; border:none; background:none; color:var(--text-3); cursor:pointer; }
  .sec-item .rm:hover{ color:var(--red); }

  .model-wrap{ position:relative; }
  .model-menu{ position:absolute; top:calc(100% + 6px); left:0; right:0; background:#fff; border:1px solid var(--border-light); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); padding:6px; display:none; z-index:30; }
  .model-menu.show{ display:block; }
  .model-opt{ display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:6px; font-size:13px; cursor:pointer; }
  .model-opt:hover{ background:#F2F3F5; }
  .model-opt.cur{ color:var(--primary); font-weight:500; }
  .model-opt .mo-name{ color:inherit; }
  .model-opt .mo-prov{ margin-left:auto; font-size:11px; color:var(--text-3); }
  .model-opt.cur .mo-prov{ color:var(--primary); }
  .model-opt.none{ color:var(--text-3); cursor:default; }
  .model-opt.none:hover{ background:transparent; }

  .prompt-box{ border:1px solid var(--border); border-radius:8px; overflow:hidden; }
  .prompt-box:focus-within{ border-color:var(--primary); box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  .prompt-box textarea{ width:100%; border:none; min-height:150px; padding:12px 14px; resize:vertical; line-height:1.7; font-size:14px; background:#F7F8FA; }
  .prompt-tools{ display:flex; align-items:center; gap:12px; padding:7px 12px; border-top:1px solid var(--border-light); background:#fff; }
  .prompt-tools .tl{ border:none; background:none; color:var(--text-2); font-size:13px; cursor:pointer; padding:2px 4px; border-radius:4px; }
  .prompt-tools .tl:hover{ color:var(--primary); }

  .adv-body .cfg-row label{ display:flex; justify-content:space-between; }
  .adv-body input[type=range]{ width:100%; accent-color:var(--primary); }

  /* 中栏底部固定条 */
  .cf-footbar{ border-top:1px solid var(--border-light); padding:10px 18px; display:flex; align-items:center; gap:8px; flex-shrink:0; background:#fff; }
  .mode-badge{ display:inline-block; background:#FFF6E5; color:#C07A00; border:1px solid #F5DFAE; font-size:12px; font-weight:500; border-radius:6px; padding:2px 8px; margin-left:8px; vertical-align:2px; }
  .mode-tip{ font-size:13px; color:var(--text-2); line-height:1.6; margin:8px 0 4px; }
  .cf-footbar .st{ display:flex; align-items:center; font-size:13px; }
  .draft-info{ margin-left:10px; color:var(--text-3); cursor:pointer; }
  .draft-info:hover{ color:var(--primary); }
  .draft-ops{ margin-left:auto; display:flex; gap:8px; }
  .cf-footbar .st{ font-size:12px; color:var(--text-3); display:flex; align-items:center; gap:6px; }
  .cf-footbar .st .dot{ width:7px; height:7px; border-radius:50%; background:var(--green); display:inline-block; }
  .cf-footbar .pub{ margin-left:auto; border:none; background:#F2F3F5; color:var(--text-3); border-radius:6px; padding:6px 16px; font-size:13px; cursor:pointer; }
  .cf-footbar .pub:hover{ color:var(--primary); }

  /* ---------- 右栏：通过对话构建 ---------- */
  .cf-side{ flex:1; background:#F7F9FC; display:flex; flex-direction:column; min-width:0; }
  .bd-body{ flex:1; overflow-y:auto; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:30px 40px; }
  .bd-ico{ width:52px; height:52px; border-radius:14px; background:var(--primary-light); display:flex; align-items:center; justify-content:center; font-size:26px; margin-bottom:16px; }
  .bd-title{ font-size:16px; font-weight:600; }
  .bd-sub{ font-size:13px; color:var(--text-2); margin-top:8px; }
  .bd-msgs{ width:min(560px,100%); margin-top:22px; display:flex; flex-direction:column; gap:12px; }
  .msg{ max-width:85%; padding:10px 14px; border-radius:10px; font-size:13px; line-height:1.7; }
  .msg.ai{ background:#fff; border:1px solid var(--border-light); align-self:flex-start; }
  .msg.user{ background:var(--primary); color:#fff; align-self:flex-end; }
  .bd-inputwrap{ padding:0 40px 8px; width:100%; }
  .bd-inputbox{ width:min(640px,100%); margin:0 auto; background:#fff; border:1px solid var(--border); border-radius:12px; padding:10px 12px 10px 16px; display:flex; align-items:center; gap:10px; box-shadow:0 2px 10px rgba(29,33,41,.05); }
  .bd-inputbox input{ flex:1; border:none; font-size:14px; }
  .bd-note{ text-align:center; font-size:12px; color:var(--text-3); padding-bottom:16px; }

  /* 预览模式占位 */
  .pv-body{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; color:var(--text-3); padding:30px; }
  .pv-ico{ width:64px; height:64px; border-radius:18px; background:linear-gradient(135deg,#8AB4FF,#2E63F0); display:flex; align-items:center; justify-content:center; font-size:30px; margin-bottom:16px; }

  /* 下拉（顶栏发布） */
  .dd-wrap{ position:relative; }  .dd-menu{ position:absolute; top:calc(100% + 6px); right:0; background:#fff; border:1px solid var(--border-light); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); min-width:140px; padding:6px; display:none; z-index:40; }
  .dd-menu.show{ display:block; }
  .dd-item{ padding:8px 12px; border-radius:6px; font-size:13px; cursor:pointer; color:var(--text-1); white-space:nowrap; }
  .dd-item:hover{ background:#F2F3F5; color:var(--primary); }
  #statusTag.published{ background:var(--green-bg); color:var(--green); }
  #pubBtn.disabled{ opacity:.6; cursor:not-allowed; }

  /* 选择 Skill 弹窗 */
  .pk-search{ display:flex; align-items:center; gap:10px; }
  .pk-search input{ flex:1; border:1px solid var(--border); border-radius:6px; padding:8px 12px; font-size:13px; outline:none; background:#fff; }
  .pk-search input:focus{ border-color:var(--primary); }
  .pk-list{ display:flex; flex-direction:column; gap:8px; margin-top:14px; max-height:340px; overflow-y:auto; }
  .pk-item{ display:flex; align-items:center; gap:10px; border:1px solid var(--border-light); border-radius:8px; padding:10px 12px; cursor:pointer; font-size:13px; transition:border-color .12s; }
  .pk-item:hover{ border-color:var(--primary); }
  .pk-item.on{ border-color:var(--primary); background:var(--primary-light); }
  .pk-item input{ accent-color:var(--primary); }
  .pk-ico{ width:30px; height:30px; border-radius:6px; background:#F2F3F5; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .pk-name{ font-weight:500; color:var(--text-1); }
  .pk-src{ margin-left:auto; font-size:12px; color:var(--text-3); }
  .pk-empty{ text-align:center; color:var(--text-3); font-size:13px; padding:40px 0; }
  .bound-skill .skill-name{ flex:1; }
  .bound-skill .skill-kind{ font-size:11px; color:var(--text-3); background:#F2F3F5; padding:2px 6px; border-radius:4px; }
.agent-config-root{ min-height:100vh; }

/* ---------- 长期记忆 ---------- */
.mem-desc{ font-size:12px; color:var(--text-3); margin:8px 0; line-height:1.5; }
.switch{ position:relative; display:inline-block; width:40px; height:22px; flex-shrink:0; }
.switch input{ opacity:0; width:0; height:0; }
.switch-slider{ position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background:#ccc; border-radius:22px; transition:.2s; }
.switch-slider:before{ position:absolute; content:""; height:16px; width:16px; left:3px; bottom:3px; background:#fff; border-radius:50%; transition:.2s; }
.switch input:checked + .switch-slider{ background:var(--primary); }
.switch input:checked + .switch-slider:before{ transform:translateX(18px); }
.mem-toggle-manage{ margin-top:8px; font-size:12px; color:var(--primary); background:none; border:none; cursor:pointer; padding:4px 0; }
.mem-toggle-manage:hover{ text-decoration:underline; }
.mem-manage{ margin-top:8px; border-top:1px solid var(--border-light); padding-top:8px; }
.mem-toolbar{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.mem-count{ font-size:12px; color:var(--text-3); flex:1; }
.btn-sm{ height:26px; padding:0 10px; font-size:12px; border:1px solid var(--border-light); background:#fff; border-radius:6px; cursor:pointer; color:var(--text-2); }
.btn-sm:hover{ border-color:var(--primary); color:var(--primary); }
.btn-danger{ color:#E74C3C; border-color:#E74C3C; }
.btn-danger:hover{ background:#E74C3C; color:#fff; }
.mem-list{ max-height:240px; overflow-y:auto; display:flex; flex-direction:column; gap:4px; }
.mem-item{ display:flex; align-items:flex-start; gap:6px; padding:6px 8px; background:#F7F8FA; border-radius:6px; }
.mem-item-text{ flex:1; font-size:12px; color:var(--text-1); line-height:1.5; max-height:60px; overflow:hidden; }
.mem-item-meta{ display:flex; align-items:center; gap:4px; flex-shrink:0; }
.mem-status{ font-size:11px; }
.mem-del-btn{ width:20px; height:20px; border:none; background:none; color:var(--text-3); cursor:pointer; border-radius:4px; font-size:12px; }
.mem-del-btn:hover{ background:#fee; color:#E74C3C; }
.mem-empty{ text-align:center; font-size:12px; color:var(--text-3); padding:12px; }

/* ---------- Agent 策略 ---------- */
.strategy-desc{ font-size:12px; color:var(--text-3); margin:8px 0; line-height:1.5; padding:8px 10px; background:#F7F8FA; border-radius:6px; }
.strategy-options{ margin-top:12px; padding-top:12px; border-top:1px solid var(--border-light); }
.cfg-revisions{ margin-top:12px; border-top:1px solid var(--border-light); padding-top:8px; }
.cfg-rev-toolbar{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.cfg-rev-title{ font-size:12px; font-weight:600; color:var(--text-2); flex:1; }
.cfg-rev-list{ max-height:200px; overflow-y:auto; display:flex; flex-direction:column; gap:6px; }
.cfg-rev-item{ border:1px solid var(--border-light); border-radius:6px; padding:8px 10px; }
.cfg-rev-info{ display:flex; align-items:center; gap:8px; margin-bottom:4px; }
.cfg-rev-time{ font-size:11px; color:var(--text-3); }
.cfg-rev-strategy{ font-size:11px; color:var(--primary); background:var(--primary-light); padding:1px 6px; border-radius:4px; }
.cfg-rev-summary{ font-size:12px; color:var(--text-2); margin-bottom:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cfg-rev-rollback{ font-size:11px; color:var(--primary); background:none; border:1px solid var(--primary); border-radius:4px; padding:2px 8px; cursor:pointer; }
.cfg-rev-rollback:hover{ background:var(--primary); color:#fff; }
.cfg-rev-empty{ text-align:center; font-size:12px; color:var(--text-3); padding:12px; }
</style>

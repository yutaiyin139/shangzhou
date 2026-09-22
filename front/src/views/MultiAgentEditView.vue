<template>
  <AppShell id="page-root" active-key="multi-agent" main-class="main-white">
    <div class="page-root multi-agent-edit-root">
      <div class="editor">
        <!-- 顶栏 -->
        <div class="editor-top">
          <button class="back" data-action="location.hash = '/multi-agent'">←</button>
          <span class="app-ico"></span>
          <div>
            <div class="app-name"><span class="js-name">多智能体</span> <span class="pen" data-action="renameApp()">✎</span></div>
            <div class="app-sub">Multi-Agent模式<span class="sep">|</span>自动保存于 <span id="saveTime">--:--:--</span><span class="sep">|</span><span class="pending" id="pendTag">待发布</span></div>
          </div>
          <div class="ops">
            <button class="btn" data-action="saveConfig()">保存</button>
            <button class="btn btn-primary" id="pubBtn" data-action="publish()">▶ 发布</button>
          </div>
        </div>

        <div class="editor-body">
          <!-- 左侧配置 -->
          <div class="editor-left">

            <!-- Agent 卡片 -->
            <div class="agent-card" id="agentCard">
              <div class="ac-head" data-action="this.parentElement.classList.toggle('closed')">
                <span class="lbl">主智能体描述 <i class="q">?</i></span>
                <span class="ac-ops"><span class="arrow">▾</span></span>
              </div>
              <div class="ac-body">




                <div class="in-wrap">
                  <input class="form-input" id="handoffInput" placeholder="请输入主Agent描述" maxlength="200">
                  <span class="in-cnt" id="handoffCnt">0/200</span>
                </div>
                <div class="handoff-err" id="handoffErr">请输入Agent描述内容</div>

                <div class="row-head">
                  <span class="lbl">模型 <i class="q">?</i></span>
                </div>

                 <div class="dd-wrap" style="margin-bottom:14px;max-width:360px;">
                  <div class="model-select" data-action="toggleDrop(event,this)">
                    <span class="drop-val" id="mainModelVal">加载中…</span><span class="caret">▾</span>
                  </div>
                  <div class="drop" id="mainModelOpts"></div>
                </div>

                <div class="row-head">
                  <span class="lbl">提示词 <i class="q">?</i></span>
                  <span class="rh-ops">
                    <button class="plain-ico" data-action="showHistoryVersions()" title="历史版本">◷</button>
                    <button class="mini-btn" data-action="showPromptTemplates()">模板</button>
                    <button class="ai-btn" id="optBtn" data-action="optPrompt()"><i class="ai">AI</i>一键优化</button>
                  </span>
                </div>
                <div class="ta-wrap">
                  <textarea id="promptTa" placeholder="通过填写描述，设定以下内容&#10;# 任务目标&#10;# 任务流程&#10;# 限制说明&#10;输入/插入应用级变量 或 输入@添加连接器与工具"></textarea>
                  <span class="grip">⠿</span>
                  <span class="cnt" id="promptCnt">0/20000</span>
                </div>

                <div class="sub-sec" id="toolSec">
                  <div class="sub-head" data-action="this.parentElement.classList.toggle('closed')">
                    <span class="lbl">工具</span>
                    <span class="rh-ops">
                      <span class="add-link" data-action="event.stopPropagation();openToolModal()">＋ 添加 <span class="cnt-txt" id="toolCnt">(0/120)</span></span>
                      <span class="arrow">▾</span>
                    </span>
                  </div>
                  <div class="sub-list" id="toolList"></div>
                </div>

                <div class="sub-sec" id="connSec">
                  <div class="sub-head" data-action="this.parentElement.classList.toggle('closed')">
                    <span class="lbl">连接器</span>
                    <span class="rh-ops">
                      <span class="add-link" data-action="event.stopPropagation();openConnModal()">＋ 添加 <span class="cnt-txt" id="connCnt">(0/120)</span></span>
                      <span class="arrow">▾</span>
                    </span>
                  </div>
                  <div class="sub-list" id="connList"></div>
                </div>
              </div>
            </div>

            <button class="add-agent" id="addAgentBtn" data-action="openAgentModal()">＋ 添加 Agent（0/10）</button>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">💬</span><span class="t">欢迎语</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <textarea class="form-textarea" id="welcomeTa" placeholder="例如：你好！我是智能客服多智能体，可以帮你处理售前咨询、订单查询等问题～"></textarea>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">🗨️</span><span class="t">对话体验</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="cfg-row"><label>对话轮次上限</label><input class="form-input" id="roundsInput" type="number" min="1" max="50" value="10"></div>
                <div class="cfg-row"><label>追问建议</label>
                  <select class="form-input" id="suggestSel"><option value="1">开启</option><option value="0">关闭</option></select>
                </div>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">🔢</span><span class="t">变量与记忆</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="cfg-row"><label>应用级变量（每行一个，格式：变量名=默认值）</label>
                  <textarea class="form-textarea" id="varTa" placeholder="例如：&#10;customer_name=&#10;region=华东"></textarea>
                </div>
                <div class="cfg-row"><label>长期记忆</label>
                  <div id="memList" class="mem-list"></div>
                  <div class="mem-add"><input class="form-input" id="memInput" placeholder="输入记忆内容，如：用户偏好简洁回答"><button class="btn btn-sm" id="addMemBtn">添加</button></div>
                </div>
              </div>
            </div>

          </div>

          <!-- 右侧预览 -->
          <div class="editor-right">
            <div class="preview-head">
              <button class="plain-ico" data-action="togglePreviewPanel()" title="面板开关">▦</button>
              <span class="mini-dot"></span>
              <span class="js-name">多智能体</span>
            </div>
            <div class="preview-body" id="previewBody">
              <div class="p-empty">
                <div class="p-ico"></div>
                <div class="p-name js-name">多智能体</div>
              </div>
              <div class="msg-list" id="msgList"></div>
            </div>
            <div class="preview-input">
              <button class="plain-ico" style="font-size:17px;" data-action="uploadFile()" title="上传文件">＋</button>
              <input type="file" id="fileInput" style="display:none;" multiple onchange="handleFileUpload(event)">
              <input id="chatInput" placeholder="请输入你的问题，支持上传图片或文件。">
              <button class="send" id="sendBtn" data-action="sendMsg()">↑</button>
            </div>
            <div class="preview-foot">AI生成仅供参考。当前为应用调试环境，发布后点击体验链接即可体验发布环境效果。</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 选择工具弹窗 -->
    <div class="modal-mask" id="toolModal">
      <div class="modal" style="width:640px;">
        <div class="modal-head"><div class="modal-title">添加工具 <i class="q" data-action="toast('从数据库列出的可用工具')">?</i></div>
          <button class="modal-close" data-action="closeModal('toolModal')">✕</button></div>
        <div class="modal-body">
          <div class="pk-search"><input id="toolQ" placeholder="搜索工具"><button class="btn btn-primary btn-sm" id="toolOk">确认添加</button></div>
          <div class="pk-list" id="toolListBox"></div>
        </div>
      </div>
    </div>

    <!-- 选择连接器弹窗 -->
    <div class="modal-mask" id="connModal">
      <div class="modal" style="width:640px;">
        <div class="modal-head"><div class="modal-title">添加连接器 <i class="q" data-action="toast('从数据库列出的可用连接器')">?</i></div>
          <button class="modal-close" data-action="closeModal('connModal')">✕</button></div>
        <div class="modal-body">
          <div class="pk-search"><input id="connQ" placeholder="搜索连接器"><button class="btn btn-primary btn-sm" id="connOk">确认添加</button></div>
          <div class="pk-list" id="connListBox"></div>
        </div>
      </div>
    </div>

    <!-- 添加 Agent 弹窗 -->
    <div class="modal-mask" id="agentModal">
      <div class="modal modal-xl">
        <div class="modal-head"><div class="modal-title">添加 Agent <i class="q" data-action="toast('从已有单智能体应用中选择并添加为子 Agent')">?</i></div>
          <button class="modal-close" data-action="closeModal('agentModal')">✕</button></div>
        <div class="modal-body">
          <div class="am-toolbar">
            <span class="am-right">
              <span class="select"><select id="amScope"><option>全部</option><option>我创建的</option></select></span>
              <span class="am-search">
                <input id="amQ" placeholder="搜索Agent/应用名称">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
              </span>
              <button class="am-refresh" data-action="loadSubAgents();toast('已刷新')">⟳</button>
            </span>
          </div>
          <table class="am-tbl">
            <thead><tr><th>Agent</th><th>描述</th><th>创建者</th><th>状态</th><th></th></tr></thead>
            <tbody id="amBody"></tbody>
          </table>
          <div class="am-empty" id="amEmpty">无匹配的 Agent</div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal, getLoginUser } from '../utils/global'

/* 下拉菜单的全局点击关闭 */
function onDocClick(){
  document.querySelectorAll('.drop.show').forEach(function(x){ x.classList.remove('show'); });
}
var onHashChangeRef = null;

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

  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var agentId = params.get('id');
  var curName = '多智能体';
  var subAgents = [];       // 子智能体 [{id, name, description}]
  var selectedTools = [];
  var selectedConns = [];
  var toolCandidates = [];
  var connCandidates = [];
  var amAgents = [];
  var mems = [];
  var modelList = [];

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function setNames(n){ document.querySelectorAll('.js-name').forEach(function(el){ el.textContent = n; }); }

  /* 加载可用模型 */
  function loadModelList(cb){
    apiGet('/api/model-configs').then(function(data){
      if (data.code === 200){
        modelList = (data.data || []).filter(function(m){ return m.status === 1; });
        renderModelSelect();
        if (cb) cb();
      }
    });
  }

  function renderModelSelect(){
    var optsBox = document.getElementById('mainModelOpts');
    var valEl = document.getElementById('mainModelVal');
    if (!modelList.length){
      optsBox.innerHTML = '<div class="opt" data-action="pickOpt(event,this)">暂无可用模型</div>';
      valEl.textContent = '暂无可用模型';
      return;
    }
    var html = modelList.map(function(m){
      var label = m.credential_name || m.model_name || m.provider;
      return '<div class="opt" data-action="pickOpt(event,this)" data-model="' + esc(label) + '">' + esc(label) + '</div>';
    }).join('');
    optsBox.innerHTML = html;
  }

  function setSelectedModel(name){
    var valEl = document.getElementById('mainModelVal');
    var found = modelList.some(function(m){ return (m.credential_name || m.model_name || m.provider) === name; });
    valEl.textContent = found ? name : (modelList.length ? (modelList[0].credential_name || modelList[0].model_name || modelList[0].provider) : '暂无可用模型');
    valEl.setAttribute('data-model', valEl.textContent);
  }

  function getSelectedModel(){
    var valEl = document.getElementById('mainModelVal');
    return valEl.getAttribute('data-model') || valEl.textContent.trim();
  }

  /* 加载多智能体详情 */
  function loadAgent(){
    if (!agentId) return;
    apiGet('/api/multi-agents/' + agentId).then(function(data){
      if (data.code !== 200) return;
      var ag = data.data;
      curName = ag.name;
      setNames(ag.name);
      var c = ag.config || {};
      document.getElementById('handoffInput').value = c.handoff || '';
      document.getElementById('handoffCnt').textContent = (c.handoff || '').length + '/200';
      if (c.handoff) document.getElementById('handoffErr').style.display = 'none';
      document.getElementById('promptTa').value = c.prompt || '';
      document.getElementById('promptCnt').textContent = (c.prompt || '').length + '/20000';
      document.getElementById('welcomeTa').value = c.welcome || '';
      document.getElementById('roundsInput').value = c.rounds || 10;
      document.getElementById('suggestSel').value = c.suggest === false ? '0' : '1';
      document.getElementById('varTa').value = c.variables || '';
      selectedTools = c.tools || [];
      selectedConns = c.connectors || [];
      subAgents = c.agents || [];
      if (c.model) setSelectedModel(c.model);
      renderTools();
      renderConns();
      renderSubAgents();
      loadMems();
      var pub = document.getElementById('pubBtn');
      if (ag.status === 'published'){
        pub.textContent = '✔ 已发布';
        pub.disabled = true;
        pub.classList.add('disabled');
        markPublished();
      }
      if (ag.updated_at) document.getElementById('saveTime').textContent = ag.updated_at.slice(11);
    });
  }

  function collectForm(){
    curName = document.querySelector('.editor-top .js-name').textContent.trim();
    return {
      handoff: document.getElementById('handoffInput').value.trim(),
      prompt: document.getElementById('promptTa').value,
      model: getSelectedModel(),
      tools: selectedTools,
      connectors: selectedConns,
      agents: subAgents,
      welcome: document.getElementById('welcomeTa').value.trim(),
      rounds: parseInt(document.getElementById('roundsInput').value, 10) || 10,
      suggest: document.getElementById('suggestSel').value === '1',
      variables: document.getElementById('varTa').value
    };
  }

  function saveConfig(){
    if (!agentId){ toast('请先创建多智能体应用'); return; }
    apiPut('/api/multi-agents/' + agentId, { name: curName, config: collectForm() }).then(function(data){
      toast(data.code === 200 ? '已保存' : (data.msg || '保存失败'));
      if (data.code === 200 && data.data && data.data.updated_at){
        document.getElementById('saveTime').textContent = data.data.updated_at.slice(11);
      }
    });
  }

  function publish(){
    if (!agentId){ toast('请先保存'); return; }
    apiPut('/api/multi-agents/' + agentId, { name: curName, status: 'published', config: collectForm() }).then(function(data){
      if (data.code === 200){
        var pub = document.getElementById('pubBtn');
        pub.textContent = '✔ 已发布';
        pub.disabled = true;
        pub.classList.add('disabled');
        markPublished();
        toast('发布成功，多智能体已上线');
      } else {
        toast(data.msg || '发布失败');
      }
    });
  }
  function markPublished(){
    var tag = document.getElementById('pendTag');
    if (tag){ tag.textContent = '已发布'; tag.className = 'pending pub'; }
  }

  /* AI 生成转交描述 */
  function genDesc(){
    var btn = document.getElementById('genDescBtn');
    if (!btn || btn.dataset.busy) return;
    btn.dataset.busy = '1';
    btn.innerHTML = '<i class="ai">AI</i>生成中…';
    apiPost('/api/multi-agent/gen-desc', { name: curName, agents: subAgents.map(function(a){ return a.name; }) }).then(function(data){
      delete btn.dataset.busy;
      btn.innerHTML = '<i class="ai">AI</i>一键生成';
      if (data.code === 200){
        var h = document.getElementById('handoffInput');
        h.value = data.data.desc;
        document.getElementById('handoffCnt').textContent = h.value.length + '/200';
        document.getElementById('handoffErr').style.display = 'none';
        toast('转交描述已生成');
      } else {
        toast(data.msg || '生成失败');
      }
    });
  }

  /* AI 优化提示词 */
  function optPrompt(){
    var ta = document.getElementById('promptTa');
    var btn = document.getElementById('optBtn');
    if (!ta.value.trim()){ toast('请先填写提示词'); return; }
    if (btn.dataset.busy) return;
    btn.dataset.busy = '1';
    btn.innerHTML = '<i class="ai">AI</i>优化中…';
    apiPost('/api/multi-agent/optimize-prompt', { prompt: ta.value }).then(function(data){
      delete btn.dataset.busy;
      btn.innerHTML = '<i class="ai">AI</i>一键优化';
      if (data.code === 200){
        ta.value = data.data.prompt;
        document.getElementById('promptCnt').textContent = ta.value.length + '/20000';
        toast('提示词优化完成');
      } else {
        toast(data.msg || '优化失败');
      }
    });
  }

  /* 加载候选工具/连接器 */
  function loadCandidates(){
    apiGet('/api/multi-agent/tools').then(function(data){
      if (data.code === 200) toolCandidates = data.data || [];
    });
    apiGet('/api/multi-agent/connectors').then(function(data){
      if (data.code === 200) connCandidates = data.data || [];
    });
  }

  function renderPick(boxId, cands, selected, qId){
    var q = document.getElementById(qId).value.trim();
    var box = document.getElementById(boxId);
    var list = cands.filter(function(c){ return !q || c.name.indexOf(q) > -1; });
    if (!list.length){ box.innerHTML = '<div class="pk-empty">暂无可用项（数据库中未配置）</div>'; return; }
    box.innerHTML = list.map(function(c){
      var on = selected.some(function(s){ return s.key === c.key; });
      return '<label class="pk-item' + (on ? ' on' : '') + '"><input type="checkbox" data-key="' + esc(c.key) + '"' + (on ? ' checked' : '') + '> <span class="pk-ico">' + esc(c.icon) + '</span> <span class="pk-name">' + esc(c.name) + '</span> <span class="pk-src">' + esc(c.source) + '</span></label>';
    }).join('');
  }
  function openToolModal(){
    renderPick('toolListBox', toolCandidates, selectedTools, 'toolQ');
    openModal('toolModal');
  }
  function openConnModal(){
    renderPick('connListBox', connCandidates, selectedConns, 'connQ');
    openModal('connModal');
  }
  document.getElementById('toolQ').addEventListener('input', function(){ renderPick('toolListBox', toolCandidates, selectedTools, 'toolQ'); });
  document.getElementById('connQ').addEventListener('input', function(){ renderPick('connListBox', connCandidates, selectedConns, 'connQ'); });
  document.getElementById('toolOk').addEventListener('click', function(){
    selectedTools = Array.prototype.slice.call(document.querySelectorAll('#toolListBox input:checked')).map(function(i){
      return toolCandidates.filter(function(c){ return c.key === i.dataset.key; })[0];
    }).filter(Boolean);
    renderTools();
    closeModal('toolModal');
    toast('已更新工具');
  });
  document.getElementById('connOk').addEventListener('click', function(){
    selectedConns = Array.prototype.slice.call(document.querySelectorAll('#connListBox input:checked')).map(function(i){
      return connCandidates.filter(function(c){ return c.key === i.dataset.key; })[0];
    }).filter(Boolean);
    renderConns();
    closeModal('connModal');
    toast('已更新连接器');
  });

  function renderTools(){
    var box = document.getElementById('toolList');
    if (!selectedTools.length){
      box.innerHTML = '<div class="conn-tip">未添加工具，点击上方「＋ 添加」选择</div>';
    } else {
      box.innerHTML = selectedTools.map(function(t, i){
        return '<div class="tool-item"><span class="ti-ico">' + esc(t.icon) + '</span> <span class="ti-name">' + esc(t.name) + '</span><span class="ti-src">' + esc(t.source) + '</span><button class="plain-ico ti-more" data-action="removeTool(' + i + ')">✕</button></div>';
      }).join('');
    }
    document.getElementById('toolCnt').textContent = '(' + selectedTools.length + '/120)';
  }
  function renderConns(){
    var box = document.getElementById('connList');
    if (!selectedConns.length){
      box.innerHTML = '<div class="conn-tip">未添加连接器，点击上方「＋ 添加」选择</div>';
    } else {
      box.innerHTML = selectedConns.map(function(c, i){
        return '<div class="tool-item"><span class="ti-ico">' + esc(c.icon) + '</span> <span class="ti-name">' + esc(c.name) + '</span><span class="ti-src">' + esc(c.source) + '</span><button class="plain-ico ti-more" data-action="removeConn(' + i + ')">✕</button></div>';
      }).join('');
    }
    document.getElementById('connCnt').textContent = '(' + selectedConns.length + '/120)';
  }
  function removeTool(i){ selectedTools.splice(i, 1); renderTools(); }
  function removeConn(i){ selectedConns.splice(i, 1); renderConns(); }

  /* 折叠面板 */
  document.querySelectorAll('.cfg-head').forEach(function(h){
    h.addEventListener('click', function(){ h.parentElement.classList.toggle('closed'); });
  });

  /* 自定义下拉 */
  function toggleDrop(e, el){
    e.stopPropagation();
    var d = el.parentElement.querySelector('.drop');
    var was = d.classList.contains('show');
    closeDrops();
    if (!was) d.classList.add('show');
  }
  function closeDrops(){ document.querySelectorAll('.drop.show').forEach(function(x){ x.classList.remove('show'); }); }
  document.addEventListener('click', onDocClick);
  function pickOpt(e, opt){
    e.stopPropagation();
    var model = opt.getAttribute('data-model');
    var wrap = opt.closest('.dd-wrap');
    wrap.querySelector('.drop-val').textContent = model;
    wrap.querySelector('.drop-val').setAttribute('data-model', model);
    closeDrops();
  }

  /* 字数统计 */
  bindCharCount(document.getElementById('promptTa'), document.getElementById('promptCnt'), 20000);
  var handoff = document.getElementById('handoffInput');
  handoff.addEventListener('input', function(){
    document.getElementById('handoffCnt').textContent = handoff.value.length + '/200';
    if (handoff.value.trim()) document.getElementById('handoffErr').style.display = 'none';
  });

  /* 重命名 */
  function renameApp(){
    var v = prompt('请输入应用名称', curName);
    if (v && v.trim()){
      curName = v.trim();
      setNames(curName);
      toast('已重命名（点「保存」生效）');
    }
  }

  /* 添加 Agent */
  function loadSubAgents(){
    var uid = (getLoginUser() && getLoginUser().id) || 1;
    apiGet('/api/agents/accessible', { params: { uid: uid } }).then(function(data){
      if (data.code === 200){
        amAgents = data.data || [];
        renderAgentRows();
      } else {
        console.error('[loadSubAgents] API error:', data.msg);
        toast('加载失败：' + (data.msg || '未知错误'));
        amAgents = [];
        renderAgentRows();
      }
    }).catch(function(err){
      console.error('[loadSubAgents] Network error:', err);
      toast('网络异常，请稍后重试');
      amAgents = [];
      renderAgentRows();
    });
  }
  function renderAgentRows(){
    var body = document.getElementById('amBody');
    body.innerHTML = '';
    if (!amAgents.length){
      document.getElementById('amEmpty').style.display = 'block';
      return;
    }
    amAgents.forEach(function(r, i){
      var tr = document.createElement('tr');
      var sourceTag = r.is_mine
        ? '<span class="am-tag mine">我创建的</span>'
        : '<span class="am-tag pub">已发布</span>';
      var statusTag = r.status === 'published'
        ? '<span class="am-status pub">已发布</span>'
        : '<span class="am-status draft">草稿</span>';
      tr.innerHTML =
        '<td><span class="am-agent"><span class="am-dot"></span>' +
          '<span>' + esc(r.name) + '</span>' + sourceTag + '</span></td>' +
        '<td>' + esc(r.description || '单智能体应用') + '</td>' +
        '<td>' + esc(r.owner_name || r.role || '未知') + '</td>' +
        '<td>' + statusTag + '</td>' +
        '<td style="text-align:right;"><span class="am-link" data-i="' + i + '">添加</span></td>';
      tr.querySelector('.am-link').addEventListener('click', function(){ addFromModal(i); });
      body.appendChild(tr);
    });
    filterAgentRows();
  }
  function filterAgentRows(){
    var q = document.getElementById('amQ').value.trim();
    var scope = document.getElementById('amScope').value;
    var shown = 0;
    document.querySelectorAll('#amBody tr').forEach(function(tr, idx){
      var ag = amAgents[idx];
      var ok = true;
      if (q && tr.cells[0].textContent.indexOf(q) === -1 && tr.cells[1].textContent.indexOf(q) === -1) ok = false;
      if (scope === '我创建的' && ag && !ag.is_mine) ok = false;
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    document.getElementById('amEmpty').style.display = shown ? 'none' : 'block';
  }
  document.getElementById('amQ').addEventListener('input', filterAgentRows);
  document.getElementById('amScope').addEventListener('change', filterAgentRows);

  function openAgentModal(){
    loadSubAgents();
    openModal('agentModal');
  }
  function addFromModal(i){
    var r = amAgents[i];
    if (!r) return;
    if (subAgents.length >= 10){ toast('最多添加 10 个 Agent'); return; }
    if (subAgents.some(function(a){ return a.id === r.id; })){ toast('该 Agent 已添加'); return; }
    subAgents.push({ id: r.id, name: r.name, description: r.description || '' });
    renderSubAgents();
    closeModal('agentModal');
    toast('已添加子智能体「' + r.name + '」');
  }
  function renderSubAgents(){
    document.querySelectorAll('.agent-card.sub').forEach(function(c){ c.remove(); });
    document.getElementById('addAgentBtn').textContent = '＋ 添加 Agent（' + subAgents.length + '/10）';
    subAgents.forEach(function(a, i){
      var card = document.createElement('div');
      card.className = 'agent-card sub closed';
      card.innerHTML = '<div class="ac-head"><span class="mini-dot"></span><span class="ac-name">' + esc(a.name) + '</span><span class="ac-ops"><button class="plain-ico" data-action="removeSubAgent(' + i + ')">✕</button><span class="arrow">▾</span></span></div>' +
        '<div class="ac-body"><div class="conn-tip">' + esc(a.description || '子 Agent，id=' + a.id) + '</div></div>';
      card.querySelector('.ac-head').addEventListener('click', function(e){
        if (e.target.closest('[data-action]')) return;
        card.classList.toggle('closed');
      });
      document.getElementById('addAgentBtn').before(card);
    });
  }
  function removeSubAgent(i){
    subAgents.splice(i, 1);
    renderSubAgents();
    toast('已移除子智能体');
  }

  /* 长期记忆 */
  function loadMems(){
    if (!agentId){ renderMems(); return; }
    apiGet('/api/memories', { params: { agent_id: agentId } }).then(function(data){
      if (data.code === 200){ mems = data.data || []; renderMems(); }
    });
  }
  function renderMems(){
    var box = document.getElementById('memList');
    if (!mems.length){ box.innerHTML = '<div class="conn-tip">暂无记忆，可在下方添加</div>'; return; }
    box.innerHTML = mems.map(function(m){
      return '<div class="mem-item"><span class="mem-txt">' + esc(m.content) + '</span><span class="mem-time">' + esc(m.updated_at || '') + '</span><button class="plain-ico" data-action="delMem(' + m.id + ')">✕</button></div>';
    }).join('');
  }
  document.getElementById('addMemBtn').addEventListener('click', addMem);
  document.getElementById('memInput').addEventListener('keydown', function(e){ if (e.key === 'Enter') addMem(); });
  function addMem(){
    var v = document.getElementById('memInput').value.trim();
    if (!v){ toast('请输入记忆内容'); return; }
    if (!agentId){ toast('请先创建多智能体应用'); return; }
    apiPost('/api/memories', { agent_id: parseInt(agentId, 10), content: v }).then(function(data){
      if (data.code === 200){
        document.getElementById('memInput').value = '';
        loadMems();
        toast('记忆已添加');
      } else {
        toast(data.msg || '添加失败');
      }
    });
  }
  function delMem(id){
    apiDelete('/api/memories/' + id).then(function(data){
      if (data.code === 200){ loadMems(); toast('已删除'); }
      else toast(data.msg || '删除失败');
    });
  }

  /* 预览对话 */
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('sendBtn');
  input.addEventListener('input', function(){ sendBtn.classList.toggle('ready', !!input.value.trim()); });
  input.addEventListener('keydown', function(e){ if (e.key === 'Enter') sendMsg(); });

  function sendMsg(){
    var v = input.value.trim();
    if (!v) return;
    if (!agentId){ toast('请先保存多智能体应用'); return; }
    var body = document.getElementById('previewBody');
    body.classList.add('chatting');
    var list = document.getElementById('msgList');
    list.insertAdjacentHTML('beforeend', '<div class="msg user"><div class="bubble"></div></div>');
    list.lastElementChild.querySelector('.bubble').textContent = v;
    input.value = '';
    sendBtn.classList.remove('ready');
    body.scrollTop = body.scrollHeight;
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'msg bot';
    loadingDiv.id = 'msg-loading';
    loadingDiv.innerHTML = '<div class="bubble">思考中…</div>';
    list.appendChild(loadingDiv);
    body.scrollTop = body.scrollHeight;
    apiPut('/api/multi-agents/' + agentId, { name: curName, config: collectForm() }).then(function(){
      return apiPost('/api/multi-agents/' + agentId + '/debug', { message: v, file_ids: uploadedFiles.map(function(f){ return f.id; }) });
    }).then(function(data){
      var ld = document.getElementById('msg-loading');
      if (ld) ld.remove();
      if (data.code === 200){
        var reply = data.data.reply;
        var handledBy = data.data.handled_by || '主 Agent';
        list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble"></div><div class="msg-agent-tag">🤖 ' + esc(handledBy) + '</div></div>');
        list.lastElementChild.querySelector('.bubble').textContent = reply;
      } else {
        list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble" style="color:#F53F3F;">⚠ ' + esc(data.msg || '请求失败') + '</div></div>');
      }
      body.scrollTop = body.scrollHeight;
    }).catch(function(){
      var ld = document.getElementById('msg-loading');
      if (ld) ld.remove();
      list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble" style="color:#F53F3F;">⚠ 网络异常，请稍后重试</div></div>');
      body.scrollTop = body.scrollHeight;
    });
  }
  function clearChat(){
    document.getElementById('msgList').innerHTML = '';
    document.getElementById('previewBody').classList.remove('chatting');
    toast('已清空对话');
  }

  /* ================= P2 占位功能实现 ================= */

  /* 历史版本 */
  function showHistoryVersions(){
    if (!agentId){ toast('请先保存多智能体应用'); return; }
    var versions = [
      { time: '2024-01-15 14:30', version: 'v3', author: '当前用户' },
      { time: '2024-01-14 10:20', version: 'v2', author: '当前用户' },
      { time: '2024-01-10 09:00', version: 'v1', author: '当前用户' }
    ];
    var html = '<div class="ver-list">' + versions.map(function(v, i){
      return '<div class="ver-item">' +
        '<span class="ver-num">' + v.version + '</span>' +
        '<span class="ver-time">' + v.time + '</span>' +
        '<span class="ver-author">' + esc(v.author) + '</span>' +
        (i > 0 ? '<button class="ver-restore" data-action="restoreVersion(' + i + ')">恢复</button>' : '<span class="ver-current">当前</span>') +
      '</div>';
    }).join('') + '</div>';
    openModal('历史版本', html);
  }
  function restoreVersion(i){
    closeModal();
    toast('已恢复到 v' + (3 - i));
  }
  window.showHistoryVersions = showHistoryVersions;

  /* 提示词模板 */
  function showPromptTemplates(){
    var templates = [
      { name: '客服多智能体', desc: '处理售前咨询、订单查询、售后问题', prompt: '你是客服多智能体协调者，负责将用户问题分配给专业客服 Agent 处理。\n\n# 任务目标\n准确识别用户意图，转交至对应子 Agent。\n\n# 转交规则\n- 售前咨询 → 销售 Agent\n- 订单查询 → 订单 Agent\n- 售后问题 → 售后 Agent' },
      { name: '研发多智能体', desc: '代码审查、Bug 修复、文档编写', prompt: '你是研发多智能体协调者，管理代码相关任务。\n\n# 任务目标\n协调代码审查、Bug 修复和文档编写。\n\n# 转交规则\n- 代码审查 → 审查 Agent\n- Bug 修复 → 开发 Agent\n- 文档编写 → 文档 Agent' },
      { name: '营销多智能体', desc: '内容创作、数据分析、渠道投放', prompt: '你是营销多智能体协调者，负责营销活动全流程。\n\n# 任务目标\n协调内容创作、数据分析和渠道投放。\n\n# 转交规则\n- 内容创作 → 创意 Agent\n- 数据分析 → 数据 Agent\n- 渠道投放 → 运营 Agent' }
    ];
    var html = '<div class="tpl-list">' + templates.map(function(t, i){
      return '<div class="tpl-item">' +
        '<div class="tpl-name">' + esc(t.name) + '</div>' +
        '<div class="tpl-desc">' + esc(t.desc) + '</div>' +
        '<button class="tpl-use" data-action="applyTemplate(' + i + ')">使用模板</button>' +
      '</div>';
    }).join('') + '</div>';
    openModal('提示词模板', html);
  }
  var promptTemplates = [
    '你是客服多智能体协调者，负责将用户问题分配给专业客服 Agent 处理。\n\n# 任务目标\n准确识别用户意图，转交至对应子 Agent。\n\n# 转交规则\n- 售前咨询 → 销售 Agent\n- 订单查询 → 订单 Agent\n- 售后问题 → 售后 Agent',
    '你是研发多智能体协调者，管理代码相关任务。\n\n# 任务目标\n协调代码审查、Bug 修复和文档编写。\n\n# 转交规则\n- 代码审查 → 审查 Agent\n- Bug 修复 → 开发 Agent\n- 文档编写 → 文档 Agent',
    '你是营销多智能体协调者，负责营销活动全流程。\n\n# 任务目标\n协调内容创作、数据分析和渠道投放。\n\n# 转交规则\n- 内容创作 → 创意 Agent\n- 数据分析 → 数据 Agent\n- 渠道投放 → 运营 Agent'
  ];
  function applyTemplate(i){
    var ta = document.getElementById('promptTa');
    ta.value = promptTemplates[i];
    document.getElementById('promptCnt').textContent = ta.value.length + '/20000';
    closeModal();
    toast('已应用模板');
  }
  window.showPromptTemplates = showPromptTemplates;

  /* 面板开关（预览面板显隐） */
  function togglePreviewPanel(){
    var right = document.querySelector('.editor-right');
    if (right.style.display === 'none'){
      right.style.display = '';
      toast('已显示预览面板');
    } else {
      right.style.display = 'none';
      toast('已隐藏预览面板');
    }
  }
  window.togglePreviewPanel = togglePreviewPanel;

  /* 文件上传 */
  var uploadedFiles = [];
  function uploadFile(){
    document.getElementById('fileInput').click();
  }
  function handleFileUpload(e){
    var files = Array.prototype.slice.call(e.target.files);
    files.forEach(function(file){
      var formData = new FormData();
      formData.append('file', file);
      var chipId = 'fc-' + Date.now() + Math.random().toString(36).slice(2, 6);
      var preview = document.querySelector('.preview-input');
      var chip = document.createElement('span');
      chip.className = 'file-chip uploading';
      chip.id = chipId;
      chip.innerHTML = '<span class="fc-name">' + esc(file.name) + '</span><span class="fc-progress">上传中…</span>';
      preview.before(chip);
      apiPost('/api/files/upload', formData).then(function(data){
          if (data.code === 200){
            chip.classList.remove('uploading');
            chip.classList.add('done');
            chip.innerHTML = '<span class="fc-name">📎 ' + esc(file.name) + '</span><span class="fc-size">' + (file.size / 1024).toFixed(1) + 'KB</span><button class="fc-del" data-action="removeFile(\'' + chipId + '\',' + data.data.id + ')">✕</button>';
            uploadedFiles.push({ id: data.data.id, name: file.name });
          } else {
            chip.classList.remove('uploading');
            chip.classList.add('error');
            chip.innerHTML = '<span class="fc-name">' + esc(file.name) + '</span><span class="fc-err">上传失败</span>';
          }
        }).catch(function(){
          chip.classList.remove('uploading');
          chip.classList.add('error');
          chip.innerHTML = '<span class="fc-name">' + esc(file.name) + '</span><span class="fc-err">上传失败</span>';
        });
    });
    e.target.value = '';
  }
  function removeFile(chipId, fileId){
    document.getElementById(chipId).remove();
    uploadedFiles = uploadedFiles.filter(function(f){ return f.id !== fileId; });
    toast('已移除文件');
  }
  window.uploadFile = uploadFile;

  /* 初始加载 */
  loadModelList(function(){
    loadAgent();
  });
  loadCandidates();

  /* hash 路由组件复用时重新加载 */
  onHashChangeRef = function onHashChange(){
    var p = new URLSearchParams(location.hash.split('?')[1] || '');
    var newId = p.get('id');
    if (newId === agentId) return;
    agentId = newId;
    if (!agentId) return;
    curName = '多智能体';
    subAgents = []; selectedTools = []; selectedConns = []; mems = [];
    setNames(curName);
    document.getElementById('handoffInput').value = '';
    document.getElementById('handoffCnt').textContent = '0/200';
    document.getElementById('promptTa').value = '';
    document.getElementById('promptCnt').textContent = '0/20000';
    document.getElementById('welcomeTa').value = '';
    document.getElementById('roundsInput').value = 10;
    document.getElementById('suggestSel').value = '1';
    document.getElementById('varTa').value = '';
    document.getElementById('saveTime').textContent = '--:--:--';
    var tag = document.getElementById('pendTag');
    tag.textContent = '待发布'; tag.className = 'pending';
    var pub = document.getElementById('pubBtn');
    pub.textContent = '▶ 发布'; pub.disabled = false; pub.classList.remove('disabled');
    renderTools(); renderConns(); renderSubAgents(); renderMems();
    loadAgent();
    loadMems();
  };
  window.addEventListener('hashchange', onHashChangeRef);
})

onUnmounted(function(){
  document.removeEventListener('click', onDocClick);
  if (onHashChangeRef) window.removeEventListener('hashchange', onHashChangeRef);
});
</script>
<style>
.editor-top{position:relative;}
  .pen{color:var(--text-3);cursor:pointer;font-size:13px;}
  .pen:hover{color:var(--primary);}
  .app-sub .sep{margin:0 6px;color:var(--text-4);}
  .bell-ico{width:20px;height:20px;color:var(--text-2);cursor:pointer;display:inline-flex;}
  .bell-ico:hover{color:var(--primary);}
  .bell-ico svg{width:20px;height:20px;}
  .cfg-ico{font-size:15px;width:20px;text-align:center;}
  .q{display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;border-radius:50%;border:1px solid var(--text-4);color:var(--text-4);font-size:9px;font-style:normal;margin:0 2px;cursor:help;}
  /* 自定义下拉 */
  .dd-wrap{position:relative;}
  .drop{display:none;position:absolute;top:calc(100% + 4px);left:0;min-width:100%;background:#fff;border:1px solid var(--border);border-radius:6px;box-shadow:0 6px 24px rgba(29,33,41,.12);z-index:50;padding:4px;}
  .drop.show{display:block;}
  .drop .opt{padding:8px 10px;border-radius:4px;font-size:13px;cursor:pointer;white-space:nowrap;}
  .drop .opt:hover{background:var(--primary-light);color:var(--primary);}
  .drop .opt .ctx{background:#F2F3F5;color:var(--text-3);font-size:11px;padding:1px 6px;border-radius:4px;margin-left:8px;}
  .model-select .caret{color:var(--text-3);font-size:12px;}
  .plain-ico{border:none;background:none;color:var(--text-2);font-size:14px;cursor:pointer;padding:2px 4px;border-radius:4px;}
  .plain-ico:hover{color:var(--primary);}
  .mini-btn{border:1px solid var(--border);background:#fff;border-radius:6px;padding:3px 12px;font-size:12px;color:var(--text-1);cursor:pointer;}
  .mini-btn:hover{border-color:var(--primary);color:var(--primary);}
  .ai-btn{display:inline-flex;align-items:center;gap:4px;border:1px solid #B8CCFF;background:#F0F5FF;border-radius:6px;padding:3px 10px;font-size:12px;color:var(--primary);cursor:pointer;}
  .ai-btn:hover{background:var(--primary-light);}
  .ai-btn .ai{background:var(--primary);color:#fff;font-size:10px;border-radius:3px;padding:0 3px;font-weight:700;font-style:normal;}
  /* Agent 标签 */
  .msg-agent-tag{font-size:11px;color:var(--text-3);margin-top:4px;padding:2px 8px;background:#F2F3F5;border-radius:4px;display:inline-block;}
  /* Agent 卡片 */
  .agent-card{margin:14px;border:1px solid var(--border);border-radius:10px;background:#fff;}
  .ac-head{display:flex;align-items:center;gap:8px;padding:14px 16px;cursor:pointer;user-select:none;}
  .ac-head .mini-dot{width:20px;height:20px;border-radius:50%;background:linear-gradient(135deg,#8AB4FF,#2E63F0);flex-shrink:0;}
  .ac-name{font-size:15px;font-weight:600;}
  .ac-ops{margin-left:auto;display:flex;align-items:center;gap:8px;color:var(--text-3);}
  .ac-head .arrow{transition:transform .2s;font-size:12px;color:var(--text-3);}
  .agent-card.closed .ac-body{display:none;}
  .agent-card.closed .ac-head .arrow{transform:rotate(-90deg);}
  .ac-body{padding:0 16px 16px;}
  .row-head{display:flex;align-items:center;margin:14px 0 8px;}
  .row-head .lbl{font-size:13px;color:var(--text-2);}
  .rh-ops{margin-left:auto;display:flex;align-items:center;gap:8px;}
  .in-wrap{position:relative;}
  .in-wrap .form-input{padding-right:52px;}
  .in-cnt{position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:12px;color:var(--text-4);pointer-events:none;}
  .ta-wrap{position:relative;border:1px solid var(--border);border-radius:6px;background:#fff;}
  .ta-wrap:focus-within{border-color:var(--primary);}
  .ta-wrap textarea{width:100%;border:none;resize:vertical;min-height:210px;padding:12px 12px 26px;font-size:13px;line-height:1.9;background:transparent;display:block;}
  .ta-wrap .grip{position:absolute;left:50%;bottom:5px;transform:translateX(-50%);color:var(--text-4);font-size:10px;}
  .ta-wrap .cnt{position:absolute;right:10px;bottom:6px;font-size:12px;color:var(--text-4);}
  /* 工具 / 连接器 */
  .sub-sec{border-top:1px solid var(--border-light);margin-top:14px;padding-top:12px;}
  .sub-head{display:flex;align-items:center;cursor:pointer;user-select:none;}
  .sub-head .lbl{font-size:13px;color:var(--text-2);}
  .add-link{color:var(--primary);font-size:13px;cursor:pointer;}
  .add-link:hover{text-decoration:underline;}
  .add-link .cnt-txt{color:var(--text-3);}
  .sub-head .arrow{transition:transform .2s;font-size:12px;color:var(--text-3);}
  .sub-sec.closed .sub-list{display:none;}
  .sub-sec.closed .sub-head .arrow{transform:rotate(-90deg);}
  .tool-item{display:flex;align-items:center;gap:8px;padding:10px 4px;font-size:13px;}
  .tool-item .ti-name{color:var(--text-1);}
  .tool-item .ti-more{margin-left:auto;}
  .conn-tip{font-size:12px;color:var(--text-3);padding:8px 0 2px;}
  /* 添加 Agent */
  .add-agent{display:block;width:calc(100% - 28px);margin:4px 14px 14px;padding:13px;border:1.5px dashed var(--border);border-radius:10px;background:#fff;color:var(--primary);font-size:14px;cursor:pointer;}
  .add-agent:hover{border-color:var(--primary);background:var(--primary-light);}
  /* 添加 Agent 弹窗 */
  .modal-xl{width:900px;}
  .am-toolbar{display:flex;align-items:center;gap:10px;margin-bottom:14px;}
  .am-right{margin-left:auto;display:flex;align-items:center;gap:10px;}
  .am-search{display:flex;align-items:center;gap:8px;border:1px solid var(--border);border-radius:6px;padding:7px 12px;width:250px;background:#fff;}
  .am-search input{border:none;background:none;flex:1;font-size:13px;outline:none;}
  .am-search svg{width:15px;height:15px;color:var(--text-3);flex-shrink:0;}
  .am-refresh{border:1px solid var(--border);background:#fff;border-radius:6px;width:34px;height:34px;display:inline-flex;align-items:center;justify-content:center;color:var(--text-2);font-size:16px;cursor:pointer;}
  .am-refresh:hover{color:var(--primary);border-color:var(--primary);}
  .am-tbl{width:100%;border-collapse:collapse;}
  .am-tbl th{background:#F7F8FA;font-size:13px;color:var(--text-3);font-weight:400;text-align:left;padding:10px 14px;}
  .am-tbl th:first-child{border-radius:6px 0 0 6px;}
  .am-tbl th:last-child{border-radius:0 6px 6px 0;}
  .am-tbl td{padding:12px 14px;font-size:14px;border-bottom:1px solid var(--border-light);}
  .am-agent{display:flex;align-items:center;gap:10px;}
  .am-dot{width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,#8AB4FF,#2E63F0);flex-shrink:0;}
  .am-tag{font-size:10px;padding:1px 6px;border-radius:3px;margin-left:6px;}
  .am-tag.mine{background:#E8F0FE;color:#2E63F0;}
  .am-tag.pub{background:#E8FFEA;color:#00B42A;}
  .am-status{font-size:11px;padding:2px 8px;border-radius:4px;}
  .am-status.pub{background:#E8FFEA;color:#00B42A;}
  .am-status.draft{background:#F2F3F5;color:#86909C;}
  .am-link{color:var(--primary);cursor:pointer;font-size:13px;white-space:nowrap;}
  .am-link:hover{text-decoration:underline;}
  .am-empty{display:none;text-align:center;color:var(--text-4);font-size:13px;padding:26px 0;}
  /* 配置区块 */
  .cfg-section{margin:0 14px 14px;border:1px solid var(--border);border-radius:10px;background:#fff;}
  .cfg-head{display:flex;align-items:center;gap:8px;padding:13px 16px;cursor:pointer;user-select:none;font-size:14px;font-weight:500;}
  .cfg-head .t{flex:1;}
  .cfg-head .arrow{transition:transform .2s;font-size:12px;color:var(--text-3);}
  .cfg-section.closed .cfg-body{display:none;}
  .cfg-section.closed .cfg-head .arrow{transform:rotate(-90deg);}
  .cfg-body{padding:0 16px 16px;}
  .cfg-row{margin-top:14px;}
  .cfg-row label{display:block;font-size:13px;color:var(--text-2);margin-bottom:8px;}
  /* 长期记忆 */
  .mem-list{display:flex;flex-direction:column;gap:8px;margin-bottom:10px;}
  .mem-item{display:flex;align-items:center;gap:8px;background:#F7F8FA;border-radius:8px;padding:9px 12px;font-size:13px;}
  .mem-txt{flex:1;color:var(--text-1);line-height:1.6;word-break:break-word;}
  .mem-time{font-size:11px;color:var(--text-4);white-space:nowrap;flex-shrink:0;}
  .mem-add{display:flex;gap:8px;}
  .mem-add .form-input{flex:1;}
  /* 发布按钮禁用态 */
  #pubBtn.disabled{background:#F2F3F5;border-color:#F2F3F5;color:var(--text-4);cursor:not-allowed;}
  .pending.pub{color:#00B42A;}
.multi-agent-edit-root{ min-height:100vh; }
  /* 文件芯片 */
  .file-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:14px;font-size:12px;margin:4px 4px 0 0;background:#F2F3F5;border:1px solid var(--border);}
  .file-chip.uploading{background:#FFF7E8;border-color:#FF7D00;color:#FF7D00;}
  .file-chip.done{background:#E8F0FE;border-color:#B8CCFF;color:#2E63F0;}
  .file-chip.error{background:#FFECE8;border-color:#F53F3F;color:#F53F3F;}
  .fc-name{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .fc-del{border:none;background:none;cursor:pointer;color:inherit;font-size:11px;padding:0 2px;}
  /* 历史版本 */
  .ver-list{display:flex;flex-direction:column;gap:10px;}
  .ver-item{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid var(--border);border-radius:8px;}
  .ver-num{font-weight:600;color:var(--primary);}
  .ver-time{color:var(--text-3);font-size:13px;flex:1;}
  .ver-author{color:var(--text-3);font-size:12px;}
  .ver-current{font-size:12px;color:#00B42A;}
  .ver-restore{border:1px solid var(--primary);background:var(--primary-light);color:var(--primary);border-radius:4px;padding:2px 10px;font-size:12px;cursor:pointer;}
  /* 提示词模板 */
  .tpl-list{display:flex;flex-direction:column;gap:10px;}
  .tpl-item{border:1px solid var(--border);border-radius:8px;padding:12px 14px;}
  .tpl-name{font-weight:600;font-size:14px;margin-bottom:4px;}
  .tpl-desc{color:var(--text-3);font-size:13px;margin-bottom:8px;}
  .tpl-use{border:1px solid var(--primary);background:var(--primary-light);color:var(--primary);border-radius:4px;padding:4px 14px;font-size:12px;cursor:pointer;}
</style>

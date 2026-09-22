<template>
  <AppShell id="page-root" active-key="workflow-app">
    <div class="page-pad">
      <div class="page-title">工作流应用</div>
            <div class="st-filter">
              <span class="sf-chip" data-action="openTypeFilter()">类型 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
              <span class="sf-chip" data-action="openTagFilter()">标签 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
              <span class="sf-chip" data-action="openCreatorFilter()">创建者 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
              <span class="sf-chip" data-action="openSortMenu()">排序方式 <b id="sortLabel">最近修改</b> <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
              <span class="sf-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="q" placeholder="搜索"></span>
              <span class="sf-right">
                <div class="dd-wrap">
                  <button class="btn btn-primary" data-action="event.stopPropagation();document.getElementById(&#x27;newMenu&#x27;).classList.toggle(&#x27;show&#x27;)">＋ 创建 ▾</button>
                  <div class="dd-menu" id="newMenu">
                    <div class="dd-item" data-action="closeMenus();openWfModal()">创建空白应用</div>
                    <div class="dd-item" data-action="closeMenus();location.hash=&#x27;#/app-templates&#x27;">从模板创建</div>
                    <div class="dd-item" data-action="closeMenus();importDslFile()">导入 DSL 文件</div>
                  </div>
                </div>
              </span>
            </div>
            <div class="st-grid" id="stGrid"></div>
            <div class="st-dsl"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v12M8 11l4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>拖放 DSL 文件到此处创建应用</div>
          </div>
    <!-- 创建空白应用弹窗 -->
    <div class="modal-mask" id="wfModal">
      <div class="modal modal-create">
        <button class="mc-close" data-action="closeModal(&#x27;wfModal&#x27;)">✕</button>
        <div class="mc-left">
          <div class="mc-title">创建空白应用</div>
          <div class="mc-label" style="margin-top:0;">选择应用类型</div>
          <div class="mc-types">
            <div class="mc-type sel" id="typeWf" data-action="pickType(&#x27;workflow&#x27;)">
              <span class="mt-ico" style="background:#4E5BF5;">🧩</span>
              <span><div class="mt-name">工作流</div><div class="mt-desc">面向单轮自动化任务的编排工作流</div></span>
            </div>
            <div class="mc-type" id="typeCf" data-action="pickType(&#x27;chatflow&#x27;)">
              <span class="mt-ico" style="background:#00B2FF;">💬</span>
              <span><div class="mt-name">Chatflow</div><div class="mt-desc">支持记忆的复杂多轮对话工作流</div></span>
            </div>
          </div>
          <span class="mc-newbie" data-action="showNewbieHelp()">新手适用 <b style="font-weight:400;">›</b></span>
          <div class="mc-label">应用名称 &amp; 图标</div>
          <div class="mc-name-row">
            <input class="form-input" id="wfName" placeholder="给你的应用起个名字">
            <span class="mc-app-ico" data-action="openIconPicker()">🤖</span>
          </div>
          <div class="wf-err" id="wfNameErr">请输入应用名称</div>
          <div class="mc-label">描述 <span class="opt-txt">(可选)</span></div>
          <textarea class="form-textarea" id="wfDesc" placeholder="输入应用的描述"></textarea>
          <div class="mc-label">默认模型</div>
          <select class="form-input" id="wfModel" onchange="onModelChange(this)">
            <option value="">请选择模型</option>
          </select>
          <div class="mc-foot">
            <span class="mc-tpl" data-action="showAppTemplates()">没有想法？ 试试我们的模板 →</span>
            <span class="mc-foot-btns">
              <button class="btn" data-action="closeModal(&#x27;wfModal&#x27;)">取消</button>
              <button class="btn btn-primary" data-action="createWf()">创建 <span class="kbd-sub">Ctrl ⏎</span></button>
            </span>
          </div>
        </div>
        <div class="mc-right">
          <div id="pvWf">
            <div class="pv-title">工作流</div>
            <div class="pv-sub">基于工作流编排，适用于自动化、批处理等单轮生成类任务的场景。</div>
            <div class="pv-canvas">
              <div class="pv-flow">
                <span class="pv-node"><span class="pn-ico" style="background:#2E63F0;">✳</span>开始</span>
                <span class="pv-edge"></span>
                <span class="pv-node"><span class="pn-ico" style="background:#722ED1;">✦</span>LLM <span class="pn-sub">qwen3.7-max</span></span>
                <span class="pv-edge"></span>
                <span class="pv-node"><span class="pn-ico" style="background:#F77234;">⏹</span>结束</span>
              </div>
            </div>
          </div>
          <div id="pvCf" style="display:none;">
            <div class="pv-title">Chatflow</div>
            <div class="pv-sub">支持记忆的复杂多轮对话工作流</div>
            <div class="pv-canvas">
              <div class="pv-flow">
                <span class="pv-node"><span class="pn-ico" style="background:#2E63F0;">👤</span>用户输入</span>
                <span class="pv-edge"></span>
                <span class="pv-node"><span class="pn-ico" style="background:#722ED1;">✦</span>LLM <span class="pn-sub">qwen3.7-max</span></span>
                <span class="pv-edge"></span>
                <span class="pv-node"><span class="pn-ico" style="background:#F77234;">↩</span>直接回复</span>
              </div>
              <div class="pv-chat">
                <span class="pv-bub u">你好，帮我总结一下这份文档</span>
                <span class="pv-bub b">好的，这是文档摘要…（支持多轮记忆）</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 导出 DSL 弹窗 -->
    <div class="dsl-mask" id="dslModal">
      <div class="dsl-box">
        <div class="dsl-head">
          <h3 id="dsl-title">导出 DSL</h3>
          <button class="dsl-close" data-action="closeModal(&#x27;dslModal&#x27;)">✕</button>
        </div>
        <div class="dsl-sub">应用配置数据（DSL 格式），可复制内容或下载文件。</div>
        <div class="dsl-body">
          <textarea id="dslContent" readonly></textarea>
        </div>
        <div class="dsl-foot">
          <button class="btn" data-action="copyDsl()">📋 复制</button>
          <button class="btn btn-primary" data-action="downloadDsl()">⬇ 下载 DSL 文件</button>
        </div>
      </div>
    </div>
    
    <!-- 复制应用弹窗 -->
    <div class="copy-mask" id="copyModal">
      <div class="copy-box">
        <h3>复制应用</h3>
        <div class="copy-field">
          <label>应用名称</label>
          <input id="copyName" placeholder="请输入新应用名称">
        </div>
        <div class="copy-field">
          <label>描述</label>
          <textarea id="copyDesc" placeholder="请输入应用描述（可选）"></textarea>
        </div>
        <div class="copy-foot">
          <button class="btn" data-action="closeModal(&#x27;copyModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="copySaveBtn">复制</button>
        </div>
      </div>
    </div>
    
    <!-- 编辑信息弹窗 -->
    <div class="edit-mask" id="editModal">
      <div class="edit-box">
        <h3>编辑应用信息</h3>
        <div class="edit-icon-row">
          <span class="edit-icon-preview" id="editIconPreview"></span>
          <select id="editIconSel">
            <option value="chat">💬 聊天</option>
            <option value="robot">🤖 机器人</option>
            <option value="doc">📄 文档</option>
            <option value="num">🔢 数字</option>
          </select>
        </div>
        <div class="edit-field">
          <label>应用名称</label>
          <input id="editName" placeholder="请输入应用名称">
        </div>
        <div class="edit-field">
          <label>描述</label>
          <textarea id="editDesc" placeholder="请输入应用描述（可选）"></textarea>
        </div>
        <div class="edit-foot">
          <button class="btn" data-action="closeModal(&#x27;editModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="editSaveBtn">确定</button>
        </div>
      </div>
    </div>
    
    <!-- 删除确认弹窗 -->
    <div class="confirm-mask" id="confirm-del-mask">
      <div class="confirm-box">
        <h3>确认删除</h3>
        <p>确定要删除应用「<span id="confirm-del-name"></span>」吗？<br>此操作不可恢复。</p>
        <div class="cf-foot">
          <button class="btn" id="confirm-del-cancel">取消</button>
          <button class="btn btn-danger" id="confirm-del-ok">删除</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onActivated, onDeactivated } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal, getLoginUser } from '../utils/global'
import { apiGet, apiPost, apiDelete } from '../api/client'

/* 命名函数：点击空白处关闭卡片更多菜单 */
function onDocClick(e){
  if (!e.target.closest('.sc-more-wrap')){
    document.querySelectorAll('.sc-dd.show').forEach(function(m){ m.classList.remove('show'); });
  }
}

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
  
  /* 图标 */
  var IC = {
    chat: '<svg viewBox="0 0 24 24" fill="none" stroke="#E8B23A" stroke-width="1.8"><path d="M4 5h16v11H9l-5 4V5z"/><circle cx="9" cy="10.5" r=".8" fill="#E8B23A"/><circle cx="12.5" cy="10.5" r=".8" fill="#E8B23A"/><circle cx="16" cy="10.5" r=".8" fill="#E8B23A"/></svg>',
    robot: '<svg viewBox="0 0 24 24" fill="none" stroke="#5A6B7A" stroke-width="1.8"><rect x="5" y="8" width="14" height="10" rx="3"/><path d="M12 8V5M9 5h6"/><circle cx="9.5" cy="13" r="1" fill="#5A6B7A"/><circle cx="14.5" cy="13" r="1" fill="#5A6B7A"/><path d="M4 12v3M20 12v3"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="#4A7FE8" stroke-width="1.8"><path d="M6 3h8l4 4v14H6V3z"/><path d="M14 3v4h4"/><path d="M9 12l1.2 4L12 13l1.8 3L15 12"/></svg>',
    num: '<svg viewBox="0 0 24 24" fill="#fff"><rect x="4" y="4" width="16" height="16" rx="3" fill="none"/><text x="8" y="12" font-size="6" fill="#fff">1 2</text><text x="8" y="18" font-size="6" fill="#fff">3 4</text></svg>'
  };
  var BADGE = {
    chatflow: '<span class="sc-badge" style="background:#37B6FF;"><svg viewBox="0 0 24 24" fill="#fff"><path d="M5 5h14v9H10l-5 4V5z"/></svg></span>',
    workflow: '<span class="sc-badge" style="background:#7B5BF5;"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4"><circle cx="6" cy="12" r="2.4"/><circle cx="18" cy="12" r="2.4"/><path d="M8.4 12h7.2"/></svg></span>',
    agent: '<span class="sc-badge" style="background:#9B4DFF;"><svg viewBox="0 0 24 24" fill="#fff"><path d="M12 3l2.2 4.6L19 8.5l-3.5 3.4.8 4.9L12 14.4 7.7 16.8l.8-4.9L5 8.5l4.8-.9z"/></svg></span>'
  };
  var GLOBE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.3 3.8 5.2 3.8 8.5s-1.3 6.2-3.8 8.5c-2.5-2.3-3.8-5.2-3.8-8.5s1.3-6.2 3.8-8.5z"/></svg>';
  
  var apps = [];
  var creating = false;
  var uid = (getLoginUser() && getLoginUser().id) || '';
  var models = [];
  var selectedModel = null;
  var TYPE_LABEL = { workflow: '工作流', chatflow: 'CHATFLOW', chat: 'CHATFLOW', agent: 'AGENT', 'advanced-chat': '对话流', 'agent-chat': 'Agent' };
  var MODE_BADGE = {
    workflow: BADGE.workflow,
    chatflow: BADGE.chatflow,
    chat: BADGE.chatflow,
    agent: BADGE.agent,
    'advanced-chat': BADGE.chatflow,
    'agent-chat': BADGE.agent
  };
  var MODE_BG = { workflow: '#EDF3F8', chatflow: '#FFF6DE', chat: '#FFF6DE', agent: '#F0EBFF', 'advanced-chat': '#FFF6DE', 'agent-chat': '#F0EBFF' };

  function appBadge(mode){ return MODE_BADGE[mode] || BADGE.workflow; }
  function appIcoBg(mode){ return MODE_BG[mode] || '#EDF3F8'; }
  function studioHash(a){
    return '#/workflow-studio?id=' + encodeURIComponent(a.id) + '&mode=' + encodeURIComponent(a.mode || 'workflow');
  }

  /* 从后端加载工作流应用 */
  function loadApps(){
    apiGet('/api/workflows-app').then(function(res){
        if (res.code !== 200){ toast('加载失败: ' + (res.msg || '')); return; }
        apps = (res.data || []).map(function(a){
          return {
            id: a.id,
            name: a.name,
            type: (TYPE_LABEL[a.mode] || a.mode || '').toUpperCase(),
            mode: a.mode,
            badge: appBadge(a.mode),
            icoBg: appIcoBg(a.mode),
            ico: '<span style="font-size:24px;">' + (a.icon || '🤖') + '</span>',
            desc: a.desc,
            time: a.updated_at || ''
          };
        });
        renderApps(apps);
      })
      .catch(function(err){ toast('加载应用失败: ' + err.message); });
  }

  function loadModels(){
    apiGet('/api/model-configs').then(function(res){
        if (res.code === 200){
          models = (res.data || []).filter(function(m){ return m.status === 1; });
          renderModelOptions();
        }
      })
      .catch(function(){});
  }

  function renderModelOptions(){
    var sel = document.getElementById('wfModel');
    if (!sel) return;
    sel.innerHTML = '<option value="">请选择模型</option>' +
      models.map(function(m, i){
        return '<option value="' + i + '">' + (m.credential_name || m.model_name || m.provider) + '</option>';
      }).join('');
    if (models.length > 0){
      selectedModel = models[0];
      sel.value = '0';
    }
  }

  function renderApps(list){
    var q = (document.getElementById('q').value || '').trim();
    if (q) list = list.filter(function(a){ return a.name.indexOf(q) > -1; });
    document.getElementById('stGrid').innerHTML = list.map(function(a, i){
      var href = studioHash(a);
      return '<div class="st-card" onclick="location.hash=\'' + href + '\'" style="position:relative">' +
        '<div class="sc-more-wrap"><button class="sc-more" onclick="event.stopPropagation();toggleCardMenu(this,' + i + ')"><svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="18" cy="12" r="2"/></svg></button>' +
        '<div class="sc-dd" id="card-dd-' + i + '">' +
          '<div class="sc-dd-item" onclick="event.stopPropagation();location.hash=\'' + href + '\'">打开编排</div>' +
          '<div class="sc-dd-item" onclick="event.stopPropagation();openDslModal(' + i + ')">导出 DSL</div>' +
          '<div class="sc-dd-divider"></div>' +
          '<div class="sc-dd-item danger" onclick="event.stopPropagation();confirmDelete(' + i + ')">删除</div>' +
        '</div></div>' +
        '<div class="sc-head"><span class="sc-ico" style="background:' + a.icoBg + ';">' + a.ico + a.badge + '</span>' +
        '<span><div class="sc-name">' + a.name + '</div><div class="sc-type">' + a.type + '</div></span></div>' +
        (a.desc ? '<div class="sc-desc">' + a.desc + '</div>' : '') +
        '<div class="sc-foot">熵舟 · 编辑于 ' + a.time + '<span class="globe">' + GLOBE + '</span></div></div>';
    }).join('') || '<div style="grid-column:1/-1;text-align:center;color:var(--text-3);padding:60px 0;">未找到匹配的应用</div>';
  }
  loadApps();

  /* 搜索过滤 */
  document.getElementById('q').addEventListener('input', function(){
    renderApps(apps);
  });
  
  /* 创建下拉 */
  function closeMenus(){ document.querySelectorAll('.dd-menu.show').forEach(function(m){ m.classList.remove('show'); }); }
  window.closeMenus = closeMenus;

  /* 卡片更多菜单 */
  function toggleCardMenu(btn, idx){
    var dd = document.getElementById('card-dd-' + idx);
    var wasShow = dd.classList.contains('show');
    document.querySelectorAll('.sc-dd.show').forEach(function(m){ m.classList.remove('show'); });
    if (!wasShow) dd.classList.add('show');
  }
  window.toggleCardMenu = toggleCardMenu;
  // document 点击监听已移至 onActivated，避免重复注册
  
  /* 删除确认 */
  var deleteIdx = -1;
  function confirmDelete(idx){
    deleteIdx = idx;
    document.getElementById('confirm-del-mask').classList.add('show');
    document.getElementById('confirm-del-name').textContent = apps[idx].name;
  }
  window.confirmDelete = confirmDelete;
  document.getElementById('confirm-del-cancel').addEventListener('click', function(){
    document.getElementById('confirm-del-mask').classList.remove('show');
  });
  document.getElementById('confirm-del-mask').addEventListener('click', function(e){
    if (e.target === this) this.classList.remove('show');
  });
  document.getElementById('confirm-del-ok').addEventListener('click', function(){
    if (deleteIdx < 0 || deleteIdx >= apps.length) return;
    var app = apps[deleteIdx];
    var btn = document.getElementById('confirm-del-ok');
    btn.disabled = true;
    btn.textContent = '删除中…';
    apiDelete('/api/workflows-app/' + encodeURIComponent(app.id)).then(function(res){
      btn.disabled = false;
      btn.textContent = '删除';
      document.getElementById('confirm-del-mask').classList.remove('show');
      if (res.code === 200){
        apps.splice(deleteIdx, 1);
        renderApps(apps);
        toast('删除成功');
      } else {
        toast(res.msg || '删除失败');
      }
    })
    .catch(function(err){
      btn.disabled = false;
      btn.textContent = '删除';
      document.getElementById('confirm-del-mask').classList.remove('show');
      toast('删除失败：' + (err.message || '无法连接到后端'));
    });
  });
  
  /* 编辑信息 */
  var editIdx = -1;
  var ICON_KEYS = ['chat','robot','doc','num'];
  var ICON_EMOJI = { chat:'💬', robot:'🤖', doc:'📄', num:'🔢' };
  function openEditModal(idx){
    editIdx = idx;
    var app = apps[idx];
    document.getElementById('editName').value = app.name;
    document.getElementById('editDesc').value = app.desc || '';
    var curKey = ICON_KEYS.find(function(k){ return IC[k] === app.ico; }) || 'robot';
    document.getElementById('editIconSel').value = curKey;
    updateEditIconPreview(curKey, app.icoBg);
    openModal('editModal');
  }
  function updateEditIconPreview(key, bg){
    var el = document.getElementById('editIconPreview');
    el.style.background = bg || '#EDF3F8';
    el.innerHTML = ICON_EMOJI[key] || '🤖';
  }
  document.getElementById('editIconSel').addEventListener('change', function(){
    updateEditIconPreview(this.value, '#EDF3F8');
  });
  document.getElementById('editSaveBtn').addEventListener('click', function(){
    var name = document.getElementById('editName').value.trim();
    if (!name){ toast('请输入应用名称'); return; }
    var app = apps[editIdx];
    var key = document.getElementById('editIconSel').value;
    app.name = name;
    app.desc = document.getElementById('editDesc').value.trim();
    app.ico = IC[key];
    app.icoBg = '#EDF3F8';
    closeModal('editModal');
    renderApps(apps);
    toast('修改成功');
  });
  document.getElementById('editModal').addEventListener('click', function(e){
    if (e.target === this) closeModal('editModal');
  });
  
  /* 复制应用 */
  function copyApp(idx){
    var app = apps[idx];
    var dsl = genDsl(app);
    if (navigator.clipboard){
      navigator.clipboard.writeText(dsl).then(function(){ toast('复制成功'); });
    } else {
      var ta = document.createElement('textarea');
      ta.value = dsl; document.body.appendChild(ta);
      ta.select(); document.execCommand('copy');
      document.body.removeChild(ta);
      toast('复制成功');
    }
  }
  
  /* 复制应用 */
  var copyIdx = -1;
  function openCopyModal(idx){
    copyIdx = idx;
    var app = apps[idx];
    document.getElementById('copyName').value = app.name + ' 副本';
    document.getElementById('copyDesc').value = app.desc || '';
    openModal('copyModal');
  }
  document.getElementById('copySaveBtn').addEventListener('click', function(){
    var name = document.getElementById('copyName').value.trim();
    if (!name){ toast('请输入应用名称'); return; }
    var src = apps[copyIdx];
    var now = new Date();
    var pad = function(n){ return n < 10 ? '0' + n : '' + n; };
    var timeStr = now.getFullYear() + '/' + pad(now.getMonth()+1) + '/' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
    var newApp = {
      name: name,
      type: src.type,
      badge: src.badge,
      icoBg: src.icoBg,
      ico: src.ico,
      desc: document.getElementById('copyDesc').value.trim(),
      time: timeStr,
      href: src.href
    };
    apps.splice(copyIdx + 1, 0, newApp);
    closeModal('copyModal');
    renderApps(apps);
    toast('复制成功');
  });
  document.getElementById('copyModal').addEventListener('click', function(e){
    if (e.target === this) closeModal('copyModal');
  });
  
  /* 导出 DSL */
  var dslIdx = -1;
  function genDsl(app){
    return JSON.stringify({
      app: {
        name: app.name,
        type: app.type,
        description: app.desc || '',
        mode: app.type === 'CHATFLOW' ? 'chatflow' : (app.type === 'AGENT' ? 'agent' : 'workflow')
      },
      model_config: {
        provider: 'openai',
        model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 4096
      },
      variables: [],
      environment: [],
      history: [],
      graph: {
        nodes: [
          { id: 'start', type: 'start', title: '开始', position: {x:80, y:200} },
          { id: 'llm', type: 'llm', title: 'LLM', model: 'gpt-4', position: {x:300, y:200} },
          { id: 'end', type: 'end', title: '结束', position: {x:520, y:200} }
        ],
        edges: [
          { source: 'start', target: 'llm' },
          { source: 'llm', target: 'end' }
        ]
      },
      version: '1.0.0',
      created_at: app.time,
      exported_at: new Date().toISOString()
    }, null, 2);
  }
  function openDslModal(idx){
    dslIdx = idx;
    var app = apps[idx];
    document.getElementById('dsl-title').textContent = '导出 DSL - ' + app.name;
    document.getElementById('dslContent').value = genDsl(app);
    openModal('dslModal');
  }
  window.openDslModal = openDslModal;
  function copyDsl(){
    var ta = document.getElementById('dslContent');
    ta.select();
    if (navigator.clipboard){
      navigator.clipboard.writeText(ta.value).then(function(){ toast('已复制到剪贴板'); });
    } else {
      document.execCommand('copy');
      toast('已复制到剪贴板');
    }
  }
  function downloadDsl(){
    var app = apps[dslIdx];
    var content = document.getElementById('dslContent').value;
    var blob = new Blob([content], {type:'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = app.name.replace(/[^\w\u4e00-\u9fa5]/g,'_') + '.dsl.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('文件下载中…');
  }
  
  /* 创建空白应用弹窗 */
  var appType = 'workflow';
  function pickType(t){
    appType = t;
    document.getElementById('typeWf').classList.toggle('sel', t === 'workflow');
    document.getElementById('typeCf').classList.toggle('sel', t === 'chatflow');
    document.getElementById('pvWf').style.display = t === 'workflow' ? '' : 'none';
    document.getElementById('pvCf').style.display = t === 'chatflow' ? '' : 'none';
  }
  function openWfModal(){
    document.getElementById('wfName').value = '';
    document.getElementById('wfDesc').value = '';
    hideErr();
    pickType('workflow');
    loadModels();
    openModal('wfModal');
  }
  window.openWfModal = openWfModal;
  function hideErr(){
    document.getElementById('wfNameErr').style.display = 'none';
    document.getElementById('wfName').style.borderColor = '';
  }
  document.getElementById('wfName').addEventListener('input', hideErr);
  document.getElementById('wfName').addEventListener('keydown', function(e){
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) createWf();
  });
  function onModelChange(sel){
    var idx = parseInt(sel.value, 10);
    selectedModel = isNaN(idx) ? null : models[idx] || null;
  }
  window.onModelChange = onModelChange;

  function createWf(){
    if (creating) return;
    var name = document.getElementById('wfName').value.trim();
    if (!name){
      document.getElementById('wfNameErr').style.display = 'block';
      document.getElementById('wfName').style.borderColor = 'var(--red)';
      return;
    }
    if (!selectedModel){
      toast('请选择默认模型');
      return;
    }
    var description = document.getElementById('wfDesc').value.trim();
    var modelPayload = selectedModel ? {
      provider: selectedModel.provider || '',
      name: selectedModel.model_name || selectedModel.credential_name || '',
      mode: 'chat',
      completion_params: { temperature: 0.7 }
    } : null;
    creating = true;
    var btn = document.querySelector('[data-action="createWf()"]');
    var btnText = btn ? btn.innerHTML : '';
    if (btn) btn.innerHTML = '创建中…';
    apiPost('/api/workflows/create', { name: name, description: description, mode: appType, model: modelPayload }, { params: { uid } })
    .then(function(res){
      creating = false;
      if (btn) btn.innerHTML = btnText;
      if (res.data && res.data.id){
        closeModal('wfModal');
        toast('创建成功');
        location.hash = '#/workflow-studio?id=' + encodeURIComponent(res.data.id) + '&mode=' + encodeURIComponent(res.data.mode || appType);
      } else {
        toast(res.msg || '创建失败');
      }
    })
    .catch(function(err){
      creating = false;
      if (btn) btn.innerHTML = btnText;
      toast('创建失败：' + (err.message || '无法连接到后端'));
    });
  }

  /* ================= P3 占位功能实现 ================= */

  /* 类型筛选 */
  function openTypeFilter(){
    openModal('类型筛选',
      '<div class="filter-list">' +
        '<label class="fl-item"><input type="checkbox" checked> 工作流</label>' +
        '<label class="fl-item"><input type="checkbox" checked> Chatflow</label>' +
        '<label class="fl-item"><input type="checkbox" checked> Agent</label>' +
        '<button class="btn btn-primary" data-action="applyTypeFilter()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applyTypeFilter(){ closeModal(); toast('类型筛选已应用'); }
  window.openTypeFilter = openTypeFilter;

  /* 标签筛选 */
  function openTagFilter(){
    openModal('标签筛选',
      '<div class="filter-list">' +
        '<label class="fl-item"><input type="checkbox"> 客服</label>' +
        '<label class="fl-item"><input type="checkbox"> 营销</label>' +
        '<label class="fl-item"><input type="checkbox"> 研发</label>' +
        '<label class="fl-item"><input type="checkbox"> 数据分析</label>' +
        '<button class="btn btn-primary" data-action="applyTagFilter()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applyTagFilter(){ closeModal(); toast('标签筛选已应用'); }
  window.openTagFilter = openTagFilter;

  /* 创建者筛选 */
  function openCreatorFilter(){
    openModal('创建者筛选',
      '<div class="filter-list">' +
        '<label class="fl-item"><input type="checkbox" checked> 我创建的</label>' +
        '<label class="fl-item"><input type="checkbox" checked> 他人创建的</label>' +
        '<button class="btn btn-primary" data-action="applyCreatorFilter()" style="margin-top:10px;">应用</button>' +
      '</div>'
    );
  }
  function applyCreatorFilter(){ closeModal(); toast('创建者筛选已应用'); }
  window.openCreatorFilter = openCreatorFilter;

  /* 排序菜单 */
  function openSortMenu(){
    openModal('排序方式',
      '<div class="sort-menu">' +
        '<button class="sm-btn" data-action="setSort(\'最近修改\')">最近修改</button>' +
        '<button class="sm-btn" data-action="setSort(\'最早修改\')">最早修改</button>' +
        '<button class="sm-btn" data-action="setSort(\'名称 A-Z\')">名称 A-Z</button>' +
        '<button class="sm-btn" data-action="setSort(\'名称 Z-A\')">名称 Z-A</button>' +
      '</div>'
    );
  }
  function setSort(s){
    document.getElementById('sortLabel').textContent = s;
    closeModal();
    toast('排序：' + s);
  }
  window.openSortMenu = openSortMenu;

  /* 导入 DSL 文件 */
  function importDslFile(){
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.yaml,.yml';
    input.onchange = function(e){
      var file = e.target.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function(ev){
        try {
          var content = ev.target.result;
          var config = JSON.parse(content);
          if (config && config.app && config.app.name){
            document.getElementById('wfName').value = config.app.name + '（导入）';
            document.getElementById('wfDesc').value = config.app.description || '';
            toast('DSL 文件已加载：' + config.app.name);
          } else {
            toast('无效的 DSL 文件格式');
          }
        } catch(err){
          toast('解析失败：' + err.message);
        }
      };
      reader.readAsText(file);
    };
    input.click();
  }
  window.importDslFile = importDslFile;

  /* 新手适用说明 */
  function showNewbieHelp(){
    openModal('新手适用',
      '<div class="help-content">' +
        '<h4>推荐使用工作流</h4>' +
        '<p>如果您是初次使用，建议选择「工作流」类型：</p>' +
        '<ul>' +
          '<li>可视化拖拽编排</li>' +
          '<li>内置多种节点模板</li>' +
          '<li>支持 LLM、HTTP、代码执行等</li>' +
          '<li>适合自动化任务和批处理</li>' +
        '</ul>' +
      '</div>'
    );
  }
  window.showNewbieHelp = showNewbieHelp;

  /* 更换图标（创建弹窗内） */
  function openIconPicker(){
    openModal('选择图标',
      '<div class="icon-picker">' +
        '<div class="ip-grid">' +
          '<span class="ip-item" data-action="setAppIcon(\'🤖\')">🤖</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'💬\')">💬</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'📄\')">📄</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'🔢\')">🔢</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'🧩\')">🧩</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'⚡\')">⚡</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'🎯\')">🎯</span>' +
          '<span class="ip-item" data-action="setAppIcon(\'📊\')">📊</span>' +
        '</div>' +
      '</div>'
    );
  }
  function setAppIcon(icon){
    document.querySelector('.mc-app-ico').textContent = icon;
    closeModal();
    toast('图标已更换');
  }
  window.openIconPicker = openIconPicker;

  /* 应用模板 */
  function showAppTemplates(){
    location.hash = '#/app-templates';
    toast('跳转到模板库');
  }
  window.showAppTemplates = showAppTemplates;

});

/* keep-alive 兼容：注册/清理 document 点击监听器 */
onActivated(() => {
  document.addEventListener('click', onDocClick);
});

onDeactivated(() => {
  document.removeEventListener('click', onDocClick);
});
</script>
<style>
.studio-head{ display:flex; align-items:center; margin-bottom:16px; }
  .studio-head h2{ font-size:18px; font-weight:700; }

  .st-filter{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .sf-chip{ display:inline-flex; align-items:center; gap:6px; background:#F2F3F5; border-radius:8px; padding:7px 12px; font-size:13px; color:var(--text-2); cursor:pointer; border:1px solid transparent; }
  .sf-chip:hover{ color:var(--text-1); }
  .sf-chip b{ color:var(--text-1); font-weight:500; }
  .sf-search{ display:flex; align-items:center; gap:8px; background:#F2F3F5; border-radius:8px; padding:7px 12px; width:240px; }
  .sf-search svg{ width:14px; height:14px; color:var(--text-3); flex-shrink:0; }
  .sf-search input{ border:none; background:none; outline:none; font-size:13px; width:100%; }
  .sf-right{ margin-left:auto; display:flex; align-items:center; gap:10px; }
  .snip-btn{ display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid var(--border); border-radius:8px; padding:8px 14px; font-size:13px; color:var(--text-1); cursor:pointer; font-family:Consolas,Menlo,monospace; }
  .snip-btn:hover{ border-color:var(--primary); color:var(--primary); }
  .dd-wrap{ position:relative; }
  .dd-menu{ display:none; position:absolute; top:calc(100% + 4px); right:0; min-width:150px; background:#fff; border:1px solid var(--border); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); z-index:60; padding:4px; }
  .dd-menu.show{ display:block; }
  .dd-item{ padding:9px 12px; border-radius:6px; font-size:13px; cursor:pointer; }
  .dd-item:hover{ background:var(--primary-light); color:var(--primary); }

  /* 卡片网格 */
  .st-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:16px; }
  .st-card{ background:#fff; border:1px solid var(--border-light); border-radius:12px; padding:16px 16px 12px; cursor:pointer; display:flex; flex-direction:column; min-height:148px; transition:box-shadow .15s,border-color .15s; }
  .st-card:hover{ border-color:#B8CCFF; box-shadow:0 4px 16px rgba(46,99,240,.08); }
  .sc-head{ display:flex; gap:12px; align-items:flex-start; }
  .sc-ico{ width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; position:relative; }
  .sc-ico svg{ width:24px; height:24px; }
  .sc-badge{ position:absolute; right:-5px; bottom:-5px; width:18px; height:18px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #fff; }
  .sc-badge svg{ width:10px; height:10px; }
  .sc-name{ font-size:15px; font-weight:600; }
  .sc-type{ font-size:12px; color:var(--text-3); margin-top:2px; }
  .sc-desc{ font-size:12px; color:var(--text-2); margin-top:8px; line-height:1.6; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .sc-tag{ margin-top:12px; }
  .sc-tag button{ border:1px dashed var(--border); background:#fff; border-radius:6px; padding:3px 10px; font-size:12px; color:var(--text-3); cursor:pointer; }
  .sc-tag button:hover{ border-color:var(--primary); color:var(--primary); }
  .sc-foot{ margin-top:auto; padding-top:10px; display:flex; align-items:center; font-size:12px; color:var(--text-3); }
  .sc-foot .globe{ margin-left:auto; color:var(--text-4); }
  .sc-foot .globe svg{ width:15px; height:15px; }

  /* 卡片右上角更多按钮 */
  .sc-more{ width:28px; height:28px; border-radius:6px; border:none; background:#F4F5F7; cursor:pointer; display:flex; align-items:center; justify-content:center; z-index:5; padding:0; }
  .sc-more:hover{ background:#E8E9EB; }
  .sc-more svg{ width:16px; height:16px; }
  .sc-more svg circle{ fill:#86909C; }
  .sc-more-wrap{ position:absolute; top:10px; right:10px; z-index:10; }
  .sc-dd{ display:none; position:absolute; top:calc(100% + 4px); right:0; min-width:180px; background:#fff; border:1px solid var(--border); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); z-index:60; padding:4px; white-space:nowrap; }
  .sc-dd.show{ display:block; }
  .sc-dd-item{ padding:10px 14px; border-radius:6px; font-size:13px; cursor:pointer; color:var(--text-1); }
  .sc-dd-item:hover{ background:var(--primary-light); color:var(--primary); }
  .sc-dd-item.danger{ color:var(--red); }
  .sc-dd-item.danger:hover{ background:#FFECE8; color:var(--red); }
  .sc-dd-divider{ height:1px; background:var(--border-light); margin:4px 0; }

  /* 删除确认弹窗 */
  .confirm-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .confirm-mask.show{ display:flex; }
  .confirm-box{ background:#fff; border-radius:12px; width:360px; padding:28px 32px 24px; box-shadow:0 12px 40px rgba(0,0,0,.15); }
  .confirm-box h3{ font-size:17px; font-weight:700; margin-bottom:10px; }
  .confirm-box p{ font-size:14px; color:var(--text-2); line-height:1.6; margin-bottom:24px; }
  .confirm-box .cf-foot{ display:flex; justify-content:flex-end; gap:12px; }
  .confirm-box .cf-foot .btn{ padding:9px 24px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .confirm-box .cf-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .confirm-box .cf-foot .btn-danger{ background:var(--red); color:#fff; border-color:var(--red); font-weight:600; }
  .confirm-box .cf-foot .btn-danger:hover{ background:#E03030; border-color:#E03030; color:#fff; }

  .st-dsl{ text-align:center; color:var(--text-3); font-size:13px; padding:34px 0 20px; display:flex; align-items:center; justify-content:center; gap:6px; }
  .st-dsl svg{ width:15px; height:15px; }

  /* 创建弹窗（沿用原结构样式） */
  .modal-create{width:1100px;max-width:94vw;display:flex;padding:0;overflow:hidden;position:relative;max-height:88vh;}
  .mc-close{position:absolute;top:18px;right:20px;z-index:2;border:none;background:none;font-size:18px;color:var(--text-3);cursor:pointer;line-height:1;}
  .mc-close:hover{color:var(--text-1);}
  .mc-left{width:520px;flex-shrink:0;padding:28px 32px 24px;overflow-y:auto;}
  .mc-right{flex:1;background:#F7F8FA;padding:28px 32px;overflow-y:auto;}
  .mc-title{font-size:18px;font-weight:700;margin-bottom:22px;}
  .mc-label{font-size:14px;font-weight:600;margin:18px 0 10px;}
  .mc-label .opt-txt{color:var(--text-3);font-weight:400;font-size:12px;}
  .mc-types{display:flex;gap:12px;}
  .mc-type{flex:1;border:1.5px solid var(--border);border-radius:10px;padding:14px 14px 12px;cursor:pointer;display:flex;gap:10px;align-items:flex-start;background:#fff;}
  .mc-type:hover{border-color:var(--primary);}
  .mc-type.sel{border-color:var(--primary);box-shadow:0 0 0 2px rgba(46,99,240,.12);}
  .mt-ico{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;color:#fff;flex-shrink:0;}
  .mt-name{font-size:14.5px;font-weight:600;margin-top:4px;}
  .mt-desc{font-size:12px;color:var(--text-3);margin-top:4px;line-height:1.5;}
  .mc-newbie{display:inline-flex;align-items:center;gap:4px;font-size:13px;color:var(--text-2);margin-top:12px;cursor:pointer;}
  .mc-newbie:hover{color:var(--primary);}
  .mc-name-row{display:flex;align-items:center;gap:12px;}
  .mc-app-ico{width:42px;height:42px;border-radius:10px;background:#FFF3E4;display:flex;align-items:center;justify-content:center;font-size:23px;flex-shrink:0;cursor:pointer;}
  .mc-foot{display:flex;align-items:center;margin-top:26px;}
  .mc-tpl{font-size:13px;color:var(--text-2);cursor:pointer;}
  .mc-tpl:hover{color:var(--primary);}
  .mc-foot-btns{margin-left:auto;display:flex;gap:10px;}
  .kbd-sub{color:rgba(255,255,255,.65);font-size:11px;margin-left:2px;}
  .pv-title{font-size:16px;font-weight:700;}
  .pv-sub{font-size:13px;color:var(--text-3);margin:8px 0 20px;line-height:1.6;}
  .pv-canvas{background:#fff;border:1px solid var(--border-light);border-radius:12px;padding:34px 26px;background-image:radial-gradient(circle,#E5E8EC 1px,transparent 1px);background-size:14px 14px;}
  .pv-flow{display:flex;align-items:center;justify-content:center;gap:0;}
  .pv-node{background:#fff;border-radius:9px;box-shadow:0 2px 8px rgba(29,33,41,.10);padding:8px 12px;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;}
  .pv-node .pn-ico{width:20px;height:20px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:12px;color:#fff;}
  .pv-node .pn-sub{font-weight:400;color:var(--text-3);font-size:11px;}
  .pv-edge{width:44px;height:2px;background:#C9CDD4;position:relative;flex-shrink:0;}
  .pv-edge::after{content:"";position:absolute;right:0;top:-3px;border-left:7px solid #C9CDD4;border-top:4px solid transparent;border-bottom:4px solid transparent;}
  .pv-chat{display:flex;flex-direction:column;gap:10px;margin-top:18px;}
  .pv-bub{max-width:78%;padding:7px 11px;border-radius:8px;font-size:11.5px;color:var(--text-2);}
  .pv-bub.u{align-self:flex-end;background:var(--primary);color:#fff;border-bottom-right-radius:2px;}
  .pv-bub.b{align-self:flex-start;background:#F2F3F5;border-bottom-left-radius:2px;}
  .wf-err{display:none;color:var(--red);font-size:12px;margin-top:6px;}

  /* 导出 DSL 弹窗 */
  .dsl-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .dsl-mask.show{ display:flex; }
  .dsl-box{ background:#fff; border-radius:12px; width:640px; max-width:92vw; box-shadow:0 12px 40px rgba(0,0,0,.18); overflow:hidden; }
  .dsl-head{ display:flex; align-items:center; padding:20px 24px 0; }
  .dsl-head h3{ font-size:17px; font-weight:700; }
  .dsl-head .dsl-close{ margin-left:auto; border:none; background:none; font-size:20px; cursor:pointer; color:var(--text-3); line-height:1; padding:0 4px; }
  .dsl-head .dsl-close:hover{ color:var(--text-1); }
  .dsl-sub{ padding:6px 24px 0; font-size:13px; color:var(--text-3); }
  .dsl-body{ padding:14px 24px; }
  .dsl-body textarea{ width:100%; height:320px; border:1px solid var(--border); border-radius:8px; padding:14px; font-family:Consolas,Menlo,monospace; font-size:12.5px; line-height:1.7; resize:vertical; color:var(--text-1); background:#F7F8FA; outline:none; box-sizing:border-box; }
  .dsl-body textarea:focus{ border-color:var(--primary); }
  .dsl-foot{ display:flex; align-items:center; gap:12px; padding:0 24px 20px; }
  .dsl-foot .btn{ padding:9px 22px; border-radius:8px; font-size:13px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .dsl-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .dsl-foot .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .dsl-foot .btn-primary:hover{ background:#1B53D9; }

  /* 编辑信息弹窗 */
  .edit-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .edit-mask.show{ display:flex; }
  .edit-box{ background:#fff; border-radius:12px; width:440px; max-width:92vw; box-shadow:0 12px 40px rgba(0,0,0,.18); padding:28px 32px 24px; }
  .edit-box h3{ font-size:17px; font-weight:700; margin-bottom:20px; }
  .edit-box .edit-field{ margin-bottom:16px; }
  .edit-box .edit-field label{ display:block; font-size:13px; font-weight:600; color:var(--text-2); margin-bottom:6px; }
  .edit-box .edit-field input,.edit-box .edit-field textarea{ width:100%; border:1px solid var(--border); border-radius:8px; padding:10px 12px; font-size:14px; outline:none; box-sizing:border-box; font-family:inherit; }
  .edit-box .edit-field input:focus,.edit-box .edit-field textarea:focus{ border-color:var(--primary); }
  .edit-box .edit-field textarea{ height:80px; resize:vertical; }
  .edit-box .edit-icon-row{ display:flex; align-items:center; gap:12px; margin-bottom:16px; }
  .edit-box .edit-icon-preview{ width:48px; height:48px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:24px; flex-shrink:0; }
  .edit-box .edit-icon-row select{ flex:1; border:1px solid var(--border); border-radius:8px; padding:10px 12px; font-size:14px; outline:none; background:#fff; }
  .edit-box .edit-foot{ display:flex; justify-content:flex-end; gap:12px; margin-top:24px; }
  .edit-box .edit-foot .btn{ padding:9px 24px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .edit-box .edit-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .edit-box .edit-foot .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .edit-box .edit-foot .btn-primary:hover{ background:#1B53D9; }

  /* 复制应用弹窗 */
  .copy-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .copy-mask.show{ display:flex; }
  .copy-box{ background:#fff; border-radius:12px; width:440px; max-width:92vw; box-shadow:0 12px 40px rgba(0,0,0,.18); padding:28px 32px 24px; }
  .copy-box h3{ font-size:17px; font-weight:700; margin-bottom:20px; }
  .copy-box .copy-field{ margin-bottom:16px; }
  .copy-box .copy-field label{ display:block; font-size:13px; font-weight:600; color:var(--text-2); margin-bottom:6px; }
  .copy-box .copy-field input,.copy-box .copy-field textarea{ width:100%; border:1px solid var(--border); border-radius:8px; padding:10px 12px; font-size:14px; outline:none; box-sizing:border-box; font-family:inherit; }
  .copy-box .copy-field input:focus,.copy-box .copy-field textarea:focus{ border-color:var(--primary); }
  .copy-box .copy-field textarea{ height:80px; resize:vertical; }
  .copy-box .copy-foot{ display:flex; justify-content:flex-end; gap:12px; margin-top:24px; }
  .copy-box .copy-foot .btn{ padding:9px 24px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .copy-box .copy-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .copy-box .copy-foot .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .copy-box .copy-foot .btn-primary:hover{ background:#1B53D9; }
</style>

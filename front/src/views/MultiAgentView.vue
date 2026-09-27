<template>
  <AppShell id="page-root" active-key="multi-agent">
    <div class="page-pad">
    
          <div class="page-head">
            <div class="page-title">多智能体应用</div>
            <div class="ops">
              <div class="dd-wrap">
                <button class="btn btn-primary" id="createBtn">＋ 创建 ▾</button>
                <div class="dd-menu" id="createMenu">
                  <div class="dd-item" id="ddBlank">创建空白 Agent</div>
                  <div class="dd-item" data-action="openTemplatePicker()">从模板创建</div>
                </div>
              </div>
            </div>
          </div>
    
          <div class="ag-filter">
            <div class="pills" id="pills">
              <button class="pill active" data-f="all">全部</button>
              <button class="pill" data-f="published">已发布<span class="cnt"></span></button>
              <button class="pill" data-f="draft">草稿<span class="cnt"></span></button>
            </div>
            <span class="search-input">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
              <input id="q" placeholder="搜索">
            </span>
          </div>
    
          <div class="ag-grid" id="grid"></div>
    
        </div>
    <!-- 编辑信息弹窗 -->
    <div class="edit-mask" id="editModal">
      <div class="edit-box">
        <h3>编辑应用信息</h3>
        <div class="ef"><label>应用名称</label><input id="editName" placeholder="请输入应用名称"></div>
        <div class="ef"><label>描述</label><textarea id="editDesc" placeholder="请输入应用描述（可选）"></textarea></div>
        <div class="edit-foot">
          <button class="btn" data-action="closeModal(&#x27;editModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="editSaveBtn">确定</button>
        </div>
      </div>
    </div>
    
    <!-- 应用调用（调试）弹窗 -->
    <div class="debug-mask" id="debugModal">
      <div class="debug-box">
        <div class="debug-head">
          <div class="debug-title">
            <h3>应用调用</h3>
            <span class="debug-sub" id="debug-app-name"></span>
          </div>
          <button class="debug-close" data-action="closeModal(&#x27;debugModal&#x27;)">✕</button>
        </div>
        <div class="debug-body">
          <!-- API 地址 -->
          <div class="db-sec">
            <div class="db-sec-head">
              <div class="db-sec-title">API 地址</div>
              <div class="db-actions">
                <button class="btn" data-action="copyDebugUrl()">📋 复制</button>
                <button class="btn" data-action="shareDebug()">🔗 分享</button>
                <button class="btn" id="expBtn">▶ 体验</button>
              </div>
            </div>
            <div class="db-url-row">
              <input class="db-url" id="debugUrl" readonly>
            </div>
          </div>
          <!-- 调试对话 -->
          <div class="db-sec">
            <div class="db-sec-title">调试对话 <span class="db-hint">输入消息，调用该多智能体的运行逻辑</span></div>
            <div class="db-chat">
              <div class="db-msgs" id="debugMsgs"></div>
              <div class="db-input-row">
                <input class="db-input" id="debugInput" placeholder="输入调试消息，回车发送">
                <button class="btn btn-primary" id="debugSendBtn">发送</button>
              </div>
            </div>
          </div>
          <!-- API 调用步骤 -->
          <div class="db-sec">
            <div class="db-sec-title">API 调用步骤</div>
            <ol class="db-steps">
              <li>点击「新建 AppKey」生成访问凭证</li>
              <li>将消息 POST 至上方 API 地址，请求头携带 <code>Authorization: Bearer &lt;AppKey&gt;</code></li>
              <li>接口返回 JSON：<code>{"code":200,"data":{"reply":"回复内容"}}</code></li>
            </ol>
            <div class="db-curl"><code id="debugCurl"></code></div>
          </div>
          <!-- AppKey 列表 -->
          <div class="db-sec">
            <div class="db-sec-head">
              <div class="db-sec-title">AppKey 列表</div>
              <button class="btn btn-primary" id="addAppKeyBtn">＋ 新建 AppKey</button>
            </div>
            <table class="db-table">
              <thead><tr><th>AppKey</th><th style="width:170px">创建时间</th><th style="width:90px">状态</th><th style="width:150px">操作</th></tr></thead>
              <tbody id="appkeyTbody"></tbody>
            </table>
          </div>
          <!-- 运行中渠道 -->
          <div class="db-sec">
            <div class="db-sec-title">运行中渠道</div>
            <table class="db-table">
              <thead><tr><th>发布渠道</th><th>名称</th><th>备注</th><th>状态</th><th>最后修改人</th><th>操作</th></tr></thead>
              <tbody><tr><td colspan="6" class="db-empty">暂无运行中的渠道</td></tr></tbody>
            </table>
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
        <div class="dsl-body"><textarea id="dslContent" readonly></textarea></div>
        <div class="dsl-foot">
          <button class="btn" data-action="copyDsl()">📋 复制</button>
          <button class="btn btn-primary" data-action="downloadDsl()">⬇ 下载 DSL 文件</button>
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
    
    <!-- 创建 Agent 弹窗 -->
    <div class="modal-mask" id="createModal">
      <div class="modal" style="width:620px;">
        <div class="modal-head"><div class="modal-title">创建 Agent</div>
          <button class="modal-close" data-action="closeModal(&#x27;createModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="ca-top">
            <div class="ca-icon" title="更换图标" data-action="openCaIconPicker()">🤖<span class="edit">✎</span></div>
            <div class="ca-fields">
              <div class="f">
                <div class="ca-label">名称 <span class="req">*</span></div>
                <input class="ca-input" id="caName" placeholder="例如：Max">
                <div class="ca-err" id="caNameErr"></div>
              </div>
              <div class="f">
                <div class="ca-label">角色<span class="opt">（可选）</span></div>
                <input class="ca-input" id="caRole" placeholder="例如：研究助理">
              </div>
            </div>
          </div>
          <div class="ca-desc">
            <div class="ca-label">描述<span class="opt">（可选）</span></div>
            <textarea class="ca-input" id="caDesc" placeholder="描述这个 Agent 的用途…" style="min-height:96px;resize:vertical;line-height:1.6;"></textarea>
          </div>
          <div class="ca-foot">
            <button class="btn" data-action="closeModal(&#x27;createModal&#x27;)">取消</button>
            <button class="btn btn-primary" data-action="doCreate()">创建</button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onUnmounted, onActivated } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'
import { registerListGlobals } from '../utils/listGlobals'

/* keep-alive 下 onMounted 只跑一次，而这批内联 onclick 入口与“工作流应用 / 我的应用 /
   单智能体”重名，谁最后挂载谁占着 window。留一个可重放的引用，由 onActivated 重登记。 */
var _rebindListGlobals = null

/* 下拉菜单的全局点击关闭（提升为顶层：离开页面时可移除监听器，避免泄漏报错） */
function onDocClick(e){
  var cm = document.getElementById('createMenu');
  if (cm) cm.classList.remove('show');
  if (!e || !e.target || !e.target.closest || !e.target.closest('.ag-more-wrap')){
    document.querySelectorAll('.ag-dd.show').forEach(function(m){ m.classList.remove('show'); });
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
  
  var agents = [];          // 多智能体应用（来自 /api/multi-agents）
  var loaded = false;       // 列表是否已从后端加载完成
  var curFilter = 'all';
  /* 不再传 uid：列表与创建都按登录 token 里的账号归属走（后端 _safe_uid 只认 token） */

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* 更新时间显示 */
  function fmtUpd(ts){
    if (!ts) return '';
    var t = new Date(ts.replace(/-/g, '/'));
    var diff = (Date.now() - t.getTime()) / 1000;
    var p = function(n){ return n < 10 ? '0' + n : '' + n; };
    if (diff < 60) return '更新于 刚刚';
    if (diff < 3600) return '更新于 ' + Math.floor(diff / 60) + ' 分钟前';
    if (diff < 86400) return '更新于 ' + p(t.getHours()) + ':' + p(t.getMinutes());
    if (diff < 172800) return '更新于 昨天';
    return '更新于 ' + (t.getMonth() + 1) + '-' + t.getDate();
  }

  /* 从后端加载多智能体列表（当前登录用户创建的） */
  function loadAgents(){
    apiGet('/api/multi-agents').then(function(data){
      loaded = true;
      if (data.code === 200){
        agents = data.data || [];
        render();
        updatePills();
      } else {
        document.getElementById('grid').innerHTML = '<div class="ag-none">加载失败：' + esc(data.msg || '未知错误') + '</div>';
      }
    });
  }

  /* 胶囊计数：按列表实际状态统计 */
  function updatePills(){
    var published = agents.filter(function(a){ return a.status === 'published'; }).length;
    document.querySelector('#pills .pill[data-f="published"] .cnt').textContent = published;
    document.querySelector('#pills .pill[data-f="draft"] .cnt').textContent = agents.length - published;
  }
  
  function render(){
    var q = document.getElementById('q').value.trim();
    var list = agents.filter(function(a){
      var okF = curFilter === 'all' || a.status === curFilter;
      var okQ = !q || a.name.indexOf(q) > -1;
      return okF && okQ;
    });
    var grid = document.getElementById('grid');
    if (!list.length){
      grid.innerHTML = loaded
        ? '<div class="ag-none">暂无匹配的 Agent</div>'
        : '<div class="ag-none">加载中…</div>';
      return;
    }
    grid.innerHTML = list.map(function(a){
      var realIdx = agents.indexOf(a);
      var tag = a.status === 'published'
        ? '<span class="ag-tag published">已发布</span>'
        : '<span class="ag-tag">草稿</span>';
      return '<div class="ag-card" onclick="location.hash=\'/multi-agent-edit?id=' + a.id + '\'" style="position:relative">' + tag +
        '<div class="ag-more-wrap"><button class="ag-more" onclick="event.stopPropagation();toggleCardMenu(this,' + realIdx + ')"><svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="18" cy="12" r="2"/></svg></button>' +
        '<div class="ag-dd" id="card-dd-' + realIdx + '">' +
          '<div class="ag-dd-item" onclick="event.stopPropagation();openEditModal(' + realIdx + ')">编辑信息</div>' +
          '<div class="ag-dd-item' + (a.status === 'published' ? '' : ' disabled') + '" onclick="event.stopPropagation();' + (a.status === 'published' ? 'openDebug(' + realIdx + ')' : 'toast(\'未发布的应用不可调试，请先发布\')') + '">调试</div>' +
          '<div class="ag-dd-item" onclick="event.stopPropagation();toast(\'添加标签\')">添加标签</div>' +
          '<div class="ag-dd-divider"></div>' +
          '<div class="ag-dd-item" onclick="event.stopPropagation();location.hash=\'/multi-agent-edit?id=' + a.id + '\'">打开</div>' +
          '<div class="ag-dd-divider"></div>' +
          '<div class="ag-dd-item danger" onclick="event.stopPropagation();confirmDelete(' + realIdx + ')">删除</div>' +
        '</div></div>' +
        '<div class="ag-head"><span class="ag-ico">' + esc(a.icon) + '</span><span class="ag-name">' + esc(a.name) + '</span></div>' +
        '<div class="ag-foot">' + fmtUpd(a.updated_at) + '</div></div>';
    }).join('');
  }
  
  /* 胶囊过滤 */
  document.querySelectorAll('#pills .pill').forEach(function(p){
    p.addEventListener('click', function(){
      document.querySelectorAll('#pills .pill').forEach(function(x){ x.classList.remove('active'); });
      p.classList.add('active');
      curFilter = p.dataset.f;
      render();
    });
  });
  document.getElementById('q').addEventListener('input', render);
  
  /* 创建下拉菜单 */
  var createMenu = document.getElementById('createMenu');
  document.getElementById('createBtn').addEventListener('click', function(e){
    e.stopPropagation();
    createMenu.classList.toggle('show');
  });
  document.getElementById('ddBlank').addEventListener('click', function(){
    createMenu.classList.remove('show');
    resetCreateForm();
    openModal('createModal');
  });
  document.addEventListener('click', onDocClick);
  
  /* 创建 Agent 弹窗 */
  function resetCreateForm(){
    var name = document.getElementById('caName');
    name.value = '';
    name.classList.remove('err');
    document.getElementById('caNameErr').textContent = '';
    document.getElementById('caRole').value = '';
    document.getElementById('caDesc').value = '';
  }
  document.getElementById('caName').addEventListener('input', function(){
    this.classList.remove('err');
    document.getElementById('caNameErr').textContent = '';
  });
  function doCreate(){
    var name = document.getElementById('caName');
    var btn = document.querySelector('#createModal .btn-primary');
    if (!name.value.trim()){
      name.classList.add('err');
      document.getElementById('caNameErr').textContent = '请输入名称';
      name.focus();
      return;
    }
    if (btn.dataset.busy) return;
    btn.dataset.busy = '1';
    btn.textContent = '创建中…';
    apiPost('/api/multi-agents', {
      name: name.value.trim(),
      role: document.getElementById('caRole').value.trim(),
      description: document.getElementById('caDesc').value.trim()
    }).then(function(data){
      delete btn.dataset.busy;
      btn.textContent = '创建';
      if (data.code === 200){
        closeModal('createModal');
        agents.unshift(data.data);
        render();
        updatePills();
        toast('多智能体「' + data.data.name + '」创建成功');
      } else {
        toast(data.msg || '创建失败');
      }
    });
  }
  
  render();          // 初始占位：加载完成前显示「加载中…」
  loadAgents();
  
  /* 卡片更多菜单 */
  function toggleCardMenu(btn, idx){
    var dd = document.getElementById('card-dd-' + idx);
    var wasShow = dd.classList.contains('show');
    document.querySelectorAll('.ag-dd.show').forEach(function(m){ m.classList.remove('show'); });
    if (!wasShow) dd.classList.add('show');
  }
  /* 编辑信息 */
  var editIdx = -1;
  function openEditModal(idx){
    editIdx = idx;
    document.getElementById('editName').value = agents[idx].name;
    document.getElementById('editDesc').value = agents[idx].description || '';
    openModal('editModal');
  }
  document.getElementById('editSaveBtn').addEventListener('click', function(){
    var name = document.getElementById('editName').value.trim();
    if (!name){ toast('请输入应用名称'); return; }
    var a = agents[editIdx];
    if (!a) return;
    apiPut('/api/multi-agents/' + a.id, { name: name, description: document.getElementById('editDesc').value.trim() }).then(function(data){
      if (data.code === 200){
        closeModal('editModal');
        loadAgents();
        toast('修改成功');
      } else {
        toast(data.msg || '修改失败');
      }
    });
  });
  document.getElementById('editModal').addEventListener('click', function(e){
    if (e.target === this) closeModal('editModal');
  });
  
  /* 应用调用（调试） */
  var debugIdx = -1;
  function copyText(t){
    if (navigator.clipboard){ navigator.clipboard.writeText(t).then(function(){ toast('已复制到剪贴板'); }); }
    else toast('复制失败，请手动复制');
  }
  function debugApiUrl(a){
    return location.protocol + '//' + location.hostname + ':5000/api/multi-agents/' + a.id + '/debug';
  }
  function openDebug(idx){
    debugIdx = idx;
    var a = agents[idx];
    if (!a) return;
    if (a.status !== 'published'){
      toast('该应用未发布，请先发布后再调试');
      return;
    }
    document.getElementById('debug-app-name').textContent = '「' + a.name + '」';
    var url = debugApiUrl(a);
    document.getElementById('debugUrl').value = url;
    document.getElementById('debugCurl').textContent =
      'curl -X POST ' + url + ' \\' +
      "\n  -H 'Content-Type: application/json'" +
      "\n  -H 'Authorization: Bearer <你的AppKey>'" +
      '\n  -d \'{"message":"你好"}\'';
    document.getElementById('debugMsgs').innerHTML = '';
    document.getElementById('debugInput').value = '';
    loadAppKeys();
    openModal('debugModal');
    setTimeout(function(){ document.getElementById('debugInput').focus(); }, 60);
  }
  function loadAppKeys(){
    var a = agents[debugIdx];
    if (!a) return;
    apiGet('/api/multi-agents/' + a.id + '/appkeys').then(function(data){
      var tb = document.getElementById('appkeyTbody');
      var keys = (data.code === 200 && data.data) || [];
      if (!keys.length){ tb.innerHTML = '<tr><td colspan="4" class="db-empty">暂无 AppKey，点击右上角「＋ 新建 AppKey」生成</td></tr>'; return; }
      tb.innerHTML = keys.map(function(k){
        return '<tr>' +
          '<td><code class="db-key">' + esc(k.key) + '</code></td>' +
          '<td>' + esc(k.created_at || '') + '</td>' +
          '<td><span class="db-switch' + (k.enabled ? ' on' : '') + '" data-key="' + esc(k.key) + '" title="点击启用/禁用"></span></td>' +
          '<td><button class="link" data-copy="' + esc(k.key) + '">复制</button>' +
          '<button class="link link-red" data-del="' + esc(k.key) + '">删除</button></td>' +
        '</tr>';
      }).join('');
    });
  }
  document.getElementById('addAppKeyBtn').addEventListener('click', function(){
    var a = agents[debugIdx];
    if (!a) return;
    apiPost('/api/multi-agents/' + a.id + '/appkeys').then(function(data){
      if (data.code === 200){ toast('AppKey 生成成功'); loadAppKeys(); }
      else toast(data.msg || '生成失败');
    });
  });
  document.getElementById('appkeyTbody').addEventListener('click', function(e){
    var k = e.target.getAttribute('data-copy');
    if (k){ copyText(k); return; }
    k = e.target.getAttribute('data-del');
    if (k){
      if (!confirm('确定删除该 AppKey 吗？')) return;
      var a = agents[debugIdx];
      apiDelete('/api/multi-agents/' + a.id + '/appkeys/' + encodeURIComponent(k)).then(function(d){
        if (d.code === 200){ toast('已删除'); loadAppKeys(); } else toast(d.msg || '删除失败');
      });
      return;
    }
    var sw = e.target.closest('.db-switch');
    if (sw){
      var key = sw.getAttribute('data-key');
      var enabled = !sw.classList.contains('on');
      sw.classList.toggle('on', enabled);
      var a = agents[debugIdx];
      apiPut('/api/multi-agents/' + a.id + '/appkeys/' + encodeURIComponent(key), { enabled: enabled }).then(function(d){
        if (d.code !== 200){ sw.classList.toggle('on', !enabled); toast(d.msg || '操作失败'); }
      });
    }
  });
  function sendDebug(){
    var a = agents[debugIdx];
    if (!a) return;
    var inp = document.getElementById('debugInput');
    var msg = inp.value.trim();
    if (!msg){ toast('请输入调试消息'); return; }
    var msgs = document.getElementById('debugMsgs');
    msgs.innerHTML += '<div class="db-msg user"><span class="db-bubble">' + esc(msg) + '</span></div>';
    inp.value = '';
    var row = document.createElement('div');
    row.className = 'db-msg bot';
    row.innerHTML = '<span class="db-bubble loading">思考中…</span>';
    msgs.appendChild(row);
    msgs.scrollTop = msgs.scrollHeight;
    var btn = document.getElementById('debugSendBtn');
    btn.disabled = true; btn.textContent = '调用中…';
    function done(){
      btn.disabled = false; btn.textContent = '发送';
      msgs.scrollTop = msgs.scrollHeight;
    }
    apiPost('/api/multi-agents/' + a.id + '/debug', { message: msg }).then(function(data){
      var b = row.querySelector('.db-bubble');
      b.classList.remove('loading');
      if (data.code === 200 && data.data && data.data.reply){
        b.textContent = data.data.reply;
        // 显示处理该消息的 Agent 名称
        if (data.data.handled_by){
          var tag = document.createElement('div');
          tag.className = 'db-agent-tag';
          tag.textContent = '🤖 ' + data.data.handled_by;
          row.appendChild(tag);
        }
      } else {
        b.className = 'db-bubble err';
        b.textContent = '调用失败：' + (data.msg || '未知错误');
      }
      done();
    }).catch(function(){
      var b = row.querySelector('.db-bubble');
      b.classList.remove('loading');
      b.className = 'db-bubble err';
      b.textContent = '网络异常，请稍后重试';
      done();
    });
  }
  document.getElementById('debugSendBtn').addEventListener('click', sendDebug);
  document.getElementById('debugInput').addEventListener('keydown', function(e){ if (e.key === 'Enter') sendDebug(); });
  document.getElementById('expBtn').addEventListener('click', function(){
    var inp = document.getElementById('debugInput');
    inp.focus();
    toast('请输入消息，体验该多智能体的调用效果');
  });
  function copyDebugUrl(){
    var v = document.getElementById('debugUrl').value;
    copyText(v || '暂无地址');
  }
  function shareDebug(){
    var a = agents[debugIdx];
    if (a) copyText(location.origin + '/#/multi-agent-edit?id=' + a.id);
  }

  /* 内联 onclick 全局可调用：挂载到 window（函数声明已提升，无顺序问题） */
  window.toggleCardMenu = toggleCardMenu;
  window.openEditModal = openEditModal;
  window.openDebug = openDebug;
  window.sendDebug = sendDebug;
  window.copyDebugUrl = copyDebugUrl;
  window.shareDebug = shareDebug;
  window.confirmDelete = confirmDelete;

  /* 上面是挂载时的首次登记；这份可重放实现由 onActivated 在每次回到本页时跑一次，
     保证 window 上永远是当前可见页面的闭包。 */
  _rebindListGlobals = function(){
    registerListGlobals({
      toggleCardMenu: toggleCardMenu, openEditModal: openEditModal, openDebug: openDebug,
      sendDebug: sendDebug, copyDebugUrl: copyDebugUrl, shareDebug: shareDebug,
      confirmDelete: confirmDelete, openTemplatePicker: openTemplatePicker,
      openCaIconPicker: openCaIconPicker,
    })
  }
  var dslIdx = -1;
  function genDsl(a){
    return JSON.stringify({
      app: { name: a.name, type: 'multi-agent', description: a.desc || '', mode: 'agent' },
      model_config: { provider: 'openai', model: 'gpt-4', temperature: 0.7, max_tokens: 4096 },
      variables: [], environment: [], history: [],
      graph: { nodes: [
        { id: 'start', type: 'start', title: '开始', position: {x:80, y:200} },
        { id: 'llm', type: 'llm', title: 'LLM', model: 'gpt-4', position: {x:300, y:200} },
        { id: 'end', type: 'end', title: '结束', position: {x:520, y:200} }
      ], edges: [
        { source: 'start', target: 'llm' },
        { source: 'llm', target: 'end' }
      ]},
      version: '1.0.0', updated: a.updated, exported_at: new Date().toISOString()
    }, null, 2);
  }
  function openDslModal(idx){
    dslIdx = idx;
    document.getElementById('dsl-title').textContent = '导出 DSL - ' + agents[idx].name;
    document.getElementById('dslContent').value = genDsl(agents[idx]);
    openModal('dslModal');
  }
  function copyDsl(){
    var ta = document.getElementById('dslContent');
    ta.select();
    if (navigator.clipboard){ navigator.clipboard.writeText(ta.value).then(function(){ toast('已复制到剪贴板'); }); }
    else { document.execCommand('copy'); toast('已复制到剪贴板'); }
  }
  function downloadDsl(){
    var a = agents[dslIdx];
    var blob = new Blob([document.getElementById('dslContent').value], {type:'application/json'});
    var url = URL.createObjectURL(blob);
    var el = document.createElement('a');
    el.href = url; el.download = a.name.replace(/[^\w\u4e00-\u9fa5]/g,'_') + '.dsl.json';
    document.body.appendChild(el); el.click(); document.body.removeChild(el);
    URL.revokeObjectURL(url); toast('文件下载中…');
  }
  
  /* 删除确认 */
  var deleteIdx = -1;
  function confirmDelete(idx){
    deleteIdx = idx;
    document.getElementById('confirm-del-mask').classList.add('show');
    document.getElementById('confirm-del-name').textContent = agents[idx].name;
  }
  document.getElementById('confirm-del-cancel').addEventListener('click', function(){
    document.getElementById('confirm-del-mask').classList.remove('show');
  });
  document.getElementById('confirm-del-mask').addEventListener('click', function(e){
    if (e.target === this) this.classList.remove('show');
  });
  document.getElementById('confirm-del-ok').addEventListener('click', function(){
    var a = agents[deleteIdx];
    if (a){
      apiDelete('/api/multi-agents/' + a.id).then(function(data){
        if (data.code === 200){
          loadAgents();
          toast('删除成功');
        } else {
          toast(data.msg || '删除失败');
        }
      });
    }
    document.getElementById('confirm-del-mask').classList.remove('show');
  });

  /* ================= P3 占位功能实现 ================= */

  /* 从模板创建 */
  function openTemplatePicker(){
    openModal('选择模板',
      '<div class="tpl-picker">' +
        '<div class="tpl-card" data-action="createFromTemplate(\'客服多智能体\')">' +
          '<span class="tpl-ico">💬</span><div class="tpl-info"><div class="tpl-name">客服多智能体</div><div class="tpl-desc">协调售前/售后多个子 Agent</div></div>' +
        '</div>' +
        '<div class="tpl-card" data-action="createFromTemplate(\'研发多智能体\')">' +
          '<span class="tpl-ico">💻</span><div class="tpl-info"><div class="tpl-name">研发多智能体</div><div class="tpl-desc">协调代码审查/开发/文档</div></div>' +
        '</div>' +
        '<div class="tpl-card" data-action="createFromTemplate(\'营销多智能体\')">' +
          '<span class="tpl-ico">📈</span><div class="tpl-info"><div class="tpl-name">营销多智能体</div><div class="tpl-desc">协调内容/数据/投放</div></div>' +
        '</div>' +
      '</div>'
    );
  }
  function createFromTemplate(name){
    closeModal();
    document.getElementById('caName').value = name;
    document.getElementById('createBtn').click();
    toast('已选择模板：' + name);
  }
  window.openTemplatePicker = openTemplatePicker;

  /* 更换图标选择器 */
  function openCaIconPicker(){
    openModal('选择图标',
      '<div class="icon-picker"><div class="ip-grid">' +
        '<span class="ip-item" data-action="setCaIcon(\'🤖\')">🤖</span>' +
        '<span class="ip-item" data-action="setCaIcon(\'👥\')">👥</span>' +
        '<span class="ip-item" data-action="setCaIcon(\'🧩\')">🧩</span>' +
        '<span class="ip-item" data-action="setCaIcon(\'⚡\')">⚡</span>' +
        '<span class="ip-item" data-action="setCaIcon(\'🎯\')">🎯</span>' +
        '<span class="ip-item" data-action="setCaIcon(\'📊\')">📊</span>' +
      '</div></div>'
    );
  }
  function setCaIcon(icon){
    document.querySelector('.ca-icon').innerHTML = icon + '<span class="edit">✎</span>';
    closeModal();
    toast('图标已更换');
  }
  window.openCaIconPicker = openCaIconPicker;

})

onUnmounted(function(){
  /* 组件卸载时移除全局监听器，防止在其他页面点击时反复执行 */
  document.removeEventListener('click', onDocClick);
});
onActivated(function(){
  /* 抢回本视图的内联 onclick 入口（见 _rebindListGlobals 注释） */
  if (_rebindListGlobals) _rebindListGlobals();
});
</script>
<style>
/* ---------- Agents 卡片网格 ---------- */
  .ag-title{ font-size:22px; font-weight:700; }
  .ag-filter{ display:flex; align-items:center; gap:8px; margin-top:16px; }
  .ag-filter .search-input{ margin-left:auto; min-width:220px; }
  .pill .cnt{ background:#fff; border-radius:8px; padding:0 6px; font-size:11px; margin-left:4px; color:var(--text-3); }
  .pill.active .cnt{ background:rgba(46,99,240,.12); color:var(--primary); }

  .ag-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:16px; }
  @media (max-width:1400px){ .ag-grid{ grid-template-columns:repeat(2,1fr);} }
  .ag-card{ background:#fff; border-radius:10px; border:1px solid var(--border-light); padding:20px; position:relative; cursor:pointer; transition:box-shadow .15s; min-height:158px; display:flex; flex-direction:column; }
  .ag-card:hover{ box-shadow:0 4px 16px rgba(29,33,41,.08); }
  .ag-head{ display:flex; align-items:center; gap:12px; }
  .ag-ico{ width:46px; height:46px; border-radius:10px; background:var(--primary-light); display:flex; align-items:center; justify-content:center; font-size:25px; flex-shrink:0; }
  .ag-name{ font-size:16px; font-weight:600; }
  .ag-foot{ margin-top:auto; padding-top:26px; font-size:12px; color:var(--text-3); }
  .ag-tag{ position:absolute; top:0; right:0; font-size:11px; padding:3px 10px; border-radius:0 10px 0 10px; background:#F2F3F5; color:var(--text-3); }
  .ag-tag.published{ background:var(--green-bg); color:var(--green); }
  .ag-none{ grid-column:1/-1; text-align:center; color:var(--text-3); padding:60px 0; font-size:13px; }

  /* 卡片右上角更多按钮 */
  .ag-more{ position:absolute; top:10px; right:10px; width:28px; height:28px; border-radius:6px; border:none; background:#F4F5F7; cursor:pointer; display:flex; align-items:center; justify-content:center; z-index:5; padding:0; }
  .ag-more:hover{ background:#E8E9EB; }
  .ag-more svg{ width:16px; height:16px; }
  .ag-more svg circle{ fill:#86909C; }
  .ag-more-wrap{ position:relative; }
  .ag-dd{ display:none; position:absolute; top:calc(100% + 4px); right:0; min-width:180px; background:#fff; border:1px solid var(--border); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); z-index:60; padding:4px; }
  .ag-dd.show{ display:block; }
  .ag-dd-item{ padding:10px 14px; border-radius:6px; font-size:13px; cursor:pointer; color:var(--text-1); }
  .ag-dd-item:hover{ background:var(--primary-light); color:var(--primary); }
  .ag-dd-item.disabled{ color:var(--text-4); cursor:not-allowed; }
  .ag-dd-item.disabled:hover{ background:transparent; color:var(--text-4); }
  .ag-dd-item.danger{ color:var(--red); }
  .ag-dd-item.danger:hover{ background:#FFECE8; color:var(--red); }
  .ag-dd-divider{ height:1px; background:var(--border-light); margin:4px 0; }

  /* 编辑信息弹窗 */
  .edit-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .edit-mask.show{ display:flex; }
  .edit-box{ background:#fff; border-radius:12px; width:440px; max-width:92vw; box-shadow:0 12px 40px rgba(0,0,0,.18); padding:28px 32px 24px; }
  .edit-box h3{ font-size:17px; font-weight:700; margin-bottom:20px; }
  .edit-box .ef{ margin-bottom:16px; }
  .edit-box .ef label{ display:block; font-size:13px; font-weight:600; color:var(--text-2); margin-bottom:6px; }
  .edit-box .ef input,.edit-box .ef textarea{ width:100%; border:1px solid var(--border); border-radius:8px; padding:10px 12px; font-size:14px; outline:none; box-sizing:border-box; font-family:inherit; }
  .edit-box .ef input:focus,.edit-box .ef textarea:focus{ border-color:var(--primary); }
  .edit-box .ef textarea{ height:80px; resize:vertical; }
  .edit-box .edit-foot{ display:flex; justify-content:flex-end; gap:12px; margin-top:24px; }
  .edit-box .edit-foot .btn{ padding:9px 24px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .edit-box .edit-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .edit-box .edit-foot .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .edit-box .edit-foot .btn-primary:hover{ background:#1B53D9; }

  /* 应用调用（调试）弹窗 */
  .debug-mask{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:300; display:none; align-items:center; justify-content:center; }
  .debug-mask.show{ display:flex; }
  .debug-box{ background:#fff; border-radius:12px; width:860px; max-width:94vw; max-height:92vh; box-shadow:0 12px 40px rgba(0,0,0,.18); overflow:hidden; display:flex; flex-direction:column; }
  .debug-head{ display:flex; align-items:center; padding:20px 24px 14px; }
  .debug-title{ display:flex; align-items:baseline; gap:10px; }
  .debug-title h3{ font-size:17px; font-weight:700; }
  .debug-sub{ font-size:13px; color:var(--text-3); }
  .debug-close{ margin-left:auto; border:none; background:none; font-size:20px; cursor:pointer; color:var(--text-3); line-height:1; padding:0 4px; }
  .debug-close:hover{ color:var(--text-1); }
  .debug-body{ padding:0 24px 20px; overflow-y:auto; }
  .db-sec{ margin-top:16px; }
  .db-sec-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
  .db-sec-title{ font-size:13px; font-weight:600; color:var(--text-1); }
  .db-hint{ font-weight:400; color:var(--text-3); margin-left:6px; font-size:12px; }
  .db-actions{ display:flex; gap:8px; }
  .db-actions .btn{ padding:5px 12px; font-size:12px; border-radius:6px; border:1px solid var(--border); background:#fff; color:var(--text-1); cursor:pointer; }
  .db-actions .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .db-url-row{ display:flex; }
  .db-url{ flex:1; border:1px solid var(--border); border-radius:8px; padding:10px 12px; font-size:12.5px; font-family:Consolas,Menlo,monospace; background:#F7F8FA; color:var(--text-2); outline:none; box-sizing:border-box; }
  .db-chat{ border:1px solid var(--border); border-radius:8px; overflow:hidden; }
  .db-msgs{ height:210px; overflow-y:auto; padding:14px; background:#FAFBFC; display:flex; flex-direction:column; gap:10px; }
  .db-msg{ display:flex; }
  .db-msg.user{ justify-content:flex-end; }
  .db-bubble{ max-width:78%; padding:9px 13px; border-radius:10px; font-size:13px; line-height:1.65; background:#E8F0FE; color:var(--text-1); white-space:pre-wrap; word-break:break-word; }
  .db-msg.bot .db-bubble{ background:#fff; border:1px solid var(--border); }
  .db-bubble.loading{ color:var(--text-3); }
  .db-bubble.err{ background:#FFECE8; border-color:#FFCDC7; color:#E03030; }
  .db-agent-tag{ font-size:11px; color:var(--text-3); margin-top:4px; padding:2px 8px; background:#F2F3F5; border-radius:4px; display:inline-block; }
  .db-input-row{ display:flex; gap:10px; padding:10px; border-top:1px solid var(--border); background:#fff; }
  .db-input{ flex:1; border:1px solid var(--border); border-radius:8px; padding:9px 12px; font-size:13px; outline:none; box-sizing:border-box; }
  .db-input:focus{ border-color:var(--primary); }
  .db-input-row .btn{ padding:8px 22px; border-radius:8px; font-size:13px; cursor:pointer; border:1px solid var(--primary); background:var(--primary); color:#fff; }
  .db-input-row .btn:hover{ background:#1B53D9; }
  .db-input-row .btn:disabled{ opacity:.6; cursor:not-allowed; }
  .db-steps{ margin:8px 0; padding-left:20px; }
  .db-steps li{ font-size:12.5px; color:var(--text-2); line-height:2; }
  .db-steps code{ background:#F2F3F5; border-radius:4px; padding:1px 5px; font-size:11.5px; }
  .db-curl{ background:#1D2129; border-radius:8px; padding:12px 14px; }
  .db-curl code{ color:#A9D58C; font-size:12px; line-height:1.7; white-space:pre-wrap; word-break:break-all; font-family:Consolas,Menlo,monospace; }
  .db-table{ width:100%; border-collapse:collapse; font-size:12.5px; }
  .db-table th{ text-align:left; padding:9px 10px; background:#F7F8FA; color:var(--text-3); font-weight:500; border:1px solid var(--border-light); }
  .db-table td{ padding:9px 10px; border:1px solid var(--border-light); color:var(--text-1); }
  .db-key{ font-family:Consolas,Menlo,monospace; font-size:12px; color:var(--text-1); }
  .db-table .link{ background:none; border:none; color:var(--primary); cursor:pointer; font-size:12px; padding:0 4px; }
  .db-table .link.link-red{ color:var(--red); }
  .db-switch{ position:relative; display:inline-block; width:36px; height:20px; border-radius:10px; background:#C9CDD4; cursor:pointer; transition:background .15s; vertical-align:middle; }
  .db-switch::after{ content:''; position:absolute; top:2px; left:2px; width:16px; height:16px; border-radius:50%; background:#fff; transition:left .15s; }
  .db-switch.on{ background:var(--green); }
  .db-switch.on::after{ left:18px; }
  .db-empty{ text-align:center; color:var(--text-3); padding:16px 0; }

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
  .dsl-foot{ display:flex; align-items:center; gap:12px; padding:0 24px 20px; }
  .dsl-foot .btn{ padding:9px 22px; border-radius:8px; font-size:13px; cursor:pointer; border:1px solid var(--border); background:#fff; color:var(--text-1); }
  .dsl-foot .btn:hover{ border-color:var(--primary); color:var(--primary); }
  .dsl-foot .btn-primary{ background:var(--primary); color:#fff; border-color:var(--primary); }
  .dsl-foot .btn-primary:hover{ background:#1B53D9; }

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

  /* ---------- 创建下拉 ---------- */
  .dd-wrap{ position:relative; }
  .dd-menu{ position:absolute; top:calc(100% + 6px); right:0; background:#fff; border:1px solid var(--border-light); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); min-width:160px; padding:6px; display:none; z-index:30; }
  .dd-menu.show{ display:block; }
  .dd-item{ padding:8px 12px; border-radius:6px; font-size:13px; cursor:pointer; color:var(--text-1); white-space:nowrap; }
  .dd-item:hover{ background:#F2F3F5; color:var(--primary); }

  /* ---------- 创建 Agent 弹窗 ---------- */
  .ca-top{ display:flex; gap:22px; align-items:flex-start; }
  .ca-icon{ width:72px; height:72px; border-radius:14px; background:var(--primary-light); font-size:38px; display:flex; align-items:center; justify-content:center; position:relative; cursor:pointer; flex-shrink:0; }
  .ca-icon .edit{ position:absolute; right:-7px; bottom:-7px; width:22px; height:22px; border-radius:50%; background:#fff; border:1px solid var(--border); font-size:11px; display:flex; align-items:center; justify-content:center; color:var(--text-2); box-shadow:0 1px 4px rgba(0,0,0,.1); }
  .ca-fields{ flex:1; display:flex; gap:16px; }
  .ca-fields .f{ flex:1; }
  .ca-label{ font-size:13px; color:var(--text-1); margin-bottom:8px; }
  .ca-label .req{ color:var(--red); }
  .ca-label .opt{ color:var(--text-3); font-weight:400; margin-left:2px; }
  .ca-input{ width:100%; border:1px solid transparent; background:#F7F8FA; border-radius:8px; padding:9px 12px; font-size:14px; transition:.15s; }
  .ca-input:focus{ background:#fff; border-color:var(--primary); box-shadow:0 0 0 2px rgba(46,99,240,.12); }
  .ca-input.err{ background:#fff; border-color:var(--red); }
  .ca-err{ color:var(--red); font-size:12px; min-height:18px; margin-top:5px; }
  .ca-desc{ margin-top:18px; }
  .ca-foot{ display:flex; justify-content:flex-end; gap:12px; margin-top:22px; }
</style>

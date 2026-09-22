<template>
  <div id="page-root" class="page-root agent-detail-root">
    <div class="ad-shell">
      <!-- 左窄栏 -->
      <aside class="ad-side">
        <div class="ad-side-top">
          <button class="ad-back" title="返回" data-action="goBack()">‹</button>
          <span class="ad-home" title="首页" data-action="location.hash = '/home'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg></span>
          <span class="ad-crumb">/ AGENTS</span>
          <span class="sp">
            <button class="ad-icobtn" data-action="toast(&#x27;暂无新通知&#x27;)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2 2 0 0 0 4 0"/></svg><span class="dot"></span></button>
            <button class="ad-icobtn" data-action="toggleSidePanel()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg></button>
          </span>
        </div>
    
        <div class="ad-agent">
          <span class="ava" id="sideIcon">🤖</span>
          <span class="nm" id="sideName">加载中…</span>
          <button class="more" data-action="openMoreMenu()">…</button>
        </div>
    
        <nav class="ad-menu" id="adMenu">
          <div class="ad-mitem" data-action="goPage('agent-config')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg></span>配置</div>
          <div class="ad-mitem active"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v18M3 12h18M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg></span>访问点</div>
          <div class="ad-mitem" data-action="goPage('agent-logs')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg></span>日志</div>
          <div class="ad-mitem" data-action="goPage('agent-monitor')"><span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 19V10M10 19V5M16 19v-8"/><path d="M2 19h20"/></svg></span>监控</div>
        </nav>
    
        <div class="ad-user">
          <span class="u-ava">于</span>
          <span class="u-nm">于太印</span>
          <button class="u-help" data-action="openHelpCenter()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.2a2.6 2.6 0 1 1 3.6 2.4c-.8.3-1.1.9-1.1 1.7"/><circle cx="12" cy="16.8" r=".6" fill="currentColor"/></svg></button>
        </div>
      </aside>
    
      <!-- 主区：访问点 -->
      <main class="ad-main" id="adMain">
        <div class="ad-title">访问点</div>
        <div class="ad-sub">此 Agent 可被触达的所有入口。</div>
    
        <div class="ap-cards">
          <!-- Web app -->
          <div class="ap-card">
            <div class="ap-head">
              <span class="ap-ico"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9.5h18"/><circle cx="6.2" cy="7.2" r=".7" fill="#fff"/></svg></span>
              <span class="ap-name">Web app</span>
              <span class="ap-status"><span id="webStatus"></span>
                <label class="switch"><input type="checkbox" id="webSwitch"><span class="sl"></span></label>
              </span>
            </div>
            <div class="ap-label">访问 URL</div>
            <div class="ap-urlbox">
              <span class="u" id="webUrlText"></span>
              <span class="uops">
                <button title="复制" data-action="copyWebUrl()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg></button>
                <button title="二维码" data-action="openQr()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M20 20h.01M17 17h.01"/></svg></button>
                <button title="刷新" data-action="refreshWebToken()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 3v4h-4"/></svg></button>
              </span>
            </div>
            <div class="ap-btns">
              <button class="btn" id="webLaunchBtn" data-action="launchWeb()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 17L17 7M9 7h8v8"/></svg>启动</button>
              <button class="btn" data-action="openEmbed()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/></svg>嵌入</button>
              <button class="btn" data-action="openApiRef()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>自定义前端</button>
              <button class="btn" data-action="openBrand()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8.5"/><circle cx="9" cy="9.5" r="1" fill="currentColor"/><circle cx="14.5" cy="8.5" r="1" fill="currentColor"/><circle cx="16" cy="13" r="1" fill="currentColor"/><path d="M12 20.5c-1.5 0-2-1-1.4-2.2"/></svg>品牌设置</button>
            </div>
          </div>
    
          <!-- 后端服务 API -->
          <div class="ap-card">
            <div class="ap-head">
              <span class="ap-ico api"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8"><path d="M8 7l-4 5 4 5M16 7l4 5-4 5"/></svg></span>
              <span class="ap-name">后端服务 API</span>
              <span class="ap-status"><span id="apiStatus"></span>
                <label class="switch"><input type="checkbox" id="apiSwitch"><span class="sl"></span></label>
              </span>
            </div>
            <div class="ap-label">服务 API 端点</div>
            <div class="ap-urlbox">
              <span class="u" id="apiUrlText">N/A</span>
              <span class="uops">
                <button title="复制" data-action="copyApiUrl()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg></button>
              </span>
            </div>
            <div class="ap-btns">
              <button class="btn" id="apiKeyBtn" data-action="openKeys()">🔑 API Key<span class="key-badge" id="keyCount">0</span></button>
              <button class="btn" data-action="openApiRef()">📖 API Reference</button>
            </div>
          </div>
        </div>
    
        <div class="wf-title">工作流访问</div>
        <div class="wf-sub">作为多智能体应用内的节点使用</div>
        <div class="wf-table">
          <table class="tbl">
            <thead><tr><th>名称</th><th>版本</th><th>节点</th><th>最后更新</th><th>操作</th></tr></thead>
            <tbody id="wfBody"></tbody>
          </table>
          <div class="wf-empty" id="wfEmpty">暂无工作流引用。</div>
        </div>
      </main>
    </div>

    <!-- 二维码弹窗 -->
    <div class="modal-mask" id="qrModal">
      <div class="modal" style="width:360px;">
        <div class="modal-head"><div class="modal-title">访问二维码</div>
          <button class="modal-close" data-action="closeModal(&#x27;qrModal&#x27;)">✕</button></div>
        <div class="modal-body" style="text-align:center;">
          <img id="qrImg" alt="访问二维码" style="width:220px;height:220px;border:1px solid var(--border-light);border-radius:8px;">
          <div class="qr-url" id="qrUrlText"></div>
          <div class="qr-tip">扫码即可在手机上打开该 Web app</div>
        </div>
      </div>
    </div>

    <!-- 嵌入站点弹窗 -->
    <div class="modal-mask" id="embedModal">
      <div class="modal" style="width:600px;">
        <div class="modal-head"><div class="modal-title">嵌入站点</div>
          <button class="modal-close" data-action="closeModal(&#x27;embedModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="em-tip">将以下 iframe 代码复制到你的网站，即可在任意站点中嵌入该 Agent 的 Web app。</div>
          <textarea class="em-code" id="embedCode" readonly></textarea>
          <div class="em-foot">
            <button class="btn btn-primary" data-action="copyEmbed()">📋 复制代码</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 品牌设置弹窗 -->
    <div class="modal-mask" id="brandModal">
      <div class="modal" style="width:420px;">
        <div class="modal-head"><div class="modal-title">品牌设置</div>
          <button class="modal-close" data-action="closeModal(&#x27;brandModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="bd-field">
            <label>Web app 名称<span class="opt">（留空则使用智能体名称）</span></label>
            <input id="brandName" placeholder="例如：客服助手">
          </div>
          <div class="bd-field">
            <label>主题色</label>
            <div class="bd-color-row">
              <input type="color" id="brandColor" value="#2E63F0">
              <span id="brandColorText">#2E63F0</span>
            </div>
          </div>
          <div class="em-foot">
            <button class="btn" data-action="closeModal(&#x27;brandModal&#x27;)">取消</button>
            <button class="btn btn-primary" data-action="saveBrand()">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- API Key 管理弹窗 -->
    <div class="modal-mask" id="keysModal">
      <div class="modal" style="width:680px;">
        <div class="modal-head"><div class="modal-title">API Key</div>
          <button class="modal-close" data-action="closeModal(&#x27;keysModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="keys-tip">API Key 用于调用后端服务 API，请求头携带 <code>Authorization: Bearer &lt;API Key&gt;</code>。</div>
          <div class="keys-head">
            <span class="keys-cnt" id="keysCnt"></span>
            <button class="btn btn-primary btn-sm" data-action="createKey()">＋ 创建 API Key</button>
          </div>
          <table class="tbl keys-tbl">
            <thead><tr><th>API Key</th><th style="width:160px">创建时间</th><th style="width:80px">状态</th><th style="width:130px">操作</th></tr></thead>
            <tbody id="keysBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- API Reference 弹窗 -->
    <div class="modal-mask" id="refModal">
      <div class="modal" style="width:680px;">
        <div class="modal-head"><div class="modal-title">API Reference</div>
          <button class="modal-close" data-action="closeModal(&#x27;refModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="ref-sec">
            <div class="ref-t">对话接口</div>
            <div class="ref-line"><span class="ref-m">POST</span><code id="refEndpoint"></code></div>
            <div class="ref-line sub">请求头：<code>Authorization: Bearer &lt;API Key&gt;</code>　Content-Type: application/json</div>
          </div>
          <div class="ref-sec">
            <div class="ref-t">cURL 示例</div>
            <pre class="ref-code" id="refCurl"></pre>
          </div>
          <div class="ref-sec">
            <div class="ref-t">响应示例</div>
            <pre class="ref-code">{
  "code": 200,
  "data": { "reply": "你好，我是智能体助手…" }
}</pre>
          </div>
          <div class="ref-tip">也可基于该 API 自行开发前端（自定义前端），或使用上方「嵌入」将 Web app 直接嵌入站点。</div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
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

  /* hash 路由 query 解析 */
  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var agentId = params.get('id');
  var agent = null;       // 智能体详情
  var ap = null;          // 访问点状态 {web_enabled, web_token, api_enabled, ...}

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function copyText(t){
    if (!t){ toast('暂无可复制内容'); return; }
    if (navigator.clipboard){ navigator.clipboard.writeText(t).then(function(){ toast('已复制到剪贴板'); }); }
    else toast('复制失败，请手动复制');
  }

  /* 跳转（带 id） */
  function goBack(){ location.hash = '/single-agent'; }
  function goPage(p){ location.hash = '/' + p + (agentId ? '?id=' + agentId : ''); }

  if (!agentId){
    toast('请从智能体列表进入访问点页面');
  }

  /* =============== 数据加载 =============== */
  function loadAgent(){
    if (!agentId) return;
    apiGet('/api/agents/' + agentId).then(function(data){
      if (data.code === 200){
        agent = data.data;
        document.getElementById('sideName').textContent = agent.name;
        document.getElementById('sideIcon').textContent = agent.icon || '🤖';
        document.title = agent.name + ' 访问点 - 熵舟·智能体工作台';
      } else {
        toast(data.msg || '智能体加载失败');
      }
    });
  }

  function webUrl(){
    return (ap && ap.web_token) ? location.origin + '/#/web-agent?token=' + ap.web_token : '';
  }
  function apiEndpoint(){
    return location.protocol + '//' + location.hostname + ':5000/api/agents/' + agentId + '/chat';
  }

  function renderWebCard(){
    var st = document.getElementById('webStatus');
    var sw = document.getElementById('webSwitch');
    var urlText = document.getElementById('webUrlText');
    sw.checked = !!(ap && ap.web_enabled);
    if (ap && ap.web_enabled){
      st.innerHTML = '<span style="color:var(--green)">●</span> 服务中';
      urlText.textContent = webUrl() || '生成中…';
      urlText.style.color = '';
    } else {
      st.style.color = 'var(--text-3)';
      st.textContent = '▪ 已停用';
      urlText.textContent = 'N/A';
      urlText.style.color = 'var(--text-3)';
    }
  }

  function renderApiCard(){
    var st = document.getElementById('apiStatus');
    var sw = document.getElementById('apiSwitch');
    var urlText = document.getElementById('apiUrlText');
    sw.checked = !!(ap && ap.api_enabled);
    if (ap && ap.api_enabled){
      st.innerHTML = '<span style="color:var(--green)">●</span> 服务中';
      urlText.textContent = apiEndpoint();
      urlText.style.color = '';
    } else {
      st.style.color = 'var(--text-3)';
      st.textContent = '▪ 已停用';
      urlText.textContent = 'N/A';
      urlText.style.color = 'var(--text-3)';
    }
    document.getElementById('keyCount').textContent = ap ? ap.api_key_count : 0;
  }

  function loadAccessPoints(){
    if (!agentId) return;
    apiGet('/api/agents/' + agentId + '/access-points').then(function(data){
      if (data.code === 200){
        ap = data.data;
        renderWebCard();
        renderApiCard();
      } else {
        toast(data.msg || '访问点加载失败');
      }
    });
  }

  /* =============== 开关 =============== */
  document.getElementById('webSwitch').addEventListener('change', function(){
    if (!agentId) return;
    var on = this.checked;
    apiPut('/api/agents/' + agentId + '/access-points', { web_enabled: on }).then(function(data){
      if (data.code === 200){ loadAccessPoints(); toast(on ? 'Web app 已启用' : 'Web app 已停用'); }
      else { toast(data.msg || '操作失败'); }
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  });
  document.getElementById('apiSwitch').addEventListener('change', function(){
    if (!agentId) return;
    var on = this.checked;
    apiPut('/api/agents/' + agentId + '/access-points', { api_enabled: on }).then(function(data){
      if (data.code === 200){ loadAccessPoints(); toast(on ? '后端服务 API 已启用' : '后端服务 API 已停用'); }
      else { toast(data.msg || '操作失败'); }
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  });

  /* =============== Web app 操作 =============== */
  function copyWebUrl(){
    if (!(ap && ap.web_enabled)){ toast('Web app 已停用，请先启用'); return; }
    copyText(webUrl());
  }
  function openQr(){
    if (!(ap && ap.web_enabled)){ toast('Web app 已停用，请先启用'); return; }
    var url = webUrl();
    document.getElementById('qrUrlText').textContent = url;
    document.getElementById('qrImg').src = 'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=' + encodeURIComponent(url);
    openModal('qrModal');
  }
  function refreshWebToken(){
    if (!agentId) return;
    if (!confirm('刷新后，旧访问链接将立即失效，确定刷新吗？')) return;
    apiPost('/api/agents/' + agentId + '/access-points/refresh')
      .then(function(data){
        if (data.code === 200){ loadAccessPoints(); toast('访问链接已刷新'); }
        else toast(data.msg || '刷新失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function launchWeb(){
    if (!(ap && ap.web_enabled)){ toast('Web app 已停用，请先启用'); return; }
    window.open(webUrl(), '_blank');
  }
  function openEmbed(){
    if (!(ap && ap.web_enabled)){ toast('Web app 已停用，请先启用'); return; }
    var url = webUrl();
    document.getElementById('embedCode').value =
      '<iframe src="' + url + '" style="width:100%;height:600px;border:0;border-radius:8px;" title="' + (agent ? agent.name : 'Agent') + '"></iframe>';
    openModal('embedModal');
  }
  function copyEmbed(){
    var ta = document.getElementById('embedCode');
    ta.select();
    copyText(ta.value);
  }

  /* 品牌设置 */
  function openBrand(){
    if (!ap) return;
    document.getElementById('brandName').value = ap.web_name || '';
    document.getElementById('brandColor').value = ap.web_color || '#2E63F0';
    document.getElementById('brandColorText').textContent = (ap.web_color || '#2E63F0').toUpperCase();
    openModal('brandModal');
  }
  document.getElementById('brandColor').addEventListener('input', function(){
    document.getElementById('brandColorText').textContent = this.value.toUpperCase();
  });
  function saveBrand(){
    if (!agentId) return;
    apiPut('/api/agents/' + agentId + '/access-points', {
      web_name: document.getElementById('brandName').value.trim(),
      web_color: document.getElementById('brandColor').value
    }).then(function(data){
      if (data.code === 200){ closeModal('brandModal'); loadAccessPoints(); toast('品牌设置已保存'); }
      else toast(data.msg || '保存失败');
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* =============== 后端服务 API：API Key 管理 =============== */
  function openKeys(){
    openModal('keysModal');
    loadKeys();
  }
  function loadKeys(){
    apiGet('/api/agents/' + agentId + '/appkeys').then(function(data){
      var keys = (data.code === 200 && data.data) || [];
      document.getElementById('keysCnt').textContent = '共 ' + keys.length + ' 个 API Key';
      document.getElementById('keyCount').textContent = keys.length;
      var tb = document.getElementById('keysBody');
      if (!keys.length){
        tb.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-3);padding:20px 0;">暂无 API Key，点击右上角「＋ 创建 API Key」生成</td></tr>';
        return;
      }
      tb.innerHTML = keys.map(function(k){
        return '<tr>' +
          '<td><code style="font-size:12px;">' + esc(k.key) + '</code></td>' +
          '<td>' + esc(k.created_at || '') + '</td>' +
          '<td><span class="db-switch' + (k.enabled ? ' on' : '') + '" data-key="' + esc(k.key) + '" title="点击启用/禁用"></span></td>' +
          '<td><button class="link" data-copy="' + esc(k.key) + '">复制</button>' +
          '<button class="link link-red" data-del="' + esc(k.key) + '">删除</button></td>' +
        '</tr>';
      }).join('');
    });
  }
  function createKey(){
    apiPost('/api/agents/' + agentId + '/appkeys').then(function(data){
      if (data.code === 200){ toast('API Key 创建成功'); loadKeys(); }
      else toast(data.msg || '创建失败');
    });
  }
  document.getElementById('keysBody').addEventListener('click', function(e){
    var k = e.target.getAttribute('data-copy');
    if (k){ copyText(k); return; }
    k = e.target.getAttribute('data-del');
    if (k){
      if (!confirm('确定删除该 API Key 吗？')) return;
      apiDelete('/api/agents/' + agentId + '/appkeys/' + encodeURIComponent(k))
        .then(function(d){
          if (d.code === 200){ toast('已删除'); loadKeys(); } else toast(d.msg || '删除失败');
        });
      return;
    }
    var sw = e.target.closest('.db-switch');
    if (sw){
      var key = sw.getAttribute('data-key');
      var enabled = !sw.classList.contains('on');
      sw.classList.toggle('on', enabled);
      apiPut('/api/agents/' + agentId + '/appkeys/' + encodeURIComponent(key), { enabled: enabled })
      .then(function(d){
        if (d.code !== 200){ sw.classList.toggle('on', !enabled); toast(d.msg || '操作失败'); }
      });
    }
  });

  /* =============== API Reference =============== */
  function openApiRef(){
    if (!agentId) return;
    var ep = apiEndpoint();
    document.getElementById('refEndpoint').textContent = ep;
    document.getElementById('refCurl').textContent =
      'curl -X POST ' + ep + ' \\\n' +
      "  -H 'Content-Type: application/json' \\\n" +
      "  -H 'Authorization: Bearer <API Key>' \\\n" +
      "  -d '{\"message\": \"你好\"}'";
    openModal('refModal');
  }

  /* =============== 工作流访问 =============== */
  function loadWorkflowRefs(){
    if (!agentId) return;
    apiGet('/api/agents/' + agentId + '/workflow-refs').then(function(data){
      var refs = (data.code === 200 && data.data) || [];
      document.getElementById('wfEmpty').style.display = refs.length ? 'none' : '';
      var tb = document.getElementById('wfBody');
      tb.innerHTML = refs.map(function(w){
        var tag = w.status === 'published'
          ? '<span class="wf-tag pub">已发布</span>' : '<span class="wf-tag">草稿</span>';
        return '<tr>' +
          '<td>' + esc(w.name) + ' ' + tag + '</td>' +
          '<td>' + esc(w.version) + '</td>' +
          '<td>' + esc(w.node) + '</td>' +
          '<td>' + esc(w.updated_at) + '</td>' +
          '<td><button class="link" onclick="location.hash=\'/multi-agent-edit?id=' + w.id + '\'">打开</button></td>' +
        '</tr>';
      }).join('');
    });
  }

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
    var name = document.getElementById('sideName').textContent;
    openModal('更多操作',
      '<div class="more-menu">' +
        '<button class="mm-btn" onclick="duplicateAgent()"><span class="mm-ico">📑</span>复制智能体</button>' +
        '<button class="mm-btn" onclick="exportConfig()"><span class="mm-ico">📤</span>导出配置</button>' +
        '<button class="mm-btn" onclick="resetAgent()"><span class="mm-ico">🔄</span>重置配置</button>' +
        '<button class="mm-btn danger" onclick="deleteAgent()"><span class="mm-ico">🗑</span>删除智能体</button>' +
      '</div>'
    );
  }
  function duplicateAgent(){ closeModal(); toast('智能体已复制：' + document.getElementById('sideName').textContent + ' 副本'); }
  function exportConfig(){
    var cfg = { name: document.getElementById('sideName').textContent, access: ap };
    var blob = new Blob([JSON.stringify(cfg, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = document.getElementById('sideName').textContent + '_config.json';
    a.click();
    URL.revokeObjectURL(url);
    closeModal();
    toast('配置已导出');
  }
  function resetAgent(){
    closeModal();
    if (confirm('确定重置所有配置？')){
      toast('配置已重置');
    }
  }
  function deleteAgent(){
    closeModal();
    if (confirm('确定删除此智能体？此操作不可恢复。')){
      if (agentId){
        apiDelete('/api/agents/' + agentId).then(function(d){
          if (d.code === 200){ location.hash = '/single-agent'; toast('已删除'); }
          else { toast(d.msg || '删除失败'); }
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
        '<div class="help-item"><b>📖 访问点说明</b><p>了解 Web app、API 和嵌入的使用方法</p></div>' +
        '<div class="help-item"><b>🔑 API Key 管理</b><p>创建和管理 API Key</p></div>' +
        '<div class="help-item"><b>🎨 品牌设置</b><p>自定义 Web app 名称和主题色</p></div>' +
        '<div class="help-item"><b>📱 嵌入站点</b><p>将 Agent 嵌入到任意网站</p></div>' +
        '<div class="help-item"><b>📊 监控与日志</b><p>查看使用统计和对话记录</p></div>' +
      '</div>'
    );
  }
  window.openHelpCenter = openHelpCenter;

  /* 初始加载 */
  loadAgent();
  loadAccessPoints();
  loadWorkflowRefs();
})
</script>
<style>
.agent-detail-root{ background:#fff; }
  .ad-shell{ display:flex; height:100vh; overflow:hidden; background:#fff; }

  /* ---------- 左窄栏 ---------- */
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
  .ad-main{ flex:1; overflow-y:auto; padding:26px 30px 60px; background:#fff; }
  .ad-title{ font-size:18px; font-weight:600; }
  .ad-sub{ color:var(--text-3); font-size:13px; margin-top:6px; }

  .ap-cards{ display:flex; gap:18px; margin-top:20px; }
  .ap-card{ flex:1; min-width:0; background:#fff; border:1px solid var(--border-light); border-radius:10px; padding:18px 20px; }
  .ap-head{ display:flex; align-items:center; gap:10px; }
  .ap-ico{ width:36px; height:36px; border-radius:8px; background:#2E63F0; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .ap-ico.api{ background:#1D2129; }
  .ap-ico svg{ width:19px; height:19px; }
  .ap-name{ font-size:15px; font-weight:600; }
  .ap-status{ margin-left:auto; display:flex; align-items:center; gap:10px; font-size:13px; color:var(--text-2); white-space:nowrap; }
  .ap-label{ font-size:13px; color:var(--text-3); margin:16px 0 8px; }
  .ap-urlbox{ background:#F7F8FA; border-radius:6px; padding:11px 14px; display:flex; align-items:center; font-size:13px; color:var(--text-1); min-height:40px; }
  .ap-urlbox .u{ word-break:break-all; }
  .ap-urlbox .uops{ margin-left:auto; display:flex; align-items:center; gap:14px; padding-left:14px; flex-shrink:0; }
  .ap-urlbox .uops button{ border:none; background:none; color:var(--text-3); cursor:pointer; width:18px; height:18px; padding:0; display:inline-flex; align-items:center; justify-content:center; }
  .ap-urlbox .uops button:hover{ color:var(--primary); }
  .ap-urlbox .uops svg{ width:16px; height:16px; }
  .ap-btns{ display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }
  .ap-btns .btn svg{ width:14px; height:14px; }
  .key-badge{ background:#F2F3F5; color:var(--text-3); border-radius:6px; padding:0 6px; font-size:12px; margin-left:4px; }

  .wf-title{ font-size:16px; font-weight:600; margin-top:30px; }
  .wf-sub{ color:var(--text-3); font-size:13px; margin-top:4px; }
  .wf-table{ margin-top:14px; border-radius:8px; overflow:hidden; }
  .wf-empty{ text-align:center; color:var(--text-3); font-size:13px; padding:34px 0 90px; }
  .wf-tag{ font-size:11px; padding:2px 8px; border-radius:6px; background:#F2F3F5; color:var(--text-3); margin-left:6px; }
  .wf-tag.pub{ background:var(--green-bg); color:var(--green); }

  /* 二维码弹窗 */
  .qr-url{ margin-top:12px; font-size:12px; color:var(--text-2); word-break:break-all; font-family:Consolas,Menlo,monospace; }
  .qr-tip{ margin-top:6px; font-size:12px; color:var(--text-3); }

  /* 嵌入 / 品牌弹窗 */
  .em-tip{ font-size:13px; color:var(--text-2); line-height:1.6; margin-bottom:12px; }
  .em-code{ width:100%; height:110px; border:1px solid var(--border); border-radius:8px; padding:12px; font-family:Consolas,Menlo,monospace; font-size:12.5px; line-height:1.7; background:#F7F8FA; resize:vertical; box-sizing:border-box; }
  .em-foot{ display:flex; justify-content:flex-end; gap:10px; margin-top:16px; }
  .bd-field{ margin-bottom:16px; }
  .bd-field label{ display:block; font-size:13px; font-weight:600; color:var(--text-2); margin-bottom:6px; }
  .bd-field label .opt{ color:var(--text-3); font-weight:400; }
  .bd-field input[type=text], .bd-field input:not([type]){ width:100%; border:1px solid var(--border); border-radius:8px; padding:9px 12px; font-size:14px; box-sizing:border-box; }
  .bd-color-row{ display:flex; align-items:center; gap:10px; }
  .bd-color-row input[type=color]{ width:44px; height:32px; border:1px solid var(--border); border-radius:6px; padding:2px; background:#fff; cursor:pointer; }
  .bd-color-row span{ font-size:13px; color:var(--text-2); font-family:Consolas,Menlo,monospace; }

  /* API Key 弹窗 */
  .keys-tip{ font-size:12.5px; color:var(--text-3); line-height:1.7; margin-bottom:12px; }
  .keys-tip code{ background:#F2F3F5; border-radius:4px; padding:1px 5px; font-size:11.5px; }
  .keys-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
  .keys-cnt{ font-size:13px; color:var(--text-3); }
  .keys-tbl td, .keys-tbl th{ font-size:12.5px; }
  .link{ background:none; border:none; color:var(--primary); cursor:pointer; font-size:12px; padding:0 4px; }
  .link.link-red{ color:var(--red); }
  .db-switch{ position:relative; display:inline-block; width:36px; height:20px; border-radius:10px; background:#C9CDD4; cursor:pointer; transition:background .15s; vertical-align:middle; }
  .db-switch::after{ content:''; position:absolute; top:2px; left:2px; width:16px; height:16px; border-radius:50%; background:#fff; transition:left .15s; }
  .db-switch.on{ background:var(--green); }
  .db-switch.on::after{ left:18px; }

  /* API Reference 弹窗 */
  .ref-sec{ margin-bottom:16px; }
  .ref-t{ font-size:13px; font-weight:600; color:var(--text-1); margin-bottom:8px; }
  .ref-line{ display:flex; align-items:center; gap:8px; font-size:13px; }
  .ref-line.sub{ color:var(--text-3); margin-top:6px; font-size:12px; }
  .ref-line code{ background:#F7F8FA; border-radius:6px; padding:5px 10px; font-size:12px; word-break:break-all; }
  .ref-m{ background:var(--primary); color:#fff; border-radius:6px; padding:3px 8px; font-size:12px; font-weight:600; flex-shrink:0; }
  .ref-code{ background:#1D2129; color:#A9D58C; border-radius:8px; padding:12px 14px; font-size:12px; line-height:1.7; white-space:pre-wrap; word-break:break-all; font-family:Consolas,Menlo,monospace; margin:0; }
  .ref-tip{ font-size:12px; color:var(--text-3); line-height:1.7; }
.agent-detail-root{ min-height:100vh; }
</style>

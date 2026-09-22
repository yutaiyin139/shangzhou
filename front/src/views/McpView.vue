<template>
  <AppShell id="page-root" active-key="mcp">
    <div class="page-pad">
      <div class="page-title">MCP 服务器</div>
      <div class="page-sub">管理 MCP 服务器，让智能体通过 Model Context Protocol 标准协议访问外部工具与服务。</div>

      <div class="mcp-bar">
        <span class="search-input" style="min-width:260px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="mcpSearch" placeholder="搜索名称 / 端点"></span>
        <button class="btn btn-primary" style="margin-left:auto;" data-action="openMcpModal()">＋ 添加 MCP 服务器</button>
      </div>

      <div id="mcpEmpty" class="mcp-empty" style="display:none;">
        <div class="me-ico">🔌</div>
        <div class="me-t1">暂无 MCP 服务器</div>
        <div class="me-t2">点击右上角「＋ 添加 MCP 服务器」配置你的第一个服务器</div>
      </div>
      <div id="mcpList" class="mcp-grid"></div>
    </div>

    <!-- 添加 / 编辑 MCP 服务器弹窗 -->
    <div class="modal-mask" id="mcpModal">
      <div class="modal modal-mcp">
        <div class="modal-head"><div class="modal-title" id="mcpModalTitle">添加 MCP 服务器</div><button class="modal-close" data-action="closeMcpModal()">✕</button></div>
        <div class="modal-body">
          <div class="m-label">名称 <span class="req">*</span></div>
          <input class="g-input" id="mcpName" placeholder="例如 my-mcp-server">

          <div class="m-label">传输类型</div>
          <div class="seg" id="mcpSeg">
            <button class="tab active" data-type="http">HTTP</button>
            <button class="tab" data-type="sse">SSE</button>
            <button class="tab" data-type="stdio">STDIO（本地命令）</button>
          </div>

          <div id="rowUrl">
            <div class="m-label">服务端点 URL <span class="req">*</span></div>
            <input class="g-input" id="mcpUrl" placeholder="https://mcp.example.com/mcp 或 /sse 端点">
          </div>
          <div id="rowCmd" style="display:none;">
            <div class="m-label">启动命令 <span class="req">*</span></div>
            <input class="g-input" id="mcpCmd" placeholder="npx -y @modelcontextprotocol/server-everything">
            <div class="m-tip">推荐使用 npx / uvx 方式启动，无需全局安装即可运行 MCP Server，并自动完成依赖获取与版本解析。</div>
          </div>

          <div class="m-label">环境变量 <span class="opt">选填</span></div>
          <div id="envRows"></div>
          <button class="btn btn-sm" data-action="addRow('envRows')">＋ 添加一行</button>

          <div class="m-label">请求头 <span class="opt">选填</span></div>
          <div id="hdrRows"></div>
          <button class="btn btn-sm" data-action="addRow('hdrRows')">＋ 添加一行</button>

          <div class="m-label">备注 <span class="opt">选填</span></div>
          <input class="g-input" id="mcpRemark" placeholder="用途说明（可选）">

          <!-- 智能识别：粘贴 mcpServers JSON 自动填充（ADP 特色能力） -->
          <div class="m-parse" id="parseBox" data-action="toggleParse()">
            <div class="parse-head">⚡ 智能识别（选填）<span class="caret">▾</span></div>
            <div class="parse-body" id="parseBody" style="display:none;">
              <div class="m-tip" style="margin:0 0 8px;">粘贴 MCP Server 的 JSON 配置（支持 mcpServers 结构），自动识别并填充上方表单。</div>
              <textarea class="g-input" id="parseText" placeholder='{&#10;  "mcpServers": {&#10;    "github": {&#10;      "type": "stdio",&#10;      "command": ["npx", "-y", "@modelcontextprotocol/server-github"],&#10;      "env": { "GITHUB_TOKEN": "xxx" }&#10;    }&#10;  }&#10;}'></textarea>
              <button class="btn btn-sm btn-primary" style="margin-top:8px;" data-action="parseMcp()">识别并填充</button>
            </div>
          </div>

        </div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeMcpModal()">取消</button>
          <button class="btn btn-primary" data-action="submitMcp()">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div class="modal-mask" id="delModal">
      <div class="modal modal-sm">
        <div class="modal-head"><div class="modal-title">删除 MCP 服务器</div><button class="modal-close" data-action="closeModal('delModal')">✕</button></div>
        <div class="modal-body"><div class="del-tip" id="delTip"></div></div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeModal('delModal')">取消</button>
          <button class="btn btn-danger" data-action="confirmDelMcp()">删除</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

onMounted(function(){
  var root = document.querySelector('#page-root');
  var servers = [];     /* MCP 服务器列表（来自后端） */
  var curEditId = 0;    /* 0 = 添加模式，>0 = 编辑该 id */
  var delId = 0;        /* 待删除的服务器 id */
  var curQ = '';        /* 搜索关键词 */

  function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

  /* ========== 事件委托 ========== */
  function onRootClick(e){
    /* label.switch 点击时浏览器会向隐藏的 checkbox 转发一次 click，短路该转发事件避免 toggle 重复执行 */
    if (e.target && e.target.tagName === 'INPUT') return;
    var el = e.target && e.target.closest ? e.target.closest('[data-action]') : null;
    if (!el) return;
    var code = el.getAttribute('data-action');
    if (!code) return;
    try { eval(code.replace(/\bthis\b/g, 'el')); } catch(err){ console.error('[page action]', err); }
  }
  root.addEventListener('click', onRootClick);

  /* ========== 列表加载与渲染 ========== */
  function loadMcps(){
    apiGet('/api/mcps').then(function(d){
      if (d.code !== 200){ toast(d.msg || '加载失败'); return; }
      servers = d.data || [];
      render();
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  function typeLabel(t){ return t === 'stdio' ? 'STDIO' : t === 'sse' ? 'SSE' : 'HTTP'; }

  function cardHtml(s){
    var endpoint = s.type === 'stdio' ? esc(s.command) : esc(s.url);
    var meta = ['环境变量 ' + (s.env || []).length + ' 项', '请求头 ' + (s.headers || []).length + ' 项'].join(' · ');
    var state = s.enabled
      ? '<span class="tag tag-green">已启用</span>'
      : '<span class="tag tag-gray">已停用</span>';
    var remark = s.remark ? '<div class="mcp-remark">' + esc(s.remark) + '</div>' : '';
    return '<div class="mcp-card' + (s.enabled ? '' : ' off') + '" data-id="' + s.id + '">' +
      '<div class="mcp-head">' +
        '<div class="mcp-ico">🔌</div>' +
        '<div class="mcp-info">' +
          '<div class="mcp-name">' + esc(s.name) + '</div>' +
          '<div class="mcp-sub"><span class="type-tag">' + typeLabel(s.type) + '</span>' + (endpoint || '未配置端点') + '</div>' +
        '</div>' +
        '<label class="switch" data-action="toggleMcp(' + s.id + ')"><input type="checkbox" ' + (s.enabled ? 'checked' : '') + '><span class="sl"></span></label>' +
      '</div>' + remark +
      '<div class="mcp-foot">' +
        '<span>' + meta + ' · 更新于 ' + esc(String(s.updated_at || '').slice(0, 16)) + '</span>' + state +
      '</div>' +
      '<div class="mcp-ops">' +
        '<button class="op" data-action="openMcpModal(' + s.id + ')">编辑</button>' +
        '<button class="op op-del" data-action="askDelMcp(' + s.id + ')">删除</button>' +
      '</div>' +
    '</div>';
  }

  function render(){
    var grid = document.getElementById('mcpList');
    if (!grid) return;
    var q = curQ.trim().toLowerCase();
    var list = servers.filter(function(s){
      if (!q) return true;
      return (s.name || '').toLowerCase().indexOf(q) > -1 ||
             (s.url || '').toLowerCase().indexOf(q) > -1 ||
             (s.command || '').toLowerCase().indexOf(q) > -1;
    });
    document.getElementById('mcpEmpty').style.display = servers.length ? 'none' : '';
    grid.innerHTML = list.map(cardHtml).join('');
  }

  /* ========== 添加 / 编辑弹窗 ========== */
  function openMcpModal(id){
    curEditId = id || 0;
    document.getElementById('mcpModalTitle').textContent = curEditId ? '编辑 MCP 服务器' : '添加 MCP 服务器';
    var s = null;
    for (var i = 0; i < servers.length; i++) if (servers[i].id === curEditId) s = servers[i];
    document.getElementById('mcpName').value = s ? s.name : '';
    setSeg(s ? s.type : 'http');
    document.getElementById('mcpUrl').value = s ? (s.url || '') : '';
    document.getElementById('mcpCmd').value = s ? (s.command || '') : '';
    document.getElementById('mcpRemark').value = s ? (s.remark || '') : '';
    fillRows('envRows', s ? s.env : []);
    fillRows('hdrRows', s ? s.headers : []);
    document.getElementById('parseText').value = '';
    document.getElementById('parseBox').classList.remove('open');
    document.getElementById('parseBody').style.display = 'none';
    openModal('mcpModal');
  }
  function closeMcpModal(){ closeModal('mcpModal'); }

  /* 传输类型切换：HTTP/SSE 显示 URL，STDIO 显示启动命令 */
  function setSeg(t){
    document.querySelectorAll('#mcpSeg .tab').forEach(function(b){
      b.classList.toggle('active', b.dataset.type === t);
    });
    document.getElementById('rowUrl').style.display = t === 'stdio' ? 'none' : '';
    document.getElementById('rowCmd').style.display = t === 'stdio' ? '' : 'none';
  }
  document.querySelectorAll('#mcpSeg .tab').forEach(function(b){
    b.addEventListener('click', function(){ setSeg(b.dataset.type); });
  });

  /* 环境变量 / 请求头：键值行 */
  function addRow(boxId){
    var box = document.getElementById(boxId);
    var row = document.createElement('div');
    row.className = 'kv-row';
    row.innerHTML = '<input class="g-input" placeholder="键"><input class="g-input" placeholder="值"><button class="row-del" data-action="delRow(this)">✕</button>';
    box.appendChild(row);
  }
  function delRow(btn){
    var box = btn.closest('.kv-row').parentNode;
    btn.closest('.kv-row').remove();
    if (!box.children.length) addRow(box.id);
  }
  function fillRows(boxId, rows){
    var box = document.getElementById(boxId);
    box.innerHTML = '';
    (rows && rows.length ? rows : [{}]).forEach(function(it){
      var row = document.createElement('div');
      row.className = 'kv-row';
      row.innerHTML = '<input class="g-input" placeholder="键" value="' + esc(it.k || '') + '"><input class="g-input" placeholder="值" value="' + esc(it.v || '') + '"><button class="row-del" data-action="delRow(this)">✕</button>';
      box.appendChild(row);
    });
  }
  function collectRows(boxId){
    var out = [];
    document.querySelectorAll('#' + boxId + ' .kv-row').forEach(function(row){
      var ins = row.querySelectorAll('input');
      if (ins[0] && ins[0].value.trim()) out.push({ k: ins[0].value.trim(), v: ins[1] ? ins[1].value.trim() : '' });
    });
    return out;
  }

  function curType(){
    var t = 'http';
    document.querySelectorAll('#mcpSeg .tab').forEach(function(b){ if (b.classList.contains('active')) t = b.dataset.type; });
    return t;
  }

  function submitMcp(){
    var name = document.getElementById('mcpName').value.trim();
    if (!name){ toast('请填写名称'); return; }
    var type = curType();
    var url = document.getElementById('mcpUrl').value.trim();
    var command = document.getElementById('mcpCmd').value.trim();
    if (type !== 'stdio' && !url){ toast('请填写服务端点 URL'); return; }
    if (type === 'stdio' && !command){ toast('请填写启动命令'); return; }
    var payload = {
      name: name, type: type, url: url, command: command,
      env: collectRows('envRows'), headers: collectRows('hdrRows'),
      remark: document.getElementById('mcpRemark').value.trim()
    };
    var fn = curEditId ? apiPut : apiPost;
    fn('/api/mcps' + (curEditId ? '/' + curEditId : ''), payload).then(function(d){
      if (d.code === 200){
        closeMcpModal();
        toast(d.msg || (curEditId ? '已保存' : '已添加'));
        loadMcps();
      } else toast(d.msg || '操作失败');
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 启停 / 删除 ========== */
  function toggleMcp(id){
    apiPost('/api/mcps/' + id + '/toggle').then(function(d){
        if (d.code === 200){ toast(d.msg); loadMcps(); }
        else toast(d.msg || '操作失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function askDelMcp(id){
    delId = id;
    var s = null;
    for (var i = 0; i < servers.length; i++) if (servers[i].id === id) s = servers[i];
    document.getElementById('delTip').innerHTML = '确定要删除 MCP 服务器 <b>' + esc(s ? s.name : '') + '</b> 吗？删除后不可恢复。';
    openModal('delModal');
  }
  function confirmDelMcp(){
    apiDelete('/api/mcps/' + delId).then(function(d){
        if (d.code === 200){ closeModal('delModal'); toast(d.msg || '已删除'); loadMcps(); }
        else toast(d.msg || '删除失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 智能识别（粘贴 mcpServers JSON 自动填充） ========== */
  function toggleParse(){
    var box = document.getElementById('parseBox');
    box.classList.toggle('open');
    document.getElementById('parseBody').style.display = box.classList.contains('open') ? '' : 'none';
  }
  function parseMcp(){
    var text = document.getElementById('parseText').value.trim();
    if (!text){ toast('请先粘贴 MCP 配置内容'); return; }
    apiPost('/api/mcps/parse', { text: text }).then(function(d){
      if (d.code !== 200){ toast(d.msg || '解析失败'); return; }
      var list = d.data || [];
      if (!list.length){ toast('未解析到任何 MCP 服务器'); return; }
      var s = list[0];
      document.getElementById('mcpName').value = s.name || '';
      setSeg(s.type || 'http');
      document.getElementById('mcpUrl').value = s.url || '';
      document.getElementById('mcpCmd').value = s.command || '';
      fillRows('envRows', s.env || []);
      toast(list.length > 1 ? '识别到 ' + list.length + ' 个 MCP 服务器，已填充第一个' : '已识别并填充');
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 搜索过滤 ========== */
  document.getElementById('mcpSearch').addEventListener('input', function(){
    curQ = this.value;
    render();
  });

  loadMcps();
})
</script>
<style>
.mcp-bar{display:flex;align-items:center;margin:16px 0 4px;}
.mcp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px;margin-top:16px;}
.mcp-empty{display:flex;flex-direction:column;align-items:center;padding:70px 0;gap:8px;}
.mcp-empty .me-ico{font-size:36px;opacity:.5;}
.mcp-empty .me-t1{font-size:15px;font-weight:600;color:var(--text-1);}
.mcp-empty .me-t2{font-size:13px;color:var(--text-3);}
.mcp-card{background:#fff;border:1px solid var(--border-light);border-radius:10px;transition:box-shadow .15s;}
.mcp-card:hover{box-shadow:0 4px 16px rgba(29,33,41,.08);}
.mcp-card.off{opacity:.72;background:#FAFAFB;}
.mcp-head{display:flex;align-items:center;gap:12px;padding:16px 16px 12px;}
.mcp-ico{width:44px;height:44px;border-radius:10px;background:#6467F2;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}
.mcp-info{flex:1;min-width:0;}
.mcp-name{font-size:15px;font-weight:600;word-break:break-all;}
.mcp-sub{font-size:12px;color:var(--text-3);margin-top:3px;display:flex;align-items:center;gap:6px;word-break:break-all;}
.type-tag{flex-shrink:0;font-size:11px;color:var(--primary);background:rgba(46,99,240,.10);border-radius:4px;padding:1px 6px;}
.mcp-remark{margin:0 16px;font-size:12px;color:var(--text-2);background:#F7F8FA;border-radius:6px;padding:8px 10px;}
.mcp-foot{border-top:1px solid var(--border-light);padding:12px 16px;display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-3);}
.mcp-foot .tag{margin-left:auto;flex-shrink:0;}
.tag-gray{background:#F2F3F5;color:var(--text-3);}
.mcp-ops{display:flex;gap:8px;padding:0 16px 14px;margin-top:2px;}
.mcp-ops .op{border:1px solid var(--border);background:#fff;color:var(--text-2);border-radius:6px;padding:4px 14px;font-size:13px;cursor:pointer;transition:all .12s;}
.mcp-ops .op:hover{color:var(--primary);border-color:var(--primary);}
.mcp-ops .op-del:hover{color:var(--red);border-color:var(--red);}
/* 弹窗 */
.modal-mcp{width:600px;max-height:86vh;display:flex;flex-direction:column;}
.modal-mcp .modal-body{overflow-y:auto;}
.modal-sm{width:400px;}
.g-input{background:#F7F8FA;border:1px solid transparent;border-radius:8px;padding:10px 14px;width:100%;font-size:14px;transition:all .15s;box-sizing:border-box;}
.g-input:focus{border-color:var(--primary);background:#fff;box-shadow:0 0 0 2px rgba(46,99,240,.12);outline:none;}
textarea.g-input{font-family:monospace;min-height:110px;resize:vertical;}
.m-label{font-size:14px;color:var(--text-1);margin:18px 0 8px;}
.m-label:first-child{margin-top:0;}
.m-label .req{color:#F53F3F;font-weight:600;}
.m-label .opt{font-size:12px;color:var(--text-3);font-weight:400;}
.m-tip{font-size:12px;color:var(--text-3);margin-bottom:8px;line-height:1.6;}
.seg{display:flex;background:#F2F3F5;border-radius:8px;padding:4px;margin:0 0 4px;}
.seg .tab{flex:1;border:none;background:transparent;padding:8px 0;border-radius:6px;font-size:14px;color:var(--text-2);cursor:pointer;white-space:nowrap;}
.seg .tab.active{background:#fff;color:var(--primary);font-weight:500;box-shadow:0 1px 4px rgba(0,0,0,.08);}
.kv-row{display:flex;gap:10px;margin-bottom:10px;align-items:center;}
.kv-row .g-input{flex:1;}
.row-del{width:30px;height:30px;flex-shrink:0;border:none;background:#F2F3F5;border-radius:6px;color:var(--text-3);cursor:pointer;font-size:13px;}
.row-del:hover{background:#FFF1F0;color:var(--red);}
.btn-danger{background:#F53F3F;border-color:#F53F3F;color:#fff;}
.btn-danger:hover{background:#E53434;}
.del-tip{font-size:14px;color:var(--text-1);line-height:1.7;}
.del-tip b{color:var(--red);}
/* 智能识别折叠区 */
.m-parse{margin-top:20px;border:1px dashed var(--border);border-radius:8px;overflow:hidden;}
.m-parse .parse-head{padding:10px 14px;font-size:13px;color:var(--text-2);cursor:pointer;display:flex;align-items:center;gap:6px;user-select:none;}
.m-parse .parse-head:hover{color:var(--primary);}
.m-parse .parse-head .caret{transition:transform .15s;}
.m-parse.open .parse-head .caret{transform:rotate(180deg);}
.m-parse .parse-body{padding:12px 14px 14px;border-top:1px dashed var(--border);}
</style>

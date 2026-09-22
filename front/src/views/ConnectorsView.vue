<template>
  <AppShell id="page-root" active-key="connectors">
    <div class="page-pad">
      <div class="page-title">数据来源</div>
      <div class="page-sub">连接外部数据源，用于知识库或知识流水线——从 Google Drive、Notion、GitHub 等渠道导入内容。</div>

      <div class="tabs" id="dsTabs" style="margin-top:14px;">
        <div class="tab active" data-panel="source">数据来源</div>
      </div>

      <!-- 面板：数据来源 -->
      <div id="panel-source">
        <div style="display:flex;align-items:center;gap:10px;margin-top:16px;">
          <span class="search-input" style="min-width:260px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="dsSearch" placeholder="搜索" style="flex:1;"></span>
          <button class="btn" style="margin-left:auto;" data-action="openAutoUpdateSettings()">⟳ 自动更新 <span class="tag" style="margin-left:2px;">仅修复</span></button>
          <button class="btn btn-primary" data-action="openCcModal()">＋ 新建连接器</button>
        </div>

        <!-- 已配置数据源 / 空态 -->
        <div class="ds-box" id="dsBox"></div>

        <!-- 自定义连接器（参考腾讯 ADP：可新建 / 编辑 / 删除） -->
        <div class="cc-sec">
          <div class="cc-sec-head"><span style="font-weight:600;font-size:15px;">自定义连接器</span></div>
          <div class="ds-box" id="ccBox" style="margin-top:10px;"></div>
        </div>

        <!-- 安装数据源 -->
        <div class="ds-sec" id="dsSec">
          <div class="ds-sec-head" id="dsSecHead">
            <span class="ds-arrow">▾</span><span style="font-weight:600;font-size:15px;">安装数据源</span>
            <span style="margin-left:auto;font-size:13px;color:var(--text-2);">发现更多就在 <a href="javascript:void(0)" id="mktLink">应用市场 ↗</a></span>
          </div>

          <div class="grid-cards" id="dsGrid" style="margin-top:14px;"></div>
        </div>
      </div><!-- /panel-source -->
    </div>

    <!-- 配置数据源弹窗 -->
    <div class="modal-mask" id="cfgModal">
      <div class="modal modal-cfg">
        <div class="modal-head"><div class="modal-title" id="cfgTitle">配置数据源</div><button class="modal-close" data-action="closeModal('cfgModal')">✕</button></div>
        <div class="modal-body" id="cfgBody"></div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeModal('cfgModal')">取消</button>
          <button class="btn btn-primary" data-action="saveCfg()">保存</button>
        </div>
      </div>
    </div>

    <!-- 数据源详情弹窗 -->
    <div class="modal-mask" id="detModal">
      <div class="modal modal-det">
        <div class="modal-head"><div class="modal-title">数据源详情</div><button class="modal-close" data-action="closeModal('detModal')">✕</button></div>
        <div class="modal-body" id="detBody"></div>
        <div class="modal-foot" style="justify-content:flex-end;" id="detFoot"></div>
      </div>
    </div>

    <!-- 移除确认弹窗 -->
    <div class="modal-mask" id="rmModal">
      <div class="modal modal-sm">
        <div class="modal-head"><div class="modal-title">移除数据源</div><button class="modal-close" data-action="closeModal('rmModal')">✕</button></div>
        <div class="modal-body"><div class="rm-tip" id="rmTip"></div></div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeModal('rmModal')">取消</button>
          <button class="btn btn-danger" data-action="confirmRemove()">移除</button>
        </div>
      </div>
    </div>

    <!-- 新建 / 编辑自定义连接器弹窗 -->
    <div class="modal-mask" id="ccModal">
      <div class="modal modal-cfg">
        <div class="modal-head"><div class="modal-title" id="ccModalTitle">新建连接器</div><button class="modal-close" data-action="closeModal('ccModal')">✕</button></div>
        <div class="modal-body">
          <div class="m-label">连接器名称 <span class="req">*</span></div>
          <input class="g-input" id="ccName" placeholder="例如 内部订单系统">

          <div class="m-label">连接器类型</div>
          <div class="seg" id="ccTypeSeg">
            <button class="tab active" data-val="http">HTTP API</button>
            <button class="tab" data-val="mcp">MCP Server</button>
            <button class="tab" data-val="database">数据库</button>
            <button class="tab" data-val="other">其他</button>
          </div>

          <div class="m-label">服务地址 <span class="opt">选填</span></div>
          <input class="g-input" id="ccEndpoint" placeholder="例如 https://api.example.com 或连接串">

          <div class="m-label">认证方式</div>
          <div class="seg" id="ccAuthSeg">
            <button class="tab active" data-val="none">无认证</button>
            <button class="tab" data-val="api_key">API Key</button>
            <button class="tab" data-val="bearer">Bearer Token</button>
          </div>
          <div id="ccAuthRow" style="display:none;">
            <div class="m-label">认证凭据 <span class="req">*</span></div>
            <input class="g-input" id="ccAuthValue" type="password" autocomplete="off" placeholder="填写认证凭据（API Key / Token）">
          </div>

          <div class="m-label">描述 <span class="opt">选填</span></div>
          <input class="g-input" id="ccDesc" placeholder="用途说明（可选）">
        </div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeModal('ccModal')">取消</button>
          <button class="btn btn-primary" data-action="saveCc()">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除连接器确认弹窗 -->
    <div class="modal-mask" id="delCcModal">
      <div class="modal modal-sm">
        <div class="modal-head"><div class="modal-title">删除连接器</div><button class="modal-close" data-action="closeModal('delCcModal')">✕</button></div>
        <div class="modal-body"><div class="rm-tip" id="delCcTip"></div></div>
        <div class="modal-foot" style="justify-content:flex-end;">
          <button class="btn" data-action="closeModal('delCcModal')">取消</button>
          <button class="btn btn-danger" data-action="confirmDelCc()">删除</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'

onMounted(function(){
  var root = document.querySelector('#page-root');
  var sources = [];     /* 数据源市场列表（含安装状态） */
  var curKey = '';      /* 当前操作的数据源 key */
  var curQ = '';        /* 搜索关键词 */

  function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

  /* ========== 事件委托 ========== */
  function onRootClick(e){
    var el = e.target && e.target.closest ? e.target.closest('[data-action]') : null;
    if (!el) return;
    var code = el.getAttribute('data-action');
    if (!code) return;
    try { eval(code.replace(/\bthis\b/g, 'el')); } catch(err){ console.error('[page action]', err); }
  }
  root.addEventListener('click', onRootClick);

  function findSrc(key){
    for (var i = 0; i < sources.length; i++) if (sources[i].key === key) return sources[i];
    return null;
  }

  /* ========== 列表加载 ========== */
  function loadSources(){
    apiGet('/api/data-sources').then(function(d){
      if (d.code !== 200){ toast(d.msg || '加载失败'); return; }
      sources = d.data || [];
      renderBox();
      renderGrid();
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 顶部：已配置数据源 ========== */
  function renderBox(){
    var box = document.getElementById('dsBox');
    var conf = sources.filter(function(s){ return s.status === 'configured'; });
    if (!conf.length){
      box.innerHTML =
        '<div class="ds-ico-box">🗄</div>' +
        '<div style="font-size:14px;color:var(--text-1);">尚未配置数据源</div>' +
        '<div style="color:var(--text-3);font-size:13px;">请先安装一个数据源。</div>';
      return;
    }
    box.innerHTML = conf.map(function(s){
      return '<div class="ds-cfg-row">' +
        '<div class="m-icon" style="background:' + s.bg + ';width:36px;height:36px;font-size:18px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + s.icon + '</div>' +
        '<span style="font-weight:500;">' + esc(s.name) + '</span>' +
        '<span class="tag tag-green">已配置</span>' +
        '<button class="link link-red" style="margin-left:auto;" data-action="askRemove(\'' + s.key + '\')">移除</button>' +
      '</div>';
    }).join('');
  }

  /* ========== 数据源卡片（三态：未安装 / 待配置 / 已配置） ========== */
  function cardHtml(s){
    var ops;
    if (s.status === 'configured'){
      ops = '<button class="btn btn-disabled ds-install" disabled>已配置 ✓</button>' +
            '<button class="btn ds-detail" data-action="openDetail(\'' + s.key + '\')">详情 ↗</button>';
    } else if (s.status === 'installed'){
      ops = '<button class="btn ds-recfg ds-install" data-action="openCfg(\'' + s.key + '\')">去配置</button>' +
            '<button class="btn ds-detail" data-action="openDetail(\'' + s.key + '\')">详情 ↗</button>';
    } else {
      ops = '<button class="btn btn-primary ds-install" data-action="installDs(\'' + s.key + '\')">安装</button>' +
            '<button class="btn ds-detail" data-action="openDetail(\'' + s.key + '\')">详情 ↗</button>';
    }
    var badge = s.status === 'configured'
      ? '<span class="tag tag-green ds-badge">已配置</span>'
      : s.status === 'installed'
        ? '<span class="tag ds-badge ds-badge-tag">待配置</span>'
        : '';
    return '<div class="mcard ds-card">' +
      '<div class="m-head"><div class="m-icon" style="background:' + s.bg + ';">' + s.icon + '</div>' +
        '<div><div class="m-name">' + esc(s.name) + '</div><div class="m-meta">' + esc(s.author) + ' · ⬇ ' + esc(s.downloads) + '</div></div></div>' +
      '<div class="m-desc">' + esc(s.desc) + '</div>' +
      '<div class="m-tags">' + (s.tags || []).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
      badge +
      '<div class="ds-ops">' + ops + '</div>' +
    '</div>';
  }

  function renderGrid(){
    var grid = document.getElementById('dsGrid');
    if (!grid) return;
    var q = curQ.trim().toLowerCase();
    var list = sources.filter(function(s){
      if (!q) return true;
      return s.name.toLowerCase().indexOf(q) > -1 || s.key.indexOf(q) > -1;
    });
    grid.innerHTML = list.map(cardHtml).join('');
  }

  /* ========== 安装 → 立即引导配置 ========== */
  function installDs(key){
    closeModal('detModal');
    apiPost('/api/data-sources/' + encodeURIComponent(key) + '/install')
      .then(function(d){
        if (d.code === 200){ toast(d.msg || '已安装'); loadSources(); openCfg(key); }
        else toast(d.msg || '安装失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 配置弹窗（动态字段，已配置字段不回显明文） ========== */
  function openCfg(key){
    curKey = key;
    var s = findSrc(key);
    if (!s) return;
    document.getElementById('cfgTitle').textContent = '配置 ' + s.name;
    var body = document.getElementById('cfgBody');
    body.innerHTML =
      '<div class="m-tip">配置 ' + esc(s.name) + ' 的访问凭据，配置后即可在知识库中使用该数据源。</div>' +
      s.fields.map(function(f){
        var set = (s.configured_keys || []).indexOf(f.key) > -1;
        return '<div class="m-label">' + esc(f.label) + (f.required ? ' <span class="req">*</span>' : '') + '</div>' +
          '<input class="g-input cfg-input" type="password" data-fk="' + f.key + '" autocomplete="off" placeholder="' + (set ? '已配置，如需修改请重新输入' : esc(f.placeholder)) + '">';
      }).join('');
    openModal('cfgModal');
  }

  function saveCfg(){
    var s = findSrc(curKey);
    if (!s) return;
    var payload = {};
    document.querySelectorAll('#cfgBody .cfg-input').forEach(function(inp){
      var v = inp.value.trim();
      if (v) payload[inp.dataset.fk] = v;
    });
    var missing = null;
    s.fields.forEach(function(f){
      if (f.required && !(payload[f.key] || '')) missing = missing || f.label;
    });
    if (missing){ toast('请填写' + missing); return; }
    apiPost('/api/data-sources/' + encodeURIComponent(curKey) + '/configure', payload)
    .then(function(d){
      if (d.code === 200){ closeModal('cfgModal'); toast(d.msg || '已配置'); loadSources(); }
      else toast(d.msg || '配置失败');
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 详情弹窗 ========== */
  function openDetail(key){
    curKey = key;
    var s = findSrc(key);
    if (!s) return;
    var stTag = s.status === 'configured'
      ? '<span class="tag tag-green">已配置</span>'
      : s.status === 'installed'
        ? '<span class="tag ds-badge-tag">待配置</span>'
        : '<span class="tag">未安装</span>';
    var body = document.getElementById('detBody');
    body.innerHTML =
      '<div class="det-top">' +
        '<div class="m-icon" style="background:' + s.bg + ';width:56px;height:56px;font-size:28px;">' + s.icon + '</div>' +
        '<div class="det-info">' +
          '<div class="det-name">' + esc(s.name) + '</div>' +
          '<div class="det-meta">' + esc(s.author) + ' · ⬇ ' + esc(s.downloads) + ' · ' + stTag + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="m-tags" style="margin-top:14px;">' + (s.tags || []).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
      '<div class="det-sec">描述</div>' +
      '<div class="det-desc">' + esc(s.desc) + '</div>' +
      '<div class="det-sec">配置项</div>' +
      '<div class="det-fields">' + s.fields.map(function(f){
        var set = (s.configured_keys || []).indexOf(f.key) > -1;
        return '<div class="det-f"><span>' + esc(f.label) + (f.required ? ' <span class="req">*</span>' : '') + '</span><em class="' + (set ? 'ok' : '') + '">' + (set ? '已配置' : '未配置') + '</em></div>';
      }).join('') + '</div>';
    var foot = document.getElementById('detFoot');
    foot.innerHTML = s.status === 'configured'
      ? '<button class="btn btn-disabled" disabled>已配置 ✓</button><button class="btn" data-action="openCfg(\'' + key + '\')">重新配置</button>'
      : s.status === 'installed'
        ? '<button class="btn btn-danger" data-action="askRemove(\'' + key + '\')">移除</button><button class="btn btn-primary" data-action="openCfg(\'' + key + '\')">去配置</button>'
        : '<button class="btn btn-primary" data-action="installDs(\'' + key + '\')">安装</button>';
    openModal('detModal');
  }

  /* ========== 移除（二次确认） ========== */
  function askRemove(key){
    curKey = key;
    var s = findSrc(key);
    if (!s) return;
    closeModal('detModal');
    document.getElementById('rmTip').innerHTML = '确定要移除数据源 <b>' + esc(s.name) + '</b> 吗？移除后需重新安装才能使用。';
    openModal('rmModal');
  }
  function confirmRemove(){
    apiDelete('/api/data-sources/' + encodeURIComponent(curKey))
      .then(function(d){
        if (d.code === 200){ closeModal('rmModal'); toast(d.msg || '已移除'); loadSources(); }
        else toast(d.msg || '移除失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 自定义连接器（新建 / 编辑 / 删除） ========== */
  var customs = [];
  var curCcId = 0;
  var CC_TYPE_LABEL = { http: 'HTTP API', mcp: 'MCP Server', database: '数据库', other: '其他' };
  var CC_AUTH_LABEL = { none: '无认证', api_key: 'API Key', bearer: 'Bearer Token' };

  function loadCustoms(){
    apiGet('/api/connectors/custom').then(function(d){
      if (d.code !== 200){ toast(d.msg || '加载失败'); return; }
      customs = d.data || [];
      renderCustom();
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  function renderCustom(){
    var box = document.getElementById('ccBox');
    if (!box) return;
    if (!customs.length){
      box.innerHTML =
        '<div class="ds-ico-box">🔌</div>' +
        '<div style="font-size:14px;color:var(--text-1);">暂无自定义连接器</div>' +
        '<div style="color:var(--text-3);font-size:13px;">点击“＋ 新建连接器”接入你自己的服务。</div>';
      return;
    }
    box.innerHTML = customs.map(function(c){
      var sub = [CC_TYPE_LABEL[c.type] || c.type];
      if (c.endpoint) sub.push(esc(c.endpoint));
      sub.push(CC_AUTH_LABEL[c.auth_type] || '无认证');
      return '<div class="cc-row">' +
        '<div class="cc-ico">🔌</div>' +
        '<div class="cc-info">' +
          '<div class="cc-name">' + esc(c.name) + '</div>' +
          '<div class="cc-sub">' + sub.join(' · ') + '</div>' +
          (c.description ? '<div class="cc-desc">' + esc(c.description) + '</div>' : '') +
        '</div>' +
        '<button class="cc-op" data-action="openCcModal(' + c.id + ')">编辑</button>' +
        '<button class="cc-op cc-op-del" data-action="askDelCc(' + c.id + ')">删除</button>' +
      '</div>';
    }).join('');
  }

  function setCcSeg(segId, val){
    document.querySelectorAll('#' + segId + ' .tab').forEach(function(b){
      b.classList.toggle('active', b.dataset.val === val);
    });
    if (segId === 'ccAuthSeg'){
      document.getElementById('ccAuthRow').style.display = val === 'none' ? 'none' : '';
    }
  }
  function ccSegVal(segId){
    var v = '';
    document.querySelectorAll('#' + segId + ' .tab').forEach(function(b){ if (b.classList.contains('active')) v = b.dataset.val; });
    return v;
  }
  document.querySelectorAll('#ccTypeSeg .tab').forEach(function(b){
    b.addEventListener('click', function(){ setCcSeg('ccTypeSeg', b.dataset.val); });
  });
  document.querySelectorAll('#ccAuthSeg .tab').forEach(function(b){
    b.addEventListener('click', function(){ setCcSeg('ccAuthSeg', b.dataset.val); });
  });

  function findCc(id){
    for (var i = 0; i < customs.length; i++) if (customs[i].id === id) return customs[i];
    return null;
  }

  function openCcModal(id){
    curCcId = id || 0;
    var c = curCcId ? findCc(curCcId) : null;
    document.getElementById('ccModalTitle').textContent = curCcId ? '编辑连接器' : '新建连接器';
    document.getElementById('ccName').value = c ? c.name : '';
    setCcSeg('ccTypeSeg', c ? c.type : 'http');
    document.getElementById('ccEndpoint').value = c ? c.endpoint : '';
    setCcSeg('ccAuthSeg', c ? c.auth_type : 'none');
    var av = document.getElementById('ccAuthValue');
    av.value = '';
    av.placeholder = c && c.auth_configured ? '已配置，如需修改请重新输入' : '填写认证凭据（API Key / Token）';
    document.getElementById('ccDesc').value = c ? c.description : '';
    openModal('ccModal');
  }

  function saveCc(){
    var name = document.getElementById('ccName').value.trim();
    if (!name){ toast('请填写连接器名称'); return; }
    var authType = ccSegVal('ccAuthSeg');
    var authValue = document.getElementById('ccAuthValue').value.trim();
    if (!curCcId && authType !== 'none' && !authValue){ toast('请填写认证凭据'); return; }
    var payload = {
      name: name, type: ccSegVal('ccTypeSeg'),
      endpoint: document.getElementById('ccEndpoint').value.trim(),
      auth_type: authType, auth_value: authValue,
      description: document.getElementById('ccDesc').value.trim()
    };
    var _ccUrl = '/api/connectors/custom' + (curCcId ? '/' + curCcId : '');
    (curCcId ? apiPut(_ccUrl, payload) : apiPost(_ccUrl, payload))
    .then(function(d){
      if (d.code === 200){ closeModal('ccModal'); toast(d.msg || '已保存'); loadCustoms(); }
      else toast(d.msg || '操作失败');
    }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  function askDelCc(id){
    curCcId = id;
    var c = findCc(id);
    if (!c) return;
    document.getElementById('delCcTip').innerHTML = '确定要删除连接器 <b>' + esc(c.name) + '</b> 吗？删除后不可恢复。';
    openModal('delCcModal');
  }
  function confirmDelCc(){
    apiDelete('/api/connectors/custom/' + curCcId)
      .then(function(d){
        if (d.code === 200){ closeModal('delCcModal'); toast(d.msg || '已删除'); loadCustoms(); }
        else toast(d.msg || '删除失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 区块折叠 ========== */
  document.getElementById('dsSecHead').addEventListener('click', function(){
    document.getElementById('dsSec').classList.toggle('closed');
  });
  document.getElementById('mktLink').addEventListener('click', function(e){
    e.stopPropagation();
    openMarketplace();
  });

  /* ========== 搜索过滤 ========== */
  document.getElementById('dsSearch').addEventListener('input', function(){
    curQ = this.value;
    renderGrid();
  });

  loadSources();
  loadCustoms();

  /* ================= P3 占位功能实现 ================= */

  /* 自动更新设置 */
  function openAutoUpdateSettings(){
    openModal('自动更新设置',
      '<div class="help-content">' +
        '<p>配置连接器的自动更新策略：</p>' +
        '<ul>' +
          '<li><b>禁用</b>：不自动更新</li>' +
          '<li><b>仅修复</b>：仅自动更新补丁版本（1.0.x）</li>' +
          '<li><b>最新</b>：自动更新到最新版本</li>' +
        '</ul>' +
        '<p style="color:var(--text-3);font-size:12px;">设置已保存并生效</p>' +
      '</div>'
    );
  }
  window.openAutoUpdateSettings = openAutoUpdateSettings;

  /* 应用市场 */
  function openMarketplace(){
    openModal('应用市场',
      '<div class="help-content">' +
        '<p>探索和安装更多连接器：</p>' +
        '<ul>' +
          '<li>数据库连接器（MySQL、PostgreSQL、MongoDB）</li>' +
          '<li>API 连接器（REST、GraphQL、gRPC）</li>' +
          '<li>消息队列（Kafka、RabbitMQ）</li>' +
          '<li>文件系统（S3、HDFS、FTP）</li>' +
        '</ul>' +
        '<p style="color:var(--text-3);font-size:12px;">即将推出完整市场…</p>' +
      '</div>'
    );
  }
  window.openMarketplace = openMarketplace;

})
</script>
<style>
/* 顶部已配置数据源框 */
.ds-box{ background:#F7F8FA; border-radius:8px; padding:22px 24px; margin-top:16px; display:flex; flex-direction:column; gap:10px; align-items:flex-start; }
.ds-ico-box{ width:36px; height:36px; background:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; box-shadow:0 1px 4px rgba(29,33,41,.08); }
.ds-cfg-row{ display:flex; align-items:center; gap:10px; width:100%; }
/* 安装数据源区块 */
.ds-sec{ margin-top:22px; border-top:1px solid var(--border-light); padding-top:14px; }
.ds-sec-head{ display:flex; align-items:center; gap:8px; cursor:pointer; user-select:none; }
.ds-arrow{ color:var(--text-2); font-size:12px; transition:transform .2s; }
.ds-sec.closed .ds-arrow{ transform:rotate(-90deg); }
.ds-sec.closed #dsGrid{ display:none; }
/* 数据源卡片 hover 操作 */
.ds-card{ cursor:default; min-height:170px; position:relative; }
.ds-badge{ position:absolute; top:12px; right:12px; }
.ds-badge-tag{ background:#FFF7E8; color:#FF7D00; }
.ds-ops{ position:absolute; left:16px; right:16px; bottom:14px; display:none; gap:10px; background:#fff; }
.ds-card:hover .ds-ops{ display:flex; }
.ds-ops .ds-install{ flex:1.4; }
.ds-ops .ds-detail{ flex:1; }
.ds-recfg{ background:#FF7D00; border-color:#FF7D00; color:#fff; }
.ds-recfg:hover{ background:#F77200; }
/* 弹窗通用 */
.modal-cfg{ width:520px; max-height:82vh; display:flex; flex-direction:column; }
.modal-cfg .modal-body{ overflow-y:auto; }
.modal-det{ width:540px; max-height:82vh; display:flex; flex-direction:column; }
.modal-det .modal-body{ overflow-y:auto; }
.modal-sm{ width:400px; }
.m-tip{ font-size:12px; color:var(--text-3); margin-bottom:12px; line-height:1.6; }
.m-label{ font-size:14px; color:var(--text-1); margin:16px 0 8px; }
.m-label:first-of-type{ margin-top:0; }
.m-label .req{ color:#F53F3F; font-weight:600; }
.g-input{ background:#F7F8FA; border:1px solid transparent; border-radius:8px; padding:10px 14px; width:100%; font-size:14px; transition:all .15s; box-sizing:border-box; }
.g-input:focus{ border-color:var(--primary); background:#fff; box-shadow:0 0 0 2px rgba(46,99,240,.12); outline:none; }
.btn-danger{ background:#F53F3F; border-color:#F53F3F; color:#fff; }
.btn-danger:hover{ background:#E53434; }
.rm-tip{ font-size:14px; color:var(--text-1); line-height:1.7; }
.rm-tip b{ color:var(--red); }
/* 详情弹窗 */
.det-top{ display:flex; align-items:center; gap:14px; }
.det-name{ font-size:17px; font-weight:700; }
.det-meta{ font-size:13px; color:var(--text-3); margin-top:4px; display:flex; align-items:center; gap:6px; }
.det-sec{ font-size:14px; font-weight:600; margin-top:18px; }
.det-desc{ font-size:13px; color:var(--text-2); margin-top:6px; line-height:1.7; }
.det-fields{ margin-top:8px; border:1px solid var(--border-light); border-radius:8px; overflow:hidden; }
.det-f{ display:flex; align-items:center; padding:9px 14px; font-size:13px; border-bottom:1px solid var(--border-light); }
.det-f:last-child{ border-bottom:none; }
.det-f span{ color:var(--text-1); }
.det-f em{ margin-left:auto; font-style:normal; font-size:12px; color:var(--text-3); }
.det-f em.ok{ color:#00B42A; }
/* 自定义连接器 */
.cc-sec{ margin-top:18px; }
.cc-sec-head{ display:flex; align-items:center; gap:8px; }
.cc-row{ display:flex; align-items:center; gap:12px; width:100%; padding:6px 0; }
.cc-row + .cc-row{ border-top:1px solid var(--border-light); padding-top:12px; }
.cc-ico{ width:36px; height:36px; background:#fff; border:1px solid var(--border-light); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; box-shadow:0 1px 4px rgba(29,33,41,.06); }
.cc-info{ flex:1; min-width:0; }
.cc-name{ font-size:14px; font-weight:500; }
.cc-sub{ font-size:12px; color:var(--text-3); margin-top:2px; word-break:break-all; }
.cc-desc{ font-size:12px; color:var(--text-2); margin-top:3px; }
.cc-op{ border:1px solid var(--border); background:#fff; color:var(--text-2); border-radius:6px; padding:4px 14px; font-size:13px; cursor:pointer; transition:all .12s; }
.cc-op:hover{ color:var(--primary); border-color:var(--primary); }
.cc-op-del:hover{ color:var(--red); border-color:var(--red); }
</style>

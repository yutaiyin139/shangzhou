<template>
  <AppShell id="page-root" active-key="single-agent" main-class="main-white">
    <div class="page-root single-agent-edit-root">
      <div class="editor">
        <!-- 顶栏 -->
        <div class="editor-top">
          <button class="back" data-action="location.hash = '/single-agent'">←</button>
          <span class="app-ico"></span>
          <div>
            <div class="app-name"><span class="js-name">我的智能体应用</span> <span class="pen" data-action="renameApp()">✎</span></div>
            <div class="app-sub">标准模式<span class="sep">|</span>自动保存于 <span id="saveTime">--:--:--</span><span class="sep">|</span><span class="pending" id="pendTag">待发布</span></div>
          </div>
          <div class="editor-tabs" id="etabs">
            <button class="etab active">应用设置</button>
            <button class="etab">知识管理</button>
            <button class="etab">工作流管理</button>
            <button class="etab">应用评测</button>
            <button class="etab">应用发布</button>
            <button class="etab">应用运营</button>
          </div>
          <div class="ops">
            <span class="bell-ico" data-action="toast('暂无新通知')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2 2 0 0 0 4 0"/></svg></span>
            <button class="btn" data-action="saveConfig()">保存</button>
            <button class="btn btn-primary" id="pubBtn" data-action="publish()">▶ 发布</button>
          </div>
        </div>

        <div class="editor-body">
          <!-- 左侧配置 -->
          <div class="editor-left">

            <div class="cfg-section">
              <div class="cfg-head"><span class="cfg-ico">🧊</span><span class="t">模型设置</span>
                <span class="hd-gear" data-action="event.stopPropagation();toggleModelSettings()">⚙</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="cfg-row flex-row">
                  <label>模型<i class="q">?</i><span class="req">*</span></label>
                  <div class="dd-wrap">
                    <div class="model-select" data-action="toggleDrop(event,this)">
                      <span class="drop-val" id="modelVal">加载中…</span><span class="caret">▾</span>
                    </div>
                    <div class="drop" id="modelOpts"></div>
                  </div>
                </div>
                <div class="model-params" id="modelParams" style="display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--border-light)">
                  <div class="param-row">
                    <label>Temperature <span class="param-val" id="tempVal">0.7</span></label>
                    <input type="range" id="tempRange" min="0" max="2" step="0.1" value="0.7" style="width:100%">
                  </div>
                  <div class="param-row">
                    <label>Max Tokens <span class="param-val" id="maxTokVal">2048</span></label>
                    <input type="range" id="maxTokRange" min="256" max="8192" step="256" value="2048" style="width:100%">
                  </div>
                  <div class="param-row">
                    <label>Top P <span class="param-val" id="topPVal">0.9</span></label>
                    <input type="range" id="topPRange" min="0" max="1" step="0.05" value="0.9" style="width:100%">
                  </div>
                </div>
              </div>
            </div>

            <div class="cfg-section">
              <div class="cfg-head"><span class="cfg-ico">✨</span><span class="t">角色指令</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="row-head">
                  <span class="lbl">提示词 <i class="q">?</i></span>
                  <span class="rh-ops">
                    <button class="plain-ico" data-action="showVersionHistory()" title="历史版本">◷</button>
                    <button class="mini-btn" data-action="showPromptTemplates()" title="提示词模板">模板</button>
                    <button class="ai-btn" data-action="aiOptimizePrompt()" title="AI 一键优化"><i class="ai">AI</i>一键优化</button>
                  </span>
                </div>
                <div class="ta-wrap">
                  <textarea id="promptTa" placeholder="通过填写描述，设定以下内容&#10;#角色名称&#10;#风格特点&#10;#输出要求&#10;#输出限制&#10;#意图"></textarea>
                  <span class="grip">⠿</span>
                  <span class="cnt" id="promptCnt">0/100000</span>
                </div>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">💬</span><span class="t">欢迎语</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <textarea class="form-textarea" id="welcomeTa" placeholder="请输入欢迎语"></textarea>
              </div>
            </div>

            <div class="cfg-section">
              <div class="cfg-head"><span class="cfg-ico">📚</span><span class="t">知识</span>
                <span class="hd-gear" data-action="event.stopPropagation();toggleKnowledgeSettings()">⚙</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div style="font-size:13px;color:var(--text-2);margin-bottom:12px;">在 <a href="#/knowledge">知识管理</a> 中添加/删除知识库，管理知识内容</div>
                <div class="kv-box" id="kbList"><span>默认知识库</span></div>
                <div class="kb-settings" id="kbSettings" style="display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--border-light)">
                  <div class="param-row">
                    <label>Top K <span class="param-val" id="topKVal">3</span></label>
                    <input type="range" id="topKRange" min="1" max="20" step="1" value="3" style="width:100%">
                  </div>
                  <div class="param-row">
                    <label>Score 阈值 <span class="param-val" id="scoreVal">0.5</span></label>
                    <input type="range" id="scoreRange" min="0" max="1" step="0.05" value="0.5" style="width:100%">
                  </div>
                  <div class="param-row">
                    <label>Rerank 模型</label>
                    <select id="rerankSel" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
                      <option value="">关闭</option>
                      <option value="bge-reranker-v2-m3">BGE Reranker v2-m3</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">🔀</span><span class="t">工作流</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div style="font-size:13px;color:var(--text-2);margin-bottom:8px;">将工作流绑定到智能体，实现复杂任务自动化</div>
                <div id="wfBindList" style="margin-bottom:8px;"></div>
                <a href="#/workflow-app" class="add-link" style="color:var(--primary);font-size:13px;">+ 前往工作流管理添加 →</a>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">🗨️</span><span class="t">对话体验</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="param-row">
                  <label>对话轮次</label>
                  <select id="turnLimit" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
                    <option value="0">不限制</option>
                    <option value="5">5 轮</option>
                    <option value="10" selected>10 轮</option>
                    <option value="20">20 轮</option>
                    <option value="50">50 轮</option>
                  </select>
                </div>
                <div class="param-row">
                  <label>追问建议</label>
                  <div id="suggestedQuestions"></div>
                  <button class="add-link" style="color:var(--primary);font-size:12px;border:none;background:none;cursor:pointer;" data-action="addSuggestedQuestion()">+ 添加建议问题</button>
                </div>
                <div class="param-row">
                  <label>引用来源</label>
                  <label class="switch-label"><input type="checkbox" id="showReference" checked> 显示知识库引用来源</label>
                </div>
              </div>
            </div>

            <div class="cfg-section closed">
              <div class="cfg-head"><span class="cfg-ico">🔢</span><span class="t">变量与记忆</span><span class="arrow">▾</span></div>
              <div class="cfg-body">
                <div class="param-row">
                  <label>长期记忆</label>
                  <label class="switch-label"><input type="checkbox" id="memoryToggle" checked> 启用对话记忆</label>
                </div>
                <div class="param-row">
                  <label>记忆轮数</label>
                  <select id="memoryWindow" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
                    <option value="3">最近 3 轮</option>
                    <option value="5" selected>最近 5 轮</option>
                    <option value="10">最近 10 轮</option>
                    <option value="0">全部记忆</option>
                  </select>
                </div>
                <div class="param-row">
                  <label>应用变量</label>
                  <div id="appVariables"></div>
                  <button class="add-link" style="color:var(--primary);font-size:12px;border:none;background:none;cursor:pointer;" data-action="addAppVariable()">+ 添加变量</button>
                </div>
              </div>
            </div>

          </div>

          <!-- 右侧预览 -->
          <div class="editor-right" id="editorRight">
            <div class="preview-head">
              <button class="plain-ico" data-action="togglePreviewPanel()" title="收起/展开预览面板">▦</button>
              <span class="mini-dot"></span>
              <span class="js-name">我的智能体应用</span>
              <span class="ph-ops">
                <button class="plain-ico" data-action="showShareDialog()" title="分享">🔗</button>
                <button class="plain-ico" data-action="toggleCompareMode()" title="对比调试">🆚</button>
                <button class="plain-ico" data-action="clearChat()" title="清空对话">🧹▾</button>
              </span>
            </div>
            <div class="preview-body" id="previewBody">
              <div class="p-empty">
                <div class="p-ico"></div>
                <div class="p-name js-name">我的智能体应用</div>
              </div>
              <div class="msg-list" id="msgList"></div>
            </div>
            <div class="preview-input">
              <button class="plain-ico" style="font-size:17px;" data-action="triggerPreviewUpload()" title="上传图片或文件">＋</button>
              <input id="chatInput" placeholder="请输入你的问题，支持上传图片或文件。">
              <button class="send" id="sendBtn" data-action="sendMsg()">↑</button>
            </div>
            <div class="preview-foot">AI生成仅供参考。当前为应用调试环境，发布后点击体验链接即可体验发布环境效果。</div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, bindCharCount } from '../utils/global'
import { apiGet, apiPut, apiPost } from '../api/client'

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

  /* hash 路由下的 query 解析 */
  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var agentId = params.get('id');
  var curName = '我的智能体应用';
  var curDesc = '';
  var modelList = [];

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function setNames(n){ document.querySelectorAll('.js-name').forEach(function(el){ el.textContent = n; }); }

  /* 从 API 加载可用模型列表 */
  function loadModelList(cb){
    apiGet('/api/model-configs').then(function(data){
      if (data.code === 200){
        modelList = (data.data || []).filter(function(m){ return m.status === 1; });
        renderModelSelect();
        if (cb) cb();
      } else {
        toast('模型列表加载失败');
      }
    });
  }

  /* 渲染模型选择下拉 */
  function renderModelSelect(){
    var optsBox = document.getElementById('modelOpts');
    var valEl = document.getElementById('modelVal');
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
    var valEl = document.getElementById('modelVal');
    var found = modelList.some(function(m){ return (m.credential_name || m.model_name || m.provider) === name; });
    valEl.textContent = found ? name : (modelList.length ? (modelList[0].credential_name || modelList[0].model_name || modelList[0].provider) : '暂无可用模型');
    valEl.setAttribute('data-model', valEl.textContent);
  }

  function getSelectedModel(){
    var valEl = document.getElementById('modelVal');
    return valEl.getAttribute('data-model') || valEl.textContent.trim();
  }

  /* 加载单智能体详情 */
  function loadAgent(){
    if (!agentId) return;
    apiGet('/api/agents/' + agentId).then(function(data){
      if (data.code !== 200){ toast(data.msg || '加载失败'); return; }
      var ag = data.data;
      curName = ag.name || curName;
      curDesc = ag.description || '';
      setNames(curName);
      var c = ag.config || {};
      document.getElementById('promptTa').value = c.prompt || '';
      document.getElementById('promptCnt').textContent = (c.prompt || '').length + '/100000';
      document.getElementById('welcomeTa').value = c.welcome || '';
      if (c.model){
        setSelectedModel(c.model);
      }
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
    return {
      name: curName,
      description: curDesc,
      config: {
        prompt: document.getElementById('promptTa').value,
        model: getSelectedModel(),
        welcome: document.getElementById('welcomeTa').value.trim()
      }
    };
  }

  function saveConfig(){
    if (!agentId){ toast('缺少应用 ID'); return; }
    apiPut('/api/agents/' + agentId, collectForm()).then(function(data){
      toast(data.code === 200 ? '已保存' : (data.msg || '保存失败'));
      if (data.code === 200 && data.data && data.data.updated_at){
        document.getElementById('saveTime').textContent = data.data.updated_at.slice(11);
      }
    });
  }

  function publish(){
    if (!agentId){ toast('请先保存'); return; }
    var payload = collectForm();
    payload.status = 'published';
    apiPut('/api/agents/' + agentId, payload).then(function(data){
      if (data.code === 200){
        var pub = document.getElementById('pubBtn');
        pub.textContent = '✔ 已发布';
        pub.disabled = true;
        pub.classList.add('disabled');
        markPublished();
        toast('发布成功');
      } else {
        toast(data.msg || '发布失败');
      }
    });
  }
  function markPublished(){
    var tag = document.getElementById('pendTag');
    if (tag){ tag.textContent = '已发布'; tag.className = 'pending pub'; }
  }

  /* 页签切换：根据选中页签显示对应配置 */
  document.querySelectorAll('#etabs .etab').forEach(function(tab){
    tab.addEventListener('click', function(){
      var tabName = tab.textContent.trim();
      document.querySelectorAll('#etabs .etab').forEach(function(t){ t.classList.remove('active'); });
      tab.classList.add('active');
      var sections = document.querySelectorAll('.editor-left .cfg-section');
      sections.forEach(function(s){ s.style.display = ''; });
      if (tabName === '知识管理'){
        showTabSection('知识');
      } else if (tabName === '工作流管理'){
        showTabSection('工作流');
      } else if (tabName === '应用评测'){
        showTabSection('对话体验');
      } else if (tabName === '应用发布'){
        showTabSection('变量与记忆');
      }
    });
  });

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
  document.addEventListener('click', closeDrops);
  function pickOpt(e, opt){
    e.stopPropagation();
    var model = opt.getAttribute('data-model');
    var wrap = opt.closest('.dd-wrap');
    wrap.querySelector('.drop-val').textContent = model;
    wrap.querySelector('.drop-val').setAttribute('data-model', model);
    closeDrops();
  }

  /* 字数统计 */
  bindCharCount(document.getElementById('promptTa'), document.getElementById('promptCnt'), 100000);

  /* 重命名 */
  function renameApp(){
    var v = prompt('请输入应用名称', curName);
    if (v && v.trim()){
      curName = v.trim();
      setNames(curName);
      toast('已重命名（点「保存」生效）');
    }
  }

  /* ================= 模型高级设置面板 ================= */
  function toggleModelSettings(){
    var params = document.getElementById('modelParams');
    if (params.style.display === 'none'){
      params.style.display = '';
    } else {
      params.style.display = 'none';
    }
  }
  // 模型参数滑块联动
  var tempRange = document.getElementById('tempRange');
  var maxTokRange = document.getElementById('maxTokRange');
  var topPRange = document.getElementById('topPRange');
  if (tempRange) tempRange.addEventListener('input', function(){ document.getElementById('tempVal').textContent = this.value; });
  if (maxTokRange) maxTokRange.addEventListener('input', function(){ document.getElementById('maxTokVal').textContent = this.value; });
  if (topPRange) topPRange.addEventListener('input', function(){ document.getElementById('topPVal').textContent = this.value; });

  /* ================= 知识设置面板 ================= */
  function toggleKnowledgeSettings(){
    var settings = document.getElementById('kbSettings');
    if (settings.style.display === 'none'){
      settings.style.display = '';
    } else {
      settings.style.display = 'none';
    }
  }
  var topKRange = document.getElementById('topKRange');
  var scoreRange = document.getElementById('scoreRange');
  if (topKRange) topKRange.addEventListener('input', function(){ document.getElementById('topKVal').textContent = this.value; });
  if (scoreRange) scoreRange.addEventListener('input', function(){ document.getElementById('scoreVal').textContent = this.value; });

  /* ================= 历史版本 ================= */
  var promptVersions = [];  // {time, content}
  function showVersionHistory(){
    var ta = document.getElementById('promptTa');
    // 保存当前版本
    if (ta.value && !promptVersions.some(function(v){ return v.content === ta.value; })){
      promptVersions.unshift({ time: new Date().toLocaleString(), content: ta.value });
    }
    if (!promptVersions.length){
      toast('暂无历史版本');
      return;
    }
    showModal('历史版本', promptVersions.map(function(v, i){
      return '<div class="ver-item" data-idx="' + i + '">' +
        '<span class="ver-time">' + v.time + '</span>' +
        '<span class="ver-preview">' + esc(v.content.slice(0, 60)) + '…</span>' +
        '<button class="ver-restore" data-action="restoreVersion(' + i + ')">恢复</button>' +
      '</div>';
    }).join(''), '恢复选中版本将覆盖当前提示词');
  }
  function restoreVersion(idx){
    var v = promptVersions[idx];
    if (!v) return;
    document.getElementById('promptTa').value = v.content;
    document.getElementById('promptCnt').textContent = v.content.length + '/100000';
    closeModal();
    toast('已恢复版本：' + v.time);
  }

  /* ================= 提示词模板 ================= */
  var PROMPT_TEMPLATES = [
    { name: '客服助手', content: '你是一个专业的客服助手。\n#角色名称\n专业客服代表\n#风格特点\n友好、耐心、专业\n#输出要求\n1. 准确理解用户问题\n2. 提供清晰的解决方案\n3. 必要时主动追问细节\n#输出限制\n- 不涉及公司机密信息\n- 遇到无法解决的问题时引导至人工客服' },
    { name: '代码助手', content: '你是一个编程专家。\n#角色名称\n资深开发工程师\n#风格特点\n严谨、高效、善于解释\n#输出要求\n1. 提供可直接运行的代码\n2. 解释关键逻辑\n3. 指出潜在问题\n#输出限制\n- 代码需包含必要注释\n- 避免过度设计' },
    { name: '写作助手', content: '你是一个写作专家。\n#角色名称\n专业文案创作者\n#风格特点\n文笔优美、逻辑清晰、富有感染力\n#输出要求\n1. 根据主题创作内容\n2. 结构清晰、层次分明\n3. 语言生动、引人入胜\n#输出限制\n- 避免抄袭\n- 符合目标受众阅读习惯' },
    { name: '数据分析', content: '你是一个数据分析专家。\n#角色名称\n资深数据分析师\n#风格特点\n严谨、客观、善于发现规律\n#输出要求\n1. 准确解读数据含义\n2. 发现数据趋势和异常\n3. 给出可操作的建议\n#输出限制\n- 分析需基于数据事实\n- 明确说明分析假设' }
  ];
  function showPromptTemplates(){
    showModal('提示词模板', PROMPT_TEMPLATES.map(function(t, i){
      return '<div class="tpl-item" data-idx="' + i + '">' +
        '<span class="tpl-name">' + esc(t.name) + '</span>' +
        '<span class="tpl-preview">' + esc(t.content.slice(0, 50)) + '…</span>' +
        '<button class="tpl-use" data-action="useTemplate(' + i + ')">使用</button>' +
      '</div>';
    }).join(''), '选择模板后将覆盖当前提示词');
  }
  function useTemplate(idx){
    var t = PROMPT_TEMPLATES[idx];
    if (!t) return;
    document.getElementById('promptTa').value = t.content;
    document.getElementById('promptCnt').textContent = t.content.length + '/100000';
    closeModal();
    toast('已应用模板：' + t.name);
  }

  /* ================= AI 一键优化 ================= */
  function aiOptimizePrompt(){
    var ta = document.getElementById('promptTa');
    var original = ta.value.trim();
    if (!original){
      toast('请先输入提示词');
      return;
    }
    var btn = document.querySelector('.ai-btn');
    var oldHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="ai">AI</i>优化中…';
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: '请优化以下提示词，使其更清晰、更专业、更适合AI理解。只返回优化后的提示词，不要解释。\n\n原始提示词：\n' + original,
        provider: 'auto'
      })
    }).then(function(res){
      if (!res.ok){ toast('优化失败'); btn.disabled = false; btn.innerHTML = oldHtml; return; }
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var optimized = '';
      function read(){
        reader.read().then(function(r){
          if (r.done){
            if (optimized.trim()){
              ta.value = optimized.trim();
              document.getElementById('promptCnt').textContent = ta.value.length + '/100000';
              toast('优化完成');
            }
            btn.disabled = false;
            btn.innerHTML = oldHtml;
            return;
          }
          buffer += decoder.decode(r.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';
          lines.forEach(function(line){
            if (line.indexOf('data: ') === 0){
              try{
                var d = JSON.parse(line.slice(6));
                if (d.content) optimized += d.content;
                if (d.done || d.error){
                  if (d.error) toast('优化失败：' + d.error);
                  btn.disabled = false; btn.innerHTML = oldHtml;
                }
              }catch(e){}
            }
          });
          read();
        }).catch(function(){
          btn.disabled = false; btn.innerHTML = oldHtml;
        });
      };
      read();
    }).catch(function(){
      btn.disabled = false; btn.innerHTML = oldHtml;
      toast('网络异常');
    });
  }

  /* ================= 分享 ================= */
  function showShareDialog(){
    var shareUrl = location.origin + '/#/share/agent/' + (agentId || 'demo');
    showModal('分享应用',
      '<div class="share-body">' +
        '<div class="share-link-box">' +
          '<label>分享链接</label>' +
          '<div class="share-link-row">' +
            '<input type="text" id="shareLink" value="' + esc(shareUrl) + '" readonly>' +
            '<button class="btn btn-sm" data-action="copyShareLink()">复制</button>' +
          '</div>' +
        '</div>' +
        '<div class="share-perm">' +
          '<label>访问权限</label>' +
          '<div class="perm-options">' +
            '<label class="perm-opt"><input type="radio" name="perm" value="public" checked> 公开访问</label>' +
            '<label class="perm-opt"><input type="radio" name="perm" value="password"> 密码保护</label>' +
            '<label class="perm-opt"><input type="radio" name="perm" value="private"> 仅自己</label>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }
  function copyShareLink(){
    var input = document.getElementById('shareLink');
    input.select();
    try {
      document.execCommand('copy');
      toast('链接已复制');
    } catch(e){
      toast('请手动复制');
    }
  }

  /* ================= 弹窗工具函数 ================= */
  var modalEl = null;
  function showModal(title, content, hint){
    closeModal();
    modalEl = document.createElement('div');
    modalEl.className = 'modal-overlay';
    modalEl.innerHTML =
      '<div class="modal-box">' +
        '<div class="modal-head"><span>' + esc(title) + '</span><button class="modal-close" onclick="closeModal()">✕</button></div>' +
        '<div class="modal-body">' + content + '</div>' +
        (hint ? '<div class="modal-hint">' + esc(hint) + '</div>' : '') +
      '</div>';
    document.body.appendChild(modalEl);
    modalEl.addEventListener('click', function(e){
      if (e.target === modalEl) closeModal();
    });
  }
  function closeModal(){
    if (modalEl){ modalEl.remove(); modalEl = null; }
  }

  /* ================= 预览对话（真实调用 API） ================= */
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('sendBtn');
  var previewChatHistory = [];
  input.addEventListener('input', function(){ sendBtn.classList.toggle('ready', !!input.value.trim()); });
  input.addEventListener('keydown', function(e){ if (e.key === 'Enter') sendMsg(); });

  function appName(){ return document.querySelector('.editor-top .js-name').textContent.trim(); }
  function sendMsg(){
    var v = input.value.trim();
    if (!v) return;
    var body = document.getElementById('previewBody');
    body.classList.add('chatting');
    var list = document.getElementById('msgList');
    // 用户消息
    list.insertAdjacentHTML('beforeend', '<div class="msg user"><div class="bubble"></div></div>');
    list.lastElementChild.querySelector('.bubble').textContent = v;
    previewChatHistory.push({ role: 'user', content: v });
    input.value = '';
    sendBtn.classList.remove('ready');
    body.scrollTop = body.scrollHeight;
    // 加载状态
    var loadingId = 'loading-' + Date.now();
    list.insertAdjacentHTML('beforeend', '<div class="msg bot" id="' + loadingId + '"><div class="bubble">思考中…</div></div>');
    body.scrollTop = body.scrollHeight;
    // 调用真实 API
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: v,
        provider: 'auto',
        agent_id: agentId || undefined,
        conversation_id: undefined
      })
    }).then(function(res){
      var loading = document.getElementById(loadingId);
      if (loading) loading.remove();
      if (!res.ok){
        list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble">⚠ 请求失败 (' + res.status + ')</div></div>');
        body.scrollTop = body.scrollHeight;
        return;
      }
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var fullText = '';
      var botMsgId = 'bot-' + Date.now();
      list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble" id="' + botMsgId + '"></div></div>');
      body.scrollTop = body.scrollHeight;
      function read(){
        reader.read().then(function(r){
          if (r.done){
            if (fullText) previewChatHistory.push({ role: 'assistant', content: fullText });
            return;
          }
          buffer += decoder.decode(r.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';
          lines.forEach(function(line){
            if (line.indexOf('data: ') === 0){
              try{
                var d = JSON.parse(line.slice(6));
                if (d.content){
                  fullText += d.content;
                  var el = document.getElementById(botMsgId);
                  if (el) el.textContent = fullText;
                  body.scrollTop = body.scrollHeight;
                }
                if (d.error){
                  var el2 = document.getElementById(botMsgId);
                  if (el2) el2.textContent = '⚠ ' + d.error;
                }
              }catch(e){}
            }
          });
          read();
        }).catch(function(){
          var el = document.getElementById(botMsgId);
          if (el && !fullText) el.textContent = '⚠ 网络异常';
          body.scrollTop = body.scrollHeight;
        });
      };
      read();
    }).catch(function(){
      var loading = document.getElementById(loadingId);
      if (loading) loading.remove();
      list.insertAdjacentHTML('beforeend', '<div class="msg bot"><div class="bubble">⚠ 网络异常，请稍后重试</div></div>');
      body.scrollTop = body.scrollHeight;
    });
  }
  function clearChat(){
    document.getElementById('msgList').innerHTML = '';
    document.getElementById('previewBody').classList.remove('chatting');
    previewChatHistory = [];
    toast('已清空对话');
  }

  /* ================= 页签切换（真实功能） ================= */
  document.querySelectorAll('#etabs .etab').forEach(function(tab){
    tab.addEventListener('click', function(){
      var tabName = tab.textContent.trim();
      document.querySelectorAll('#etabs .etab').forEach(function(t){ t.classList.remove('active'); });
      tab.classList.add('active');
      // 根据页签切换左侧面板内容
      var sections = document.querySelectorAll('.editor-left .cfg-section');
      sections.forEach(function(s){ s.style.display = ''; });
      if (tabName === '知识管理'){
        showTabSection('知识');
      } else if (tabName === '工作流管理'){
        showTabSection('工作流');
      } else if (tabName === '应用评测'){
        showTabSection('对话体验');
      } else if (tabName === '应用发布'){
        showTabSection('变量与记忆');
      }
    });
  });
  function showTabSection(title){
    var sections = document.querySelectorAll('.editor-left .cfg-section');
    sections.forEach(function(s){
      var t = s.querySelector('.cfg-head .t');
      if (t && t.textContent.trim() === title){
        s.style.display = '';
        s.classList.remove('closed');
      } else {
        s.style.display = 'none';
      }
    });
  }

  /* ================= 上传文件（预览区） ================= */
  var previewFileInput = null;
  function initPreviewUpload(){
    var uploadBtn = document.querySelector('.preview-input .plain-ico');
    if (!uploadBtn) return;
    uploadBtn.setAttribute('data-action', 'triggerPreviewUpload()');
    previewFileInput = document.createElement('input');
    previewFileInput.type = 'file';
    previewFileInput.style.display = 'none';
    previewFileInput.accept = '.txt,.md,.pdf,.doc,.docx,.csv,.json,.py,.js,.ts,.html,.css';
    previewFileInput.addEventListener('change', function(){
      if (!previewFileInput.files || !previewFileInput.files.length) return;
      var f = previewFileInput.files[0];
      var fd = new FormData();
      fd.append('file', f);
      apiPost('/api/files/upload', fd)
        .then(function(data){
          if (data.code === 200){
            toast('文件「' + data.data.original_name + '」已上传，发送消息时将引用');
          } else {
            toast(data.msg || '上传失败');
          }
        })
        .catch(function(){ toast('上传失败'); });
      previewFileInput.value = '';
    });
    document.body.appendChild(previewFileInput);
  }
  function triggerPreviewUpload(){
    if (previewFileInput) previewFileInput.click();
  }

  /* ================= 面板开关 ================= */
  function togglePreviewPanel(){
    var right = document.getElementById('editorRight');
    var left = document.querySelector('.editor-left');
    if (right.style.display === 'none'){
      right.style.display = '';
      if (left) left.style.flex = '';
      toast('已展开预览面板');
    } else {
      right.style.display = 'none';
      if (left) left.style.flex = '1';
      toast('已收起预览面板');
    }
  }

  /* ================= 对比调试 ================= */
  var compareMode = false;
  function toggleCompareMode(){
    compareMode = !compareMode;
    var right = document.getElementById('editorRight');
    if (compareMode){
      // 分屏对比模式
      right.classList.add('compare-mode');
      right.style.display = '';
      showModal('对比调试',
        '<div class="compare-info">' +
          '<p>对比调试模式已开启</p>' +
          '<p style="font-size:12px;color:var(--text-3);">修改配置后，可在预览区对比不同版本的效果差异</p>' +
          '<div class="compare-versions">' +
            '<div class="compare-ver"><span class="ver-tag">当前版本</span><span id="verCurrent">--</span></div>' +
            '<div class="compare-ver"><span class="ver-tag">上一版本</span><span id="verPrevious">--</span></div>' +
          '</div>' +
        '</div>'
      );
      toast('对比调试模式已开启');
    } else {
      right.classList.remove('compare-mode');
      closeModal();
      toast('已退出对比调试');
    }
  }

  /* ================= 追问建议 ================= */
  var suggestedQuestions = [];
  function renderSuggestedQuestions(){
    var box = document.getElementById('suggestedQuestions');
    if (!box) return;
    box.innerHTML = suggestedQuestions.map(function(q, i){
      return '<div class="sq-item">' +
        '<input type="text" value="' + esc(q) + '" data-idx="' + i + '" class="sq-input" placeholder="输入建议问题…">' +
        '<button class="sq-del" data-action="removeSuggestedQuestion(' + i + ')">✕</button>' +
      '</div>';
    }).join('');
  }
  function addSuggestedQuestion(){
    suggestedQuestions.push('…');
    renderSuggestedQuestions();
  }
  function removeSuggestedQuestion(idx){
    suggestedQuestions.splice(idx, 1);
    renderSuggestedQuestions();
  }

  /* ================= 应用变量 ================= */
  var appVariables = [];
  function renderAppVariables(){
    var box = document.getElementById('appVariables');
    if (!box) return;
    box.innerHTML = appVariables.map(function(v, i){
      return '<div class="av-item">' +
        '<input type="text" value="' + esc(v.name) + '" placeholder="变量名" class="av-name">' +
        '<input type="text" value="' + esc(v.default || '') + '" placeholder="默认值" class="av-default">' +
        '<button class="av-del" data-action="removeAppVariable(' + i + ')">✕</button>' +
      '</div>';
    }).join('');
  }
  function addAppVariable(){
    appVariables.push({ name: '', default: '' });
    renderAppVariables();
  }
  function removeAppVariable(idx){
    appVariables.splice(idx, 1);
    renderAppVariables();
  }

  /* 暴露函数到全局（供 data-action eval 调用） */
  window.toggleModelSettings = toggleModelSettings;
  window.toggleKnowledgeSettings = toggleKnowledgeSettings;
  window.showVersionHistory = showVersionHistory;
  window.restoreVersion = restoreVersion;
  window.showPromptTemplates = showPromptTemplates;
  window.useTemplate = useTemplate;
  window.aiOptimizePrompt = aiOptimizePrompt;
  window.showShareDialog = showShareDialog;
  window.copyShareLink = copyShareLink;
  window.closeModal = closeModal;
  window.togglePreviewPanel = togglePreviewPanel;
  window.toggleCompareMode = toggleCompareMode;
  window.addSuggestedQuestion = addSuggestedQuestion;
  window.removeSuggestedQuestion = removeSuggestedQuestion;
  window.addAppVariable = addAppVariable;
  window.removeAppVariable = removeAppVariable;
  window.triggerPreviewUpload = triggerPreviewUpload;

  /* 初始加载 */
  loadModelList(function(){
    loadAgent();
    initPreviewUpload();
    renderSuggestedQuestions();
    renderAppVariables();
  });
})
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
  .hd-gear{margin-left:auto;color:var(--text-3);cursor:pointer;font-size:14px;}
  .hd-gear:hover{color:var(--primary);}
  .hd-gear + .arrow{margin-left:10px;}
  .flex-row{display:flex;align-items:center;gap:12px;}
  .flex-row > label{width:88px;margin:0;flex-shrink:0;font-size:13px;color:var(--text-2);}
  .q{display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;border-radius:50%;border:1px solid var(--text-4);color:var(--text-4);font-size:9px;font-style:normal;margin:0 2px;cursor:help;}
  .req{color:var(--red);}
  /* 自定义下拉 */
  .dd-wrap{position:relative;flex:1;}
  .drop{display:none;position:absolute;top:calc(100% + 4px);left:0;min-width:100%;background:#fff;border:1px solid var(--border);border-radius:6px;box-shadow:0 6px 24px rgba(29,33,41,.12);z-index:50;padding:4px;}
  .drop.show{display:block;}
  .drop .opt{padding:8px 10px;border-radius:4px;font-size:13px;cursor:pointer;white-space:nowrap;}
  .drop .opt:hover{background:var(--primary-light);color:var(--primary);}
  .drop .opt .ctx{background:#F2F3F5;color:var(--text-3);font-size:11px;padding:1px 6px;border-radius:4px;margin-left:8px;}
  .model-select .caret{color:var(--text-3);font-size:12px;}
  /* 行标题 + 右侧按钮 */
  .row-head{display:flex;align-items:center;margin-bottom:8px;}
  .row-head .lbl{font-size:13px;color:var(--text-2);}
  .rh-ops{margin-left:auto;display:flex;align-items:center;gap:8px;}
  .plain-ico{border:none;background:none;color:var(--text-2);font-size:14px;cursor:pointer;padding:2px 4px;border-radius:4px;}
  .plain-ico:hover{color:var(--primary);}
  .mini-btn{border:1px solid var(--border);background:#fff;border-radius:6px;padding:3px 12px;font-size:12px;color:var(--text-1);cursor:pointer;}
  .mini-btn:hover{border-color:var(--primary);color:var(--primary);}
  .ai-btn{display:inline-flex;align-items:center;gap:4px;border:1px solid #B8CCFF;background:#F0F5FF;border-radius:6px;padding:3px 10px;font-size:12px;color:var(--primary);cursor:pointer;}
  .ai-btn:hover{background:var(--primary-light);}
  .ai-btn .ai{background:var(--primary);color:#fff;font-size:10px;border-radius:3px;padding:0 3px;font-weight:700;font-style:normal;}
  /* 大文本框 */
  .ta-wrap{position:relative;border:1px solid var(--border);border-radius:6px;background:#fff;}
  .ta-wrap:focus-within{border-color:var(--primary);}
  .ta-wrap textarea{width:100%;border:none;resize:vertical;min-height:230px;padding:12px 12px 26px;font-size:13px;line-height:1.9;background:transparent;display:block;}
  .ta-wrap .grip{position:absolute;left:50%;bottom:5px;transform:translateX(-50%);color:var(--text-4);font-size:10px;}
  .ta-wrap .cnt{position:absolute;right:10px;bottom:6px;font-size:12px;color:var(--text-4);}
  /* 预览区 */
  .preview-head .mini-dot{width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,#8AB4FF,#2E63F0);display:inline-block;}
  .ph-ops{margin-left:auto;display:flex;align-items:center;gap:14px;color:var(--text-2);}
  .ph-ops .plain-ico{font-size:15px;}
  .preview-body.chatting{justify-content:flex-start;align-items:stretch;}
  .msg-list{display:none;flex-direction:column;gap:14px;width:100%;max-width:760px;margin:0 auto;padding:26px 24px;}
  .preview-body.chatting .msg-list{display:flex;}
  .preview-body.chatting .p-empty{display:none;}
  .msg{display:flex;}
  .msg.user{justify-content:flex-end;}
  .msg .bubble{max-width:72%;padding:10px 14px;border-radius:10px;font-size:14px;line-height:1.7;word-break:break-word;}
  .msg.user .bubble{background:var(--primary);color:#fff;border-bottom-right-radius:2px;}
  .msg.bot .bubble{background:#F2F3F5;color:var(--text-1);border-bottom-left-radius:2px;}
  .preview-input .send.ready{background:var(--primary);}
  .single-agent-edit-root{ min-height:100vh; }
  #pubBtn.disabled{background:#F2F3F5;border-color:#F2F3F5;color:var(--text-4);cursor:not-allowed;}
  .pending.pub{color:#00B42A;}

  /* ================= 模型参数面板 ================= */
  .model-params .param-row{ margin-bottom:8px; }
  .model-params .param-row label{ display:flex; justify-content:space-between; font-size:12px; color:var(--text-2); margin-bottom:4px; }
  .param-val{ color:var(--primary); font-weight:600; }
  .model-params input[type="range"]{ -webkit-appearance:none; height:4px; background:#E5E6EB; border-radius:2px; outline:none; }
  .model-params input[type="range"]::-webkit-slider-thumb{ -webkit-appearance:none; width:14px; height:14px; background:var(--primary); border-radius:50%; cursor:pointer; }

  /* ================= 知识设置面板 ================= */
  .kb-settings .param-row{ margin-bottom:8px; }
  .kb-settings .param-row label{ display:flex; justify-content:space-between; font-size:12px; color:var(--text-2); margin-bottom:4px; }
  .kb-settings input[type="range"]{ -webkit-appearance:none; height:4px; background:#E5E6EB; border-radius:2px; outline:none; }
  .kb-settings input[type="range"]::-webkit-slider-thumb{ -webkit-appearance:none; width:14px; height:14px; background:var(--primary); border-radius:50%; cursor:pointer; }

  /* ================= 弹窗 ================= */
  .modal-overlay{ position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,.4); z-index:1000; display:flex; align-items:center; justify-content:center; }
  .modal-box{ background:#fff; border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,.18); max-width:520px; width:90%; max-height:80vh; display:flex; flex-direction:column; }
  .modal-head{ display:flex; align-items:center; justify-content:space-between; padding:16px 20px; border-bottom:1px solid var(--border-light); font-size:16px; font-weight:600; }
  .modal-close{ border:none; background:none; font-size:18px; color:var(--text-3); cursor:pointer; padding:4px 8px; border-radius:4px; }
  .modal-close:hover{ background:#F2F3F5; }
  .modal-body{ padding:16px 20px; overflow-y:auto; flex:1; }
  .modal-hint{ padding:10px 20px; font-size:12px; color:var(--text-4); border-top:1px solid var(--border-light); background:#FAFBFC; }

  /* ================= 历史版本 ================= */
  .ver-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid var(--border-light); border-radius:6px; margin-bottom:6px; cursor:pointer; transition:background .15s; }
  .ver-item:hover{ background:#F7F8FA; }
  .ver-time{ font-size:12px; color:var(--text-3); flex-shrink:0; }
  .ver-preview{ flex:1; font-size:13px; color:var(--text-1); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ver-restore{ border:1px solid var(--primary); background:#fff; color:var(--primary); border-radius:4px; padding:3px 10px; font-size:12px; cursor:pointer; flex-shrink:0; }
  .ver-restore:hover{ background:var(--primary-light); }

  /* ================= 提示词模板 ================= */
  .tpl-item{ display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid var(--border-light); border-radius:6px; margin-bottom:6px; cursor:pointer; transition:background .15s; }
  .tpl-item:hover{ background:#F7F8FA; }
  .tpl-name{ font-size:13px; font-weight:600; color:var(--text-1); flex-shrink:0; min-width:70px; }
  .tpl-preview{ flex:1; font-size:12px; color:var(--text-3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .tpl-use{ border:1px solid var(--primary); background:#fff; color:var(--primary); border-radius:4px; padding:3px 10px; font-size:12px; cursor:pointer; flex-shrink:0; }
  .tpl-use:hover{ background:var(--primary-light); }

  /* ================= 分享弹窗 ================= */
  .share-body{ display:flex; flex-direction:column; gap:16px; }
  .share-link-box label{ font-size:13px; color:var(--text-2); margin-bottom:6px; display:block; }
  .share-link-row{ display:flex; gap:8px; }
  .share-link-row input{ flex:1; padding:8px 12px; border:1px solid var(--border); border-radius:6px; font-size:13px; background:#F7F8FA; }
  .share-perm label{ font-size:13px; color:var(--text-2); margin-bottom:6px; display:block; }
  .perm-options{ display:flex; gap:16px; }
  .perm-opt{ display:flex; align-items:center; gap:4px; font-size:13px; cursor:pointer; }

  /* ================= 对比调试 ================= */
  .compare-info{ font-size:14px; }
  .compare-info p{ margin:8px 0; }
  .compare-versions{ display:flex; gap:12px; margin-top:12px; }
  .compare-ver{ flex:1; padding:10px; background:#F7F8FA; border-radius:6px; }
  .ver-tag{ display:block; font-size:11px; color:var(--text-3); margin-bottom:4px; }
  .editor-right.compare-mode{ border:2px solid var(--primary); }

  /* ================= 追问建议 ================= */
  .sq-item{ display:flex; gap:6px; margin-bottom:6px; }
  .sq-input{ flex:1; padding:6px 10px; border:1px solid var(--border); border-radius:4px; font-size:13px; }
  .sq-del{ border:none; background:none; color:var(--text-4); cursor:pointer; font-size:14px; padding:4px; }
  .sq-del:hover{ color:#E64A19; }

  /* ================= 应用变量 ================= */
  .av-item{ display:flex; gap:6px; margin-bottom:6px; }
  .av-name{ width:100px; padding:6px 10px; border:1px solid var(--border); border-radius:4px; font-size:13px; }
  .av-default{ flex:1; padding:6px 10px; border:1px solid var(--border); border-radius:4px; font-size:13px; }
  .av-del{ border:none; background:none; color:var(--text-4); cursor:pointer; font-size:14px; padding:4px; }
  .av-del:hover{ color:#E64A19; }

  /* ================= 开关 ================= */
  .switch-label{ display:flex; align-items:center; gap:6px; font-size:13px; cursor:pointer; }
  .switch-label input{ accent-color:var(--primary); }

  /* ================= 添加链接 ================= */
  .add-link{ display:inline-block; margin-top:6px; font-size:13px; color:var(--primary); text-decoration:none; cursor:pointer; }
  .add-link:hover{ text-decoration:underline; }

  /* ================= 参数行通用 ================= */
  .param-row{ margin-bottom:10px; }
  .param-row label{ display:flex; justify-content:space-between; font-size:12px; color:var(--text-2); margin-bottom:4px; }
  .param-row select{ width:100%; padding:6px 8px; border:1px solid var(--border); border-radius:6px; font-size:13px; background:#fff; }
</style>

<template>
  <AppShell active-key="home" main-class="main-white">
    <div class="home-wrap">
      <!-- 中间：任务导航面板 -->
      <aside class="task-panel" id="task-panel">
        <div class="tp-search">
          <input id="tp-search-input" placeholder="搜索" autocomplete="off">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </div>
        <div class="tp-scroll">
          <div class="tp-item active" id="tp-new">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 5v14M5 12h14"/></svg>
            新建任务
          </div>
          <div class="tp-group"><span>任务</span></div>
          <div id="tp-task-list"></div>
        </div>
      </aside>

      <!-- 右侧：工作区 -->
      <div class="workbench">
        <div class="wb-head">
          <button class="ico-btn" id="wb-panel-toggle" title="收起/展开任务面板">
            <svg width="17" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9.5 4v16"/></svg>
          </button>
          <button class="ico-btn" id="wb-newtask" title="新任务">
            <svg width="17" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 17L17 7M9 7h8v8"/></svg>
          </button>
          <span class="t" id="wb-title">新任务</span>
        </div>

        <div class="wb-center" id="wb-center">
          <div class="wb-welcome" id="wb-welcome">
            <div class="wb-slogan">

              <span>描述需求，开启智能工作方式</span>
            </div>
            <div class="wb-desc">一站式智能工作台，连接企业知识库与技能，从规划到执行完成每一项任务。</div>
            <!-- 统计卡片 -->
            <div class="wb-stats" id="wb-stats">
              <div class="stat-card"><span class="stat-num" id="stat-apps">-</span><span class="stat-label">应用</span></div>
              <div class="stat-card"><span class="stat-num" id="stat-convs">-</span><span class="stat-label">会话</span></div>
              <div class="stat-card"><span class="stat-num" id="stat-kbs">-</span><span class="stat-label">知识库</span></div>
              <div class="stat-card"><span class="stat-num" id="stat-wfs">-</span><span class="stat-label">工作流</span></div>
            </div>
            <!-- 最近活动 -->
            <div class="wb-recent" id="wb-recent">
              <div class="wb-recent-head">最近活动</div>
              <div class="wb-recent-list" id="wb-recent-list">
                <div class="wb-recent-empty">加载中…</div>
              </div>
            </div>
          </div>
          <div class="wb-chat" id="wb-chat" style="display:none"></div>
        </div>

        <div class="wb-bottom">
          <div class="wb-inputbox">
            <textarea id="wb-input" placeholder="支持上传图片或文件进行提问，输入@唤起安装的Skills/工具/知识库"></textarea>
            <div class="wb-attach" id="wb-attach" style="display:none"></div>
            <div class="wb-toolbar">
              <button class="tl" style="font-size:17px" title="上传" id="wb-upload-btn">＋</button>
              <input type="file" id="wb-file-input" multiple style="display:none" accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.json,.xml,.yaml,.yml,.jpg,.jpeg,.png,.gif,.bmp,.webp,.svg,.py,.js,.ts,.html,.css,.sql">
              <div class="model-dd">
                <button class="tl" id="model-btn"><span style="color:#2E63F0">◉</span> <span id="model-name">Auto</span> ▾</button>
                <div class="model-menu" id="model-menu">
                  <div class="mi on" data-v="Auto" data-provider="auto">Auto</div>
                </div>
              </div>
              <div class="kb-dd">
                <button class="tl tl-gap" id="kb-btn" title="选择知识库（回答将基于所选知识库）">📄 知识库</button>
                <div class="kb-menu" id="kb-menu">
                  <div class="kb-menu-head">选择知识库（可多选，回答将基于所选知识库）</div>
                  <div class="kb-menu-list" id="kb-list">加载中…</div>
                </div>
              </div>
              <div class="skill-dd">
                <button class="tl tl-gap" id="skill-btn" title="选择技能（回答将基于所选技能）">💡 Skills</button>
                <div class="skill-menu" id="skill-menu">
                  <div class="skill-menu-head">选择技能（可多选，回答将基于所选技能）</div>
                  <div class="skill-menu-list" id="skill-list">加载中…</div>
                </div>
              </div>
              <button class="wb-send" id="wb-send" title="发送">↑</button>
            </div>
          </div>

        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { onMounted, onActivated, onDeactivated } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast } from '../utils/global'
import { apiGet, apiPost } from '../api/client'

// 提升元素引用和文档点击处理器到组件作用域，以便在 onDeactivated 中清理
var modelMenu = null, kbMenu = null, skillMenu = null;

function onModelDocClick(){ if (modelMenu) modelMenu.classList.remove('show'); }
function onKbDocClick(){ if (kbMenu) kbMenu.classList.remove('show'); }
function onSkillDocClick(){ if (skillMenu) skillMenu.classList.remove('show'); }

onMounted(function(){
  /* ================= 数据层：任务持久化（localStorage: wb_tasks） ================= */
  var STORE_KEY = 'wb_tasks';

  function defaultTasks(){
    return [
      { id:'t-cloudcode', name:'Cloud Code配置指南', time:'10:47', history:[
        { role:'user', text:'Cloud Code 如何配置本地开发环境？' },
        { role:'bot',  text:'已收到你的需求，正在为你规划执行方案…\n1. 安装插件：在 IDE 插件市场搜索「Cloud Code」并安装，重启后生效；\n2. 登录账号：打开 Cloud Code 面板，使用企业账号完成授权登录；\n3. 配置环境：在设置中填入 API 地址与访问令牌，选择默认模型；\n4. 验证连通：点击「测试连接」，显示绿色即表示配置成功。' },
        { role:'user', text:'配置完成后如何验证是否生效？' },
        { role:'bot',  text:'可以通过以下方式验证：\n1. 在 Cloud Code 面板点击「测试连接」，返回成功即生效；\n2. 新建一个测试文件，唤起代码补全，能正常返回建议说明配置无误；\n3. 若提示 401，请检查访问令牌是否过期并重新授权。' }
      ]},
      { id:'t-minutes', name:'会议纪要整理应用', time:'7/21', history:[
        { role:'user', text:'帮我做一个能自动整理会议纪要的应用' },
        { role:'bot',  text:'已收到你的需求，正在为你规划执行方案…\n1. 需求分析：支持上传会议录音或文字记录，自动提炼议题、结论与待办；\n2. 方案规划：接入语音识别 + 大模型摘要 Skill，生成结构化纪要；\n3. 任务执行：按「上传 → 转写 → 提炼 → 排版」四步构建工作流；\n4. 结果交付：输出标准会议纪要文档，支持一键导出。' },
        { role:'user', text:'支持导出为 Word 吗？' },
        { role:'bot',  text:'支持。纪要生成后点击右上角「导出」，可选 Word / PDF / Markdown 三种格式，Word 导出会自动套用公司纪要模板。' }
      ]}
    ];
  }

  function loadTasks(){
    try{
      var v = JSON.parse(localStorage.getItem(STORE_KEY));
      if (Array.isArray(v) && v.length) return v;
    }catch(e){}
    var d = defaultTasks();
    saveTasks(d);
    return d;
  }
  function saveTasks(list){ localStorage.setItem(STORE_KEY, JSON.stringify(list || tasks)); }

  var tasks = loadTasks();
  var currentId = null;

  /* ================= 元素引用 ================= */
  var input      = document.getElementById('wb-input');
  var sendBtn    = document.getElementById('wb-send');
  var center     = document.getElementById('wb-center');
  var welcome    = document.getElementById('wb-welcome');
  var chat       = document.getElementById('wb-chat');
  var headTitle  = document.getElementById('wb-title');
  var taskListEl = document.getElementById('tp-task-list');
  var tpNew      = document.getElementById('tp-new');

  var ROBOT_SVG = '<svg width="18" height="18" viewBox="0 0 48 48"><rect x="4" y="7" width="36" height="36" rx="11" fill="#1D2129"/><circle cx="16" cy="23" r="3" fill="#fff"/><circle cx="28" cy="23" r="3" fill="#fff"/><path d="M17 31c1.8 2 3.5 2.8 5 2.8s3.2-.8 5-2.8" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round"/><circle cx="39" cy="9" r="6" fill="#2E63F0"/></svg>';

  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function nowHM(){
    var d = new Date();
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  function findTask(id){
    for (var i = 0; i < tasks.length; i++) if (tasks[i].id === id) return tasks[i];
    return null;
  }

  /* ================= 思维链（Thinking Chain）渲染 ================= */

  /**
   * 创建思维链 DOM 元素
   */
  function createThinkingEl(thinkingText){
    var div = document.createElement('div');
    div.className = 'thinking-chain';

    var header = document.createElement('div');
    header.className = 'thinking-header';
    header.innerHTML =
      '<svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
        '<path d="M12 2a4 4 0 0 1 4 4c0 1.5-.8 2.8-2 3.5v1.5h2a3 3 0 0 1 3 3v1h1a2 2 0 1 1 0 4h-1v1a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-1H4a2 2 0 1 1 0-4h1v-1a3 3 0 0 1 3-3h2V9.5C8.8 8.8 8 7.5 8 6a4 4 0 0 1 4-4z"/>' +
        '<circle cx="12" cy="18" r="1"/>' +
      '</svg>' +
      '<span class="thinking-title">思考过程</span>' +
      '<svg class="thinking-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M6 9l6 6 6-6"/>' +
      '</svg>';

    var body = document.createElement('div');
    body.className = 'thinking-body';
    body.textContent = thinkingText;

    div.appendChild(header);
    div.appendChild(body);

    header.addEventListener('click', function(){
      div.classList.toggle('collapsed');
    });

    return div;
  }

  /**
   * 更新思维链内容（流式）
   */
  function updateThinkingEl(thinkingEl, delta){
    var body = thinkingEl.querySelector('.thinking-body');
    if (body){
      body.textContent += delta;
    }
  }

  /* ================= 中间面板：任务列表渲染 ================= */
  function renderTaskList(filter){
    filter = (filter || '').trim();
    taskListEl.innerHTML = '';
    tasks.forEach(function(t){
      if (filter && t.name.indexOf(filter) === -1) return;
      var div = document.createElement('div');
      div.className = 'tp-task' + (t.id === currentId ? ' active' : '');
      div.innerHTML = '<span class="nm">' + esc(t.name) + '</span><span class="tm">' + esc(t.time) + '</span>';
      div.addEventListener('click', function(){ openTask(t.id); });
      taskListEl.appendChild(div);
    });
  }

  document.getElementById('tp-search-input').addEventListener('input', function(){
    renderTaskList(this.value);
  });

  /* ================= 视图切换：新任务态 / 任务详情态 ================= */
  function newTaskState(){
    currentId = null;
    headTitle.textContent = '新任务';
    welcome.style.display = '';
    chat.style.display = 'none';
    chat.innerHTML = '';
    center.classList.remove('chatting');
    tpNew.classList.add('active');
    input.value = ''; syncSend();
    renderTaskList(document.getElementById('tp-search-input').value);
  }

  function openTask(id){
    var t = findTask(id);
    if (!t) return;
    currentId = id;
    headTitle.textContent = t.name;
    welcome.style.display = 'none';
    chat.style.display = 'flex';
    center.classList.add('chatting');
    tpNew.classList.remove('active');
    chat.innerHTML = '';
    t.history.forEach(function(m){ addMsg(m.role, m.text, false); });
    center.scrollTop = center.scrollHeight;
    renderTaskList(document.getElementById('tp-search-input').value);
  }

  tpNew.addEventListener('click', newTaskState);
  document.getElementById('wb-newtask').addEventListener('click', newTaskState);

  /* 任务面板收起/展开 */
  document.getElementById('wb-panel-toggle').addEventListener('click', function(){
    document.getElementById('task-panel').classList.toggle('hidden');
  });

  /* ================= 对话区 ================= */
  function addMsg(role, text, scroll){
    var div = document.createElement('div');
    div.className = 'msg ' + role;
    var ava = role === 'user'
      ? '<div class="m-ava">我</div>'
      : '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div>';
    div.innerHTML = ava;
    var body = document.createElement('div');
    body.className = 'm-body';
    var bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = esc(text).replace(/\n/g, '<br>');
    body.appendChild(bubble);
    div.appendChild(body);
    chat.appendChild(div);
    if (scroll !== false) center.scrollTop = center.scrollHeight;
  }

  /* 在最后一条 bot 消息下追加知识库引用标签 */
  function addKbTag(names){
    var last = chat.lastElementChild;
    if (!last || !last.classList.contains('bot')) return;
    var body = last.querySelector('.m-body');
    var tag = document.createElement('div');
    tag.className = 'msg-kb';
    tag.textContent = '📚 基于知识库：' + names.join('、');
    (body || last).appendChild(tag);
    center.scrollTop = center.scrollHeight;
  }

  /* 在最后一条 bot 消息下追加技能引用标签 */
  function addSkillTag(names){
    var last = chat.lastElementChild;
    if (!last || !last.classList.contains('bot')) return;
    var body = last.querySelector('.m-body');
    var tag = document.createElement('div');
    tag.className = 'msg-skill';
    tag.textContent = '💡 使用技能：' + names.join('、');
    (body || last).appendChild(tag);
    center.scrollTop = center.scrollHeight;
  }

  /* 在最后一条 bot 消息下追加文件引用标签 */
  function addFileTag(names){
    var last = chat.lastElementChild;
    if (!last || !last.classList.contains('bot')) return;
    var body = last.querySelector('.m-body');
    var tag = document.createElement('div');
    tag.className = 'msg-file';
    tag.textContent = '📎 参考文件：' + names.join('、');
    (body || last).appendChild(tag);
    center.scrollTop = center.scrollHeight;
  }

  function send(){
    var text = input.value.trim();
    if (!text) return;
    var t;
    if (!currentId){
      t = { id:'t' + Date.now(), name:text, time:nowHM(), history:[] };
      tasks.unshift(t);
      saveTasks();
      openTask(t.id);
      t = findTask(currentId);
    } else {
      t = findTask(currentId);
      if (!t) return;
    }
    addMsg('user', text);
    t.history.push({ role:'user', text:text });
    saveTasks();
    input.value = '';
    syncSend();
    /* 确定使用的模型 */
    var curModel = modelName.textContent;
    var usedProvider = '';
    if (curModel === 'Auto' || curModel.indexOf('(Auto)') !== -1){
      usedProvider = 'auto';
      var nextName = getNextAutoModel();
      modelName.textContent = nextName + ' (Auto)';
    } else {
      var activeMi = modelMenu.querySelector('.mi.on');
      usedProvider = activeMi ? activeMi.getAttribute('data-provider') : '';
    }
    /* 显示加载状态 */
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'msg bot';
    loadingDiv.id = 'msg-loading';
    loadingDiv.innerHTML = '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div><div class="bubble">思考中…</div>';
    chat.appendChild(loadingDiv);
    center.scrollTop = center.scrollHeight;

    /* 调用后端流式 API */
    var requestBody = {
      message: text,
      provider: usedProvider,
      knowledge_ids: selectedKb.map(function(k){ return k.id; }),
      skills: selectedSkills.map(function(s){ return s.key; }),
      file_ids: attachedFiles.map(function(f){ return f.id; })
    };
    // 清空附件（请求体已构造完毕）
    attachedFiles = [];
    attachWrap.innerHTML = '';
    attachWrap.style.display = 'none';
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    })
    .then(function(response){
      var ld = document.getElementById('msg-loading');
      if (ld) ld.remove();

      if (!response.ok){
        addMsg('bot', '⚠ 请求失败 (' + response.status + ')');
        t.history.push({ role:'bot', text:'⚠ 请求失败', model:'error' });
        saveTasks();
        return;
      }

      // 创建消息容器
      var botMsgDiv = document.createElement('div');
      botMsgDiv.className = 'msg bot';
      botMsgDiv.innerHTML = '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div>';
      var mBody = document.createElement('div');
      mBody.className = 'm-body';
      var bubble = document.createElement('div');
      bubble.className = 'bubble';
      mBody.appendChild(bubble);
      botMsgDiv.appendChild(mBody);
      chat.appendChild(botMsgDiv);

      // 思维链状态
      var thinkingEl = null;
      var fullText = '';
      var fullThinking = '';

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      function readStream(){
        reader.read().then(function(result){
          if (result.done){
            // 流结束时保存
            if (data.knowledge_used && data.knowledge_used.length) addKbTag(data.knowledge_used);
            if (data.skills_used && data.skills_used.length) addSkillTag(data.skills_used.map(function(s){ return s.name; }));
            if (data.file_used && data.file_used.length) addFileTag(data.file_used);
            t.history.push({ role:'bot', text:fullText, model:usedProvider, thinking:fullThinking });
            saveTasks();
            return;
          }
          buffer += decoder.decode(result.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (var i = 0; i < lines.length; i++){
            var line = lines[i].trim();
            if (line.indexOf('data: ') === 0){
              try{
                var data = JSON.parse(line.slice(6));

                // 处理思维链
                if (data.thinking){
                  fullThinking += data.thinking;
                  if (!thinkingEl){
                    thinkingEl = createThinkingEl(data.thinking);
                    botMsgDiv.insertBefore(thinkingEl, mBody);
                  } else {
                    updateThinkingEl(thinkingEl, data.thinking);
                  }
                }

                // 处理正文
                if (data.content){
                  if (thinkingEl && fullText === ''){
                    thinkingEl.classList.add('collapsed');
                  }
                  fullText += data.content;
                  bubble.textContent = fullText;
                }

                if (data.done){
                  if (data.knowledge_used && data.knowledge_used.length) addKbTag(data.knowledge_used);
                  if (data.skills_used && data.skills_used.length) addSkillTag(data.skills_used.map(function(s){ return s.name; }));
                  if (data.file_used && data.file_used.length) addFileTag(data.file_used);
                  t.history.push({ role:'bot', text:fullText, model:data.model || usedProvider, thinking:fullThinking });
                  saveTasks();
                  return;
                }

                if (data.error){
                  bubble.textContent = '⚠ ' + data.error;
                  t.history.push({ role:'bot', text:'⚠ ' + data.error, model:'error' });
                  saveTasks();
                  return;
                }

                if (data.stopped){
                  bubble.textContent = fullText + ' [已停止]';
                  t.history.push({ role:'bot', text:fullText + ' [已停止]', model:usedProvider, thinking:fullThinking });
                  saveTasks();
                  return;
                }
              }catch(e){}
            }
          }
          center.scrollTop = center.scrollHeight;
          readStream();
        }).catch(function(){
          if (!fullText){
            bubble.textContent = '⚠ 网络异常，请稍后重试';
            t.history.push({ role:'bot', text:'⚠ 网络异常，请稍后重试', model:'error' });
            saveTasks();
          }
        });
      }
      readStream();
    })
    .catch(function(){
      var ld = document.getElementById('msg-loading');
      if (ld) ld.remove();
      addMsg('bot', '⚠ 网络异常，请稍后重试');
      t.history.push({ role:'bot', text:'⚠ 网络异常，请稍后重试', model:'error' });
      saveTasks();
    });
  }

  /* ================= 输入区通用交互 ================= */
  function syncSend(){ sendBtn.classList.toggle('ready', !!input.value.trim()); }
  input.addEventListener('input', syncSend);

  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', function(e){
    if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); send(); }
  });

  /* 模型下拉：从 API 加载模型列表 */
  var modelBtn  = document.getElementById('model-btn');
  modelMenu = document.getElementById('model-menu');
  var modelName = document.getElementById('model-name');
  var modelList = [];  // 从 API 获取的模型列表
  var autoIndex = 0;   // Auto 轮询索引

  function loadModelList(){
    apiGet('/api/model-configs').then(function(res){
      if (res.code === 200){
        modelList = (res.data || []).filter(function(m){ return m.status === 1; });
        renderModelMenu();
      }
    }).catch(function(){});
  }

  function renderModelMenu(){
    var html = '<div class="mi on" data-v="Auto" data-provider="auto">Auto</div>';
    modelList.forEach(function(m){
      var label = (m.credential_name || m.provider);
      html += '<div class="mi" data-v="' + label + '" data-provider="' + m.provider + '">' + label + '</div>';
    });
    modelMenu.innerHTML = html;
    modelMenu.querySelectorAll('.mi').forEach(function(mi){
      mi.addEventListener('click', function(e){
        e.stopPropagation();
        modelMenu.querySelectorAll('.mi').forEach(function(x){ x.classList.remove('on'); });
        mi.classList.add('on');
        modelName.textContent = mi.getAttribute('data-v');
        modelMenu.classList.remove('show');
        if (mi.getAttribute('data-v') === 'Auto'){
          toast('已切换为 Auto 自动模式');
        } else {
          toast('已切换模型：' + mi.getAttribute('data-v'));
        }
      });
    });
  }

  modelBtn.addEventListener('click', function(e){
    e.stopPropagation();
    modelMenu.classList.toggle('show');
  });
  /* 知识库选择：加载知识库列表，多选后发送消息时携带 */
  var kbBtn     = document.getElementById('kb-btn');
  kbMenu    = document.getElementById('kb-menu');
  var kbListBox = document.getElementById('kb-list');
  var kbList = [];
  var selectedKb = [];  // {id, name}

  function renderKbMenu(){
    if (!kbList.length){
      kbListBox.innerHTML = '<div class="kb-empty">暂无可用知识库，请先在知识库页创建</div>';
      return;
    }
    kbListBox.innerHTML = kbList.map(function(k){
      var on = selectedKb.some(function(s){ return s.id === k.id; });
      return '<label class="kb-opt' + (on ? ' on' : '') + '">' +
        '<input type="checkbox" data-id="' + k.id + '"' + (on ? ' checked' : '') + '>' +
        '<span class="kb-nm">' + esc(k.name) + '</span>' +
        '<span class="kb-cnt">📄 ' + (k.doc_count || 0) + '</span>' +
      '</label>';
    }).join('');
  }
  function syncKbBtn(){
    if (selectedKb.length){
      kbBtn.textContent = '📄 知识库(' + selectedKb.length + ')';
      kbBtn.classList.add('on');
      kbBtn.title = '回答将基于：' + selectedKb.map(function(k){ return k.name; }).join('、');
    } else {
      kbBtn.textContent = '📄 知识库';
      kbBtn.classList.remove('on');
      kbBtn.title = '选择知识库（回答将基于所选知识库）';
    }
  }
  function loadKbList(){
    apiGet('/api/knowledge/datasets').then(function(res){
      if (res.code === 200) kbList = res.data || [];
      renderKbMenu();
    }).catch(function(){
      kbListBox.innerHTML = '<div class="kb-empty">知识库加载失败</div>';
    });
  }
  kbBtn.addEventListener('click', function(e){
    e.stopPropagation();
    kbMenu.classList.toggle('show');
  });
  kbListBox.addEventListener('click', function(e){
    var cb = e.target && e.target.matches && e.target.matches('input[type="checkbox"]') ? e.target : null;
    if (!cb) return;
    var id = cb.dataset.id;
    var k = null;
    kbList.forEach(function(x){ if (x.id === id) k = x; });
    if (!k) return;
    var idx = -1;
    for (var i = 0; i < selectedKb.length; i++) if (selectedKb[i].id === id){ idx = i; break; }
    if (idx > -1) selectedKb.splice(idx, 1);
    else selectedKb.push({ id: id, name: k.name });
    renderKbMenu();
    syncKbBtn();
  });
  loadKbList();

  /* 技能选择：加载技能列表，多选后发送消息时携带 */
  var skillBtn     = document.getElementById('skill-btn');
  skillMenu    = document.getElementById('skill-menu');
  var skillListBox = document.getElementById('skill-list');
  var skillList = [];
  var selectedSkills = [];  // {key, name, icon}

  function renderSkillMenu(){
    if (!skillList.length){
      skillListBox.innerHTML = '<div class="skill-empty">暂无可用技能，请先在技能广场安装</div>';
      return;
    }
    skillListBox.innerHTML = skillList.map(function(s){
      var on = selectedSkills.some(function(sk){ return sk.key === s.key; });
      var key = s.key.replace(/'/g, '\\\'');
      return '<label class="skill-opt' + (on ? ' on' : '') + '">' +
        '<input type="checkbox" data-key="' + key + '"' + (on ? ' checked' : '') + '>' +
        '<span class="skill-icon">' + esc(s.icon || '✨') + '</span>' +
        '<span class="skill-nm">' + esc(s.name) + '</span>' +
        '<span class="skill-kind">' + (s.kind === 'builtin' ? '内置' : '自定义') + '</span>' +
      '</label>';
    }).join('');
  }
  function syncSkillBtn(){
    if (selectedSkills.length){
      skillBtn.textContent = '💡 Skills(' + selectedSkills.length + ')';
      skillBtn.classList.add('on');
      skillBtn.title = '已启用技能：' + selectedSkills.map(function(s){ return s.name; }).join('、');
    } else {
      skillBtn.textContent = '💡 Skills';
      skillBtn.classList.remove('on');
      skillBtn.title = '选择技能（回答将基于所选技能）';
    }
  }
  function loadSkillList(){
    apiGet('/api/skills').then(function(res){
      if (res.code === 200){
        // 只显示已安装的技能
        skillList = (res.data || []).filter(function(s){ return s.installed; });
        renderSkillMenu();
      }
    }).catch(function(){
      skillListBox.innerHTML = '<div class="skill-empty">技能加载失败</div>';
    });
  }
  skillBtn.addEventListener('click', function(e){
    e.stopPropagation();
    skillMenu.classList.toggle('show');
  });
  skillListBox.addEventListener('click', function(e){
    var cb = e.target && e.target.matches && e.target.matches('input[type="checkbox"]') ? e.target : null;
    if (!cb) return;
    var key = cb.dataset.key;
    var s = null;
    skillList.forEach(function(x){ if (x.key === key) s = x; });
    if (!s) return;
    var idx = -1;
    for (var i = 0; i < selectedSkills.length; i++) if (selectedSkills[i].key === key){ idx = i; break; }
    if (idx > -1) selectedSkills.splice(idx, 1);
    else selectedSkills.push({ key: key, name: s.name, icon: s.icon });
    renderSkillMenu();
    syncSkillBtn();
  });
  loadSkillList();

  /* 文件上传：选择文件后立即上传，发送消息时携带文件 ID */
  var fileInput    = document.getElementById('wb-file-input');
  var uploadBtn    = document.getElementById('wb-upload-btn');
  var attachWrap   = document.getElementById('wb-attach');
  var attachedFiles = [];  // {id, original_name, file_size, file_type}

  uploadBtn.addEventListener('click', function(){
    fileInput.click();
  });

  fileInput.addEventListener('change', function(){
    if (!fileInput.files || !fileInput.files.length) return;
    var files = Array.from(fileInput.files);
    files.forEach(function(f){
      // 显示加载占位
      var chip = document.createElement('div');
      chip.className = 'attach-chip uploading';
      chip.innerHTML = '<span class="ac-name">' + esc(f.name) + '</span><span class="ac-progress">上传中…</span>';
      attachWrap.appendChild(chip);
      attachWrap.style.display = '';

      // 上传文件
      var fd = new FormData();
      fd.append('file', f);
      apiPost('/api/files/upload', fd)
        .then(function(res){
          if (res.code === 200){
            attachedFiles.push({
              id: res.data.id,
              original_name: res.data.original_name,
              file_size: res.data.file_size,
              file_type: res.data.file_type
            });
            chip.className = 'attach-chip';
            chip.innerHTML = '<span class="ac-name">' + esc(res.data.original_name) + '</span>' +
              '<span class="ac-size">' + formatFileSize(data.data.file_size) + '</span>' +
              '<span class="ac-del" data-fid="' + data.data.id + '" title="移除">✕</span>';
          } else {
            chip.className = 'attach-chip error';
            chip.innerHTML = '<span class="ac-name">' + esc(f.name) + '</span>' +
              '<span class="ac-err">' + esc(data.msg || '上传失败') + '</span>' +
              '<span class="ac-del" title="移除">✕</span>';
          }
        })
        .catch(function(){
          chip.className = 'attach-chip error';
          chip.innerHTML = '<span class="ac-name">' + esc(f.name) + '</span>' +
            '<span class="ac-err">网络错误</span>' +
            '<span class="ac-del" title="移除">✕</span>';
        });
    });
    // 清空 input，允许重复选择同一文件
    fileInput.value = '';
  });

  // 删除附件
  attachWrap.addEventListener('click', function(e){
    var del = e.target && e.target.classList && e.target.classList.contains('ac-del') ? e.target : null;
    if (!del) return;
    var fid = del.dataset.fid;
    if (fid){
      var idx = -1;
      for (var i = 0; i < attachedFiles.length; i++){
        if (attachedFiles[i].id === fid){ idx = i; break; }
      }
      if (idx > -1) attachedFiles.splice(idx, 1);
    }
    var chip = del.parentElement;
    if (chip) chip.remove();
    if (!attachedFiles.length) attachWrap.style.display = 'none';
  });

  function formatFileSize(bytes){
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  }

  /* Auto 模式：轮询切换模型 */
  function getNextAutoModel(){
    if (!modelList.length) return 'Auto';
    var m = modelList[autoIndex % modelList.length];
    autoIndex++;
    return m.credential_name || m.provider;
  }

  /* 初始加载 */
  loadModelList();
  renderTaskList('');

  /* ================= 首页统计仪表板 ================= */
  function loadStats(){
    apiGet('/api/stats/overview').then(function(res){
      if (res.code === 200){
        var d = res.data;
        var appsEl = document.getElementById('stat-apps');
        var convsEl = document.getElementById('stat-convs');
        var kbsEl = document.getElementById('stat-kbs');
        var wfsEl = document.getElementById('stat-wfs');
        if (appsEl) appsEl.textContent = d.apps || 0;
        if (convsEl) convsEl.textContent = d.conversations || 0;
        if (kbsEl) kbsEl.textContent = d.datasets || 0;
        if (wfsEl) wfsEl.textContent = d.workflows || 0;
      }
    }).catch(function(){});
  }

  function loadRecentActivity(){
    apiGet('/api/stats/recent', { params: { limit: 5 } }).then(function(res){
      if (res.code === 200){
        renderRecentActivity(res.data);
      }
    }).catch(function(){});
  }

  function renderRecentActivity(data){
    var list = document.getElementById('wb-recent-list');
    if (!list) return;
    var items = [];
    // 最近会话
    (data.recent_conversations || []).forEach(function(c){
      items.push({
        icon: '💬',
        title: c.title || '未命名会话',
        subtitle: (c.app_name || '智能体') + ' · ' + (c.message_count || 0) + ' 条消息',
        time: c.created_at || ''
      });
    });
    // 最近工作流
    (data.recent_workflows || []).forEach(function(w){
      items.push({
        icon: '⚡',
        title: w.app_name || '工作流运行',
        subtitle: (w.status || 'unknown') + ' · ' + (w.elapsed_time ? w.elapsed_time.toFixed(1) + 's' : ''),
        time: w.created_at || ''
      });
    });
    // 最近文档
    (data.recent_documents || []).forEach(function(d){
      items.push({
        icon: '📄',
        title: d.name || '文档',
        subtitle: (d.dataset_name || '知识库') + ' · ' + (d.indexing_status || ''),
        time: d.created_at || ''
      });
    });
    // 按时间排序
    items.sort(function(a, b){ return (b.time || '').localeCompare(a.time || ''); });
    items = items.slice(0, 5);

    if (!items.length){
      list.innerHTML = '<div class="wb-recent-empty">暂无活动记录</div>';
      return;
    }
    list.innerHTML = items.map(function(it){
      return '<div class="wb-recent-item">' +
        '<span class="wb-recent-icon">' + it.icon + '</span>' +
        '<span class="wb-recent-info">' +
          '<span class="wb-recent-title">' + esc(it.title) + '</span>' +
          '<span class="wb-recent-sub">' + esc(it.subtitle) + '</span>' +
        '</span>' +
        '<span class="wb-recent-time">' + esc(it.time ? it.time.slice(5, 16) : '') + '</span>' +
      '</div>';
    }).join('');
  }

  loadStats();
  loadRecentActivity();
});

/* ================= keep-alive 兼容：注册/清理 document 事件监听器 ================= */
onActivated(() => {
  document.addEventListener('click', onModelDocClick);
  document.addEventListener('click', onKbDocClick);
  document.addEventListener('click', onSkillDocClick);
});

onDeactivated(() => {
  document.removeEventListener('click', onModelDocClick);
  document.removeEventListener('click', onKbDocClick);
  document.removeEventListener('click', onSkillDocClick);
});
</script>

<style>
/* ---------- 首页三栏：任务导航面板 + 工作区 ---------- */
.home-wrap{ display:flex; flex:1; min-height:0; background:#fff; }
.task-panel{ width:300px; flex-shrink:0; background:#fff; border-right:1px solid var(--border);
  display:flex; flex-direction:column; overflow:hidden; }
.task-panel.hidden{ display:none; }
.tp-search{ margin:12px 14px 8px; background:#F2F3F5; border-radius:6px; display:flex; align-items:center;
  gap:6px; padding:7px 12px; flex-shrink:0; }
.tp-search input{ flex:1; border:none; background:transparent; font-size:13px; outline:none; }
.tp-search svg{ width:14px; height:14px; color:var(--text-3); flex-shrink:0; }
.tp-scroll{ flex:1; overflow-y:auto; padding-bottom:14px; }
.tp-item{ display:flex; align-items:center; gap:8px; margin:2px 10px; padding:8px 10px; border-radius:6px;
  font-size:14px; color:var(--text-1); cursor:pointer; }
.tp-item svg{ width:15px; height:15px; color:var(--text-2); flex-shrink:0; }
.tp-item:hover{ background:#F7F8FA; }
.tp-item.active{ background:#F2F3F5; font-weight:500; }
.tp-group{ display:flex; align-items:center; justify-content:space-between; padding:16px 20px 4px;
  font-size:12px; color:var(--text-3); user-select:none; }
.tp-gbtn{ border:none; background:none; color:var(--text-3); cursor:pointer; font-size:14px; padding:0 2px; line-height:1; }
.tp-gbtn:hover{ color:var(--primary); }
.tp-task{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin:2px 10px;
  padding:9px 10px; border-radius:6px; font-size:14px; color:var(--text-1); cursor:pointer; }
.tp-task:hover{ background:#F7F8FA; }
.tp-task.active{ background:#F2F3F5; font-weight:500; }
.tp-task .nm{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tp-task .tm{ color:var(--text-4); font-size:12px; flex-shrink:0; }

/* ---------- 工作区 ---------- */
.workbench{ flex:1; display:flex; flex-direction:column; height:100%; background:#fff; min-width:0; }
.wb-head{ height:40px; flex-shrink:0; border-bottom:1px solid var(--border-light); display:flex; align-items:center; gap:8px; padding:0 12px; }
.wb-head .t{ font-size:14px; font-weight:600; color:var(--text-1); }
.ico-btn{ width:28px; height:28px; border:1px solid var(--border-light); background:#fff; border-radius:6px;
  display:flex; align-items:center; justify-content:center; color:var(--text-2); cursor:pointer; }
.ico-btn:hover{ color:var(--primary); border-color:var(--primary); }
.wb-center{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;
  overflow:hidden; padding:2px; min-height:0; }
.main-white{ overflow:hidden !important; }
.wb-center.chatting{ justify-content:flex-start; overflow-y:auto; align-items:stretch; }
.wb-welcome{ display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1px;
  max-height:100%; overflow-y:auto; }
.wb-slogan{ display:flex; align-items:center; gap:6px; font-size:16px; font-weight:700; color:var(--text-1); }
.wb-slogan .robot{ width:28px; height:28px; }
.wb-desc{ margin-top:4px; font-size:11px; color:var(--text-3); max-width:440px; text-align:center; line-height:1.4; }

/* ---------- 统计卡片 ---------- */
.wb-stats{ display:flex; gap:6px; margin-top:6px; flex-wrap:wrap; justify-content:center; }
.stat-card{ background:#F7F8FA; border-radius:6px; padding:5px 10px; text-align:center; min-width:48px; }
.stat-num{ display:block; font-size:15px; font-weight:700; color:var(--primary); }
.stat-label{ display:block; font-size:11px; color:var(--text-3); }

/* ---------- 最近活动 ---------- */
.wb-recent{ margin-top:6px; width:min(460px,100%); text-align:left; }
.wb-recent-head{ font-size:12px; font-weight:600; color:var(--text-2); margin-bottom:2px; padding-left:4px; }
.wb-recent-list{ display:flex; flex-direction:column; gap:2px; }
.wb-recent-item{ display:flex; align-items:center; gap:6px; padding:3px 8px; border-radius:4px; background:#FAFBFC; transition:background .15s; }
.wb-recent-item:hover{ background:#F2F3F5; }
.wb-recent-icon{ font-size:16px; flex-shrink:0; }
.wb-recent-info{ flex:1; min-width:0; display:flex; flex-direction:column; }
.wb-recent-title{ font-size:13px; color:var(--text-1); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.wb-recent-sub{ font-size:11px; color:var(--text-3); }
.wb-recent-time{ font-size:11px; color:var(--text-4); flex-shrink:0; }
.wb-recent-empty{ text-align:center; font-size:13px; color:var(--text-3); padding:10px; }
.wb-recent-icon{ font-size:16px; flex-shrink:0; }
.wb-chat{ width:min(880px,100%); margin:0 auto; padding:26px 24px; display:flex; flex-direction:column; gap:18px; }
.msg{ display:flex; gap:10px; max-width:82%; }
.msg .m-ava{ width:32px; height:32px; border-radius:8px; flex-shrink:0; display:flex; align-items:center; justify-content:center; }
.msg.user{ align-self:flex-end; flex-direction:row-reverse; }
.msg.user .m-ava{ background:linear-gradient(135deg,#7BA7FF,#2E63F0); color:#fff; font-size:13px; border-radius:50%; }
.msg .bubble{ padding:10px 15px; border-radius:12px; font-size:14px; line-height:1.7; word-break:break-word; }
.msg.user .bubble{ background:var(--primary); color:#fff; border-top-right-radius:4px; }
.msg.bot .bubble{ background:#F2F3F5; color:var(--text-1); border-top-left-radius:4px; }
.model-dd{ position:relative; }
.model-menu{ position:absolute; bottom:32px; left:0; background:#fff; border:1px solid var(--border); border-radius:8px;
  box-shadow:0 6px 24px rgba(29,33,41,.14); min-width:190px; display:none; z-index:30; overflow:hidden; }
.model-menu.show{ display:block; }
.model-menu .mi{ padding:9px 14px; font-size:13px; cursor:pointer; color:var(--text-1); }
.model-menu .mi:hover{ background:#F7F8FA; }
.model-menu .mi.on{ color:var(--primary); background:var(--primary-light); }

/* ---------- 知识库选择面板 ---------- */
.kb-dd{ position:relative; }
.kb-menu{ position:absolute; bottom:32px; left:0; background:#fff; border:1px solid var(--border); border-radius:8px;
  box-shadow:0 6px 24px rgba(29,33,41,.14); width:320px; display:none; z-index:30; overflow:hidden; }
.kb-menu.show{ display:block; }
.kb-menu-head{ padding:10px 14px; font-size:12px; color:var(--text-3); border-bottom:1px solid var(--border-light); background:#FAFBFC; }
.kb-menu-list{ max-height:260px; overflow-y:auto; padding:6px; }
.kb-opt{ display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:6px; font-size:13px; color:var(--text-1); cursor:pointer; }
.kb-opt:hover{ background:#F7F8FA; }
.kb-opt.on{ background:var(--primary-light); }
.kb-opt input{ accent-color:var(--primary); width:14px; height:14px; cursor:pointer; flex-shrink:0; }
.kb-nm{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.kb-cnt{ color:var(--text-3); font-size:12px; flex-shrink:0; }
.kb-empty{ padding:22px 10px; text-align:center; font-size:13px; color:var(--text-3); }
.tl.on{ color:var(--primary); border-color:var(--primary); background:var(--primary-light); }
.msg-kb{ font-size:12px; color:var(--text-3); margin-top:5px; }

/* ---------- 技能选择面板 ---------- */
.skill-dd{ position:relative; }
.skill-menu{ position:absolute; bottom:36px; left:0; background:#fff; border:1px solid var(--border); border-radius:8px;
  box-shadow:0 6px 24px rgba(29,33,41,.14); width:300px; display:none; z-index:30; overflow:hidden; }
.skill-menu.show{ display:block; }
.skill-menu-head{ padding:10px 14px; font-size:12px; color:var(--text-3); border-bottom:1px solid var(--border-light); background:#FAFBFC; }
.skill-menu-list{ max-height:260px; overflow-y:auto; padding:6px; }
.skill-opt{ display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:6px; font-size:13px; color:var(--text-1); cursor:pointer; }
.skill-opt:hover{ background:#F7F8FA; }
.skill-opt.on{ background:var(--primary-light); }
.skill-opt input{ accent-color:var(--primary); width:14px; height:14px; cursor:pointer; flex-shrink:0; }
.skill-icon{ font-size:16px; flex-shrink:0; }
.skill-nm{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.skill-kind{ color:var(--text-4); font-size:11px; flex-shrink:0; }
.skill-empty{ padding:22px 10px; text-align:center; font-size:13px; color:var(--text-3); }
.msg-skill{ font-size:12px; color:var(--text-3); margin-top:5px; }
.msg-file{ font-size:12px; color:var(--text-3); margin-top:5px; }
.m-body{ display:flex; flex-direction:column; align-items:flex-start; gap:2px; min-width:0; }

/* ---------- 思维链样式 ---------- */
.thinking-chain {
  margin-bottom: 8px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--purple-bg);
  overflow: hidden;
  max-width: 100%;
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: var(--text-3);
  transition: background .15s;
}
.thinking-header:hover {
  background: rgba(114, 46, 209, 0.05);
}
.thinking-icon {
  width: 14px;
  height: 14px;
  color: var(--purple);
  flex-shrink: 0;
}
.thinking-title {
  flex: 1;
  font-weight: 500;
  color: var(--purple);
}
.thinking-arrow {
  width: 12px;
  height: 12px;
  color: var(--text-3);
  transition: transform .2s;
}
.thinking-chain.collapsed .thinking-arrow {
  transform: rotate(-90deg);
}
.thinking-body {
  padding: 8px 10px 10px 30px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-2);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}
.thinking-chain.collapsed .thinking-body {
  display: none;
}
.thinking-chain.streaming .thinking-icon {
  animation: thinking-pulse 1.5s infinite ease-in-out;
}
@keyframes thinking-pulse {
  0%, 100% { opacity: 0.5; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* ---------- 底部输入区 ---------- */
.wb-bottom{ flex-shrink:0; padding:0 20px 14px; }
.wb-inputbox{ border:1px solid var(--border); border-radius:12px; background:#fff; padding:14px 14px 10px;
  box-shadow:0 2px 10px rgba(29,33,41,.05); }
.wb-inputbox textarea{ width:100%; border:none; outline:none; resize:none; font-size:14px; color:var(--text-1);
  min-height:66px; max-height:200px; line-height:1.6; background:transparent; font-family:inherit; }
.wb-toolbar{ display:flex; align-items:center; gap:6px; margin-top:10px; flex-wrap:wrap; }
.tl-gap{ margin-left:10px; }
.tl{ border:1px solid var(--border-light); background:#fff; border-radius:6px; height:36px; padding:0 12px;
  font-size:13px; color:var(--text-2); cursor:pointer; display:flex; align-items:center; gap:4px; white-space:nowrap; }
.tl:hover{ color:var(--primary); border-color:var(--primary); }
.wb-send{ width:38px; height:38px; border-radius:8px; border:none; background:#E5E6EB; color:#fff; font-size:16px;
  cursor:pointer; margin-left:auto; transition:background .15s; flex-shrink:0; }
.wb-send.ready{ background:linear-gradient(135deg,#2E63F0,#4A86F8); }
.wb-foot{ text-align:center; font-size:12px; color:var(--text-4); margin-top:10px; }
.wb-foot a{ color:var(--text-3); text-decoration:none; }
.wb-foot a:hover{ color:var(--primary); }

/* ---------- 附件芯片 ---------- */
.wb-attach{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
.attach-chip{ display:flex; align-items:center; gap:6px; padding:4px 10px 4px 10px; border-radius:16px;
  background:#F2F3F5; font-size:12px; color:var(--text-1); max-width:220px; }
.attach-chip .ac-name{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }
.attach-chip .ac-size{ color:var(--text-4); font-size:11px; flex-shrink:0; }
.attach-chip .ac-progress{ color:var(--primary); font-size:11px; flex-shrink:0; }
.attach-chip .ac-err{ color:#E64A19; font-size:11px; flex-shrink:0; }
.attach-chip.uploading{ background:var(--primary-light); }
.attach-chip.error{ background:#FFF0ED; }
.attach-chip .ac-del{ width:16px; height:16px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:10px; color:var(--text-3); cursor:pointer; flex-shrink:0; transition:all .15s; }
.attach-chip .ac-del:hover{ background:#E5E6EB; color:var(--text-1); }
</style>

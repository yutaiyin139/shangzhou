<template>
  <AppShell id="page-root" active-key="agent-chat" main-class="main-white">
    <div class="chat-wrap">
    
            <!-- 左：会话面板 -->
            <aside class="conv-panel" id="conv-panel">
              <div class="cp-head">
                <div class="cp-icon">🤖</div>
                <div class="cp-name" id="agent-name">聊天机器人</div>
                <button class="cp-fold" id="cp-fold" title="收起面板">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9.5 4v16"/></svg>
                </button>
              </div>
              <button class="cp-new" id="cp-new">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                开启新对话
              </button>
              <div class="cp-body" id="cp-body"></div>
              <div class="cp-foot">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg>
              </div>
            </aside>
    
            <!-- 右：聊天区 -->
            <div class="chat-main" id="chat-main">
              <button class="ico-btn cm-expand" id="cm-expand" title="展开面板">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9.5 4v16"/></svg>
              </button>
              <div class="cm-scroll" id="cm-scroll">
                <div class="cm-list" id="cm-list"></div>
              </div>
              <div class="cm-inputbar">
                <div class="cm-input">
                  <input id="cm-input" placeholder="和 聊天机器人 聊天" autocomplete="off">
                  <button class="cm-stop" id="cm-stop" title="停止生成" style="display:none">
                    <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                  </button>
                  <button class="cm-send" id="cm-send" title="发送">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.4 20.4l17.4-7.5c.8-.35.8-1.45 0-1.8L3.4 3.6c-.66-.29-1.39.2-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"/></svg>
                  </button>
                </div>
              </div>
            </div>
    
          </div>
  </AppShell>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet, apiPost, apiDelete } from '../api/client'

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

  /* 智能体名称与配置：支持 ?id=（加载真实配置）与 ?name=（名称兜底） */
  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var agentId = params.get('id');
  var agentName = params.get('name') || '聊天机器人';
  var agentPrompt = '';    // 智能体提示词（system prompt）
  var agentKbIds = [];     // 智能体配置的知识库 id 列表
  var currentConvId = null; // 当前会话 id
  document.getElementById('agent-name').textContent = agentName;
  document.getElementById('cm-input').placeholder = '和 ' + agentName + ' 聊天';
  document.title = agentName + ' - 熵舟·智能体工作台';

  if (agentId){
    apiGet('/api/agents/' + agentId).then(function(data){
      if (data.code === 200){
        var ag = data.data;
        document.getElementById('agent-name').textContent = ag.name;
        document.getElementById('cm-input').placeholder = '和 ' + ag.name + ' 聊天';
        document.title = ag.name + ' - 熵舟·智能体工作台';
        if (ag.config){
          agentPrompt = ag.config.prompt || '';
          var kbs = ag.config.kbs || [];
          if (kbs.length){
            /* 知识库名称 → 匹配数据集 id */
            apiGet('/api/knowledge/datasets').then(function(d2){
              if (d2.code === 200){
                agentKbIds = (d2.data || []).filter(function(k){
                  return kbs.some(function(kb){ return kb.name === k.name; });
                }).map(function(k){ return k.id; });
              }
            });
          }
        }
        // 加载会话列表
        loadConversations();
      }
    });
  } else {
    // 无智能体 id 时也加载会话列表
    loadConversations();
  }

  var list   = document.getElementById('cm-list');
  var scroll = document.getElementById('cm-scroll');
  var input  = document.getElementById('cm-input');
  var cpBody = document.getElementById('cp-body');

  var ROBOT_SVG = '<svg width="18" height="18" viewBox="0 0 48 48"><rect x="4" y="7" width="36" height="36" rx="11" fill="#1D2129"/><circle cx="16" cy="23" r="3" fill="#fff"/><circle cx="28" cy="23" r="3" fill="#fff"/><path d="M17 31c1.8 2 3.5 2.8 5 2.8s3.2-.8 5-2.8" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round"/><circle cx="39" cy="9" r="6" fill="#2E63F0"/></svg>';

  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* ================= 思维链（Thinking Chain）渲染 ================= */

  /**
   * 创建思维链 DOM 元素
   * @param {string} thinkingText - 思维链文本
   * @returns {HTMLElement}
   */
  function createThinkingEl(thinkingText){
    var div = document.createElement('div');
    div.className = 'thinking-chain';

    // 头部（可折叠）
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

    // 内容区
    var body = document.createElement('div');
    body.className = 'thinking-body';
    body.textContent = thinkingText;

    div.appendChild(header);
    div.appendChild(body);

    // 折叠/展开交互
    header.addEventListener('click', function(){
      div.classList.toggle('collapsed');
    });

    return div;
  }

  /**
   * 更新思维链内容（流式）
   * @param {HTMLElement} thinkingEl - 思维链元素
   * @param {string} delta - 新增内容
   */
  function updateThinkingEl(thinkingEl, delta){
    var body = thinkingEl.querySelector('.thinking-body');
    if (body){
      body.textContent += delta;
    }
  }

  function fmtTime(iso){
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var now = new Date();
    var diff = now - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前';
    if (diff < 172800000) return '昨天';
    return (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }

  function addMsg(role, text){
    var div = document.createElement('div');
    div.className = 'msg ' + role;
    var ava = role === 'user'
      ? '<div class="m-ava">我</div>'
      : '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div>';
    div.innerHTML = ava + '<div class="bubble">' + esc(text).replace(/\n/g, '<br>') + '</div>';
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
  }

  /* 加载会话列表 */
  function loadConversations(){
    var queryParams = { params: { page_size: 50 } };
    if (agentId) queryParams.params.agent_id = agentId;
    apiGet('/api/conversations', queryParams).then(function(data){
      if (data.code === 200){
        renderConversationList(data.data.items);
      }
    }).catch(function(){});
  }

  /* 渲染会话列表 */
  function renderConversationList(items){
    cpBody.innerHTML = '';
    if (!items || !items.length){
      cpBody.innerHTML = '<div class="cp-empty">暂无对话历史</div>';
      return;
    }
    items.forEach(function(item){
      var div = document.createElement('div');
      div.className = 'cp-item' + (item.id === currentConvId ? ' active' : '');
      div.dataset.id = item.id;
      div.innerHTML =
        '<div class="cp-item-title">' + esc(item.title) + '</div>' +
        '<div class="cp-item-meta">' +
          '<span>' + fmtTime(item.last_message_at || item.created_at) + '</span>' +
          '<span class="cp-item-count">' + (item.message_count || 0) + ' 条</span>' +
        '</div>';
      div.addEventListener('click', function(){
        loadConversation(item.id);
      });
      cpBody.appendChild(div);
    });
  }

  /* 加载指定会话的消息 */
  function loadConversation(convId){
    currentConvId = convId;
    // 更新选中状态
    var items = cpBody.querySelectorAll('.cp-item');
    items.forEach(function(el){
      el.classList.toggle('active', el.dataset.id === convId);
    });
    apiGet('/api/conversations/' + convId).then(function(data){
      if (data.code === 200){
        list.innerHTML = '';
        var msgs = data.data.messages || [];
        // 为每条 assistant 消息获取思考链和引用
        var detailPromises = msgs.map(function(m){
          if (m.role === 'assistant' && m.id){
            var thoughtsP = apiGet('/api/messages/' + m.id + '/thoughts')
              .then(function(d){ return {msgId: m.id, key: 'thoughts', data: (d.code === 200 && d.data) ? d.data.items : []}; })
              .catch(function(){ return {msgId: m.id, key: 'thoughts', data: []}; });
            var citationsP = apiGet('/api/messages/' + m.id + '/retriever-resources')
              .then(function(d){ return {msgId: m.id, key: 'citations', data: (d.code === 200 && d.data) ? d.data.items : []}; })
              .catch(function(){ return {msgId: m.id, key: 'citations', data: []}; });
            return Promise.all([thoughtsP, citationsP]);
          }
          return Promise.resolve([]);
        });
        Promise.all(detailPromises).then(function(results){
          var detailMap = {};
          results.forEach(function(pair){
            pair.forEach(function(item){
              if (!detailMap[item.msgId]) detailMap[item.msgId] = {};
              detailMap[item.msgId][item.key] = item.data;
            });
          });
          msgs.forEach(function(m){
            // 解析 metadata 中的思维链
            var thinking = '';
            if (m.metadata){
              try{
                var meta = JSON.parse(m.metadata);
                thinking = meta.thinking_chain || '';
              }catch(e){}
            }
            var details = detailMap[m.id] || {};
            var tc = details.thoughts || [];
            var cit = details.citations || [];
            addMsgWithThinking(
              m.role === 'assistant' ? 'bot' : m.role,
              m.content, thinking,
              tc.length ? tc : null,
              cit.length ? cit : null
            );
          });
        });
        // 更新智能体名称显示
        if (data.data.title){
          document.getElementById('agent-name').textContent = agentName + ' - ' + data.data.title;
        }
      }
    }).catch(function(){
      toast('加载会话失败');
    });
  }

  /**
   * 创建 Agent 思考链 DOM 元素（结构化 ReAct 步骤）
   * @param {Array} thoughtChain - 思考链条目 [{position, thought, tool_name, tool_input, tool_output, observation}]
   * @returns {HTMLElement}
   */
  function createThoughtChainEl(thoughtChain){
    var div = document.createElement('div');
    div.className = 'thinking-chain agent-thought-chain';

    var toolCallCount = 0;
    if (thoughtChain && thoughtChain.length){
      toolCallCount = thoughtChain.filter(function(s){ return s.tool_name; }).length;
    }

    // 头部（可折叠）
    var header = document.createElement('div');
    header.className = 'thinking-header';
    header.innerHTML =
      '<svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
        '<circle cx="12" cy="12" r="3"/>' +
        '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>' +
      '</svg>' +
      '<span class="thinking-title">Agent 思考过程' + (toolCallCount ? '（' + toolCallCount + ' 次工具调用）' : '') + '</span>' +
      '<svg class="thinking-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M6 9l6 6 6-6"/>' +
      '</svg>';

    // 内容区：逐步展示
    var body = document.createElement('div');
    body.className = 'thinking-body';

    if (thoughtChain && thoughtChain.length){
      thoughtChain.forEach(function(step, idx){
        var stepDiv = document.createElement('div');
        stepDiv.className = 'thought-step';

        if (step.tool_name){
          // 工具调用步骤
          stepDiv.innerHTML =
            '<div class="thought-step-num">步骤 ' + (idx + 1) + '</div>' +
            '<div class="thought-action">🔧 调用工具：<strong>' + esc(step.tool_name) + '</strong></div>' +
            (step.tool_input ? '<div class="thought-detail">输入：<code>' + esc(step.tool_input) + '</code></div>' : '') +
            (step.tool_output ? '<div class="thought-detail">输出：<code>' + esc(step.tool_output) + '</code></div>' : '');
        } else {
          // 推理步骤
          var thoughtText = (step.thought || '').substring(0, 500);
          stepDiv.innerHTML =
            '<div class="thought-step-num">步骤 ' + (idx + 1) + '</div>' +
            '<div class="thought-reasoning">💭 ' + esc(thoughtText) + '</div>';
        }
        body.appendChild(stepDiv);
      });
    } else {
      body.textContent = '暂无思考记录';
    }

    div.appendChild(header);
    div.appendChild(body);

    // 折叠/展开交互
    header.addEventListener('click', function(){
      div.classList.toggle('collapsed');
    });

    return div;
  }

  /**
   * 创建引用气泡 DOM 元素（知识库来源）
   * @param {Array} resources - 引用列表 [{document_name, content, score, segment_id}]
   * @returns {HTMLElement}
   */
  function createCitationsEl(resources){
    var div = document.createElement('div');
    div.className = 'citation-bubbles';

    resources.forEach(function(r, idx){
      var bubble = document.createElement('div');
      bubble.className = 'citation-bubble';
      bubble.title = (r.content || '').substring(0, 200);
      var scorePct = r.score ? Math.round(r.score * 100) : 0;
      bubble.innerHTML =
        '<span class="cit-num">' + (idx + 1) + '</span>' +
        '<span class="cit-doc">' + esc(r.document_name || '未知文档') + '</span>' +
        (scorePct ? '<span class="cit-score">' + scorePct + '%</span>' : '');
      div.appendChild(bubble);
    });

    return div;
  }

  /**
   * 添加消息（含思维链 + Agent 思考链 + 引用）
   */
  function addMsgWithThinking(role, text, thinking, thoughtChain, citations){
    var div = document.createElement('div');
    div.className = 'msg ' + role;
    var ava = role === 'user'
      ? '<div class="m-ava">我</div>'
      : '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div>';
    div.innerHTML = ava;
    var mBody = document.createElement('div');
    mBody.className = 'm-body';

    // 引用气泡（知识库来源）
    if (citations && citations.length && role === 'bot'){
      mBody.appendChild(createCitationsEl(citations));
    }

    // Agent 思考链（ReAct 步骤，优先显示）
    if (thoughtChain && thoughtChain.length && role === 'bot'){
      var tcEl = createThoughtChainEl(thoughtChain);
      tcEl.classList.add('collapsed'); // 历史消息默认折叠
      mBody.appendChild(tcEl);
    }

    // 思维链（DeepSeek R1 等推理模型的纯文本思维链）
    if (thinking && role === 'bot'){
      var thinkingEl = createThinkingEl(thinking);
      thinkingEl.classList.add('collapsed'); // 历史消息默认折叠
      mBody.appendChild(thinkingEl);
    }

    var bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = esc(text).replace(/\n/g, '<br>');
    mBody.appendChild(bubble);
    div.appendChild(mBody);
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
  }

  /* 删除会话 */
  function deleteConversation(convId, e){
    e.stopPropagation();
    if (!confirm('确定要删除这个对话吗？')) return;
    apiDelete('/api/conversations/' + convId).then(function(data){
      if (data.code === 200){
        if (currentConvId === convId){
          currentConvId = null;
          list.innerHTML = '';
        }
        loadConversations();
        toast('已删除');
      } else {
        toast(data.msg || '删除失败');
      }
    }).catch(function(){
      toast('删除失败');
    });
  }

  var sending = false;
  var currentTaskId = null; // 当前流式任务 ID
  var reader = null;        // 当前流的 reader

  // 显示/隐藏停止按钮
  function showStopBtn(show){
    var stopBtn = document.getElementById('cm-stop');
    var sendBtn = document.getElementById('cm-send');
    if (stopBtn) stopBtn.style.display = show ? 'flex' : 'none';
    if (sendBtn) sendBtn.style.display = show ? 'none' : 'flex';
  }

  // 停止生成
  function stopGeneration(){
    if (!currentTaskId) return;
    var taskId = currentTaskId;
    // 立即标记停止（前端先响应）
    currentTaskId = null;
    // 关闭流
    if (reader){
      reader.cancel().catch(function(){});
      reader = null;
    }
    // 通知后端停止
    apiPost('/api/chat/stream/' + taskId + '/stop')
      .then(function(data){
        if (data.code !== 200 && data.code !== 404){
          console.warn('[stop]', data.msg);
        }
      })
      .catch(function(){});
  }

  function send(){
    var text = input.value.trim();
    if (!text || sending) return;
    sending = true;
    currentTaskId = null;
    addMsg('user', text);
    input.value = '';
    // 创建流式消息气泡
    var botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'msg bot';
    var ava = '<div class="m-ava" style="background:#fff;border:1px solid var(--border-light)">' + ROBOT_SVG + '</div>';
    var bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    botMsgDiv.innerHTML = ava;
    botMsgDiv.appendChild(bubble);
    list.appendChild(botMsgDiv);
    scroll.scrollTop = scroll.scrollHeight;
    // 显示停止按钮
    showStopBtn(true);

    var body = {
      message: text,
      system: agentPrompt,
      knowledge_ids: agentKbIds,
      agent_id: agentId,
      conversation_id: currentConvId
    };

    // 思维链状态
    var thinkingEl = null;
    var fullThinking = '';
    var currentMessageId = null; // 当前消息 ID（用于反馈）
    // Agent 思考链状态（ReAct 步骤）
    var agentThoughtSteps = [];
    var agentThoughtEl = null;

    // 使用 SSE 流式接收
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function(response){
      if (!response.ok){
        bubble.innerHTML = '';
        bubble.appendChild(document.createTextNode('⚠ 请求失败 (' + response.status + ')'));
        sending = false;
        showStopBtn(false);
        return;
      }
      reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var fullText = '';

      function readStream(){
        reader.read().then(function(result){
          if (result.done){
            // 流结束时，如果有思维链但没有正文，显示提示
            if (fullThinking && !fullText && thinkingEl){
              var tb = thinkingEl.querySelector('.thinking-body');
              if (tb) tb.textContent += '\n\n（思考完成，但未生成回复）';
            }
            sending = false;
            showStopBtn(false);
            reader = null;
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
                // 首条事件：获取 task_id
                if (data.task_id){
                  currentTaskId = data.task_id;
                }
                // 处理思维链事件
                if (data.thinking){
                  fullThinking += data.thinking;
                  if (!thinkingEl){
                    // 首次收到思维链，创建 DOM
                    thinkingEl = createThinkingEl(data.thinking);
                    // 插入到气泡之前
                    botMsgDiv.insertBefore(thinkingEl, bubble);
                  } else {
                    updateThinkingEl(thinkingEl, data.thinking);
                  }
                  scroll.scrollTop = scroll.scrollHeight;
                }
                // Agent 思考链事件（ReAct 步骤）
                if (data.agent_thought_stream){
                  var thought = data.agent_thought_stream;
                  agentThoughtSteps.push(thought);
                  if (!agentThoughtEl){
                    // 首次收到，创建 Agent 思考链 DOM
                    agentThoughtEl = createThoughtChainEl(agentThoughtSteps);
                    botMsgDiv.insertBefore(agentThoughtEl, bubble);
                  } else {
                    // 更新思考链
                    var body = agentThoughtEl.querySelector('.thinking-body');
                    if (body){
                      var stepDiv = document.createElement('div');
                      stepDiv.className = 'thought-step';
                      if (thought.tool_name){
                        stepDiv.innerHTML =
                          '<div class="thought-step-num">步骤 ' + agentThoughtSteps.length + '</div>' +
                          '<div class="thought-action">🔧 调用工具：<strong>' + esc(thought.tool_name) + '</strong></div>' +
                          (thought.tool_input ? '<div class="thought-detail">输入：<code>' + esc(JSON.stringify(thought.tool_input)) + '</code></div>' : '') +
                          (thought.tool_output ? '<div class="thought-detail">输出：<code>' + esc(thought.tool_output) + '</code></div>' : '');
                      } else {
                        stepDiv.innerHTML =
                          '<div class="thought-step-num">步骤 ' + agentThoughtSteps.length + '</div>' +
                          '<div class="thought-reasoning">💭 ' + esc((thought.content || '').substring(0, 500)) + '</div>';
                      }
                      body.appendChild(stepDiv);
                    }
                    // 更新头部计数
                    var title = agentThoughtEl.querySelector('.thinking-title');
                    if (title){
                      var tc = agentThoughtSteps.filter(function(s){ return s.tool_name; }).length;
                      title.textContent = 'Agent 思考过程' + (tc ? '（' + tc + ' 次工具调用）' : '');
                    }
                  }
                  scroll.scrollTop = scroll.scrollHeight;
                }
                if (data.content){
                  // 首次收到正文时，如果有思维链则默认折叠
                  if (thinkingEl && fullText === ''){
                    thinkingEl.classList.add('collapsed');
                  }
                  fullText += data.content;
                  bubble.innerHTML = '';
                  bubble.appendChild(document.createTextNode(fullText));
                  scroll.scrollTop = scroll.scrollHeight;
                }
                if (data.error){
                  bubble.innerHTML = '';
                  bubble.appendChild(document.createTextNode('⚠ ' + data.error));
                  sending = false;
                  showStopBtn(false);
                  reader = null;
                  return;
                }
                if (data.stopped){
                  // 用户主动停止
                  if (data.content){
                    fullText = data.content;
                  }
                  bubble.innerHTML = '';
                  bubble.appendChild(document.createTextNode(fullText + ' [已停止]'));
                  scroll.scrollTop = scroll.scrollHeight;
                  // 更新会话 id
                  if (data.conversation_id && !currentConvId){
                    currentConvId = data.conversation_id;
                    loadConversations();
                  }
                  sending = false;
                  showStopBtn(false);
                  reader = null;
                  return;
                }
                if (data.done){
                  // 更新会话 id
                  if (data.conversation_id){
                    if (!currentConvId){
                      currentConvId = data.conversation_id;
                    }
                    loadConversations();
                  }
                  // 保存消息 ID 并添加反馈按钮
                  if (data.message_id){
                    currentMessageId = data.message_id;
                    addFeedbackButtons(botMsgDiv, data.message_id, currentConvId);
                  }
                  // 长期记忆使用指示器
                  if (data.memory_used && agentId){
                    var memHint = document.createElement('div');
                    memHint.className = 'msg-memory-hint';
                    memHint.innerHTML = '🧠 基于长期记忆回答';
                    botMsgDiv.appendChild(memHint);
                  }
                  sending = false;
                  showStopBtn(false);
                  reader = null;
                  return;
                }
              }catch(e){ /* 忽略解析错误 */ }
            }
          }
          readStream();
        }).catch(function(){
          sending = false;
          showStopBtn(false);
          reader = null;
        });
      }
      readStream();
    }).catch(function(){
      bubble.innerHTML = '';
      bubble.appendChild(document.createTextNode('⚠ 网络异常，请稍后重试'));
      sending = false;
      showStopBtn(false);
    });
  }

  /* ================= 消息反馈（点赞/踩） ================= */

  /**
   * 为 bot 消息添加反馈按钮
   */
  function addFeedbackButtons(msgDiv, messageId, convId){
    // 避免重复添加
    if (msgDiv.querySelector('.msg-feedback')) return;

    var feedbackBar = document.createElement('div');
    feedbackBar.className = 'msg-feedback';

    var likeBtn = document.createElement('span');
    likeBtn.className = 'fb-btn';
    likeBtn.title = '有帮助';
    likeBtn.textContent = '👍';
    likeBtn.addEventListener('click', function(){
      submitFeedback(messageId, 1, likeBtn, dislikeBtn, statusEl);
    });

    var dislikeBtn = document.createElement('span');
    dislikeBtn.className = 'fb-btn';
    dislikeBtn.title = '没帮助';
    dislikeBtn.textContent = '👎';
    dislikeBtn.addEventListener('click', function(){
      submitFeedback(messageId, -1, likeBtn, dislikeBtn, statusEl);
    });

    var statusEl = document.createElement('span');
    statusEl.className = 'fb-status';
    statusEl.id = 'fb-status-' + messageId;

    feedbackBar.appendChild(likeBtn);
    feedbackBar.appendChild(dislikeBtn);
    feedbackBar.appendChild(statusEl);
    msgDiv.appendChild(feedbackBar);
  }

  /**
   * 提交反馈
   */
  function submitFeedback(messageId, rating, likeBtn, dislikeBtn, statusEl){
    apiPost('/api/feedback', { message_id: messageId, rating: rating }).then(function(res){
      if (res.code === 200){
        if (statusEl) statusEl.textContent = rating === 1 ? '✓ 已点赞' : '✓ 已反馈';
        // 更新按钮状态
        likeBtn.classList.remove('active');
        dislikeBtn.classList.remove('active');
        if (rating === 1) likeBtn.classList.add('active');
        else dislikeBtn.classList.add('active');
      } else {
        if (statusEl) statusEl.textContent = res.msg || '反馈失败';
      }
    }).catch(function(){
      if (statusEl) statusEl.textContent = '网络错误';
    });
  }

  document.getElementById('cm-send').addEventListener('click', send);
  document.getElementById('cm-stop').addEventListener('click', stopGeneration);
  input.addEventListener('keydown', function(e){
    if (e.key === 'Enter'){ e.preventDefault(); send(); }
  });

  /* 开启新对话：清空当前会话 */
  document.getElementById('cp-new').addEventListener('click', function(){
    currentConvId = null;
    list.innerHTML = '';
    input.value = '';
    input.focus();
    // 取消选中状态
    var items = cpBody.querySelectorAll('.cp-item');
    items.forEach(function(el){ el.classList.remove('active'); });
    toast('已开启新对话');
  });

  /* 收起 / 展开会话面板 */
  var panel = document.getElementById('conv-panel');
  var main  = document.getElementById('chat-main');
  document.getElementById('cp-fold').addEventListener('click', function(){
    panel.classList.add('hidden');
    main.classList.add('expanded');
  });
  document.getElementById('cm-expand').addEventListener('click', function(){
    panel.classList.remove('hidden');
    main.classList.remove('expanded');
  });
})
</script>
<style>
.chat-wrap{ display:flex; gap:14px; height:100%; padding:14px; background:#fff; box-sizing:border-box; }

  /* 左侧会话面板 */
  .conv-panel{ width:290px; flex-shrink:0; background:#F7F8FA; border-radius:12px;
    display:flex; flex-direction:column; overflow:hidden; }
  .conv-panel.hidden{ display:none; }
  .cp-head{ display:flex; align-items:center; gap:10px; padding:16px 16px 12px; }
  .cp-icon{ width:36px; height:36px; border-radius:10px; background:#FFE3C2; display:flex;
    align-items:center; justify-content:center; font-size:20px; flex-shrink:0; }
  .cp-name{ font-size:15px; font-weight:600; color:var(--text-1); flex:1;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .cp-fold{ border:none; background:none; cursor:pointer; color:var(--text-3); padding:4px; }
  .cp-fold svg{ width:16px; height:16px; display:block; }
  .cp-fold:hover{ color:var(--text-1); }
  .cp-new{ margin:2px 14px; padding:9px 0; background:#fff; border:1px solid var(--border);
    border-radius:8px; color:var(--primary); font-size:14px; cursor:pointer;
    display:flex; align-items:center; justify-content:center; gap:6px; }
  .cp-new:hover{ border-color:var(--primary); }
  .cp-new svg{ width:14px; height:14px; }
  .cp-body{ flex:1; overflow-y:auto; padding:10px 14px; }
  .cp-empty{ text-align:center; color:var(--text-3); font-size:13px; padding:30px 0; }
  .cp-item{ padding:10px 12px; border-radius:8px; cursor:pointer; margin-bottom:4px;
    transition:background .15s; position:relative; }
  .cp-item:hover{ background:#ECEEF1; }
  .cp-item.active{ background:#E5EEFF; }
  .cp-item-title{ font-size:13px; color:var(--text-1); overflow:hidden; text-overflow:ellipsis;
    white-space:nowrap; margin-bottom:4px; }
  .cp-item-meta{ display:flex; justify-content:space-between; font-size:11px; color:var(--text-3); }
  .cp-item-count{ background:#ECEEF1; padding:1px 6px; border-radius:4px; }
  .cp-item.active .cp-item-count{ background:#D4E3FF; color:var(--primary); }
  .cp-foot{ display:flex; align-items:center; gap:10px; padding:12px 16px; color:var(--text-3); }
  .cp-foot svg{ width:16px; height:16px; }
  .cp-powered{ flex:1; text-align:center; font-size:11px; letter-spacing:.4px; color:#8A919E; }
  .cp-powered b{ color:#1D2129; font-size:13px; letter-spacing:0; }

  /* 右侧聊天区 */
  .chat-main{ flex:1; display:flex; flex-direction:column; min-width:0; position:relative; }
  .cm-expand{ position:absolute; top:6px; left:6px; z-index:5; display:none; }
  .chat-main.expanded .cm-expand{ display:inline-flex; }
  .cm-scroll{ flex:1; overflow-y:auto; padding:20px 24px; }
  .cm-list{ width:min(860px,100%); margin:0 auto; display:flex; flex-direction:column; gap:16px; }
  .msg{ display:flex; gap:10px; max-width:82%; }
  .msg .m-ava{ width:32px; height:32px; border-radius:8px; flex-shrink:0; display:flex;
    align-items:center; justify-content:center; }
  .msg.user{ align-self:flex-end; flex-direction:row-reverse; }
  .msg.user .m-ava{ background:linear-gradient(135deg,#7BA7FF,#2E63F0); color:#fff; font-size:13px; border-radius:50%; }
  .msg .bubble{ padding:10px 15px; border-radius:12px; font-size:14px; line-height:1.7; word-break:break-word; }
  .msg.user .bubble{ background:var(--primary); color:#fff; border-top-right-radius:4px; }
  .msg.bot .bubble{ background:#F2F3F5; color:var(--text-1); border-top-left-radius:4px; }

  /* 底部输入 */
  .cm-inputbar{ padding:14px 24px 22px; }
  .cm-input{ width:min(680px,100%); margin:0 auto; display:flex; align-items:center; gap:10px;
    background:#fff; border:1px solid var(--border); border-radius:12px; padding:10px 12px 10px 18px;
    box-shadow:0 2px 10px rgba(29,33,41,.05); }
  .cm-input:focus-within{ border-color:var(--primary); }
  .cm-input input{ flex:1; border:none; font-size:14px; }
  .cm-send{ width:38px; height:38px; border:none; border-radius:9px; background:var(--primary);
    color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .cm-send svg{ width:17px; height:17px; }
  .cm-send:hover{ background:#1F4FD8; }
  .cm-stop{ width:38px; height:38px; border:none; border-radius:9px; background:#F53F3F;
    color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .cm-stop svg{ width:14px; height:14px; }
  .cm-stop:hover{ background:#E63535; }

  /* 流式输入动画 */
  .typing-dot{ display:inline-block; width:6px; height:6px; margin:0 1px; border-radius:50%;
    background:var(--text-3); animation: typing-bounce 1.4s infinite ease-in-out; }
  .typing-dot:nth-child(1){ animation-delay: 0s; }
  .typing-dot:nth-child(2){ animation-delay: 0.2s; }
  .typing-dot:nth-child(3){ animation-delay: 0.4s; }
  @keyframes typing-bounce{
    0%, 80%, 100%{ transform: scale(0.6); opacity: 0.4; }
    40%{ transform: scale(1); opacity: 1; }
  }

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

  /* ---------- Agent 思考链（ReAct 步骤）样式 ---------- */
  .agent-thought-chain {
    border-color: rgba(46, 99, 240, 0.2);
    background: rgba(46, 99, 240, 0.04);
  }
  .agent-thought-chain .thinking-header:hover {
    background: rgba(46, 99, 240, 0.06);
  }
  .agent-thought-chain .thinking-icon {
    color: var(--primary, #2E63F0);
  }
  .agent-thought-chain .thinking-title {
    color: var(--primary, #2E63F0);
  }
  .agent-thought-chain .thinking-body {
    padding: 8px 10px 10px 12px;
  }
  .thought-step {
    padding: 6px 0;
    border-bottom: 1px dashed var(--border-light);
  }
  .thought-step:last-child {
    border-bottom: none;
  }
  .thought-step-num {
    font-size: 11px;
    color: var(--text-3);
    margin-bottom: 3px;
    font-weight: 500;
  }
  .thought-action {
    font-size: 12.5px;
    color: var(--text-1);
    margin-bottom: 3px;
  }
  .thought-reasoning {
    font-size: 12.5px;
    color: var(--text-2);
    line-height: 1.5;
  }
  .thought-detail {
    font-size: 12px;
    color: var(--text-3);
    margin-top: 2px;
    padding-left: 8px;
  }
  .thought-detail code {
    background: var(--bg-1);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 11.5px;
    word-break: break-all;
  }

  /* ---------- 引用气泡样式 ---------- */
  .citation-bubbles {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }
  .citation-bubble {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    background: var(--primary-light);
    border: 1px solid rgba(46, 99, 240, 0.15);
    border-radius: 12px;
    font-size: 11.5px;
    color: var(--primary);
    cursor: help;
    max-width: 220px;
  }
  .cit-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    background: var(--primary);
    color: #fff;
    border-radius: 50%;
    font-size: 10px;
    font-weight: 600;
    flex-shrink: 0;
  }
  .cit-doc {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cit-score {
    font-size: 10px;
    opacity: 0.7;
    flex-shrink: 0;
  }
  .m-body {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    min-width: 0;
  }

  /* ---------- 消息反馈按钮 ---------- */
  .msg-feedback {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    padding-left: 4px;
  }
  .fb-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    font-size: 14px;
    transition: all .15s;
    opacity: 0.5;
  }
  .fb-btn:hover {
    opacity: 1;
    background: var(--primary-light);
    border-color: var(--border-light);
  }
  .fb-btn.active {
    opacity: 1;
    background: var(--primary-light);
    border-color: var(--primary);
  }
  .fb-status {
    font-size: 11px;
    color: var(--text-3);
    margin-left: 4px;
  }
  .msg:hover .fb-btn {
    opacity: 0.8;
  }
  .msg-memory-hint {
    font-size: 11px;
    color: var(--purple);
    margin-top: 4px;
    padding: 2px 8px;
    background: var(--purple-bg, rgba(114,46,209,.06));
    border-radius: 4px;
    display: inline-block;
  }
</style>

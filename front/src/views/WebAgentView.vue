<template>
  <div id="page-root" class="wa-root">
    <!-- 顶部品牌栏 -->
    <header class="wa-head" id="waHead">
      <span class="wa-ico" id="waIcon">🤖</span>
      <span class="wa-name" id="waName">加载中…</span>
      <span class="wa-powered">熵舟 · Web app</span>
    </header>

    <!-- 对话区 -->
    <div class="wa-scroll" id="waScroll">
      <div class="wa-list" id="waList"></div>
    </div>

    <!-- 输入区 -->
    <div class="wa-inputbar">
      <div class="wa-input" id="waInputBox">
        <input id="waInput" placeholder="输入消息…" autocomplete="off" disabled>
        <button class="wa-send" id="waSend" title="发送" disabled>
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.4 20.4l17.4-7.5c.8-.35.8-1.45 0-1.8L3.4 3.6c-.66-.29-1.39.2-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"/></svg>
        </button>
      </div>
    </div>

    <!-- 访问点失效遮罩 -->
    <div class="wa-dead" id="waDead" style="display:none;">
      <div class="wa-dead-ico">🔒</div>
      <div class="wa-dead-t">访问点不存在或已停用</div>
      <div class="wa-dead-s">请联系 Agent 管理员确认 Web app 访问链接是否有效</div>
    </div>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import { apiGet, apiPost } from '../api/client'

onMounted(function(){
  var params = new URLSearchParams(location.hash.split('?')[1] || '');
  var token = params.get('token') || '';
  var brandColor = '#2E63F0';

  var list   = document.getElementById('waList');
  var scroll = document.getElementById('waScroll');
  var input  = document.getElementById('waInput');
  var sendBtn = document.getElementById('waSend');

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function applyBrand(color){
    brandColor = color || '#2E63F0';
    document.getElementById('waHead').style.background = brandColor;
    var st = document.createElement('style');
    st.textContent = '.wa-send{ background:' + brandColor + ' !important; }' +
      '.wa-msg.user .wa-bubble{ background:' + brandColor + ' !important; }' +
      '#waInput:focus{ border-color:' + brandColor + ' !important; }';
    document.head.appendChild(st);
  }

  function dead(){
    document.getElementById('waDead').style.display = 'flex';
  }

  /* 加载 Web app 基础信息（无需登录） */
  if (!token){
    dead();
  } else {
    apiGet('/api/web-agent/' + encodeURIComponent(token)).then(function(data){
      var d = data.data;
      document.getElementById('waName').textContent = d.name || '智能体';
      document.getElementById('waIcon').textContent = d.icon || '🤖';
      document.title = (d.name || '智能体') + ' - Web app';
      applyBrand(d.color);
      input.disabled = false;
      sendBtn.disabled = false;
      input.placeholder = '和 ' + (d.name || '智能体') + ' 对话…';
      addMsg('bot', '你好，我是 ' + (d.name || '智能体') + (d.description ? '：' + d.description : '') + '\n请输入你的问题。');
    }).catch(function(){ dead(); });
  }

  function addMsg(role, text){
    var div = document.createElement('div');
    div.className = 'wa-msg ' + role;
    var bubble = document.createElement('div');
    bubble.className = 'wa-bubble';
    bubble.innerHTML = esc(text).replace(/\n/g, '<br>');
    div.appendChild(bubble);
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
    return bubble;
  }

  var sending = false;
  function send(){
    var text = input.value.trim();
    if (!text || sending || !token) return;
    sending = true;
    addMsg('user', text);
    input.value = '';
    var b = addMsg('bot', '思考中…');
    b.classList.add('loading');
    apiPost('/api/web-agent/' + encodeURIComponent(token) + '/chat', { message: text }).then(function(data){
      b.classList.remove('loading');
      if (data.data && data.data.reply){
        b.innerHTML = esc(data.data.reply).replace(/\n/g, '<br>');
      } else {
        b.classList.add('err');
        b.textContent = '调用失败：未知错误';
      }
      sending = false;
      scroll.scrollTop = scroll.scrollHeight;
    }).catch(function(err){
      b.classList.remove('loading');
      b.classList.add('err');
      /* 后端会把真实原因放在 code!=200 的 msg 里（apiPost 已将其 throw 出来），
         不能笼统显示成“网络异常”，否则模型侧报错永远看不到。*/
      b.textContent = '⚠ ' + ((err && err.message) ? err.message : '网络异常，请稍后重试');
      sending = false;
    });
  }
  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', function(e){ if (e.key === 'Enter') send(); });
})
</script>
<style>
  .wa-root{ position:fixed; inset:0; display:flex; flex-direction:column; background:#F7F9FC; }

  .wa-head{ display:flex; align-items:center; gap:10px; padding:14px 20px; background:#2E63F0; color:#fff; flex-shrink:0; }
  .wa-ico{ width:34px; height:34px; border-radius:10px; background:rgba(255,255,255,.22); display:inline-flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
  .wa-name{ font-size:16px; font-weight:600; }
  .wa-powered{ margin-left:auto; font-size:12px; opacity:.75; }

  .wa-scroll{ flex:1; overflow-y:auto; padding:22px 16px; }
  .wa-list{ max-width:760px; margin:0 auto; display:flex; flex-direction:column; gap:14px; }
  .wa-msg{ display:flex; }
  .wa-msg.user{ justify-content:flex-end; }
  .wa-bubble{ max-width:78%; padding:10px 14px; border-radius:12px; font-size:14px; line-height:1.7; background:#fff; border:1px solid var(--border-light); color:var(--text-1); white-space:pre-wrap; word-break:break-word; }
  .wa-msg.user .wa-bubble{ background:#2E63F0; color:#fff; border:none; }
  .wa-bubble.loading{ color:var(--text-3); }
  .wa-bubble.err{ background:#FFECE8; border-color:#FFCDC7; color:#E03030; }

  .wa-inputbar{ padding:12px 16px 20px; flex-shrink:0; }
  .wa-input{ max-width:760px; margin:0 auto; display:flex; align-items:center; gap:10px; background:#fff; border:1px solid var(--border); border-radius:12px; padding:10px 12px 10px 16px; box-shadow:0 2px 10px rgba(29,33,41,.05); }
  .wa-input input{ flex:1; border:none; outline:none; font-size:14px; background:transparent; }
  .wa-send{ width:34px; height:34px; border:none; border-radius:9px; background:#2E63F0; color:#fff; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
  .wa-send svg{ width:17px; height:17px; }
  .wa-send:disabled{ opacity:.5; cursor:not-allowed; }

  .wa-dead{ position:absolute; inset:0; background:#fff; flex-direction:column; align-items:center; justify-content:center; gap:10px; z-index:10; }
  .wa-dead-ico{ font-size:40px; }
  .wa-dead-t{ font-size:16px; font-weight:600; color:var(--text-1); }
  .wa-dead-s{ font-size:13px; color:var(--text-3); }
</style>

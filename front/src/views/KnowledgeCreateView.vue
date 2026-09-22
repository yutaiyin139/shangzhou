<template>
  <div id="page-root" class="page-root knowledge-create-root">
    <!-- 顶部细条 -->
    <header class="kc-top">
      <button class="kc-back" data-action="location.hash = '/knowledge'">‹ 知识库</button>
      <div class="kc-steps">
        <span class="kc-step" id="step1">
          <span class="kc-badge-on" id="step1Badge">STEP 1</span>
          <span class="kc-txt-on" id="step1Txt">选择数据源</span>
        </span>
        <span class="kc-line"></span>
        <span class="kc-step" id="step2">
          <span class="kc-badge-off" id="step2Badge">2</span>
          <span class="kc-txt-off" id="step2Txt">文本分段与清洗</span>
        </span>
        <span class="kc-line"></span>
        <span class="kc-step" id="step3">
          <span class="kc-badge-off">3</span>
          <span class="kc-txt-off">处理并完成</span>
        </span>
      </div>
    </header>
    
    <div class="kc-body">
      <!-- 选择数据源 -->
      <div class="kc-sec-t">选择数据源</div>
      <div class="src-cards" id="srcCards">
        <div class="src-card sel">
          <span class="src-ico"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h8l4 4v14H6V3z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 16h6"/></svg></span>
          导入已有文本
        </div>
        <div class="src-card">
          <span class="src-ico"><span class="src-n">N</span></span>
          同步自 Notion 内容
        </div>
        <div class="src-card">
          <span class="src-ico"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.3 3.8 5.2 3.8 8.5s-1.2 6.2-3.8 8.5c-2.6-2.3-3.8-5.2-3.8-8.5S9.4 5.8 12 3.5z"/></svg></span>
          同步自 Web 站点
        </div>
      </div>
    
      <!-- 上传文本文件 -->
      <div class="kc-sec-t">上传文本文件</div>
      <div class="up-zone" id="upZone">
        <div class="up-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7 18a4.5 4.5 0 1 1 .7-8.95A5.5 5.5 0 0 1 18.3 11 3.8 3.8 0 0 1 17.5 18H7z"/><path d="M12 12v6M9.5 13.5L12 11l2.5 2.5"/></svg></div>
        <div class="up-tip">拖拽文件或文件夹至此，或者 <a class="link" id="pickLink">选择文件</a></div>
        <div class="up-fmt">已支持 MD、HTML、HTM、XLSX、DOCX、VTT、XLS、TXT、PROPERTIES、CSV、MDX、PDF、MARKDOWN，每批最多 5 个文件，每个文件不超过 15 MB。</div>
      </div>
      <input type="file" id="fileInput" multiple accept=".md,.html,.htm,.xlsx,.docx,.vtt,.xls,.txt,.properties,.csv,.mdx,.pdf,.markdown" style="display:none;">
      <div id="fileList"></div>
    
      <div class="kc-next-row">
        <button class="btn btn-primary kc-next" id="nextBtn" disabled>下一步 →</button>
      </div>
    
      <hr class="kc-div">
    
      <a class="link" data-action="openModal(&#x27;kcModal&#x27;)">▣ 创建一个空知识库</a>
    </div>
    
    <!-- 创建空知识库 弹窗 -->
    <div class="modal-mask" id="kcModal">
      <div class="modal">
        <div class="modal-head"><div class="modal-title">创建空知识库</div><button class="modal-close" data-action="closeModal(&#x27;kcModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div style="font-size:13px;color:var(--text-2);margin-bottom:20px;">空知识库中还没有文档，你可以在今后任何时候上传文档至该知识库。</div>
          <div class="form-item" style="margin-bottom:0;">
            <div class="form-label">知识库名称</div>
            <input class="form-input" id="kcName" placeholder="请输入知识库名称">
            <div class="kc-err" id="kcNameErr">请输入知识库名称</div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" data-action="closeModal(&#x27;kcModal&#x27;)">取消</button>
          <button class="btn btn-primary" data-action="createEmptyKb()">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiPost } from '../api/client'

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
  
  /* 数据源卡片切换选中 */
  document.querySelectorAll('#srcCards .src-card').forEach(function(c){
    c.addEventListener('click', function(){
      document.querySelectorAll('#srcCards .src-card').forEach(function(x){ x.classList.remove('sel'); });
      c.classList.add('sel');
    });
  });
  
  /* 文件选择：真实文件输入 + 拖拽，支持多文件（≤5、≤15MB） */
  var fileInput = document.getElementById('fileInput');
  var fileList = document.getElementById('fileList');
  var nextBtn = document.getElementById('nextBtn');
  var upZone = document.getElementById('upZone');
  var selectedFiles = [];

  function escHtml(s){
    return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function fmtSize(n){
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(2) + ' MB';
  }
  function fileExt(fn){
    var i = fn.lastIndexOf('.');
    return i > -1 ? fn.slice(i + 1).toUpperCase() : '';
  }
  function fileColor(ext){
    var m = { DOCX:'#2B579A', DOC:'#2B579A', PDF:'#E21B1B', TXT:'#5B6B7B', MD:'#1F6FEB', MARKDOWN:'#1F6FEB', HTML:'#E34F26', HTM:'#E34F26', CSV:'#2E7D32', XLSX:'#217346', XLS:'#217346' };
    return m[ext] || '#8A94A6';
  }
  function renderFiles(){
    fileList.innerHTML = selectedFiles.map(function(f, i){
      var ext = fileExt(f.name);
      return '<div class="file-row" style="display:flex;">' +
        '<span class="f-ico"><svg width="30" height="30" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3" fill="' + fileColor(ext) + '"/><text x="12" y="16.5" font-size="11" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">' + escHtml(ext.charAt(0) || 'F') + '</text></svg></span>' +
        '<span style="display:flex;flex-direction:column;gap:2px;min-width:0;">' +
          '<span style="font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escHtml(f.name) + '</span>' +
          '<span class="f-size">' + escHtml(ext || 'FILE') + ' · ' + fmtSize(f.size) + '</span>' +
        '</span>' +
        '<button class="f-del" data-idx="' + i + '" title="移除"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13M10 11v6M14 11v6"/></svg></button>' +
      '</div>';
    }).join('');
    nextBtn.disabled = selectedFiles.length === 0;
  }
  function addFiles(list){
    Array.prototype.forEach.call(list, function(file){
      if (selectedFiles.length >= 5){ toast('每批最多 5 个文件'); return; }
      var ext = (file.name.split('.').pop() || '').toLowerCase();
      if (!/^(txt|md|markdown|html|htm|csv|properties|vtt|mdx|json|docx|pdf|xlsx)$/.test(ext)){
        toast('不支持的文件类型：' + file.name);
        return;
      }
      if (file.size > 15 * 1024 * 1024){ toast('文件超过 15MB：' + file.name); return; }
      selectedFiles.push(file);
    });
    renderFiles();
  }
  upZone.addEventListener('click', function(){ fileInput.click(); });
  document.getElementById('pickLink').addEventListener('click', function(e){
    e.stopPropagation();
    fileInput.click();
  });
  fileInput.addEventListener('change', function(){
    addFiles(fileInput.files);
    fileInput.value = '';
  });
  /* 拖拽上传 */
  upZone.addEventListener('dragover', function(e){ e.preventDefault(); });
  upZone.addEventListener('drop', function(e){
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  });
  fileList.addEventListener('click', function(e){
    var btn = e.target && e.target.closest ? e.target.closest('.f-del') : null;
    if (!btn) return;
    selectedFiles.splice(Number(btn.dataset.idx), 1);
    renderFiles();
  });

  /* 读取第一个文件内容并存储到 sessionStorage（用于预览） */
  function storeFirstFileContent(cb){
    if (!selectedFiles.length){ cb && cb(); return; }
    var file = selectedFiles[0];
    var ext = (file.name.split('.').pop() || '').toLowerCase();
    // 只读取文本类文件
    if (/^(txt|md|markdown|html|htm|csv|properties|vtt|mdx|json)$/.test(ext)){
      var reader = new FileReader();
      reader.onload = function(e){
        sessionStorage.setItem('_uploadedFileContent', e.target.result);
        sessionStorage.setItem('_uploadedFileName', file.name);
        cb && cb();
      };
      reader.readAsText(file);
    } else {
      // 二进制文件不读取内容（预览时通过 API 处理）
      sessionStorage.setItem('_uploadedFileName', file.name);
      cb && cb();
    }
  }

  /* 下一步：存储文件内容 → 跳转到分段设置页 */
  nextBtn.addEventListener('click', function(){
    if (nextBtn.disabled || nextBtn.dataset.busy) return;
    if (!selectedFiles.length){ toast('请先选择文件'); return; }
    nextBtn.dataset.busy = '1';
    nextBtn.textContent = '处理中…';
    // 存储文件列表到 sessionStorage
    sessionStorage.setItem('_uploadedFileNames', JSON.stringify(selectedFiles.map(function(f){ return f.name; })));
    // 将 File 对象存储到全局变量（用于后续上传）
    window._uploadedFiles = selectedFiles;
    // 读取第一个文件内容用于预览
    storeFirstFileContent(function(){
      location.hash = '/knowledge-process';
      nextBtn.dataset.busy = '';
      nextBtn.textContent = '下一步 →';
    });
  });
  
  /* 创建空知识库：名称非空校验 → 调用后端保存到 MySQL → 返回知识库列表 */
  function createEmptyKb(){
    var input = document.getElementById('kcName');
    var err = document.getElementById('kcNameErr');
    var name = input.value.trim();
    if (!name){
      input.style.borderColor = 'var(--red)';
      err.style.display = 'block';
      input.focus();
      return;
    }
    input.style.borderColor = '';
    err.style.display = 'none';
    apiPost('/api/knowledge/datasets', { name: name }).then(function(data){
      closeModal('kcModal');
      toast('知识库「' + name + '」已创建');
      location.hash = '/knowledge';
    }).catch(function(err){
      console.error('[knowledge-create]', err);
      toast('创建失败：网络错误');
    });
  }
  window.createEmptyKb = createEmptyKb;
})
</script>
<style>
.knowledge-create-root{ background:#fff; }
  /* ---------- 顶部细条 ---------- */
  .kc-top{ height:56px; border-bottom:1px solid var(--border-light); display:flex; align-items:center; padding:0 20px; position:relative; flex-shrink:0; }
  .kc-back{ display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; color:var(--text-1); cursor:pointer; border:none; background:none; padding:0; }
  .kc-back:hover{ color:var(--primary); }
  .kc-steps{ position:absolute; left:50%; transform:translateX(-50%); display:flex; align-items:center; gap:10px; font-size:13px; white-space:nowrap; }
  .kc-step{ display:flex; align-items:center; gap:8px; }
  .kc-badge-on{ background:var(--primary); color:#fff; border-radius:14px; padding:3px 12px; font-size:12px; font-weight:600; }
  .kc-txt-on{ color:var(--primary); font-weight:500; }
  .kc-badge-off{ width:22px; height:22px; border-radius:50%; border:1px solid var(--border); color:var(--text-3); display:inline-flex; align-items:center; justify-content:center; font-size:12px; background:#fff; }
  .kc-txt-off{ color:var(--text-3); }
  .kc-line{ width:42px; height:1px; background:var(--border); }

  /* ---------- 内容区 ---------- */
  .kc-body{ max-width:1000px; padding:38px 24px 80px; }
  .kc-sec-t{ font-size:15px; font-weight:600; margin-bottom:16px; }
  .src-cards{ display:flex; gap:20px; margin-bottom:34px; }
  .src-card{ width:300px; max-width:100%; height:84px; background:#fff; border:1px solid var(--border-light); border-radius:10px; display:flex; align-items:center; gap:14px; padding:0 20px; cursor:pointer; transition:all .15s; user-select:none; }
  .src-card:hover{ border-color:#B8CCFF; }
  .src-card.sel{ border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
  .src-ico{ width:40px; height:40px; border-radius:8px; background:#F2F3F5; display:flex; align-items:center; justify-content:center; font-size:19px; color:var(--text-2); flex-shrink:0; }
  .src-card.sel .src-ico{ color:var(--primary); background:var(--primary-light); }
  .src-n{ font-size:15px; font-weight:700; font-family:Georgia,serif; }

  .up-zone{ border:1.5px dashed var(--border); border-radius:10px; background:#FAFBFC; padding:34px 20px 26px; text-align:center; cursor:pointer; transition:border-color .15s; }
  .up-zone:hover{ border-color:var(--primary); }
  .up-ico{ width:30px; height:30px; color:var(--text-3); margin:0 auto 10px; }
  .up-ico svg{ width:100%; height:100%; }
  .up-tip{ font-size:14px; color:var(--text-1); }
  .up-fmt{ margin-top:14px; font-size:13px; color:var(--text-3); line-height:1.8; }

  .file-row{ display:none; align-items:center; gap:10px; border:1px solid var(--border-light); border-radius:8px; padding:10px 14px; margin-top:14px; font-size:13px; background:#fff; }
  .file-row .f-ico{ font-size:17px; }
  .file-row .f-size{ color:var(--text-3); }
  .file-row .f-del{ margin-left:auto; border:none; background:none; color:var(--text-3); cursor:pointer; font-size:14px; }
  .file-row .f-del:hover{ color:var(--red); }

  .kc-next-row{ display:flex; justify-content:flex-end; margin-top:16px; }
  .kc-next[disabled]{ background:#B9CBF9 !important; border-color:#B9CBF9 !important; color:#fff !important; cursor:not-allowed; }

  .kc-div{ border:none; border-top:1px solid var(--border-light); margin:42px 0 18px; }

  .kc-err{ display:none; color:var(--red); font-size:12px; margin-top:6px; }
.knowledge-create-root{ min-height:100vh; }
</style>

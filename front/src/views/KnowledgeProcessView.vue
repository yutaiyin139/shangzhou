<template>
  <div id="page-root" class="page-root knowledge-process-root">
    <!-- 顶部细条 -->
    <header class="kc-top">
      <button class="kc-back" data-action="location.hash = '/knowledge'">‹ 知识库</button>
      <div class="kc-steps">
        <span class="kc-step"><span class="kc-badge-off">1</span><span class="kc-txt-off">选择数据源</span></span>
        <span class="kc-line"></span>
        <span class="kc-step"><span class="kc-badge-on">STEP 2</span><span class="kc-txt-on">文本分段与清洗</span></span>
        <span class="kc-line"></span>
        <span class="kc-step"><span class="kc-badge-off">3</span><span class="kc-txt-off">处理并完成</span></span>
      </div>
    </header>
    
    <div class="kp-wrap">
      <!-- ============ 左栏 ============ -->
      <div class="kp-left">
    
        <div class="kp-sec-t">分段设置</div>
    
        <!-- 通用（选中） -->
        <div class="opt-card sel" id="cardGeneral">
          <div class="opt-head" data-action="selectSeg(&#x27;general&#x27;)">
            <span class="opt-ico">⚙</span>
            <div>
              <div class="opt-t">通用</div>
              <div class="opt-d">通用文本分块模式，检索和召回的块是相同的</div>
            </div>
          </div>
          <div class="opt-body" id="generalBody">
            <div class="seg-grid">
              <div class="seg-item">
                <div class="seg-label">分段标识符 <span class="q" data-action="showSegHelp(&#x27;delimiter&#x27;)">ⓘ</span></div>
                <div class="seg-input-wrap"><input id="segDelimiter" value="\n"></div>
              </div>
              <div class="seg-item">
                <div class="seg-label">分段最大长度</div>
                <div class="seg-input-wrap"><input id="segMax" type="number" value="1024"><span class="suffix">characters</span></div>
              </div>
              <div class="seg-item">
                <div class="seg-label">分段重叠长度 <span class="q" data-action="showSegHelp(&#x27;overlap&#x27;)">ⓘ</span></div>
                <div class="seg-input-wrap"><input id="segOverlap" type="number" value="50"><span class="suffix">characters</span></div>
              </div>
            </div>
    
            <div style="font-size:13px;font-weight:600;margin-bottom:6px;">文本预处理规则</div>
            <label class="rule-row"><input type="checkbox" id="ruleSpace" checked> 替换掉连续的空格、换行符和制表符</label>
            <label class="rule-row"><input type="checkbox" id="ruleUrl"> 删除所有 URL 和电子邮件地址</label>
    
            <label class="rule-row" style="margin-top:6px;">
              <span class="switch"><input type="checkbox" id="summarySwitch"><span class="sl"></span></span> 摘要自动生成
            </label>
    
            <hr class="kp-div">
    
            <div class="qa-row">
              <input type="checkbox" id="qaCheck" style="width:16px;height:16px;accent-color:var(--primary);cursor:pointer;">
              <span>使用 Q&amp;A 分段，语言</span>
              <span class="qa-lang" data-action="openQaLangPicker()">Chinese Simplified ▾</span>
              <span class="q" style="color:var(--text-4);cursor:help;" data-action="showSegHelp(&#x27;qa&#x27;)">ⓘ</span>
            </div>
    
            <div style="display:flex;gap:12px;margin-top:18px;">
              <button class="btn" style="color:var(--primary);border-color:#B8CCFF;" data-action="previewBlocks()">🔍 预览块</button>
              <button class="btn" style="border:none;" data-action="resetSeg()">重置</button>
            </div>
          </div>
        </div>
    
        <!-- 父子分段（未选） -->
        <div class="opt-card" id="cardParent">
          <div class="opt-head" data-action="selectSeg(&#x27;parent&#x27;)">
            <span class="opt-ico">👨‍👧</span>
            <div>
              <div class="opt-t">父子分段</div>
              <div class="opt-d">使用父子模式时，子块用于检索，父块用作上下文</div>
            </div>
          </div>
          <div class="opt-body" id="parentBody" style="display:none;">
            <div class="seg-grid">
              <div class="seg-item" style="max-width:220px;">
                <div class="seg-label">分段标识符 <span class="q" data-action="showSegHelp(&#x27;delimiter&#x27;)">ⓘ</span></div>
                <div class="seg-input-wrap"><input value="\n"></div>
              </div>
            </div>
            <div style="display:flex;gap:12px;margin-top:6px;">
              <button class="btn" style="color:var(--primary);border-color:#B8CCFF;" data-action="previewBlocks()">🔍 预览块</button>
              <button class="btn" style="border:none;" data-action="resetSeg()">重置</button>
            </div>
          </div>
        </div>
    
        <div class="kp-sec-t">索引方式</div>
        <div class="idx-cards">
          <div class="opt-card sel" id="idxHigh" data-action="selectIdx(&#x27;high&#x27;)">
            <div class="opt-head">
              <span class="opt-ico">✳</span>
              <div>
                <div class="opt-t">高质量 <span class="rec-tag">推荐</span></div>
                <div class="opt-d">调用嵌入模型处理文档以实现更精确的检索，可以帮助 LLM 生成高质量的答案。</div>
              </div>
            </div>
          </div>
          <div class="opt-card" id="idxEco" data-action="selectIdx(&#x27;eco&#x27;)">
            <div class="opt-head">
              <span class="opt-ico">💰</span>
              <div>
                <div class="opt-t">经济</div>
                <div class="opt-d">每个数据块使用 10 个关键词进行检索，不会消耗任何 tokens，但会以降低检索准确性为代价。</div>
              </div>
            </div>
          </div>
        </div>
        <div class="warn-bar" style="margin-top:12px;">
          <span class="wi">⚠</span><span>使用高质量模式进行嵌入后，无法切换回经济模式。</span>
        </div>
    
        <div class="kp-sec-t">Embedding 模型</div>
        <div class="mdl-select" id="embSelect">
          <div class="mdl-field" data-action="event.stopPropagation();toggleMenu(&#x27;embMenu&#x27;)">
            <span class="mdl-ico">✦</span>
            <span id="embValue">multimodal-embedding-v1</span>
            <span style="color:var(--text-4);font-size:12px;">🧠</span>
            <span class="arr">▾</span>
          </div>
          <div class="mdl-menu" id="embMenu">
            <div class="mdl-opt cur" data-action="pickModel(&#x27;emb&#x27;,&#x27;multimodal-embedding-v1&#x27;,this)"><span class="mdl-ico">✦</span>multimodal-embedding-v1<span class="ck">✓</span></div>
            <div class="mdl-opt" data-action="pickModel(&#x27;emb&#x27;,&#x27;text-embedding-v3&#x27;,this)"><span class="mdl-ico">✦</span>text-embedding-v3<span class="ck">✓</span></div>
          </div>
        </div>
    
        <div class="kp-sec-t">检索设置</div>
        <div class="kp-sec-sub">关于检索方法，您可以随时在知识库设置中更改此设置。</div>
    
        <!-- 向量检索（选中） -->
        <div class="opt-card sel" id="retVector">
          <div class="opt-head" data-action="selectRet(&#x27;vector&#x27;)">
            <span class="opt-ico">▦</span>
            <div>
              <div class="opt-t">向量检索</div>
              <div class="opt-d">通过生成查询嵌入并查询与其向量表示最相似的文本分段</div>
            </div>
          </div>
          <div class="opt-body" id="vectorBody">
            <div style="display:flex;align-items:center;gap:10px;font-size:14px;font-weight:600;">
              <span class="switch"><input type="checkbox" id="rerankSwitch" checked><span class="sl"></span></span>
              Rerank 模型 <span class="q" style="color:var(--text-4);cursor:help;font-weight:400;" data-action="showSegHelp(&#x27;rerank&#x27;)">ⓘ</span>
            </div>
            <div class="mdl-select" id="rerankSelect" style="margin-top:12px;">
              <div class="mdl-field" data-action="event.stopPropagation();toggleMenu(&#x27;rerankMenu&#x27;)">
                <span class="mdl-ico">✦</span>
                <span id="rerankValue">qwen3-rerank</span>
                <span class="arr">▾</span>
              </div>
              <div class="mdl-menu" id="rerankMenu">
                <div class="mdl-opt cur" data-action="pickModel(&#x27;rerank&#x27;,&#x27;qwen3-rerank&#x27;,this)"><span class="mdl-ico">✦</span>qwen3-rerank<span class="ck">✓</span></div>
                <div class="mdl-opt" data-action="pickModel(&#x27;rerank&#x27;,&#x27;bge-reranker-v2&#x27;,this)"><span class="mdl-ico">✦</span>bge-reranker-v2<span class="ck">✓</span></div>
              </div>
            </div>
            <div class="warn-bar" style="margin-top:12px;">
              <span class="wi">⚠</span><span>当 Embedding 模型支持多模态时，请选择多模态 Rerank 模型以获得更好的检索效果。</span>
            </div>
    
            <div class="slider-row">
              <div class="slider-item">
                <div class="slider-head">Top K <span class="q" data-action="showSegHelp(&#x27;topk&#x27;)">ⓘ</span></div>
                <div class="slider-ctrl">
                  <input class="num-box" type="number" id="topkNum" value="3" min="1" max="10">
                  <input type="range" id="topkRange" min="1" max="10" value="3">
                </div>
              </div>
              <div class="slider-item">
                <div class="slider-head">
                  <span class="switch"><input type="checkbox" id="scoreSwitch"><span class="sl"></span></span>
                  Score 阈值 <span class="q" data-action="showSegHelp(&#x27;score&#x27;)">ⓘ</span>
                </div>
                <div class="slider-ctrl">
                  <input class="num-box" type="number" id="scoreNum" value="0.5" step="0.05" min="0" max="1" disabled>
                  <input type="range" id="scoreRange" min="0" max="1" step="0.05" value="0.5" disabled>
                </div>
              </div>
            </div>
          </div>
        </div>
    
        <!-- 全文检索（未选） -->
        <div class="opt-card" id="retFulltext">
          <div class="opt-head" data-action="selectRet(&#x27;fulltext&#x27;)">
            <span class="opt-ico">🔎</span>
            <div>
              <div class="opt-t">全文检索</div>
              <div class="opt-d">索引文档中的所有词汇，从而允许用户查询任意词汇，并返回包含这些词汇的文本片段</div>
            </div>
          </div>
        </div>
    
        <!-- 混合检索（未选） -->
        <div class="opt-card" id="retHybrid">
          <div class="opt-head" data-action="selectRet(&#x27;hybrid&#x27;)">
            <span class="opt-ico">▦</span>
            <div>
              <div class="opt-t">混合检索 <span class="rec-tag">推荐</span></div>
              <div class="opt-d">同时执行全文检索和向量检索，并应用重排序步骤，从两类查询结果中选择匹配用户问题的最佳结果，用户可以选择设置权重或配置重新排序模型。</div>
            </div>
          </div>
        </div>
    
        <div class="kp-foot">
          <button class="btn" data-action="location.hash = '/knowledge-create'">← 上一步</button>
          <button class="btn btn-primary" data-action="saveProcess()">保存并处理</button>
        </div>
      </div>
    
      <!-- ============ 右栏：预览 ============ -->
      <div class="kp-right">
        <div class="pv-card">
          <div class="pv-label">预览</div>
          <div class="pv-file">
            <svg width="22" height="22" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3" fill="#2B579A"/><text x="12" y="16.5" font-size="11" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">W</text></svg>
            <span class="f-name">百度智能客服对话平台UNIT企业版白皮书-v1.1.docx</span>
            <span class="arr">▾</span>
            <span class="pv-count" id="pvCount">0 预估块</span>
          </div>
          <div class="pv-empty" id="pvEmpty">
            <svg class="ei" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/><circle cx="11" cy="11" r="2.5"/></svg>
            <span class="et">点击左侧的"预览块"按钮来加载预览</span>
          </div>
          <div class="pv-blocks" id="pvBlocks">
            <div class="pv-block">
              <div class="b-h"><span class="bn">块 #1</span> · 128 字符</div>
              <div class="b-t">百度智能客服对话平台 UNIT 企业版白皮书。UNIT 是百度推出的智能对话定制与服务平台，面向企业级客户提供任务式对话、问答对话与闲聊等多种对话能力的一站式搭建方案。</div>
            </div>
            <div class="pv-block">
              <div class="b-h"><span class="bn">块 #2</span> · 128 字符</div>
              <div class="b-t">平台内置意图识别、词槽抽取与对话管理引擎，支持通过可视化流程编排快速构建客服机器人，并提供丰富的预置技能与行业知识库，大幅降低对话系统的开发门槛。</div>
            </div>
            <div class="pv-block">
              <div class="b-h"><span class="bn">块 #3</span> · 128 字符</div>
              <div class="b-t">UNIT 企业版支持私有化部署与云端服务两种模式，提供完善的 API 接口与 SDK，可与企业现有 CRM、工单系统无缝集成，保障数据安全的同时提升客服效率与用户满意度。</div>
            </div>
          </div>
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
  
  /* ---------- 分段设置：通用 / 父子分段 切换 ---------- */
  function selectSeg(mode){
    var g = document.getElementById('cardGeneral');
    var p = document.getElementById('cardParent');
    if (mode === 'general'){
      g.classList.add('sel'); p.classList.remove('sel');
      document.getElementById('generalBody').style.display = '';
      document.getElementById('parentBody').style.display = 'none';
    } else {
      p.classList.add('sel'); g.classList.remove('sel');
      document.getElementById('generalBody').style.display = 'none';
      document.getElementById('parentBody').style.display = '';
    }
  }
  
  /* ---------- 索引方式切换 ---------- */
  function selectIdx(mode){
    document.getElementById('idxHigh').classList.toggle('sel', mode === 'high');
    document.getElementById('idxEco').classList.toggle('sel', mode === 'eco');
  }
  
  /* ---------- 检索方式切换 ---------- */
  function selectRet(mode){
    document.getElementById('retVector').classList.toggle('sel', mode === 'vector');
    document.getElementById('retFulltext').classList.toggle('sel', mode === 'fulltext');
    document.getElementById('retHybrid').classList.toggle('sel', mode === 'hybrid');
    document.getElementById('vectorBody').style.display = mode === 'vector' ? '' : 'none';
  }
  
  /* ---------- 模型下拉 ---------- */
  function toggleMenu(id){
    var m = document.getElementById(id);
    var was = m.classList.contains('show');
    document.querySelectorAll('.mdl-menu').forEach(function(x){ x.classList.remove('show'); });
    if (!was) m.classList.add('show');
  }
  document.addEventListener('click', function(){
    document.querySelectorAll('.mdl-menu').forEach(function(x){ x.classList.remove('show'); });
  });
  function pickModel(prefix, value, opt){
    document.getElementById(prefix + 'Value').textContent = value;
    opt.parentNode.querySelectorAll('.mdl-opt').forEach(function(x){ x.classList.remove('cur'); });
    opt.classList.add('cur');
    toast('已切换模型：' + value);
  }
  
  /* ---------- Top K / Score 阈值 联动 ---------- */
  var topkNum = document.getElementById('topkNum');
  var topkRange = document.getElementById('topkRange');
  topkNum.addEventListener('input', function(){ topkRange.value = this.value; });
  topkRange.addEventListener('input', function(){ topkNum.value = this.value; });
  
  var scoreSwitch = document.getElementById('scoreSwitch');
  var scoreNum = document.getElementById('scoreNum');
  var scoreRange = document.getElementById('scoreRange');
  scoreSwitch.addEventListener('change', function(){
    scoreNum.disabled = !this.checked;
    scoreRange.disabled = !this.checked;
  });
  scoreNum.addEventListener('input', function(){ scoreRange.value = this.value; });
  scoreRange.addEventListener('input', function(){ scoreNum.value = this.value; });
  
  /* ---------- 分段配置 ---------- */
  function getSegmentationConfig(){
    var delimiter = document.getElementById('segDelimiter').value;
    // 处理转义字符
    delimiter = delimiter.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
    return {
      delimiter: delimiter,
      max_length: parseInt(document.getElementById('segMax').value) || 1024,
      overlap: parseInt(document.getElementById('segOverlap').value) || 50,
      clean_rules: {
        replace_whitespace: document.getElementById('ruleSpace').checked,
        remove_urls: document.getElementById('ruleUrl').checked,
      }
    };
  }

  /* ---------- 预览块 ---------- */
  function previewBlocks(){
    var segConfig = getSegmentationConfig();
    // 获取上传的文件内容（从 sessionStorage 读取）
    var fileContent = sessionStorage.getItem('_uploadedFileContent') || '';
    var fileName = sessionStorage.getItem('_uploadedFileName') || '';

    if (!fileContent && !fileName){
      // 没有文件内容，尝试从文件列表读取
      var fileInput = document.getElementById('fileInput');
      if (fileInput && fileInput.files && fileInput.files.length > 0){
        var file = fileInput.files[0];
        var reader = new FileReader();
        reader.onload = function(e){
          sessionStorage.setItem('_uploadedFileContent', e.target.result);
          sessionStorage.setItem('_uploadedFileName', file.name);
          doPreview(e.target.result, segConfig);
        };
        reader.readAsText(file);
        return;
      }
    }

    if (fileContent){
      doPreview(fileContent, segConfig);
    } else {
      // 调用 API 预览（使用文件）
      previewWithFile(segConfig);
    }
  }

  function doPreview(content, segConfig){
    // 调用分段预览 API
    apiPost('/api/knowledge/preview-segments', { content: content, segmentation: segConfig }).then(function(data){
      renderPreviewBlocks(data.data.segments);
      document.getElementById('pvCount').textContent = data.data.total + ' 预估块';
    }).catch(function(){
      toast('预览请求失败');
    });
  }

  function previewWithFile(segConfig){
    // 从 sessionStorage 获取文件对象
    var fileContent = sessionStorage.getItem('_uploadedFileContent') || '';
    if (fileContent){
      doPreview(fileContent, segConfig);
      return;
    }
    toast('请先上传文件');
  }

  function renderPreviewBlocks(segments){
    var container = document.getElementById('pvBlocks');
    container.innerHTML = '';
    segments.forEach(function(seg){
      var div = document.createElement('div');
      div.className = 'pv-block';
      div.innerHTML =
        '<div class="b-h"><span class="bn">块 #' + (seg.index + 1) + '</span> · ' + seg.char_count + ' 字符</div>' +
        '<div class="b-t">' + esc(seg.content) + '</div>';
      container.appendChild(div);
    });
    document.getElementById('pvEmpty').style.display = 'none';
    container.style.display = 'flex';
  }

  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function resetSeg(){
    selectSeg('general');
    document.getElementById('segDelimiter').value = '\\n';
    document.getElementById('segMax').value = 1024;
    document.getElementById('segOverlap').value = 50;
    document.getElementById('ruleSpace').checked = true;
    document.getElementById('ruleUrl').checked = false;
    document.getElementById('summarySwitch').checked = false;
    document.getElementById('qaCheck').checked = false;
    document.getElementById('pvBlocks').style.display = 'none';
    document.getElementById('pvEmpty').style.display = 'flex';
    document.getElementById('pvCount').textContent = '0 预估块';
    toast('已重置为默认配置');
  }

  /* ---------- 保存并处理 ---------- */
  function saveProcess(){
    var segConfig = getSegmentationConfig();
    // 获取上传的文件
    var files = window._uploadedFiles || [];
    if (!files.length){
      toast('请先上传文件');
      location.hash = '/knowledge-create';
      return;
    }

    // 构建 FormData
    var fd = new FormData();
    Array.prototype.forEach.call(files, function(f){ fd.append('files', f); });
    fd.append('segmentation', JSON.stringify(segConfig));

    // 上传文件并创建知识库
    toast('正在处理…');
    apiPost('/api/knowledge/datasets', fd)
      .then(function(data){
        toast('知识库「' + data.data.name + '」已创建，共 ' + data.data.segment_count + ' 个分段');
        // 清理临时数据
        window._uploadedFiles = null;
        sessionStorage.removeItem('_uploadedFileContent');
        sessionStorage.removeItem('_uploadedFileName');
        sessionStorage.removeItem('_uploadedFileNames');
        sessionStorage.removeItem('_segmentationConfig');
        setTimeout(function(){ location.hash = '/knowledge'; }, 800);
      })
      .catch(function(err){
        console.error('[knowledge-process]', err);
        toast('创建失败：网络错误');
      });
  }

  /* ================= P3 占位功能实现 ================= */

  /* 分段设置帮助 */
  function showSegHelp(type){
    var help = {
      delimiter: '分段标识符：用于将长文本切分为多个分段的符号或字符串。常用值：\\n（换行）、\\n\\n（空行）、句号、逗号等。',
      overlap: '分段重叠长度：相邻两个分段之间重叠的字符数。适当的重叠可保持上下文连贯性，避免信息在分段边界处丢失。',
      qa: 'Q&A 分段：将文档内容自动整理为问答对格式，适用于 FAQ 类文档。需要选择文档语言以使用对应的分词和问答生成模型。',
      rerank: 'Rerank 模型：对初步召回的候选分段进行二次重排序，提升最终返回结果的相关性。建议选择与 Embedding 模型配套的 Rerank 模型。',
      topk: 'Top K：每次检索返回的分段数量。值越大，返回的上下文越多，但可能引入噪声，也会增加 Token 消耗。',
      score: 'Score 阈值：过滤低于该相似度分数的分段。取值范围 0-1，值越高表示要求越严格，返回的分段越少但越相关。'
    };
    openModal('参数说明', '<div class="help-content"><p>' + (help[type] || '暂无说明') + '</p></div>');
  }
  window.showSegHelp = showSegHelp;

  /* Q&A 语言选择器 */
  function openQaLangPicker(){
    openModal('选择语言',
      '<div class="lang-picker">' +
        '<button class="lp-btn" data-action="setQaLang(\'Chinese Simplified\')">简体中文</button>' +
        '<button class="lp-btn" data-action="setQaLang(\'Chinese Traditional\')">繁體中文</button>' +
        '<button class="lp-btn" data-action="setQaLang(\'English\')">English</button>' +
        '<button class="lp-btn" data-action="setQaLang(\'Japanese\')">日本語</button>' +
        '<button class="lp-btn" data-action="setQaLang(\'Korean\')">한국어</button>' +
      '</div>'
    );
  }
  function setQaLang(lang){
    var el = document.querySelector('.qa-lang');
    if (el) el.textContent = lang + ' ▾';
    closeModal();
    toast('已选择语言：' + lang);
  }
  window.openQaLangPicker = openQaLangPicker;

})
</script>
<style>
.knowledge-process-root{ background:#fff; }
  /* ---------- 顶部细条（同 knowledge-create） ---------- */
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

  /* ---------- 双栏布局 ---------- */
  .kp-wrap{ display:flex; height:calc(100vh - 56px); }
  .kp-left{ width:55%; overflow-y:auto; padding:26px 34px 40px; }
  .kp-right{ width:45%; border-left:1px solid var(--border-light); background:#fff; overflow-y:auto; padding:22px 24px; }

  .kp-sec-t{ font-size:15px; font-weight:600; margin:26px 0 12px; }
  .kp-sec-t:first-child{ margin-top:0; }
  .kp-sec-sub{ font-size:13px; color:var(--text-2); margin:-6px 0 12px; }
  .kp-sec-sub .link{ font-size:13px; }

  /* 可选卡片 */
  .opt-card{ border:1px solid var(--border-light); border-radius:10px; background:#fff; margin-bottom:14px; transition:border-color .15s, box-shadow .15s; }
  .opt-card.sel{ border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
  .opt-head{ display:flex; gap:12px; padding:16px 18px; cursor:pointer; user-select:none; }
  .opt-ico{ width:36px; height:36px; border-radius:8px; background:#F2F3F5; display:flex; align-items:center; justify-content:center; font-size:17px; color:var(--text-2); flex-shrink:0; }
  .opt-card.sel .opt-ico{ background:var(--primary-light); color:var(--primary); }
  .opt-t{ font-size:14px; font-weight:600; display:flex; align-items:center; gap:8px; }
  .rec-tag{ border:1px solid #B8CCFF; color:var(--primary); font-size:11px; padding:0 7px; border-radius:4px; font-weight:500; line-height:18px; }
  .opt-d{ font-size:13px; color:var(--text-3); margin-top:4px; line-height:1.6; }
  .opt-body{ border-top:1px solid var(--border-light); padding:18px; }

  /* 三列小表单 */
  .seg-grid{ display:flex; gap:14px; margin-bottom:18px; }
  .seg-item{ flex:1; }
  .seg-label{ font-size:13px; font-weight:500; margin-bottom:8px; display:flex; align-items:center; gap:4px; }
  .seg-label .q{ color:var(--text-4); cursor:help; }
  .seg-input-wrap{ display:flex; align-items:center; background:#F7F8FA; border:1px solid var(--border-light); border-radius:6px; overflow:hidden; }
  .seg-input-wrap input{ border:none; background:transparent; padding:9px 10px; font-size:13px; width:100%; outline:none; }
  .seg-input-wrap .suffix{ color:var(--text-3); font-size:12px; padding:0 10px; white-space:nowrap; border-left:1px solid var(--border-light); align-self:stretch; display:flex; align-items:center; background:#F2F3F5; }

  .rule-row{ display:flex; align-items:center; gap:9px; font-size:13px; padding:7px 0; color:var(--text-1); }
  .rule-row input[type=checkbox]{ width:16px; height:16px; accent-color:var(--primary); cursor:pointer; }
  .kp-div{ border:none; border-top:1px solid var(--border-light); margin:14px 0; }
  .qa-row{ display:flex; align-items:center; gap:9px; font-size:13px; color:var(--text-1); }
  .qa-lang{ display:inline-flex; align-items:center; gap:6px; background:#F2F3F5; border-radius:6px; padding:5px 10px; font-size:12px; color:var(--text-2); cursor:pointer; }

  /* 警告条 */
  .warn-bar{ display:flex; gap:10px; align-items:flex-start; background:#FFF7E8; border-radius:8px; padding:11px 14px; font-size:13px; color:var(--text-2); line-height:1.6; }
  .warn-bar .wi{ color:#FF7D00; flex-shrink:0; }

  /* 模型下拉 */
  .mdl-select{ position:relative; user-select:none; }
  .mdl-field{ display:flex; align-items:center; gap:10px; background:#F7F8FA; border:1px solid var(--border-light); border-radius:8px; padding:11px 14px; font-size:14px; cursor:pointer; }
  .mdl-field:hover{ border-color:#B8CCFF; }
  .mdl-field .arr{ margin-left:auto; color:var(--text-3); font-size:11px; }
  .mdl-ico{ width:20px; height:20px; border-radius:5px; background:linear-gradient(135deg,#7BA7FF,#2E63F0); display:inline-flex; align-items:center; justify-content:center; color:#fff; font-size:11px; flex-shrink:0; }
  .mdl-menu{ position:absolute; left:0; right:0; top:calc(100% + 6px); background:#fff; border:1px solid var(--border-light); border-radius:8px; box-shadow:0 6px 24px rgba(29,33,41,.12); padding:6px; display:none; z-index:40; }
  .mdl-menu.show{ display:block; }
  .mdl-opt{ display:flex; align-items:center; gap:10px; padding:9px 12px; border-radius:6px; font-size:13px; cursor:pointer; }
  .mdl-opt:hover{ background:#F2F3F5; }
  .mdl-opt .ck{ margin-left:auto; color:var(--primary); visibility:hidden; }
  .mdl-opt.cur .ck{ visibility:visible; }

  /* 索引方式双卡 */
  .idx-cards{ display:flex; gap:14px; }
  .idx-cards .opt-card{ flex:1; margin-bottom:0; }

  /* 滑块行 */
  .slider-row{ display:flex; align-items:flex-start; gap:40px; margin-top:16px; }
  .slider-item{ flex:1; }
  .slider-head{ display:flex; align-items:center; gap:6px; font-size:14px; font-weight:600; margin-bottom:10px; }
  .slider-head .q{ color:var(--text-4); cursor:help; font-weight:400; }
  .slider-ctrl{ display:flex; align-items:center; gap:12px; }
  .num-box{ width:72px; border:1px solid var(--border-light); border-radius:6px; padding:7px 10px; font-size:13px; background:#F7F8FA; outline:none; }
  .num-box:focus{ border-color:var(--primary); }
  input[type=range]{ flex:1; accent-color:var(--primary); cursor:pointer; }
  input[type=range][disabled]{ accent-color:#C9CDD4; cursor:not-allowed; }
  .num-box[disabled]{ color:var(--text-4); }

  /* 底部按钮 */
  .kp-foot{ display:flex; justify-content:space-between; margin-top:34px; }

  /* 右栏预览 */
  .pv-card{ border:1px solid var(--border-light); border-radius:12px; min-height:calc(100% - 4px); display:flex; flex-direction:column; }
  .pv-label{ font-size:13px; font-weight:600; color:var(--primary); padding:16px 18px 0; }
  .pv-file{ display:flex; align-items:center; gap:10px; padding:12px 18px; border-bottom:1px solid var(--border-light); }
  .pv-file .f-name{ font-size:14px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:240px; }
  .pv-file .arr{ color:var(--text-3); font-size:11px; }
  .pv-count{ margin-left:auto; background:#F2F3F5; color:var(--text-3); font-size:12px; padding:2px 10px; border-radius:5px; flex-shrink:0; }
  .pv-empty{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:16px; color:var(--text-3); padding:60px 20px; }
  .pv-empty .ei{ width:56px; height:56px; color:#C9CDD4; }
  .pv-empty .et{ font-size:14px; }
  .pv-blocks{ display:none; flex-direction:column; gap:12px; padding:16px 18px; }
  .pv-block{ background:#F7F8FA; border-radius:8px; padding:12px 14px; }
  .pv-block .b-h{ font-size:12px; color:var(--text-3); margin-bottom:6px; display:flex; align-items:center; gap:8px; }
  .pv-block .b-h .bn{ color:var(--primary); font-weight:600; }
  .pv-block .b-t{ font-size:13px; color:var(--text-1); line-height:1.7; }
.knowledge-process-root{ min-height:100vh; }
</style>

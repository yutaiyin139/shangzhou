<template>
  <AppShell id="page-root" active-key="skills">
    <div class="page-pad">
      <div class="page-head">
        <div>
          <div class="page-title">Skills 广场</div>
          <div class="page-sub">开箱即用的内置 Skills 与导入的自定义 Skills —— 为智能体扩展专业能力。</div>
        </div>
        <div class="ops">
          <button class="btn btn-primary" data-action="openAddSkill()">＋ 导入自定义 Skill</button>
        </div>
      </div>

      <!-- 工具栏：页签 + 搜索 + 场景分类（参考 ADP Skills 广场） -->
      <div class="sk-tabs" id="skTabs">
        <button class="sk-tab active" data-f="all">全部</button>
        <button class="sk-tab" data-f="builtin">内置 Skills</button>
        <button class="sk-tab" data-f="custom">自定义 Skills</button>
      </div>
      <div class="sk-bar">
        <span class="search-input" style="min-width:260px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="skSearch" placeholder="搜索技能"></span>
        <select class="sk-cate" id="skCate"></select>
        <span class="sk-count" id="skCount"></span>
      </div>

      <div class="sk-grid" id="skGrid"></div>

    </div>

    <!-- 导入自定义 Skill 弹窗（参考 ADP：导入 ZIP 包，内含 SKILL.md） -->
    <div class="modal-mask" id="skillModal">
      <div class="modal" style="width:640px;">
        <div class="modal-head"><div class="modal-title">导入自定义 Skill</div>
          <button class="modal-close" data-action="closeModal(&#x27;skillModal&#x27;)">✕</button></div>
        <div class="modal-body">
          <div class="zip-drop" id="zipDrop">
            <div class="z1">点击或拖拽 ZIP 文件到此处</div>
            <div class="z2">ZIP 包内必须包含 SKILL.md 文件（含 name / description 元信息）</div>
            <div class="z3" id="zipName"></div>
          </div>
          <input type="file" id="zipInput" accept=".zip" style="display:none">
        </div>
        <div class="modal-foot">
          <button class="btn" data-action="closeModal(&#x27;skillModal&#x27;)">取消</button>
          <button class="btn btn-primary" id="skillImportBtn">确认导入</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onUnmounted } from 'vue'
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

  /* ================= 数据 ================= */
  var skills = [];           // 技能列表（内置 + 自定义）
  var loaded = false;        // 是否已加载
  var curFilter = 'all';     // all / builtin / custom
  var curQ = '';             // 搜索词
  var curCate = '';          // 场景分类（空 = 全部）

  /* 场景分类（对齐 ADP Skills 广场分类体系） */
  var CATES = ['知识引擎', '办公文档', '文字识别', '图像处理', '音视频', '设计开发', '智能搜索', '其他'];

  function esc(s){ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  /* ========== 加载技能列表 ========== */
  function loadSkills(){
    apiGet('/api/skills').then(function(data){
      loaded = true;
      if (data.code === 200){
        skills = data.data || [];
        render();
      } else {
        document.getElementById('skGrid').innerHTML = '<div class="sk-none">加载失败：' + esc(data.msg || '未知错误') + '</div>';
      }
    }).catch(function(){ loaded = true; render(); });
  }

  /* ========== 渲染（页签 + 搜索 + 分类过滤，与 ADP 广场一致） ========== */
  function render(){
    var grid = document.getElementById('skGrid');
    if (!grid) return;   // 组件已卸载（如安装/卸载后立即离开页面）
    var q = curQ.trim().toLowerCase();
    var list = skills.filter(function(s){
      var okF = curFilter === 'all' || s.kind === curFilter;
      var okC = !curCate || s.category === curCate;
      var okQ = !q || s.name.toLowerCase().indexOf(q) > -1 || s.description.toLowerCase().indexOf(q) > -1;
      return okF && okC && okQ;
    });
    document.getElementById('skCount').textContent = list.length + ' 个技能';
    var grid = document.getElementById('skGrid');
    if (!list.length){
      grid.innerHTML = loaded
        ? '<div class="sk-none">未找到技能</div>'
        : '<div class="sk-none">加载中…</div>';
      return;
    }
    grid.innerHTML = list.map(function(s){
      var badge = s.kind === 'custom'
        ? '<span class="sk-badge custom">自定义</span>'
        : '<span class="sk-badge builtin">内置</span>';
      var act = s.kind === 'custom'
        ? '<button class="sk-del" data-action="delSkill(\'' + s.key + '\')">删除</button>'
        : (s.installed
            ? '<span class="sk-ver">v' + esc(s.version || '1.0.0') + '</span><button class="sk-un" data-action="uninstallSkill(\'' + s.key + '\')">卸载</button>'
            : '<button class="sk-inst-btn" data-action="installSkill(\'' + s.key + '\')">安装</button>');
      return '<div class="sk-card" data-key="' + esc(s.key) + '">' + badge +
        '<div class="sk-h">' +
          '<span class="sk-ico">' + (s.icon || '✨') + '</span>' +
          '<span class="sk-name">' + esc(s.name) + '</span>' +
        '</div>' +
        '<span class="sk-cate">' + esc(s.category || '其他') + '</span>' +
        '<div class="sk-desc">' + esc(s.description) + '</div>' +
        '<div class="sk-foot"><span class="sk-time">更新于 ' + esc(s.updated_at || '') + '</span>' + act + '</div>' +
      '</div>';
    }).join('');
    grid.querySelectorAll('.sk-card').forEach(function(c){
      c.addEventListener('click', function(e){
        /* 卡片内按钮（安装/卸载/删除）不触发跳转 */
        if (e.target && e.target.closest && e.target.closest('button')) return;
        location.hash = '/skill-detail?key=' + encodeURIComponent(c.dataset.key);
      });
    });
  }

  /* ========== 页签 / 搜索 / 分类 ========== */
  document.querySelectorAll('#skTabs .sk-tab').forEach(function(t){
    t.addEventListener('click', function(){
      document.querySelectorAll('#skTabs .sk-tab').forEach(function(x){ x.classList.remove('active'); });
      t.classList.add('active');
      curFilter = t.dataset.f;
      render();
    });
  });
  document.getElementById('skSearch').addEventListener('input', function(){ curQ = this.value; render(); });
  document.getElementById('skCate').addEventListener('change', function(){ curCate = this.value; render(); });

  /* ========== 安装 / 卸载 / 删除 ========== */
  function setSkill(key, installed){
    skills.forEach(function(s){ if (s.key === key) s.installed = installed; });
    render();
  }
  function installSkill(key){
    /* 模拟在线安装：按钮进入「安装中…」拉取状态，成功后切换为版本号 + 卸载 */
    var btn = document.querySelector('[data-action="installSkill(\'' + key + '\')"]');
    if (btn){ btn.disabled = true; btn.textContent = '安装中…'; }
    apiPost('/api/skills/' + encodeURIComponent(key) + '/install').then(function(data){
        if (data.code === 200){
          var v = data.data && data.data.version ? 'v' + data.data.version : '';
          setSkill(key, true);
          toast('已安装（' + v + '），可在智能体编排中使用');
        } else {
          if (btn){ btn.disabled = false; btn.textContent = '安装'; }
          toast(data.msg || '安装失败');
        }
      }).catch(function(){ if (btn){ btn.disabled = false; btn.textContent = '安装'; } toast('网络异常，请稍后重试'); });
  }
  function uninstallSkill(key){
    apiDelete('/api/skills/' + encodeURIComponent(key) + '/install').then(function(data){
        if (data.code === 200){ setSkill(key, false); toast('已卸载'); }
        else toast(data.msg || '卸载失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }
  function delSkill(key){
    var s = skills.filter(function(x){ return x.key === key; })[0];
    if (!confirm('确定删除自定义 Skill「' + (s ? s.name : '') + '」吗？')) return;
    var sid = key.replace(/^custom_/, '');
    apiDelete('/api/skills/' + sid).then(function(data){
        if (data.code === 200){ skills = skills.filter(function(x){ return x.key !== key; }); render(); toast('已删除'); }
        else toast(data.msg || '删除失败');
      }).catch(function(){ toast('网络异常，请稍后重试'); });
  }

  /* ========== 导入自定义 Skill（ZIP 上传） ========== */
  var zipDrop  = document.getElementById('zipDrop');
  var zipInput = document.getElementById('zipInput');
  var zipName  = document.getElementById('zipName');
  var pickedFile = null;

  function openAddSkill(){
    pickedFile = null;
    zipInput.value = '';
    zipName.style.display = 'none';
    openModal('skillModal');
  }
  zipDrop.addEventListener('click', function(){ zipInput.click(); });
  zipInput.addEventListener('change', function(){
    if (zipInput.files && zipInput.files[0]){
      pickedFile = zipInput.files[0];
      zipName.textContent = '已选择：' + pickedFile.name;
      zipName.style.display = 'block';
    }
  });
  zipDrop.addEventListener('dragover', function(e){ e.preventDefault(); zipDrop.classList.add('over'); });
  zipDrop.addEventListener('dragleave', function(){ zipDrop.classList.remove('over'); });
  zipDrop.addEventListener('drop', function(e){
    e.preventDefault();
    zipDrop.classList.remove('over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]){
      pickedFile = e.dataTransfer.files[0];
      zipName.textContent = '已选择：' + pickedFile.name;
      zipName.style.display = 'block';
    }
  });
  document.getElementById('skillImportBtn').addEventListener('click', function(){
    if (!pickedFile){ toast('请先选择 ZIP 文件'); return; }
    var fd = new FormData();
    fd.append('file', pickedFile);
    var btn = this;
    btn.disabled = true;
    apiPost('/api/skills/import', fd).then(function(data){
        if (data.code === 200){
          closeModal('skillModal');
          toast('导入成功：' + (data.data ? data.data.name : ''));
          /* 切到自定义页签并刷新 */
          document.querySelectorAll('#skTabs .sk-tab').forEach(function(x){ x.classList.remove('active'); });
          document.querySelector('#skTabs .sk-tab[data-f="custom"]').classList.add('active');
          curFilter = 'custom';
          loadSkills();
        } else {
          toast(data.msg || '导入失败');
        }
      }).catch(function(){ toast('网络异常，请稍后重试'); })
      .finally(function(){ btn.disabled = false; });
  });

  /* 内联 onclick 全局可调用：挂载到 window */
  window.installSkill = installSkill;
  window.uninstallSkill = uninstallSkill;
  window.delSkill = delSkill;
  window.openAddSkill = openAddSkill;

  /* 分类下拉初始化 */
  document.getElementById('skCate').innerHTML = '<option value="">全部分类</option>' +
    CATES.map(function(c){ return '<option value="' + esc(c) + '">' + esc(c) + '</option>'; }).join('');

  render();
  loadSkills();
})
</script>
<style>
  .page-head{ display:flex; align-items:flex-start; margin-bottom:18px; }
  .page-head .ops{ margin-left:auto; display:flex; gap:10px; }
  .page-title{ font-size:18px; font-weight:600; }
  .page-sub{ color:var(--text-3); font-size:13px; margin-top:4px; }
  .sk-tabs{ display:flex; gap:28px; margin-top:20px; border-bottom:1px solid var(--border-light); }
  .sk-tab{ padding:10px 2px; font-size:14px; color:var(--text-2); cursor:pointer; border:none; background:none;
    border-bottom:2px solid transparent; margin-bottom:-1px; }
  .sk-tab.active{ color:var(--primary); font-weight:500; border-bottom-color:var(--primary); }
  .sk-bar{ display:flex; align-items:center; gap:14px; margin:16px 0 4px; }
  .sk-cate{ border:1px solid var(--border); border-radius:8px; padding:8px 12px; font-size:13px; color:var(--text-1); background:#fff; outline:none; }
  .sk-cate:focus{ border-color:var(--primary); }
  .sk-count{ margin-left:auto; font-size:12px; color:var(--text-3); }

  .sk-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:16px; }
  @media (max-width:1400px){ .sk-grid{ grid-template-columns:repeat(2,1fr);} }
  .sk-card{ background:#fff; border:1px solid var(--border-light); border-radius:10px; padding:20px;
    cursor:pointer; transition:box-shadow .15s; display:flex; flex-direction:column; min-height:190px; position:relative; }
  .sk-card:hover{ box-shadow:0 4px 16px rgba(29,33,41,.08); }
  .sk-h{ display:flex; align-items:center; gap:12px; }
  .sk-ico{ width:40px; height:40px; border-radius:10px; background:#F2F3F5; display:flex; align-items:center;
    justify-content:center; font-size:19px; flex-shrink:0; }
  .sk-name{ font-size:16px; font-weight:700; color:var(--text-1); }
  .sk-badge{ position:absolute; top:18px; right:18px; font-size:12px; border-radius:5px; padding:2px 9px; }
  .sk-badge.custom{ background:#E8F9EE; color:#00B42A; }
  .sk-badge.builtin{ background:#EAF1FE; color:#2E63F0; }
  .sk-cate{ display:inline-block; margin-top:10px; font-size:11px; color:var(--primary); background:var(--primary-light);
    border-radius:4px; padding:2px 8px; align-self:flex-start; }
  .sk-desc{ font-size:13px; color:var(--text-2); line-height:1.7; margin-top:10px; display:-webkit-box;
    -webkit-line-clamp:2; line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .sk-foot{ margin-top:auto; padding-top:16px; display:flex; align-items:center; }
  .sk-time{ font-size:12px; color:var(--text-3); }
  .sk-inst-btn{ margin-left:auto; border:1px solid var(--primary); color:var(--primary); background:#fff;
    border-radius:6px; padding:4px 16px; font-size:13px; cursor:pointer; transition:all .12s; }
  .sk-inst-btn:hover{ background:var(--primary); color:#fff; }
  .sk-inst-btn:disabled{ opacity:.6; cursor:not-allowed; }
  .sk-ver{ margin-left:auto; font-size:11px; color:var(--text-3); background:#F2F3F5; border-radius:4px; padding:1px 6px; }
  .sk-un{ margin-left:auto; border:1px solid var(--border); color:var(--text-2); background:#fff;
    border-radius:6px; padding:4px 14px; font-size:13px; cursor:pointer; transition:all .12s; }
  .sk-un:hover{ color:var(--red); border-color:var(--red); }
  .sk-del{ margin-left:auto; border:1px solid var(--red); color:var(--red); background:#fff;
    border-radius:6px; padding:4px 14px; font-size:13px; cursor:pointer; }
  .sk-del:hover{ background:#FFF1F0; }
  .sk-none{ grid-column:1/-1; text-align:center; color:var(--text-3); padding:60px 0; font-size:13px; }

  /* 导入弹窗 */
  .zip-drop{ border:1.5px dashed #C9CDD4; border-radius:10px; padding:56px 30px; text-align:center;
    cursor:pointer; transition:border-color .15s, background .15s; }
  .zip-drop:hover, .zip-drop.over{ border-color:var(--primary); background:#F7FAFF; }
  .zip-drop .z1{ font-size:15px; color:var(--text-1); }
  .zip-drop .z2{ font-size:13px; color:var(--text-3); margin-top:10px; }
  .zip-drop .z3{ font-size:13px; color:var(--primary); margin-top:14px; display:none; }
</style>

<template>
  <AppShell id="page-root" active-key="knowledge">
    <div class="page-pad">
    
          <div class="page-head">
            <div class="page-title">知识库</div>
            <div class="ops" style="align-items:center;">
              <div class="dropdown">
                <button class="btn btn-primary" data-action="event.stopPropagation();document.getElementById(&#x27;createMenu&#x27;).classList.toggle(&#x27;show&#x27;)">＋ 创建 ▾</button>
                <div class="dropdown-menu" id="createMenu">
                  <div class="dd-item" data-action="location.hash = '/knowledge-create'"><span class="di">＋</span>创建即用型知识库</div>
                  <div class="dd-item" data-action="document.getElementById(&#x27;createMenu&#x27;).classList.remove(&#x27;show&#x27;);openCustomKbBuilder()"><span class="di">⚙</span>构建自定义知识库</div>
                  <div class="dd-divider"></div>
                  <div class="dd-item" data-action="document.getElementById(&#x27;createMenu&#x27;).classList.remove(&#x27;show&#x27;);openExternalKbConnect()"><span class="di">◎</span>连接外部知识库</div>
                </div>
              </div>
            </div>
          </div>
    
          <div class="kb-toolbar">
            <span class="select"><select><option>标签</option><option>全部标签</option><option>未标记</option></select></span>
            <span class="search-input" style="min-width:220px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="kbSearch" placeholder="搜索"></span>
            <label class="chk"><input type="checkbox" id="kbPermFilter" checked data-action="togglePermFilter()"> 所有知识库 <span style="color:var(--text-4);cursor:help;" data-action="event.preventDefault();showPermHelp()">ⓘ</span></label>
          </div>
    
          <div class="kb-list" id="kbList">
            <div class="kb-none" id="kbEmpty">正在加载知识库...</div>
          </div>
    
        </div>
  </AppShell>
</template>
<script setup>
import { onMounted, onActivated, onDeactivated } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal } from '../utils/global'
import { apiGet } from '../api/client'

/* 命名函数：点击空白处关闭创建下拉 */
function onDocClick(){
  var m = document.getElementById('createMenu');
  if (m) m.classList.remove('show');
}

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
  
  /* 点击卡片进入知识库详情（记录当前知识库名称供详情页展示） */
  function goDetail(e){
    var card = e && e.target && e.target.closest ? e.target.closest('.kb-card') : null;
    if (card && card.dataset.id) {
      sessionStorage.setItem('kbDetailName', card.dataset.name);
      location.hash = '/knowledge-detail/' + card.dataset.id;
    }
  }
  window.goDetail = goDetail;
  
  /* 添加标签：chip → 输入框，回车生成灰 tag */
  function addTag(e, chip){
    e.stopPropagation();
    var input = document.createElement('input');
    input.className = 'tag-input';
    input.placeholder = '输入标签名';
    chip.replaceWith(input);
    input.focus();
    input.addEventListener('click', function(ev){ ev.stopPropagation(); });
    var done = false;
    function finish(commit){
      if (done) return;
      if (!input.isConnected) return;
      var v = input.value.trim();
      if (commit && v){
        done = true;
        var tag = document.createElement('span');
        tag.className = 'tag-chip';
        tag.textContent = v;
        input.replaceWith(tag);
        tag.after(chip);
      } else {
        done = true;
        input.replaceWith(chip);
      }
    }
    input.addEventListener('keydown', function(ev){
      if (ev.key === 'Enter'){ ev.preventDefault(); finish(true); }
      if (ev.key === 'Escape'){ finish(false); }
    });
    input.addEventListener('blur', function(){ finish(true); });
  }
  window.addTag = addTag;
  
  /* 搜索过滤知识库卡片 */
  document.getElementById('kbSearch').addEventListener('input', function(){
    var q = this.value.trim().toLowerCase();
    document.querySelectorAll('#kbList .kb-card').forEach(function(c){
      c.style.display = !q || c.dataset.name.toLowerCase().indexOf(q) > -1 ? '' : 'none';
    });
  });

  /* 加载知识库列表（后端 /api/knowledge/datasets 读取 MySQL 数据） */
  function esc(s){
    return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function fmtTime(iso){
    if (!iso) return '';
    var t = new Date(iso.replace(' ', 'T'));
    var diff = (Date.now() - t.getTime()) / 1000;
    if (diff < 60) return '刚刚';
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
    return Math.floor(diff / 86400) + ' 天前';
  }
  function renderKb(list){
    var box = document.getElementById('kbList');
    if (!list || !list.length){
      box.innerHTML = '<div class="kb-none">暂无知识库，点击右上角「＋ 创建」新建知识库</div>';
      return;
    }
    box.innerHTML = list.map(function(d){
      return '<div class="kb-card" data-name="' + esc(d.name) + '" data-id="' + esc(d.id) + '" data-action="goDetail(event)">' +
        '<div class="kb-card-top">' +
          '<span class="kb-card-ico">📚</span>' +
          '<span class="kb-card-name">' + esc(d.name) + '</span>' +
        '</div>' +
        '<div class="kb-tags"><span class="tag-add" data-action="addTag(event,this)">🏷 添加标签</span></div>' +
        '<div class="kb-meta"><span>📄 ' + (d.doc_count || 0) + '</span><span class="sep">/</span><span>更新于 ' + fmtTime(d.updated_at) + '</span></div>' +
      '</div>';
    }).join('');
  }
  apiGet('/api/knowledge/datasets').then(function(data){
    if (data.code === 200){
      renderKb(data.data || []);
    } else {
      renderKb([]);
      console.error('[knowledge]', data.msg);
    }
  }).catch(function(err){
    renderKb([]);
    console.error('[knowledge]', err);
  });

  /* ================= P3 占位功能实现 ================= */

  /* 自定义知识库构建器 */
  function openCustomKbBuilder(){
    openModal('构建自定义知识库',
      '<div class="help-content">' +
        '<p>自定义知识库构建器允许您：</p>' +
        '<ul>' +
          '<li>选择分段策略（按标题/段落/自定义标识符）</li>' +
          '<li>配置清洗规则（去重/去噪/格式标准化）</li>' +
          '<li>设置索引方式（向量索引/全文索引/混合索引）</li>' +
          '<li>选择 Embedding 模型</li>' +
        '</ul>' +
        '<p style="color:var(--text-3);font-size:12px;">即将推出完整向导…</p>' +
      '</div>'
    );
  }
  window.openCustomKbBuilder = openCustomKbBuilder;

  /* 连接外部知识库 */
  function openExternalKbConnect(){
    openModal('连接外部知识库',
      '<div class="help-content">' +
        '<p>支持连接以下外部知识库：</p>' +
        '<ul>' +
          '<li>Notion 工作区</li>' +
          '<li>Confluence 空间</li>' +
          '<li>飞书文档</li>' +
          '<li>SharePoint 站点</li>' +
          '<li>Web 站点抓取</li>' +
        '</ul>' +
        '<p style="color:var(--text-3);font-size:12px;">即将推出完整配置向导…</p>' +
      '</div>'
    );
  }
  window.openExternalKbConnect = openExternalKbConnect;

  /* 权限筛选切换 */
  function togglePermFilter(){
    var cb = document.getElementById('kbPermFilter');
    toast(cb.checked ? '显示所有知识库' : '仅显示本人创建的知识库');
  }
  window.togglePermFilter = togglePermFilter;

  /* 权限说明 */
  function showPermHelp(){
    toast('勾选后展示你有权限访问的全部知识库（包括共享给你的）');
  }
  window.showPermHelp = showPermHelp;

});

/* keep-alive 兼容：注册/清理 document 点击监听器 */
onActivated(() => {
  document.addEventListener('click', onDocClick);
});

onDeactivated(() => {
  document.removeEventListener('click', onDocClick);
});
</script>
<style>
.kb-toolbar{display:flex;align-items:center;gap:14px;margin:18px 0 16px;}
  .chk{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-2);cursor:pointer;user-select:none;}
  .chk input{accent-color:var(--primary);width:15px;height:15px;cursor:pointer;}
  .kb-list{display:flex;gap:16px;flex-wrap:wrap;}
  .kb-none{width:100%;padding:60px 0;text-align:center;color:var(--text-3);font-size:13px;background:#fff;border:1px dashed var(--border);border-radius:10px;}
  .kb-card{width:380px;max-width:100%;background:#fff;border:1px solid var(--border-light);border-radius:10px;padding:16px 18px 14px;cursor:pointer;transition:box-shadow .15s;display:flex;flex-direction:column;min-height:128px;}
  .kb-card:hover{box-shadow:0 4px 16px rgba(29,33,41,.08);}
  .kb-card-top{display:flex;align-items:center;gap:12px;}
  .kb-card-ico{width:42px;height:42px;border-radius:10px;background:#FBF0DC;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}
  .kb-card-name{font-size:15px;font-weight:600;}
  .kb-tags{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:14px 0 10px;min-height:22px;}
  .tag-add{border:1px dashed var(--border);color:var(--text-3);font-size:12px;padding:2px 9px;border-radius:5px;cursor:pointer;user-select:none;background:#fff;}
  .tag-add:hover{border-color:var(--primary);color:var(--primary);}
  .tag-input{border:1px solid var(--primary);border-radius:5px;font-size:12px;padding:2px 8px;width:110px;outline:none;box-shadow:0 0 0 2px rgba(46,99,240,.12);}
  .tag-chip{background:#F2F3F5;color:var(--text-2);font-size:12px;padding:2px 9px;border-radius:5px;}
  .kb-meta{margin-top:auto;font-size:13px;color:var(--text-3);display:flex;align-items:center;gap:14px;}
  .kb-meta .sep{color:var(--border);}
  .dropdown{position:relative;}
  .dropdown-menu{position:absolute;right:0;top:calc(100% + 6px);background:#fff;border:1px solid var(--border-light);border-radius:8px;box-shadow:0 6px 24px rgba(29,33,41,.12);min-width:210px;padding:6px;display:none;z-index:50;}
  .dropdown-menu.show{display:block;}
  .dropdown-menu .dd-item{padding:9px 12px;border-radius:6px;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:10px;color:var(--text-1);}
  .dropdown-menu .dd-item:hover{background:#F2F3F5;color:var(--primary);}
  .dropdown-menu .dd-item .di{width:16px;text-align:center;color:var(--text-3);}
  .dropdown-menu .dd-item:hover .di{color:var(--primary);}
  .dd-divider{height:1px;background:var(--border-light);margin:6px 4px;}
</style>

<template>
  <AppShell id="page-root" active-key="app-templates">
    <div class="page-pad">

      <div class="page-title">应用模板</div>

      <div class="filter-row">
        <div class="pills-clip">
          <div class="pills-scroll" id="pillScroll">
            <button class="pill active" data-cat="all">全部</button>
            <button v-for="cat in categories" :key="cat" class="pill" :data-cat="cat">{{ cat }}</button>
          </div>
        </div>

        <span class="search-input" style="min-width:260px;">
          <input id="tplSearch" placeholder="搜索模板" v-model="searchQuery">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </span>
        <button class="ico-btn" title="刷新模板" @click="syncTemplates">⟳</button>
      </div>

      <div class="grid-cards" id="tplGrid">
        <div v-for="tpl in filteredTemplates" :key="tpl.id" class="mcard" :data-cat="tpl.display_category" :data-name="tpl.name" @click="openTplModal(tpl)">
          <div class="m-head">
            <div class="m-icon" :style="{background: tpl.icon_background || '#EAF1FE'}">
              <img v-if="tpl.iconImg" :src="tpl.iconImg" class="tpl-icon-img" alt="" @error="$event.target.style.display='none'">
              <span v-else>{{ tpl.iconEmoji }}</span>
            </div>
            <div class="m-title-wrap">
              <div class="m-name">{{ tpl.name }}</div>
              <div class="m-meta">{{ tpl.display_category }} · {{ kindLabel(tpl.kind) }}</div>
            </div>
          </div>
          <div class="m-desc">{{ tpl.description || tpl.overview || '暂无描述' }}</div>
          <div class="m-tags">
            <span class="tag tag-cat" v-if="tpl.display_category">{{ tpl.display_category }}</span>
            <span class="tag" v-for="tag in (tpl.tags || []).slice(0,2)" :key="tag">{{ tag }}</span>
          </div>
        </div>
      </div>

      <div class="empty" id="tplEmpty" v-show="filteredTemplates.length === 0">
        <span v-html="EMPTY_SVG"></span>
        <div>暂无匹配的模板</div>
      </div>

      <div class="bottom-bar">
        <span>共 {{ filteredTemplates.length }} 项</span>
      </div>

    </div>
    <!-- 从模板创建应用程序弹窗 -->
    <div class="modal-mask" id="tplModal">
      <div class="modal">
        <div class="modal-head">
          <div class="modal-title" id="tplModalTitle">从模板创建应用程序</div>
          <button class="modal-close" @click="closeModal('tplModal')">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <div class="form-label">应用名称 &amp; 图标</div>
            <div class="tpl-name-row">
              <div class="tpl-ico" id="tplModalIco" :style="{background: selectedTpl?.icon_background || '#EAF1FE'}">
                <img v-if="selectedTpl?.iconImg" :src="selectedTpl.iconImg" class="tpl-icon-img" alt="" @error="$event.target.style.display='none'">
                <span v-else>{{ selectedTpl?.iconEmoji || '🤖' }}</span>
              </div>
              <input class="tpl-name-input" id="tplAppName" v-model="form.name" @keydown.enter="createFromTpl">
            </div>
          </div>
          <div class="form-item" style="margin-bottom:0;">
            <div class="form-label">描述</div>
            <textarea class="form-textarea" id="tplAppDesc" v-model="form.description" placeholder="输入应用的描述" style="background:#F7F8FA;border:none;min-height:100px;"></textarea>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="closeModal('tplModal')">取消</button>
          <button class="btn btn-primary" :disabled="creating" @click="createFromTpl">
            {{ creating ? '创建中...' : '创建' }} <span class="kbd-hint">Ctrl ⏎</span>
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
<script setup>
import { ref, computed, onMounted, onDeactivated } from 'vue'
import AppShell from '../components/AppShell.vue'
import { toast, openModal, closeModal, getLoginUser, EMPTY_SVG } from '../utils/global'
import { apiGet, apiPost } from '../api/client'

const templates = ref([])
const categories = ref([])
const searchQuery = ref('')
const creating = ref(false)
const curCat = ref('all')
const selectedTpl = ref(null)
const form = ref({ name: '', description: '' })

const EMOJI_MAP = {
  robot_face: '🤖', robot: '🤖', ai: '🤖',
  earth_asia: '🌏', globe_showing_americas: '🌎', globe_showing_europe_africa: '🌍', globe: '🌍', earth: '🌍', world: '🌍',
  technologist: '🧑‍💻', developer: '👩‍💻', computer: '💻', laptop: '💻', desktop_computer: '🖥️',
  bookmark_tabs: '📑', bookmark: '🔖', label: '🏷️',
  memo: '📝', notebook: '📓', notes: '📝', spiral_notepad: '🗒️', page_facing_up: '📄', page_with_curl: '📃',
  speech_balloon: '💬', thought_balloon: '💭', left_speech_bubble: '🗨️',
  headset: '🎧', headphones: '🎧', earphone: '📞', telephone_receiver: '📞', telephone: '☎️', phone: '📱',
  books: '📚', book: '📖', open_book: '📖', closed_book: '📕', green_book: '📗', blue_book: '📘', orange_book: '📙',
  magnifying_glass: '🔍', magnifying_glass_tilted_left: '🔍', magnifying_glass_tilted_right: '🔎', search: '🔎',
  brain: '🧠', light_bulb: '💡', idea: '💡', sparkles: '✨', star: '⭐', glowing_star: '🌟', fire: '🔥', rocket: '🚀',
  chart_with_upwards_trend: '📈', chart_with_downwards_trend: '📉', chart: '📊', bar_chart: '📊', pie: '🥧',
  megaphone: '📣', loudspeaker: '📢', bullhorn: '📣', marketing: '📣',
  briefcase: '💼', office: '🏢', building: '🏢', calendar: '📅', date: '📅', clipboard: '📋', pushpin: '📌', paperclip: '📎',
  moneybag: '💰', money_with_wings: '💸', dollar: '💵', yen: '💴', euro: '💶', pound: '💷', coin: '🪙',
  handshake: '🤝', clinking_hands: '🙏', trophy: '🏆', medal: '🏅', target: '🎯', dart: '🎯',
  shopping_cart: '🛒', shopping_bags: '🛍️', store: '🏪', shop: '🏪',
  hammer: '🔨', wrench: '🔧', tools: '🛠️', gear: '⚙️', cog: '⚙️', nut_and_bolt: '🔩',
  paintbrush: '🖌️', artist_palette: '🎨', palette: '🎨', design: '🎨', pencil: '✏️', pen: '🖊️',
  lock: '🔒', key: '🔑', shield: '🛡️', bell: '🔔', envelope: '✉️', email: '📧', incoming_envelope: '📨',
  heart: '❤️', red_heart: '❤️', check_mark_button: '✅', check: '✅', cross_mark: '❌', x: '❌',
  question_mark: '❓', exclamation_mark: '❗', warning: '⚠️',
  sun: '☀️', sunny: '☀️', cloud: '☁️', umbrella: '☂️', snowflake: '❄️', rainbow: '🌈', moon: '🌙',
  camera: '📷', video_camera: '📹', movie_camera: '🎥', film: '🎬', tv: '📺', radio: '📻',
  musical_note: '🎵', music: '🎵', microphone: '🎤', speaker: '🔊',
  car: '🚗', taxi: '🚕', bus: '🚌', train: '🚆', airplane: '✈️', ship: '🚢',
  clock: '🕐', alarm_clock: '⏰', stopwatch: '⏱️', timer: '⏲️', hourglass: '⏳',
  package: '📦', box: '📦', gift: '🎁', balloon: '🎈', party_popper: '🎉', confetti: '🎊',
  puzzle_piece: '🧩', jigsaw: '🧩', maze: '🌀', link: '🔗', paperclip: '📎', chain: '⛓️',
  magic_wand: '🪄', crystal_ball: '🔮', telescope: '🔭', microscope: '🔬', satellite: '🛰️',
  fingerprint: '🫵', face_with_monocle: '🧐', nerd_face: '🤓', sunglasses: '😎',
  bug: '🐛', beetle: '🪲', ant: '🐜', honeybee: '🐝', butterfly: '🦋',
  leaf: '🍃', seedling: '🌱', tree: '🌳', flower: '🌸', rose: '🌹', sunflower: '🌻',
  pizza: '🍕', burger: '🍔', coffee: '☕', tea: '🍵', beer: '🍺', wine: '🍷',
  basketball: '🏀', football: '⚽', tennis: '🎾', baseball: '⚾', game: '🎮', controller: '🎮',
  hourglass_done: '⌛', infinity: '♾️', recycle: '♻️', white_check_mark: '✅', ballot_box: '☑️'
}

const KEYWORD_EMOJI = [
  ['weather', '☀️'], ['forecast', '🌤️'], ['rain', '🌧️'],
  ['deepresearch', '🔬'], ['research', '🔬'], ['pipeline', '🔧'],
  ['hugging', '📚'], ['translate', '🌐'], ['translation', '🌐'],
  ['ticket', '🎫'], ['support', '🎧'], ['customer', '🎧'], ['service', '🎧'],
  ['novel', '📖'], ['story', '📖'], ['write', '✍️'], ['writing', '✍️'],
  ['code', '💻'], ['program', '💻'], ['dev', '💻'], ['api', '🔌'],
  ['summar', '📝'], ['summary', '📝'], [' meeting', '📅'], ['email', '✉️'],
  ['market', '📈'], ['seo', '🔍'], ['ads', '📣'], ['ad', '📣'],
  ['sales', '💰'], ['lead', '🎯'], ['crm', '🤝'], ['deal', '🤝'],
  ['knowledge', '📚'], ['rag', '🔍'], ['retriev', '🔍'], ['qna', '❓'],
  ['agent', '🤖'], ['bot', '🤖'], ['chat', '💬'], ['workflow', '⚙️'],
  ['image', '🖼️'], ['pdf', '📄'], ['doc', '📄'], ['file', '📁']
]

function kindLabel(kind) {
  const map = {
    workflow: '工作流',
    'advanced-chat': '对话流',
    'agent-chat': 'Agent',
    chat: '对话',
    agent: 'Agent',
    completion: '文本补全',
    classic: '工作流'
  }
  return map[kind] || (kind || '工作流')
}

function fallbackEmoji(name) {
  const lower = (name || '').toLowerCase()
  for (const [k, v] of KEYWORD_EMOJI) {
    if (lower.includes(k)) return v
  }
  return '🤖'
}

function resolveIcon(t) {
  const raw = (t.icon || '').trim()
  // 优先使用自定义图标图片
  if (t.icon_url) {
    return { img: t.icon_url, emoji: fallbackEmoji(t.name) }
  }
  // 若 icon 是 UUID（无 icon_file_key），按名称回退 emoji
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(raw)) {
    return { img: '', emoji: fallbackEmoji(t.name) }
  }
  // 短代码映射
  if (raw && EMOJI_MAP[raw.toLowerCase()]) {
    return { img: '', emoji: EMOJI_MAP[raw.toLowerCase()] }
  }
  // 本身就是 emoji
  if (raw && /\p{Emoji}/u.test(raw) && !/^[a-z0-9_\-]+$/i.test(raw)) {
    return { img: '', emoji: raw }
  }
  return { img: '', emoji: fallbackEmoji(t.name) }
}

function normalizeTemplate(t) {
  const icon = resolveIcon(t)
  return {
    ...t,
    tags: t.tags || t.categories || [],
    iconImg: icon.img,
    iconEmoji: icon.emoji,
    icon_background: t.icon_background || '#EAF1FE'
  }
}

const filteredTemplates = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const cat = curCat.value
  return templates.value.filter(t => {
    const okCat = cat === 'all' || (t.display_category || '') === cat
    const text = [t.name, t.description, t.overview, t.display_category, (t.categories || []).join(' '), (t.tags || []).join(' ')].join(' ').toLowerCase()
    const okQ = !q || text.includes(q)
    return okCat && okQ
  })
})

async function loadTemplates() {
  try {
    const res = await apiGet('/api/app-templates')
    templates.value = (res.data || []).map(normalizeTemplate)
  } catch (e) {
    toast('加载模板失败')
  }
}

async function loadCategories() {
  try {
    const res = await apiGet('/api/app-templates/categories')
    categories.value = res.data || []
  } catch (e) {}
}

async function syncTemplates() {
  toast('正在同步模板...')
  try {
    const res = await apiPost('/api/app-templates/sync', {})
    toast('同步完成：' + (res.data && res.data.success || 0) + ' 个模板')
    await loadTemplates()
    await loadCategories()
  } catch (e) {
    toast('同步失败')
  }
}

function openTplModal(tpl) {
  selectedTpl.value = tpl
  form.value.name = tpl.name
  form.value.description = tpl.description || ''
  openModal('tplModal')
}

async function createFromTpl() {
  if (!selectedTpl.value) return
  if (creating.value) return
  const name = form.value.name.trim() || selectedTpl.value.name
  const description = form.value.description.trim() || selectedTpl.value.description || ''
  const loginUser = getLoginUser()
  const uid = loginUser ? (loginUser.account_id || loginUser.id || '') : ''
  creating.value = true
  try {
    const res = await apiPost('/api/app-templates/' + encodeURIComponent(selectedTpl.value.id) + '/create', { name, description }, { params: { uid } })
    if (res.data && res.data.id) {
      closeModal('tplModal')
      toast('创建成功')
      location.hash = '/workflow-studio?id=' + encodeURIComponent(res.data.id) + '&mode=' + encodeURIComponent(res.data.mode || 'workflow')
    } else {
      toast(res.msg || '创建失败')
    }
  } catch (e) {
    toast('创建失败：' + (e.message || '无法连接到后端，请确认服务已启动'))
  } finally {
    creating.value = false
  }
}

onMounted(function(){
  loadTemplates()
  loadCategories()

  function onRootClick(e){
    var el = e.target && e.target.closest ? e.target.closest('[data-action]') : null;
    if (!el) return;
    var code = el.getAttribute('data-action');
    if (!code) return;
    try { eval(code.replace(/\bthis\b/g, 'el')); } catch(err){ console.error('[page action]', err); }
  }
  var root = document.querySelector('#page-root');
  if (root) root.addEventListener('click', onRootClick);

  /* 分类切换 */
  var pillScroll = document.getElementById('pillScroll');
  var onPillClick = function(e){
    var p = e.target.closest && e.target.closest('.pill');
    if (!p) return;
    pillScroll.querySelectorAll('.pill').forEach(function(x){ x.classList.remove('active'); });
    p.classList.add('active');
    curCat.value = p.dataset.cat || 'all';
  };
  if (pillScroll) pillScroll.addEventListener('click', onPillClick);

  var onKeydown = function(e){
    var mask = document.getElementById('tplModal');
    if (e.key === 'Escape' && mask && mask.classList.contains('show')) closeModal('tplModal');
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && mask && mask.classList.contains('show')) createFromTpl();
  };
  document.addEventListener('keydown', onKeydown);

  /* 清理事件监听器，防止内存泄漏（keep-alive 场景下用 onDeactivated） */
  onDeactivated(function(){
    if (root) root.removeEventListener('click', onRootClick);
    if (pillScroll) pillScroll.removeEventListener('click', onPillClick);
    document.removeEventListener('keydown', onKeydown);
  });
})
</script>
<style>
.filter-row{display:flex;align-items:center;gap:10px;margin:14px 0 6px;}
  .pills-clip{flex:1;min-width:0;overflow:hidden;}
  .pills-scroll{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px;}
  .pills-scroll::-webkit-scrollbar{display:none;}
  .pills-scroll .pill{flex-shrink:0;border:none;background:#F2F3F5;color:var(--text-2);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;transition:all .15s;}
  .pills-scroll .pill:hover{background:#E5E6EB;color:var(--text-1);}
  .pills-scroll .pill.active{background:var(--primary);color:#fff;}
  .ico-btn{border:1px solid var(--border);background:#fff;border-radius:8px;width:32px;height:32px;display:inline-flex;align-items:center;justify-content:center;color:var(--text-2);font-size:15px;cursor:pointer;flex-shrink:0;transition:all .15s;}
  .ico-btn:hover{color:var(--primary);border-color:var(--primary);}
  .bottom-bar{display:flex;align-items:center;padding:18px 4px;font-size:13px;color:var(--text-2);}
  /* 卡片风格 */
  .mcard{background:#fff;border-radius:12px;padding:16px;border:1px solid var(--border-light);transition:all .18s;cursor:pointer;position:relative;display:flex;flex-direction:column;}
  .mcard:hover{box-shadow:0 6px 24px rgba(29,33,41,.10);transform:translateY(-1px);border-color:rgba(46,99,240,.18);}
  .mcard .m-head{display:flex;align-items:flex-start;gap:12px;}
  .mcard .m-icon{width:48px;height:48px;border-radius:10px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:26px;background:#F2F3F5;overflow:hidden;}
  .mcard .m-title-wrap{min-width:0;flex:1;padding-top:2px;}
  .mcard .m-name{font-size:15px;font-weight:600;color:var(--text-1);line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .mcard .m-meta{font-size:12px;color:var(--text-3);margin-top:4px;}
  .mcard .m-desc{color:var(--text-2);font-size:13px;line-height:1.7;margin:12px 0 10px;flex:1;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:44px;}
  .mcard .m-tags{display:flex;gap:6px;flex-wrap:wrap;}
  .tag-cat{background:rgba(46,99,240,.1);color:var(--primary);}
  .tpl-icon-img{width:100%;height:100%;object-fit:cover;}
  /* 从模板创建应用弹窗 */
  #tplModal .modal-foot{justify-content:flex-end;}
  .tpl-name-row{display:flex;gap:14px;align-items:stretch;}
  .tpl-ico{width:56px;height:56px;border-radius:10px;background:#F2F3F5;display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0;overflow:hidden;}
  .tpl-ico img{width:100%;height:100%;object-fit:cover;}
  .tpl-name-input{flex:1;background:#F7F8FA;border:none;border-radius:8px;padding:0 14px;font-size:14px;color:var(--text-1);outline:none;}
  .tpl-name-input:focus{box-shadow:0 0 0 2px rgba(46,99,240,.15);}
  .kbd-hint{font-size:11px;opacity:.75;background:rgba(255,255,255,.22);border-radius:4px;padding:1px 6px;margin-left:2px;}
  /* 应用模板页一行三列 */
  .grid-cards{ grid-template-columns:repeat(3,1fr) !important; }
</style>

<template>
  <Teleport to="body">
    <div class="search-mask" @click.self="$emit('close')">
      <div class="search-modal">
        <!-- 搜索输入框 -->
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            ref="inputRef"
            v-model="query"
            class="search-input"
            placeholder="搜索页面、功能、智能体..."
            @input="handleInput"
            @keydown="handleKeydown"
          />
          <span class="search-shortcut">ESC</span>
        </div>

        <!-- 搜索结果 -->
        <div class="search-results" v-if="query.length > 0">
          <div v-if="filteredItems.length === 0" class="search-empty">
            未找到匹配结果
          </div>
          <div
            v-for="(item, idx) in filteredItems"
            :key="item.key"
            class="search-item"
            :class="{ 'search-item--active': idx === activeIndex }"
            @click="goTo(item)"
            @mouseenter="activeIndex = idx"
          >
            <span class="search-item__icon" v-html="ICONS[item.icon] || ICONS.grid"></span>
            <div class="search-item__content">
              <div class="search-item__label">{{ item.label }}</div>
              <div class="search-item__group">{{ item.group }}</div>
            </div>
            <span class="search-item__shortcut">↵</span>
          </div>
        </div>

        <!-- 快捷导航（无输入时显示） -->
        <div class="search-quick" v-else>
          <div class="search-quick__title">快捷导航</div>
          <div
            v-for="(item, idx) in quickItems"
            :key="item.key"
            class="search-item"
            :class="{ 'search-item--active': idx === activeIndex }"
            @click="goTo(item)"
            @mouseenter="activeIndex = idx"
          >
            <span class="search-item__icon" v-html="ICONS[item.icon] || ICONS.grid"></span>
            <div class="search-item__content">
              <div class="search-item__label">{{ item.label }}</div>
              <div class="search-item__group">{{ item.group }}</div>
            </div>
          </div>
        </div>

        <!-- 底部提示 -->
        <div class="search-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> 导航</span>
          <span><kbd>↵</kbd> 跳转</span>
          <span><kbd>ESC</kbd> 关闭</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { NAV, ICONS } from '../utils/global'

const emit = defineEmits(['close'])
const router = useRouter()

const query = ref('')
const inputRef = ref(null)
const activeIndex = ref(0)

// 将所有导航项扁平化
const allItems = computed(() => {
  const items = []
  for (const group of NAV) {
    for (const item of group.items) {
      items.push({
        ...item,
        group: group.group,
      })
    }
  }
  return items
})

// 快捷导航（常用功能）
const quickItems = computed(() => {
  const quickKeys = ['home', 'my-agents', 'single-agent', 'workflow-app', 'knowledge', 'models']
  return allItems.value.filter(item => quickKeys.includes(item.key)).slice(0, 6)
})

// 搜索结果
const filteredItems = computed(() => {
  if (!query.value.trim()) return []
  const q = query.value.toLowerCase().trim()
  return allItems.value.filter(item => {
    return item.label.toLowerCase().includes(q) ||
           item.group.toLowerCase().includes(q) ||
           item.key.toLowerCase().includes(q)
  }).slice(0, 10)
})

function goTo(item) {
  emit('close')
  router.push(item.href)
}

function handleInput() {
  activeIndex.value = 0
}

function handleKeydown(e) {
  const list = query.value.length > 0 ? filteredItems.value : quickItems.value

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, list.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (list[activeIndex.value]) {
      goTo(list[activeIndex.value])
    }
  } else if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  nextTick(() => {
    inputRef.value?.focus()
  })
})
</script>

<style scoped>
.search-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: 1500;
}

.search-modal {
  width: 560px;
  max-width: 90vw;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  gap: 10px;
}

.search-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  color: var(--text-1);
}
.search-input::placeholder {
  color: var(--text-4);
}

.search-shortcut {
  font-size: 11px;
  color: var(--text-4);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
}

.search-results,
.search-quick {
  max-height: 360px;
  overflow-y: auto;
  padding: 8px 0;
}

.search-quick__title {
  font-size: 12px;
  color: var(--text-3);
  padding: 8px 16px 4px;
  font-weight: 500;
}

.search-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-3);
  font-size: 14px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s;
}
.search-item:hover,
.search-item--active {
  background: var(--primary-light);
}

.search-item__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--text-3);
}
.search-item__icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.search-item__content {
  flex: 1;
  min-width: 0;
}
.search-item__label {
  font-size: 14px;
  color: var(--text-1);
}
.search-item__group {
  font-size: 12px;
  color: var(--text-3);
}

.search-item__shortcut {
  font-size: 12px;
  color: var(--text-4);
  opacity: 0;
  transition: opacity 0.1s;
}
.search-item--active .search-item__shortcut {
  opacity: 1;
}

.search-footer {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  border-top: 1px solid var(--border-light);
  font-size: 11px;
  color: var(--text-4);
}
.search-footer kbd {
  display: inline-block;
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 4px;
  font-family: inherit;
  font-size: 10px;
  margin: 0 2px;
}
</style>

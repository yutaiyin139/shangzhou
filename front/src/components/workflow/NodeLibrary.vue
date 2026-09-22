<template>
  <div class="node-library">
    <div class="nl-search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input v-model="query" placeholder="搜索节点">
    </div>
    <div class="nl-cats">
      <div v-for="cat in filteredCategories" :key="cat.key" class="nl-cat">
        <div class="nl-cat-title" @click="toggleCat(cat.key)">
          <span>{{ cat.label }}</span>
          <span class="nl-cat-arr" :class="{ open: openCats[cat.key] !== false }">▾</span>
        </div>
        <div v-show="openCats[cat.key] !== false" class="nl-nodes">
          <div
            v-for="node in cat.nodes"
            :key="node.type"
            class="nl-node"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
          >
            <span class="nl-node-ico" :style="{ background: node.color }">{{ node.icon }}</span>
            <span class="nl-node-name">{{ node.title }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { nodeCategoriesList } from '../../utils/workflow/nodeRegistry'

const query = ref('')
const openCats = ref({})

const categories = computed(() => nodeCategoriesList())

const filteredCategories = computed(() => {
  const q = query.value.trim().toLowerCase()
  return categories.value.map(cat => ({
    ...cat,
    nodes: q ? cat.nodes.filter(n => n.title.toLowerCase().includes(q) || n.type.toLowerCase().includes(q)) : cat.nodes
  })).filter(cat => cat.nodes.length > 0)
})

function toggleCat(key) {
  openCats.value = { ...openCats.value, [key]: !openCats.value[key] }
}

function onDragStart(event, type) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/wf-node-type', type)
    event.dataTransfer.effectAllowed = 'move'
  }
}
</script>

<style scoped>
.node-library{ width: 240px; background: #F7F8FA; border-right: 1px solid var(--border-light); display: flex; flex-direction: column; flex-shrink: 0; height: 100%; }
.nl-search{ display: flex; align-items: center; gap: 8px; padding: 12px; border-bottom: 1px solid var(--border-light); }
.nl-search svg{ width: 16px; height: 16px; color: var(--text-3); flex-shrink: 0; }
.nl-search input{ border: none; background: transparent; flex: 1; font-size: 13px; outline: none; }
.nl-cats{ flex: 1; overflow-y: auto; padding: 8px; }
.nl-cat{ margin-bottom: 6px; }
.nl-cat-title{ display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; font-size: 13px; font-weight: 600; color: var(--text-2); cursor: pointer; border-radius: 6px; }
.nl-cat-title:hover{ background: #ECEEF1; }
.nl-cat-arr{ font-size: 11px; transition: transform .15s; }
.nl-cat-arr.open{ transform: rotate(180deg); }
.nl-nodes{ display: flex; flex-direction: column; gap: 2px; }
.nl-node{ display: flex; align-items: center; gap: 8px; padding: 7px 8px; border-radius: 6px; cursor: grab; font-size: 13px; color: var(--text-1); }
.nl-node:hover{ background: #ECEEF1; }
.nl-node-ico{ width: 22px; height: 22px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #fff; flex-shrink: 0; }
.nl-node-name{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>

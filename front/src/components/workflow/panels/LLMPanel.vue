<template>
  <div>
    <div class="pp-field">
      <label>模型</label>
      <div class="pp-model-row">
        <select v-model="modelKey" @change="commitModel" class="pp-model-select">
          <option value="">请选择模型</option>
          <option v-for="o in modelChoices" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
        <button class="mp-btn mp-btn-outline mp-btn-sm" @click="showModelModal = true" title="配置模型供应商">
          ⚙️ 配置
        </button>
      </div>
      <div v-if="modelChoices.length === 0" class="pp-hint">暂无可用模型，请点击「配置」按钮添加模型供应商。</div>
    </div>
    <!-- 模型配置模态窗口 -->
    <ModelProviderModal :visible="showModelModal" @close="showModelModal = false; refreshModels()" />
    <div class="pp-field">
      <label>Temperature</label>
      <input type="range" min="0" max="1" step="0.1" v-model.number="temperature" @change="commit">
      <span class="pp-range-val">{{ temperature }}</span>
    </div>
    <div class="pp-field">
      <label>System Prompt</label>
      <textarea v-model="systemPrompt" rows="4" @change="commitPrompt"></textarea>
    </div>
    <div class="pp-field">
      <label>User Prompt</label>
      <textarea v-model="userPrompt" rows="4" @change="commitPrompt"></textarea>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePanelState } from './usePanelState'
import ModelProviderModal from '../../ModelProviderModal.vue'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const {
  local, commit, models, modelKey, modelChoices, temperature, systemPrompt, userPrompt,
  commitModel, commitPrompt, loadAllOptions: refreshModels,
} = usePanelState(props, emit)

const showModelModal = ref(false)
</script>

<style scoped>
.pp-model-row { display: flex; gap: 8px; align-items: center; }
.pp-model-select { flex: 1; }
</style>

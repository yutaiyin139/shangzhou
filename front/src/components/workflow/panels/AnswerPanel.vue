<template>
  <div>
    <div class="pp-field">
      <label>回复内容</label>
      <textarea v-model="local.answer" rows="6" @change="commit"></textarea>
    </div>
  </div>
</template>

<script setup>
import { usePanelState } from './usePanelState'

const props = defineProps({ node: { type: Object, default: null } })
const emit = defineEmits(['update'])

const { local, commit } = usePanelState(props, emit)
</script>

<template>
  <router-view v-slot="{ Component }">
    <keep-alive>
      <component :is="Component" />
    </keep-alive>
  </router-view>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'

// 初始化应用级状态
const appStore = useAppStore()

onMounted(() => {
  // 初始化主题
  appStore.initTheme()
})
</script>

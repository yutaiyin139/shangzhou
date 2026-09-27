<template>
  <router-view v-slot="{ Component, route }">
    <keep-alive :max="10">
      <component :is="Component" :key="route.fullPath" />
    </keep-alive>
  </router-view>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'

/* <component> 上的 :key="route.fullPath" 不能删，且注释不能写进 <keep-alive> 内部
   （Vue 要求 <KeepAlive> 恰好只有一个子节点，HTML 注释也算一个，会导致整个应用编译失败）。
   原因：多个详情页在 setup/onMounted 里一次性读 location.hash 的参数（技能详情 ?key=、
   智能体详情/配置/对话 ?id= 等），若只按组件名缓存，第二次带不同参数进来会复用旧实例，
   页面仍显示上一个资源的内容（Skills 广场点开任何技能都显示“网页摘要”就是这个原因）。

   :max="10" 是给这个修复兼容的上限：key 改成 fullPath 后，“每个看过的不同 URL”都会占
   一个缓存实例（以前同组件只占一个），而 keep-alive 里的实例永不卸载。工作流工作室、
   智能体配置这类带图/带长列表的页面很重，连开十几个应用就会只涨不降。超出后 Vue 会
   淘汰最早的那个（它下次挂载会重新拉数据，行为与以前无缓存时一致）。注意：任何
   注释都不能写进 <keep-alive> 内部，那会被当成第二个子节点而让整个应用编译失败。 */

// 初始化应用级状态
const appStore = useAppStore()

onMounted(() => {
  // 初始化主题
  appStore.initTheme()
})
</script>

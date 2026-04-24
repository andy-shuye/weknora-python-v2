<script setup lang="ts">
import { useTweaksStore } from '../stores/tweaks'

const tweaks = useTweaksStore()
</script>

<template>
  <aside class="panel">
    <div class="title">UI Tweaks</div>
    <el-button size="small" @click="tweaks.setEditMode(false)">关闭</el-button>
  </aside>
</template>

<style scoped>
.panel {
  width: 220px;
  border-left: 1px solid var(--border);
  padding: 12px;
  background: #fff;
}
.title {
  font-weight: 600;
  margin-bottom: 12px;
}
</style>

<script setup lang="ts">
defineProps<{
  num: number
  title: string
  source: string
  excerpt: string
  page?: string
}>()
</script>

<template>
  <div class="citation">
    <span class="num">{{ num }}</span>
    <div class="body">
      <div class="head">
        <el-icon><Document /></el-icon>
        <span class="title">{{ title }}</span>
        <span v-if="page" class="page">§{{ page }}</span>
      </div>
      <div class="excerpt">{{ excerpt }}</div>
      <div class="source">{{ source }}</div>
    </div>
  </div>
</template>

<style scoped>
.citation {
  display: flex; gap: 10px;
  padding: 10px 12px;
  background: var(--ink-50);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 12.5px;
}
.num {
  width: 22px; height: 22px; border-radius: 6px;
  background: var(--accent-soft); color: var(--accent-ink);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  flex-shrink: 0;
}
.body { flex: 1; min-width: 0; }
.head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.title { font-weight: 500; color: var(--ink-800); }
.page { font-family: var(--font-mono); font-size: 10px; color: var(--ink-400); }
.excerpt { color: var(--ink-600); line-height: 1.6; }
.source { margin-top: 6px; font-size: 11px; color: var(--ink-500); font-family: var(--font-mono); }
</style>

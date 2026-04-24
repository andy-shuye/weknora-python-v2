<script setup lang="ts">
defineProps<{ num: number }>()
</script>

<template>
  <sup class="inline-cite">{{ num }}</sup>
</template>

<style scoped>
.inline-cite {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 16px; height: 16px; padding: 0 4px;
  margin: 0 2px;
  background: var(--accent-soft); color: var(--accent-ink);
  border-radius: 4px;
  font-family: var(--font-mono); font-size: 9px; font-weight: 600;
  cursor: pointer; vertical-align: top; line-height: 16px;
}
</style>

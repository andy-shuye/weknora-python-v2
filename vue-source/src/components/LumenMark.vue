<script setup lang="ts">
defineProps<{ size?: number }>()
</script>

<template>
  <svg :width="size || 28" :height="size || 28" viewBox="0 0 32 32" fill="none">
    <circle cx="12" cy="16" r="8" stroke="currentColor" stroke-width="1.6"/>
    <rect x="16" y="8" width="12" height="12" rx="2" fill="currentColor"/>
    <circle cx="22" cy="14" r="2" fill="var(--paper)"/>
  </svg>
</template>

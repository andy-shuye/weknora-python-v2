<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import { useTweaksStore } from './stores/tweaks'
import LoginView from './views/LoginView.vue'
import AppSidebar from './components/AppSidebar.vue'
import TweaksPanel from './components/TweaksPanel.vue'

const auth = useAuthStore()
const tweaks = useTweaksStore()
const authed = computed(() => auth.isAuthed)
</script>

<template>
  <LoginView v-if="!authed" />
  <div v-else class="app-shell">
    <AppSidebar />
    <main class="app-main">
      <router-view />
    </main>
    <TweaksPanel v-if="tweaks.editMode" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--paper);
}
.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from './stores/auth'
import { useTweaksStore } from './stores/tweaks'
import LoginView from './views/LoginView.vue'
import AppSidebar from './components/AppSidebar.vue'
import TweaksPanel from './components/TweaksPanel.vue'

const auth = useAuthStore()
const tweaks = useTweaksStore()
const authed = computed(() => auth.isAuthed)
const sessionLoading = ref(true)

onMounted(async () => {
  await auth.restoreSession()
  sessionLoading.value = false
})
</script>

<template>
  <div v-if="sessionLoading" class="loading">Loading...</div>
  <LoginView v-else-if="!authed" />
  <div v-else class="app-shell">
    <AppSidebar />
    <main class="app-main">
      <router-view />
    </main>
    <TweaksPanel v-if="tweaks.editMode" />
  </div>
</template>

<style scoped>
.loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-500);
}
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

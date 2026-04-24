import { defineStore } from 'pinia'

export const useTweaksStore = defineStore('tweaks', {
  state: () => ({
    sidebarCollapsed: false,
    chatDensity: 'comfortable' as 'comfortable' | 'dense',
    showCitations: true,
    editMode: false,
  }),
  actions: {
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed },
    setDensity(d: 'comfortable' | 'dense') { this.chatDensity = d },
    toggleCitations() { this.showCitations = !this.showCitations },
    setEditMode(v: boolean) { this.editMode = v },
  },
  persist: true,
})

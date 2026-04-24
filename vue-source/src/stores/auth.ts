import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    isAuthed: false,
    user: null as null | { name: string; email: string; avatar?: string },
  }),
  actions: {
    async login(email: string, _password: string) {
      // TODO: call /auth/login endpoint
      this.isAuthed = true
      this.user = { name: 'Lena Tanaka', email }
    },
    logout() {
      this.isAuthed = false
      this.user = null
    },
  },
})

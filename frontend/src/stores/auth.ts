import { defineStore } from 'pinia'

export type AuthProvider = 'local' | 'ldap' | 'auto'

export type LoginUser = {
  id: number
  login_name: string
  full_name: string
  email: string
  role_level: 'user' | 'dept_admin' | 'super_admin'
  department_id: number | null
  department_name: string | null
}

type LoginOptions = {
  default_provider: AuthProvider
  available_providers: AuthProvider[]
  ldap_enabled: boolean
  allow_local_fallback: boolean
}

const TOKEN_KEY = 'weknora_token'
const USER_KEY = 'weknora_user'
const LOGIN_PROVIDER_KEY = 'weknora_login_provider'

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  const result = await response.json().catch(() => ({}))
  if (!response.ok || result?.success === false) {
    throw new Error(result?.message || `Request failed with ${response.status}`)
  }
  return result
}

function normalizeProvider(raw: string): AuthProvider {
  if (raw === 'ldap' || raw === 'auto') return raw
  return 'local'
}

export const useAuthStore = defineStore('auth', {
  state: () => {
    const token = localStorage.getItem(TOKEN_KEY)
    const userRaw = localStorage.getItem(USER_KEY)
    const user = userRaw ? JSON.parse(userRaw) : null
    const storedProvider = normalizeProvider(localStorage.getItem(LOGIN_PROVIDER_KEY) || 'local')

    return {
      token,
      isAuthed: Boolean(token),
      user: user as null | { id: number; name: string; email: string; roleLevel: string; loginName: string },
      loginOptions: {
        default_provider: 'local' as AuthProvider,
        available_providers: ['local'] as AuthProvider[],
        ldap_enabled: false,
        allow_local_fallback: true,
      },
      selectedLoginProvider: storedProvider as AuthProvider,
    }
  },
  actions: {
    async fetchLoginOptions() {
      try {
        const res = await request('/api/auth/login-options', { method: 'GET' })
        const options = (res.data || {}) as Partial<LoginOptions>
        const providers = (options.available_providers || ['local']).filter((item) =>
          ['local', 'ldap', 'auto'].includes(item),
        ) as AuthProvider[]

        this.loginOptions = {
          default_provider: normalizeProvider(options.default_provider || 'local'),
          available_providers: providers.length ? providers : ['local'],
          ldap_enabled: Boolean(options.ldap_enabled),
          allow_local_fallback: Boolean(options.allow_local_fallback),
        }

        if (!this.loginOptions.available_providers.includes(this.selectedLoginProvider)) {
          this.selectedLoginProvider = this.loginOptions.default_provider
          localStorage.setItem(LOGIN_PROVIDER_KEY, this.selectedLoginProvider)
        }
      } catch {
        this.loginOptions = {
          default_provider: 'local',
          available_providers: ['local'],
          ldap_enabled: false,
          allow_local_fallback: true,
        }
        this.selectedLoginProvider = 'local'
      }
    },

    setSelectedLoginProvider(provider: AuthProvider) {
      this.selectedLoginProvider = provider
      localStorage.setItem(LOGIN_PROVIDER_KEY, provider)
    },

    async login(account: string, password: string, authProvider?: AuthProvider) {
      const provider = authProvider || this.selectedLoginProvider || this.loginOptions.default_provider
      const res = await request('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ account, password, auth_provider: provider }),
      })

      const payloadUser = res.data.user as LoginUser
      const token = res.data.token as string
      const providerUsed = normalizeProvider((res.data.auth_provider || provider) as string)

      this.token = token
      this.isAuthed = true
      this.user = {
        id: payloadUser.id,
        name: payloadUser.full_name,
        email: payloadUser.email,
        roleLevel: payloadUser.role_level,
        loginName: payloadUser.login_name,
      }

      this.selectedLoginProvider = providerUsed
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      localStorage.setItem(LOGIN_PROVIDER_KEY, providerUsed)

      return {
        authProvider: providerUsed,
        fallbackUsed: Boolean(res.data.fallback_used),
      }
    },

    async restoreSession() {
      const token = localStorage.getItem(TOKEN_KEY)
      if (!token) {
        this.isAuthed = false
        this.user = null
        this.token = null
        return
      }

      try {
        const res = await request('/api/auth/me', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        const me = res.data as LoginUser
        this.token = token
        this.isAuthed = true
        this.user = {
          id: me.id,
          name: me.full_name,
          email: me.email,
          roleLevel: me.role_level,
          loginName: me.login_name,
        }
        localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      } catch {
        this.logout()
      }
    },

    logout() {
      this.isAuthed = false
      this.user = null
      this.token = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})

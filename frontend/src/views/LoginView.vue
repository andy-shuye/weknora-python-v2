<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore, type AuthProvider } from '../stores/auth'
import LumenMark from '../components/LumenMark.vue'

const auth = useAuthStore()
const loading = ref(false)
const loadingOptions = ref(false)
const form = reactive({ account: 'admin', password: '' })

const selectedProvider = computed<AuthProvider>({
  get: () => auth.selectedLoginProvider,
  set: (value) => auth.setSelectedLoginProvider(value),
})

const providerLabelMap: Record<AuthProvider, string> = {
  local: '本地账号',
  ldap: 'LDAP/域账号',
  auto: '自动（优先域账号）',
}

const footText = computed(() => {
  if (!auth.loginOptions.ldap_enabled) return '当前环境仅启用本地账号登录'
  if (auth.loginOptions.allow_local_fallback) return '当前环境支持 LDAP/域账号，并可回退本地登录'
  return '当前环境已启用 LDAP/域账号登录'
})

const onSubmit = async () => {
  if (!form.account || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  loading.value = true
  try {
    const result = await auth.login(form.account, form.password, selectedProvider.value)
    if (result.fallbackUsed) {
      ElMessage.success(`登录成功（实际使用 ${providerLabelMap[result.authProvider]}）`)
    } else {
      ElMessage.success('登录成功')
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  loadingOptions.value = true
  try {
    await auth.fetchLoginOptions()
  } finally {
    loadingOptions.value = false
  }
})
</script>

<template>
  <div class="login">
    <section class="hero">
      <div class="brand">
        <LumenMark :size="30" />
        <div>
          <div class="name">Lumen AI</div>
          <div class="sub">Knowledge Retrieval</div>
        </div>
      </div>
      <div class="geo">
        <svg viewBox="0 0 420 420" width="420" height="420">
          <circle cx="210" cy="210" r="180" fill="none" stroke="var(--accent)" stroke-width="1.2" stroke-dasharray="3 6" />
          <circle cx="210" cy="210" r="130" fill="none" stroke="rgba(20,22,28,0.12)" />
          <circle cx="210" cy="30" r="5" fill="var(--accent)" />
          <circle cx="390" cy="210" r="4" fill="var(--coral)" />
        </svg>
      </div>
    </section>

    <section class="panel">
      <el-form @submit.prevent="onSubmit" label-position="top" v-loading="loadingOptions">
        <h1>欢迎回来</h1>
        <p class="intro">登录以继续使用企业级文档检索与智能问答平台</p>

        <el-form-item label="登录方式">
          <el-radio-group v-model="selectedProvider">
            <el-radio-button v-for="provider in auth.loginOptions.available_providers" :key="provider" :label="provider">
              {{ providerLabelMap[provider] }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="账号" required>
          <el-input v-model="form.account" placeholder="请输入登录账号">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-button :loading="loading" type="primary" native-type="submit" size="large" class="w-full">登录</el-button>
        <div class="foot">{{ footText }}</div>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.login { min-height: 100vh; display: flex; background: var(--paper); }
.hero { flex: 1 1 55%; background: linear-gradient(135deg, #f8f7f3, #eeece5); position: relative; }
.brand { position: absolute; top: 40px; left: 48px; display: flex; align-items: center; gap: 12px; }
.brand .name { font-size: 20px; font-weight: 700; }
.brand .sub { font-size: 11px; color: var(--ink-500); font-family: var(--font-mono); }
.geo { height: 100%; display: flex; align-items: center; justify-content: center; }
.panel { flex: 1 1 45%; display: flex; flex-direction: column; justify-content: center; padding: 40px 64px; }
.panel h1 { font-size: 42px; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 12px; }
.panel .intro { color: var(--ink-500); margin: 0 0 24px; }
.w-full { width: 100%; }
.foot { text-align: center; margin-top: 16px; font-size: 13px; color: var(--ink-500); }
</style>

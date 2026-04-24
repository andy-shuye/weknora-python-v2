<script setup lang="ts">
// See the HTML prototype (Lumen AI.html) for the full interactive spec.
// This is a concise Vue version showing the Element Plus form pattern.
import { reactive } from 'vue'
import { useAuthStore } from '../stores/auth'
import LumenMark from '../components/LumenMark.vue'

const auth = useAuthStore()
const form = reactive({ email: 'demo@lumen.ai', password: '' })
const onSubmit = () => auth.login(form.email, form.password)
</script>

<template>
  <div class="login">
    <section class="hero">
      <div class="brand">
        <LumenMark :size="30"/>
        <div>
          <div class="name">Lumen AI</div>
          <div class="sub">Knowledge Retrieval</div>
        </div>
      </div>
      <!-- Abstract geometric composition -->
      <div class="geo">
        <svg viewBox="0 0 420 420" width="420" height="420">
          <circle cx="210" cy="210" r="180" fill="none" stroke="var(--accent)" stroke-width="1.2" stroke-dasharray="3 6"/>
          <circle cx="210" cy="210" r="130" fill="none" stroke="rgba(20,22,28,0.12)"/>
          <circle cx="210" cy="30" r="5" fill="var(--accent)"/>
          <circle cx="390" cy="210" r="4" fill="var(--coral)"/>
        </svg>
      </div>
    </section>

    <section class="panel">
      <el-form @submit.prevent="onSubmit" label-position="top">
        <h1>欢迎回来</h1>
        <p class="intro">登录以继续使用企业级文档检索与智能问答平台</p>

        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" placeholder="you@company.com">
            <template #prefix><el-icon><Message/></el-icon></template>
          </el-input>
        </el-form-item>

        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="8-32 位, 包含字母和数字">
            <template #prefix><el-icon><Lock/></el-icon></template>
          </el-input>
        </el-form-item>

        <el-button type="primary" native-type="submit" size="large" class="w-full">登录</el-button>
        <div class="foot">还没有账户? <a>立即注册</a></div>
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
.panel .intro { color: var(--ink-500); margin: 0 0 32px; }
.w-full { width: 100%; }
.foot { text-align: center; margin-top: 16px; font-size: 13px; color: var(--ink-500); }
.foot a { color: var(--accent-ink); font-weight: 500; }
</style>

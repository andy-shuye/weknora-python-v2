<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTweaksStore } from '../stores/tweaks'
import { useAuthStore } from '../stores/auth'
import LumenMark from './LumenMark.vue'

const route = useRoute()
const router = useRouter()
const tweaks = useTweaksStore()
const auth = useAuthStore()

const nav = [
  { id: 'chat', label: '对话', icon: 'ChatDotRound', to: '/chat' },
  { id: 'kb', label: '知识库', icon: 'Collection', to: '/kb' },
  { id: 'search', label: '检索', icon: 'Search', to: '/search' },
  { id: 'agents', label: '智能体', icon: 'MagicStick', to: '/agents' },
  { id: 'spaces', label: '共享空间', icon: 'Connection', to: '/spaces' },
  { id: 'settings', label: '设置', icon: 'Setting', to: '/settings' },
]

const chats = ref([
  { id: 'c1', title: 'API 文档问答会话', active: true },
  { id: 'c2', title: 'SSE 流式响应调试' },
  { id: 'c3', title: '合同条款对比分析' },
  { id: 'c4', title: '产品需求澄清' },
])
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: tweaks.sidebarCollapsed }">
    <header class="brand">
      <LumenMark :size="24" />
      <div v-if="!tweaks.sidebarCollapsed" class="brand-text">
        <span class="brand-name">Lumen AI</span>
        <span class="brand-sub">workspace · 默认</span>
      </div>
      <el-button text @click="tweaks.toggleSidebar()" class="collapse-btn">
        <el-icon><Expand v-if="tweaks.sidebarCollapsed" /><Fold v-else /></el-icon>
      </el-button>
    </header>

    <div class="new-chat" v-if="!tweaks.sidebarCollapsed">
      <el-button class="w-full" @click="router.push('/chat')">
        <el-icon><Plus /></el-icon>新建对话
      </el-button>
    </div>

    <el-menu
      :default-active="route.path"
      :collapse="tweaks.sidebarCollapsed"
      router
      class="nav-menu"
    >
      <el-menu-item v-for="n in nav" :key="n.id" :index="n.to">
        <el-icon><component :is="n.icon" /></el-icon>
        <template #title>{{ n.label }}</template>
      </el-menu-item>
    </el-menu>

    <div class="recent" v-if="!tweaks.sidebarCollapsed">
      <div class="recent-header">最近对话</div>
      <el-scrollbar>
        <button
          v-for="c in chats" :key="c.id"
          class="chat-item" :class="{ active: c.active }"
        >
          <span class="dot" :class="{ active: c.active }" />
          {{ c.title }}
        </button>
      </el-scrollbar>
    </div>

    <footer class="user-footer">
      <el-avatar :size="32" class="avatar">LT</el-avatar>
      <div v-if="!tweaks.sidebarCollapsed" class="user-info">
        <div class="name">{{ auth.user?.name }}</div>
        <div class="email">{{ auth.user?.email }}</div>
      </div>
      <el-dropdown v-if="!tweaks.sidebarCollapsed" @command="(c) => c === 'logout' && auth.logout()">
        <el-button text><el-icon><ArrowDown /></el-icon></el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </footer>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px; flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--paper);
  display: flex; flex-direction: column;
  transition: width .2s ease;
}
.sidebar.collapsed { width: 64px; }

.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 18px 16px;
}
.brand-text { display: flex; flex-direction: column; line-height: 1.1; flex: 1; }
.brand-name { font-size: 15px; font-weight: 700; letter-spacing: -0.01em; }
.brand-sub { font-size: 10px; color: var(--ink-500); font-family: var(--font-mono); margin-top: 2px; }
.collapse-btn { margin-left: auto; }

.new-chat { padding: 0 14px 14px; }
.w-full { width: 100%; }

.nav-menu { background: transparent; padding: 0 10px; }

.recent { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 20px 10px 0; }
.recent-header {
  font-size: 11px; font-weight: 600; color: var(--ink-500);
  letter-spacing: 0.08em; padding: 0 6px 8px;
}
.chat-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 0 12px; height: 34px;
  border-radius: 6px; border: none; background: transparent;
  color: var(--ink-600); font-size: 13px; text-align: left; cursor: pointer;
}
.chat-item:hover { background: var(--ink-50); }
.chat-item.active { background: var(--ink-100); color: var(--ink-900); font-weight: 500; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: var(--ink-300); }
.dot.active { background: var(--accent); }

.user-footer {
  border-top: 1px solid var(--border);
  padding: 12px; display: flex; align-items: center; gap: 10px;
}
.avatar { background: var(--accent); color: white; }
.user-info { flex: 1; min-width: 0; line-height: 1.2; }
.user-info .name { font-size: 13px; font-weight: 500; }
.user-info .email { font-size: 11px; color: var(--ink-500); font-family: var(--font-mono); }
</style>

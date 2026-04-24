import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import KBListView from '../views/KBListView.vue'
import KBDetailView from '../views/KBDetailView.vue'
import SearchView from '../views/SearchView.vue'
import AgentsView from '../views/AgentsView.vue'
import SpacesView from '../views/SpacesView.vue'
import SettingsView from '../views/SettingsView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/chat/:id', name: 'chat-detail', component: ChatView },
    { path: '/kb', name: 'kb', component: KBListView },
    { path: '/kb/:id', name: 'kb-detail', component: KBDetailView },
    { path: '/search', name: 'search', component: SearchView },
    { path: '/agents', name: 'agents', component: AgentsView },
    { path: '/spaces', name: 'spaces', component: SpacesView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

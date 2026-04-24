<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTweaksStore } from '../stores/tweaks'
import Composer from '../components/Composer.vue'
import Citation from '../components/Citation.vue'
import CitationInline from '../components/CitationInline.vue'
import LumenMark from '../components/LumenMark.vue'

const tweaks = useTweaksStore()

type Seg = { type: 'text' | 'code' | 'cite'; text?: string; num?: number }
type CiteItem = { num: number; title: string; source: string; excerpt: string; page?: string }
type Msg =
  | { role: 'user'; text: string }
  | { role: 'assistant'; segments: Seg[]; heading?: string; list?: { k: string; v: string }[]; tail?: Seg[]; citations: CiteItem[] }

const input = ref('')
const streaming = ref(false)
const messages = ref<Msg[]>([
  { role: 'user', text: 'SSE 流式响应的完整事件序列和数据结构是怎样的?' },
  {
    role: 'assistant',
    segments: [
      { type: 'text', text: '基于知识库中的 ' },
      { type: 'code', text: 'agent-chat API' },
      { type: 'text', text: ' 文档，SSE 响应遵循以下事件生命周期' },
      { type: 'cite', num: 1 },
      { type: 'text', text: '。' },
    ],
    heading: 'response_type 枚举值',
    list: [
      { k: 'text', v: '默认纯文本响应' },
      { k: 'tool_call', v: '智能体调用外部工具' },
      { k: 'citation', v: '检索到的引用片段' },
      { k: 'thought', v: 'ReAct 推理过程' },
      { k: 'final', v: '最终答案，触发 session.end' },
    ],
    citations: [
      { num: 1, title: 'agent-chat-api.md', source: 'docs/api/agent-chat-api.md', page: '事件序列', excerpt: 'SSE 连接建立后，服务端按顺序推送 session.start → delta* → session.end 三类事件。' },
    ],
  },
])

const send = () => {
  if (!input.value.trim()) return
  messages.value.push({ role: 'user', text: input.value })
  input.value = ''
  streaming.value = true
  setTimeout(() => {
    messages.value.push({
      role: 'assistant',
      segments: [{ type: 'text', text: '已执行混合检索，召回 Top-3 片段' }, { type: 'cite', num: 1 }],
      citations: [{ num: 1, title: 'retrieval-config.md', source: 'docs/engine/retrieval-config.md', excerpt: 'BM25 + Dense 混合检索默认权重 0.3 / 0.7。' }],
    })
    streaming.value = false
  }, 900)
}

const density = computed(() => tweaks.chatDensity)
</script>

<template>
  <div class="chat">
    <header class="topbar">
      <div class="title-row">
        <h2>API 文档问答会话</h2>
        <el-tag type="success" size="small" round>已连接</el-tag>
      </div>
      <div>
        <el-button text><el-icon><Download /></el-icon>导出</el-button>
      </div>
    </header>

    <el-scrollbar class="messages">
      <div class="messages-inner">
        <template v-for="(m, i) in messages" :key="i">
          <!-- User -->
          <div v-if="m.role === 'user'" class="user-msg" :class="density">
            <div class="bubble">{{ m.text }}</div>
            <el-avatar :size="32" class="avatar-user">LT</el-avatar>
          </div>

          <!-- Assistant -->
          <div v-else class="asst-msg" :class="density">
            <div class="asst-avatar"><LumenMark :size="18" /></div>
            <div class="asst-body">
              <div class="asst-meta"><strong>Lumen</strong><span>qwen3.5-plus · 1.24s</span></div>
              <p>
                <template v-for="(s, j) in m.segments" :key="j">
                  <span v-if="s.type === 'text'">{{ s.text }}</span>
                  <code v-else-if="s.type === 'code'">{{ s.text }}</code>
                  <CitationInline v-else :num="s.num!" />
                </template>
              </p>
              <div v-if="m.heading" class="list-heading">{{ m.heading }}</div>
              <div v-if="m.list" class="list-box">
                <div v-for="(li, k) in m.list" :key="k" class="list-row">
                  <code class="key">{{ li.k }}</code><span>{{ li.v }}</span>
                </div>
              </div>
              <div v-if="tweaks.showCitations && m.citations.length" class="citations">
                <div class="cite-label">引用来源 · {{ m.citations.length }}</div>
                <Citation v-for="c in m.citations" :key="c.num" v-bind="c" />
              </div>
            </div>
          </div>
        </template>

        <div v-if="streaming" class="streaming">检索中…</div>
      </div>
    </el-scrollbar>

    <div class="composer-wrap">
      <Composer v-model="input" :kbs="['API 文档', 'test']" @send="send" />
    </div>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 28px; border-bottom: 1px solid var(--border);
}
.title-row { display: flex; align-items: center; gap: 12px; }
.title-row h2 { font-size: 14px; font-weight: 600; margin: 0; }

.messages { flex: 1; }
.messages-inner { max-width: 820px; margin: 0 auto; padding: 32px 28px 16px; }

.user-msg { display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 28px; }
.user-msg.dense { margin-bottom: 16px; }
.user-msg .bubble {
  max-width: 75%;
  background: var(--ink-900); color: var(--paper);
  padding: 14px 18px; border-radius: 18px 18px 4px 18px;
  font-size: 14.5px; line-height: 1.6;
}
.user-msg.dense .bubble { padding: 10px 14px; }
.avatar-user { background: var(--accent); color: white; }

.asst-msg { display: flex; gap: 12px; margin-bottom: 36px; }
.asst-msg.dense { margin-bottom: 20px; }
.asst-avatar {
  width: 32px; height: 32px; border-radius: 10px;
  background: var(--ink-900); color: var(--paper);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.asst-body { flex: 1; min-width: 0; font-size: 14.5px; line-height: 1.75; }
.asst-meta { display: flex; gap: 10px; margin-bottom: 8px; font-size: 13px; }
.asst-meta span { font-size: 11px; color: var(--ink-400); font-family: var(--font-mono); }
.asst-body p { margin: 0 0 12px; }
.asst-body code {
  font-family: var(--font-mono); font-size: 12.5px;
  padding: 2px 6px; background: var(--ink-100); border-radius: 4px;
}
.list-heading { font-size: 13px; font-weight: 600; margin: 18px 0 8px; }
.list-box {
  padding: 12px 14px; background: var(--ink-50);
  border: 1px solid var(--border); border-radius: 10px;
  display: flex; flex-direction: column; gap: 6px;
}
.list-row { display: flex; gap: 10px; font-size: 13px; }
.list-row .key {
  font-family: var(--font-mono); color: var(--accent-ink);
  min-width: 72px; font-weight: 500;
}

.citations { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.cite-label {
  font-size: 11px; font-weight: 600; color: var(--ink-500);
  letter-spacing: 0.08em; margin-bottom: 4px;
}

.streaming { padding: 12px; color: var(--ink-500); font-family: var(--font-mono); font-size: 12px; }
.composer-wrap { padding: 12px 28px 22px; }
</style>

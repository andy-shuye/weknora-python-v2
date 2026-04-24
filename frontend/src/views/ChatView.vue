<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowRight,
  CircleClose,
  Delete,
  Document,
  Edit,
  FolderOpened,
  MoreFilled,
  Plus,
  Reading,
  Refresh,
  Select,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKnowledgeBases } from '../api/knowledge'
import {
  batchDeleteChatSessions,
  ChatMessage,
  ChatMode,
  ChatSession,
  clearChatSessionMessages,
  createChatSession,
  deleteChatSession,
  getChatOptions,
  getKnowledgeDetail,
  getKnowledgePreview,
  listChatSessionMessages,
  listChatSessions,
  streamChat,
  updateChatSession,
} from '../api/chat'

type UiMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt?: string
  citations: Array<{
    key: string
    knowledge_id: string
    knowledge_title: string
    knowledge_filename: string
    chunk_content: string
    score?: number
  }>
  steps: Array<{ type: string; content: string }>
  streaming?: boolean
  refsCollapsed?: boolean
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const sending = ref(false)
const sessions = ref<ChatSession[]>([])
const activeSessionId = ref('')
const messages = ref<UiMessage[]>([])
const inputText = ref('')

const mode = ref<ChatMode>('quick')
const modelId = ref('')
const defaultModelId = ref('')
const modelOptions = ref<Array<{ id: string; name: string; type: string }>>([])
const modeOptions = ref<Array<{ id: ChatMode; label: string }>>([
  { id: 'quick', label: '快速问答' },
  { id: 'reasoning', label: '智能推理' },
])

const kbOptions = ref<Array<{ id: number; name: string; weknora_kb_id: string }>>([])
const selectedKbIds = ref<string[]>([])
const selectedKbNames = computed(() =>
  kbOptions.value.filter((kb) => selectedKbIds.value.includes(kb.weknora_kb_id)).map((kb) => kb.name),
)

const mentionOpen = ref(false)
const mentionQuery = ref('')
const mentionCandidates = computed(() => {
  const keyword = mentionQuery.value.trim().toLowerCase()
  if (!keyword) return kbOptions.value
  return kbOptions.value.filter((kb) => kb.name.toLowerCase().includes(keyword))
})

const batchMode = ref(false)
const selectedSessionIds = ref<string[]>([])

const previewVisible = ref(false)
const previewTitle = ref('')
const previewMeta = ref<any>(null)
const previewText = ref('')
const previewLoading = ref(false)

const todayLabel = computed(() => new Date().toLocaleDateString())
const activeSession = computed(() => sessions.value.find((s) => s.id === activeSessionId.value) || null)

const listRef = ref<HTMLElement | null>(null)

function normalizeMessage(item: ChatMessage): UiMessage {
  return {
    id: item.id,
    role: item.role,
    content: item.content || '',
    createdAt: item.created_at,
    citations: (item.knowledge_references || []).map((r: any, idx: number) => ({
      key: `${item.id}-${idx}-${r.id || r.knowledge_id || idx}`,
      knowledge_id: String(r.knowledge_id || ''),
      knowledge_title: String(r.knowledge_title || r.knowledge_filename || '引用文档'),
      knowledge_filename: String(r.knowledge_filename || r.knowledge_title || ''),
      chunk_content: String(r.content || ''),
      score: Number(r.score || 0),
    })),
    steps: (item.agent_steps || []).map((s: any) => ({
      type: String(s?.type || 'step'),
      content: String(s?.content || ''),
    })),
    streaming: false,
    refsCollapsed: true,
  }
}

function extractReferences(raw: any): any[] {
  if (Array.isArray(raw?.knowledge_references)) return raw.knowledge_references
  if (Array.isArray(raw?.data?.references)) return raw.data.references
  return []
}

function mergeCitations(current: UiMessage['citations'], refs: any[]): UiMessage['citations'] {
  const next = [...current]
  for (const r of refs) {
    const knowledgeId = String(r.knowledge_id || '')
    const key = String(r.id || `${knowledgeId}-${r.chunk_index || 0}`)
    if (!knowledgeId || next.some((c) => c.key === key)) continue
    next.push({
      key,
      knowledge_id: knowledgeId,
      knowledge_title: String(r.knowledge_title || r.knowledge_filename || '引用文档'),
      knowledge_filename: String(r.knowledge_filename || r.knowledge_title || ''),
      chunk_content: String(r.content || ''),
      score: Number(r.score || 0),
    })
  }
  return next
}

function toggleReferences(message: UiMessage) {
  message.refsCollapsed = !message.refsCollapsed
}

async function loadChatOptions() {
  const res = await getChatOptions()
  defaultModelId.value = res.data.default_model_id || ''
  modelOptions.value = res.data.models || []
  modelId.value = defaultModelId.value || modelOptions.value[0]?.id || ''
  modeOptions.value = res.data.modes || modeOptions.value
}

async function loadKnowledgeBases() {
  const res = await listKnowledgeBases()
  kbOptions.value = (res.data || []).map((i) => ({
    id: i.id,
    name: i.name,
    weknora_kb_id: i.weknora_kb_id,
  }))
}

async function loadSessions() {
  const res = await listChatSessions(1, 300)
  sessions.value = (res.data.items || []).sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')))
}

function openSession(sessionId: string) {
  if (!sessionId) return
  if (activeSessionId.value === sessionId) return
  router.push(`/chat/${sessionId}`)
}

async function ensureSessionForRoute() {
  const routeId = String(route.params.id || '').trim()
  if (routeId) {
    const exists = sessions.value.some((s) => s.id === routeId)
    if (exists) {
      activeSessionId.value = routeId
      return
    }
  }
  if (sessions.value.length === 0) {
    const created = await createChatSession({ title: '新会话' })
    sessions.value.unshift(created.data)
    activeSessionId.value = created.data.id
    await router.replace(`/chat/${created.data.id}`)
    return
  }
  activeSessionId.value = sessions.value[0].id
  await router.replace(`/chat/${sessions.value[0].id}`)
}

async function loadMessages() {
  if (!activeSessionId.value) return
  loading.value = true
  try {
    const res = await listChatSessionMessages(activeSessionId.value, 200)
    messages.value = (res.data || [])
      .slice()
      .sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')))
      .map(normalizeMessage)
  } catch (e: any) {
    const message = String(e?.message || '')
    if (message.includes('session not found or inaccessible')) {
      await loadSessions()
      await ensureSessionForRoute()
      if (activeSessionId.value) {
        const retry = await listChatSessionMessages(activeSessionId.value, 200)
        messages.value = (retry.data || [])
          .slice()
          .sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')))
          .map(normalizeMessage)
      }
    } else {
      ElMessage.error(message || '加载消息失败')
    }
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

async function createNewSession() {
  const created = await createChatSession({ title: '新会话' })
  sessions.value.unshift(created.data)
  await router.push(`/chat/${created.data.id}`)
  ElMessage.success('已新建对话')
}

async function renameSession(session: ChatSession) {
  try {
    const result = await ElMessageBox.prompt('请输入新的对话名称', '重命名', {
      inputValue: session.title || '',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    const title = (result.value || '').trim()
    if (!title) return
    await updateChatSession(session.id, { title })
    await loadSessions()
    ElMessage.success('重命名成功')
  } catch {
    // canceled
  }
}

async function removeSession(session: ChatSession) {
  try {
    await ElMessageBox.confirm(`确认删除对话“${session.title || '未命名'}”？`, '删除确认', { type: 'warning' })
    await deleteChatSession(session.id)
    await loadSessions()
    if (activeSessionId.value === session.id) {
      await ensureSessionForRoute()
      await loadMessages()
    }
    ElMessage.success('已删除')
  } catch {
    // canceled
  }
}

async function clearMessages(session: ChatSession) {
  try {
    await ElMessageBox.confirm(`确认清空“${session.title || '未命名'}”中的消息？`, '清空消息', { type: 'warning' })
    await clearChatSessionMessages(session.id)
    if (activeSessionId.value === session.id) {
      messages.value = []
    }
    ElMessage.success('已清空')
  } catch {
    // canceled
  }
}

async function removeSelectedSessions() {
  if (selectedSessionIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的对话')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedSessionIds.value.length} 个对话？`, '批量删除', {
      type: 'warning',
    })
    await batchDeleteChatSessions(selectedSessionIds.value)
    selectedSessionIds.value = []
    await loadSessions()
    await ensureSessionForRoute()
    await loadMessages()
    ElMessage.success('批量删除成功')
  } catch {
    // canceled
  }
}

function toggleKb(kbId: string) {
  if (selectedKbIds.value.includes(kbId)) {
    selectedKbIds.value = selectedKbIds.value.filter((id) => id !== kbId)
  } else {
    selectedKbIds.value = [...selectedKbIds.value, kbId]
  }
}

function removeKb(kbName: string) {
  const target = kbOptions.value.find((k) => k.name === kbName)
  if (!target) return
  selectedKbIds.value = selectedKbIds.value.filter((id) => id !== target.weknora_kb_id)
}

function handleInputForMention() {
  const value = inputText.value
  const index = value.lastIndexOf('@')
  if (index < 0) {
    mentionOpen.value = false
    mentionQuery.value = ''
    return
  }
  const tail = value.slice(index + 1)
  if (tail.includes(' ') || tail.includes('\n')) {
    mentionOpen.value = false
    mentionQuery.value = ''
    return
  }
  mentionQuery.value = tail
  mentionOpen.value = true
}

function pickMentionKb(kb: { name: string; weknora_kb_id: string }) {
  toggleKb(kb.weknora_kb_id)
  const idx = inputText.value.lastIndexOf('@')
  if (idx >= 0) {
    inputText.value = `${inputText.value.slice(0, idx)}@${kb.name} `
  }
  mentionOpen.value = false
  mentionQuery.value = ''
}

async function scrollToBottom() {
  await nextTick()
  if (!listRef.value) return
  listRef.value.scrollTop = listRef.value.scrollHeight + 200
}

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || sending.value) return

  if (!activeSessionId.value) {
    await createNewSession()
  }
  if (!activeSessionId.value) return

  if (activeSession.value?.title === '新会话') {
    await updateChatSession(activeSessionId.value, { title: query.slice(0, 20) })
    await loadSessions()
  }

  const userMsg: UiMessage = {
    id: `local-user-${Date.now()}`,
    role: 'user',
    content: query,
    citations: [],
    steps: [],
  }
  const asstMsg: UiMessage = {
    id: `local-asst-${Date.now()}`,
    role: 'assistant',
    content: '',
    citations: [],
    steps: [],
    streaming: true,
    refsCollapsed: true,
  }

  messages.value.push(userMsg)
  messages.value.push(asstMsg)
  inputText.value = ''
  mentionOpen.value = false
  sending.value = true
  await scrollToBottom()

  const selectedMentioned = kbOptions.value
    .filter((kb) => selectedKbIds.value.includes(kb.weknora_kb_id))
    .map((kb) => ({ id: kb.weknora_kb_id, name: kb.name, type: 'kb' as const, kb_type: 'document' }))

  try {
    await streamChat({
      sessionId: activeSessionId.value,
      query,
      mode: mode.value,
      modelId: modelId.value,
      knowledgeBaseIds: selectedKbIds.value,
      mentionedItems: selectedMentioned,
      onEvent: async (eventType, raw) => {
        if (!raw || typeof raw !== 'object') return
        const responseType = String(raw.response_type || eventType || '').toLowerCase()
        const content = String(raw.content || '')

        if (responseType === 'references') {
          const refs = extractReferences(raw)
          if (refs.length) {
            asstMsg.citations = mergeCitations(asstMsg.citations, refs)
          }
        } else if (responseType === 'answer') {
          if (content) {
            asstMsg.content += content
          }
          if (raw.done === true) {
            asstMsg.streaming = false
          }
        } else if (
          responseType === 'thinking' ||
          responseType === 'tool_call' ||
          responseType === 'tool_result' ||
          responseType === 'reflection' ||
          responseType === 'agent_query'
        ) {
          asstMsg.steps.push({ type: responseType, content: content || JSON.stringify(raw.data || {}) })
        } else if (responseType === 'session_title' && content && activeSessionId.value) {
          await updateChatSession(activeSessionId.value, { title: content })
          await loadSessions()
        } else if (responseType === 'error') {
          asstMsg.steps.push({ type: 'error', content: content || '推理出现错误' })
          asstMsg.streaming = false
        } else if (responseType === 'complete' || responseType === 'stop') {
          asstMsg.streaming = false
        }
        await scrollToBottom()
      },
    })

    asstMsg.streaming = false
  } catch (e: any) {
    asstMsg.streaming = false
    if (!asstMsg.content) {
      asstMsg.content = `请求失败：${e.message || 'unknown error'}`
    }
    ElMessage.error(e.message || '发送失败')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function openReference(cite: UiMessage['citations'][number]) {
  previewVisible.value = true
  previewLoading.value = true
  previewText.value = ''
  previewMeta.value = null
  previewTitle.value = cite.knowledge_filename || cite.knowledge_title || '引用文档'
  try {
    const [detailRes, previewRes] = await Promise.all([
      getKnowledgeDetail(cite.knowledge_id),
      getKnowledgePreview(cite.knowledge_id),
    ])
    previewMeta.value = detailRes.data || null
    previewText.value = previewRes.data.text || ''
  } catch (e: any) {
    ElMessage.error(e.message || '加载引用文档失败')
  } finally {
    previewLoading.value = false
  }
}

watch(
  () => route.params.id,
  async (id) => {
    const sessionId = String(id || '').trim()
    if (!sessionId) return
    const exists = sessions.value.some((s) => s.id === sessionId)
    if (!exists) {
      await loadSessions()
      await ensureSessionForRoute()
      return
    }
    activeSessionId.value = sessionId
    await loadMessages()
  },
)

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadChatOptions(), loadKnowledgeBases(), loadSessions()])
    await ensureSessionForRoute()
    await loadMessages()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="chat-page" v-loading="loading">
    <aside class="session-panel">
      <div class="panel-head">
        <h3>对话</h3>
        <el-button text type="success" @click="createNewSession">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="panel-actions">
        <el-button size="small" @click="batchMode = !batchMode">{{ batchMode ? '取消批量' : '批量管理' }}</el-button>
        <el-button v-if="batchMode" size="small" type="danger" @click="removeSelectedSessions">
          删除选中 ({{ selectedSessionIds.length }})
        </el-button>
      </div>
      <div class="panel-date">今天 {{ todayLabel }}</div>
      <el-scrollbar class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === activeSessionId }"
          @click="openSession(s.id)"
        >
          <label v-if="batchMode" class="session-checkbox" @click.stop>
            <input v-model="selectedSessionIds" type="checkbox" :value="s.id" />
          </label>
          <span class="session-title">{{ s.title || '未命名会话' }}</span>
          <el-dropdown trigger="click" @click.stop>
            <el-button text class="session-more"><el-icon><MoreFilled /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="clearMessages(s)">
                  <el-icon><CircleClose /></el-icon>清空消息
                </el-dropdown-item>
                <el-dropdown-item @click="renameSession(s)">
                  <el-icon><Edit /></el-icon>重命名
                </el-dropdown-item>
                <el-dropdown-item divided @click="removeSession(s)" style="color:#ef4444">
                  <el-icon><Delete /></el-icon>删除记录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-scrollbar>
    </aside>

    <section class="chat-main">
      <div ref="listRef" class="message-list">
        <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
          <div v-if="m.role === 'user'" class="bubble user-bubble">{{ m.content }}</div>
          <div v-else class="assistant-wrap">
            <div v-if="m.steps.length" class="steps">
              <div class="steps-title"><el-icon><Reading /></el-icon> 完成 {{ m.steps.length }} 个步骤</div>
              <div v-for="(step, idx) in m.steps" :key="`${m.id}-step-${idx}`" class="step-row">
                <span class="step-type">{{ step.type }}</span>
                <span class="step-content">{{ step.content }}</span>
              </div>
            </div>
            <div v-if="m.citations.length" class="refs">
              <button class="refs-toggle" type="button" @click="toggleReferences(m)">
                <span class="refs-title">引用来源 {{ m.citations.length }}</span>
                <el-icon class="refs-arrow" :class="{ folded: m.refsCollapsed !== false }">
                  <ArrowDown />
                </el-icon>
              </button>
              <div v-show="m.refsCollapsed === false" class="ref-list">
                <div v-for="cite in m.citations" :key="cite.key" class="ref-item">
                  <button class="ref-head" type="button" @click="openReference(cite)">
                    <el-icon><Document /></el-icon>
                    <span class="ref-file">{{ cite.knowledge_filename || cite.knowledge_title }}</span>
                    <el-icon class="ref-open"><ArrowRight /></el-icon>
                  </button>
                  <el-popover
                    placement="top-start"
                    :width="460"
                    trigger="hover"
                    popper-class="vector-popover"
                  >
                    <template #reference>
                      <button class="chunk-chip" type="button" @click="openReference(cite)">
                        向量块预览
                      </button>
                    </template>
                    <div class="chunk-preview">{{ cite.chunk_content || '暂无文本分块内容' }}</div>
                  </el-popover>
                </div>
              </div>
            </div>
            <div class="assistant-content">{{ m.content || (m.streaming ? '正在思考...' : '') }}</div>
          </div>
        </div>
      </div>

      <div class="composer">
        <div v-if="selectedKbNames.length" class="kb-tags">
          <el-tag
            v-for="name in selectedKbNames"
            :key="name"
            closable
            round
            type="success"
            @close="removeKb(name)"
          >
            {{ name }}
          </el-tag>
        </div>

        <div class="composer-box">
          <textarea
            v-model="inputText"
            class="composer-input"
            placeholder="直接向模型提问，输入 @ 可选择知识库"
            :disabled="sending"
            @input="handleInputForMention"
            @keydown.enter.exact.prevent="sendMessage"
          />

          <div v-if="mentionOpen" class="mention-panel">
            <div v-for="kb in mentionCandidates" :key="kb.weknora_kb_id" class="mention-item" @click="pickMentionKb(kb)">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ kb.name }}</span>
            </div>
            <div v-if="mentionCandidates.length === 0" class="mention-empty">未找到知识库</div>
          </div>

          <div class="composer-tools">
            <div class="left-tools">
              <el-select v-model="mode" size="small" style="width: 120px">
                <el-option v-for="m in modeOptions" :key="m.id" :label="m.label" :value="m.id" />
              </el-select>
              <el-button text @click="mentionOpen = !mentionOpen">
                <el-icon><Select /></el-icon>@
              </el-button>
              <el-button text @click="loadMessages">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
            <div class="right-tools">
              <el-select v-model="modelId" size="small" style="width: 180px">
                <el-option
                  v-for="m in modelOptions"
                  :key="m.id"
                  :label="m.name"
                  :value="m.id"
                />
                <el-option
                  v-if="modelOptions.length === 0"
                  :label="defaultModelId || '默认模型'"
                  :value="defaultModelId || ''"
                />
              </el-select>
              <el-button type="primary" :loading="sending" :disabled="!inputText.trim()" @click="sendMessage">
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <el-dialog v-model="previewVisible" :title="previewTitle" width="880px">
      <div v-loading="previewLoading" class="preview-wrap">
        <div class="preview-meta" v-if="previewMeta">
          <div>类型：{{ previewMeta.file_type || previewMeta.type || '-' }}</div>
          <div>更新时间：{{ previewMeta.updated_at || '-' }}</div>
        </div>
        <pre class="preview-content">{{ previewText || '该文档暂不支持文本预览，可在原系统中打开。' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
  overflow: hidden;
  background: #f5f7f8;
}
.session-panel {
  border-right: 1px solid #e6eaef;
  background: #f3f4f6;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 6px;
}
.panel-head h3 {
  margin: 0;
  font-size: 28px;
}
.panel-actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 8px;
}
.panel-date {
  padding: 6px 14px;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 600;
}
.session-list {
  flex: 1;
  min-height: 0;
  padding: 0 10px 12px;
}
.session-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  height: 36px;
  border-radius: 8px;
  padding: 0 8px;
  cursor: pointer;
  margin-bottom: 4px;
}
.session-item:hover {
  background: #edf2f7;
}
.session-item.active {
  background: #daf4df;
  color: #0f9f5d;
}
.session-checkbox input {
  width: 14px;
  height: 14px;
}
.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.session-more {
  height: 24px;
  width: 24px;
}

.chat-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.message-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 22px 26px 18px;
}
.msg {
  margin: 0 auto 16px;
  max-width: 860px;
}
.msg.user {
  display: flex;
  justify-content: flex-end;
}
.user-bubble {
  background: #7edc76;
  color: #111827;
  padding: 10px 14px;
  border-radius: 8px;
  max-width: 60%;
}
.assistant-wrap {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
}
.assistant-content {
  margin-top: 4px;
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 15px;
}
.steps {
  border: 1px solid #d6f1dd;
  background: #f8fdfa;
  border-radius: 8px;
  margin-bottom: 8px;
}
.steps-title {
  padding: 8px 10px;
  font-size: 13px;
  color: #0f9f5d;
  border-bottom: 1px solid #e6f4ea;
  display: flex;
  align-items: center;
  gap: 6px;
}
.step-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 10px;
  padding: 7px 10px;
  border-top: 1px dashed #e5e7eb;
}
.step-type {
  color: #4b5563;
  font-size: 12px;
}
.step-content {
  font-size: 13px;
  color: #111827;
  white-space: pre-wrap;
}

.refs {
  margin-bottom: 10px;
  border: 1px solid #d9e8df;
  border-radius: 10px;
  background: #f7fcf9;
}
.refs-toggle {
  width: 100%;
  border: 0;
  background: transparent;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}
.refs-title {
  font-size: 14px;
  color: #111827;
  font-weight: 600;
}
.refs-arrow {
  color: #0f9f5d;
  transition: transform 0.2s ease;
}
.refs-arrow.folded {
  transform: rotate(-90deg);
}
.ref-list {
  padding: 0 10px 10px;
}
.ref-item {
  border: 1px solid #dbece2;
  background: #ffffff;
  border-radius: 8px;
  padding: 8px;
  margin-bottom: 6px;
}
.ref-head {
  width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 7px;
  color: #0e9b57;
  font-size: 14px;
  cursor: pointer;
}
.ref-file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-open {
  margin-left: auto;
}
.chunk-chip {
  margin-top: 8px;
  border: 1px solid #bfe5cf;
  background: #f0fbf4;
  color: #107a4a;
  border-radius: 999px;
  font-size: 12px;
  padding: 3px 10px;
  cursor: pointer;
}
.chunk-chip:hover {
  background: #e3f7ea;
}
.chunk-preview {
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 13px;
  color: #374151;
}

.composer {
  padding: 0 22px 20px;
}
.kb-tags {
  max-width: 860px;
  margin: 0 auto 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.composer-box {
  position: relative;
  max-width: 860px;
  margin: 0 auto;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  padding: 10px 12px 8px;
}
.composer-input {
  width: 100%;
  min-height: 96px;
  border: 0;
  resize: none;
  outline: none;
  font-size: 15px;
  line-height: 1.7;
}
.mention-panel {
  position: absolute;
  left: 12px;
  bottom: 72px;
  width: 320px;
  max-height: 240px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  z-index: 10;
}
.mention-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  cursor: pointer;
}
.mention-item:hover {
  background: #f3f9f5;
}
.mention-empty {
  padding: 12px;
  font-size: 13px;
  color: #9ca3af;
}
.composer-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.left-tools,
.right-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-wrap {
  min-height: 360px;
}
.preview-meta {
  display: flex;
  gap: 24px;
  margin-bottom: 10px;
  color: #6b7280;
  font-size: 13px;
}
.preview-content {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  max-height: 62vh;
  overflow: auto;
}

@media (max-width: 1200px) {
  .chat-page {
    grid-template-columns: 220px 1fr;
  }
}
</style>

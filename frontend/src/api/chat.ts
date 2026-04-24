import { requestJson } from './client'

const TOKEN_KEY = 'weknora_token'

export type ChatMode = 'quick' | 'reasoning'

export type ChatSession = {
  id: string
  title: string
  description?: string
  created_at?: string
  updated_at?: string
}

export type ChatMessage = {
  id: string
  session_id: string
  request_id?: string
  role: 'user' | 'assistant'
  content: string
  knowledge_references?: any[]
  agent_steps?: any[]
  is_completed?: boolean
  created_at?: string
}

export async function getChatOptions() {
  return requestJson<{
    success: boolean
    data: {
      default_model_id: string
      default_rerank_model_id: string
      quick_answer_agent_id: string
      smart_reasoning_agent_id: string
      models: Array<{ id: string; name: string; type: string }>
      modes: Array<{ id: ChatMode; label: string }>
    }
  }>('/api/chat/options')
}

export async function listChatSessions(page = 1, pageSize = 200) {
  return requestJson<{
    success: boolean
    data: { items: ChatSession[]; page: number; page_size: number; total: number }
  }>(`/api/chat/sessions?page=${page}&page_size=${pageSize}`)
}

export async function createChatSession(payload: { title?: string; description?: string }) {
  return requestJson<{ success: boolean; data: ChatSession }>('/api/chat/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateChatSession(sessionId: string, payload: { title?: string; description?: string }) {
  return requestJson<{ success: boolean; data: ChatSession }>(`/api/chat/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function deleteChatSession(sessionId: string) {
  return requestJson<{ success: boolean; message: string }>(`/api/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  })
}

export async function batchDeleteChatSessions(ids: string[]) {
  return requestJson<{ success: boolean; message: string }>('/api/chat/sessions/batch-delete', {
    method: 'DELETE',
    body: JSON.stringify({ ids }),
  })
}

export async function clearChatSessionMessages(sessionId: string) {
  return requestJson<{ success: boolean; message: string }>(`/api/chat/sessions/${sessionId}/messages`, {
    method: 'DELETE',
  })
}

export async function listChatSessionMessages(sessionId: string, limit = 200) {
  return requestJson<{ success: boolean; data: ChatMessage[] }>(`/api/chat/sessions/${sessionId}/messages?limit=${limit}`)
}

export async function getKnowledgeDetail(knowledgeId: string) {
  return requestJson<{ success: boolean; data: any }>(`/api/chat/knowledge/${knowledgeId}/detail`)
}

export async function getKnowledgePreview(knowledgeId: string) {
  return requestJson<{
    success: boolean
    data: { content_type: string; content_disposition: string; text: string; size: number }
  }>(`/api/chat/knowledge/${knowledgeId}/preview`)
}

export async function streamChat(params: {
  sessionId: string
  query: string
  mode: ChatMode
  modelId?: string
  summaryModelId?: string
  knowledgeBaseIds?: string[]
  mentionedItems?: Array<{ id: string; name: string; type: 'kb'; kb_type?: string }>
  onEvent: (eventType: string, data: any) => void
}) {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`/api/chat/sessions/${params.sessionId}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      query: params.query,
      mode: params.mode,
      model_id: params.modelId || '',
      summary_model_id: params.summaryModelId || '',
      knowledge_base_ids: params.knowledgeBaseIds || [],
      mentioned_items: params.mentionedItems || [],
    }),
  })

  if (!response.ok || !response.body) {
    const result = await response.json().catch(() => ({}))
    throw new Error(result?.message || `Stream request failed with ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const flushBlocks = (force = false) => {
    const blocks = buffer.split(/\r?\n\r?\n/)
    if (!force) {
      buffer = blocks.pop() || ''
    } else {
      buffer = ''
    }

    for (const block of blocks) {
      const lines = block.split(/\r?\n/)
      let eventType = 'message'
      let payloadText = ''
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim() || 'message'
        } else if (line.startsWith('data:')) {
          payloadText += `${line.slice(5).trimStart()}\n`
        }
      }
      const payload = payloadText.trim()
      if (!payload) continue
      try {
        const parsed = JSON.parse(payload)
        params.onEvent(eventType, parsed)
      } catch {
        params.onEvent(eventType, payload)
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    flushBlocks()
  }

  buffer += decoder.decode()
  flushBlocks(true)
}

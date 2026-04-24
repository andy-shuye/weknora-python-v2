import { requestForm, requestJson } from './client'

export type KnowledgeBaseItem = {
  id: number
  weknora_kb_id: string
  name: string
  owner_user_id: number
  owner_department_id: number | null
  visibility: 'private' | 'space'
  space_id: number | null
  created_by: number
  created_at: string
  updated_at: string
  weknora?: {
    id: string
    name: string
    description?: string
    type?: string
    knowledge_count?: number
    chunk_count?: number
    processing_count?: number
  }
}

export async function listKnowledgeBases() {
  return requestJson<{ success: boolean; data: KnowledgeBaseItem[] }>('/api/knowledge/bases')
}

export async function createKnowledgeBase(payload: { name: string; description?: string; type?: string }) {
  return requestJson<{ success: boolean; data: KnowledgeBaseItem }>('/api/knowledge/bases', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getKnowledgeBaseDetail(id: number) {
  return requestJson<{ success: boolean; data: KnowledgeBaseItem }>(`/api/knowledge/bases/${id}`)
}

export async function updateKnowledgeBase(id: number, payload: { name?: string; description?: string }) {
  return requestJson<{ success: boolean; data: KnowledgeBaseItem }>(`/api/knowledge/bases/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function deleteKnowledgeBase(id: number) {
  return requestJson<{ success: boolean; message: string }>(`/api/knowledge/bases/${id}`, {
    method: 'DELETE',
  })
}

export async function listKnowledgeDocuments(id: number, page = 1, pageSize = 20) {
  return requestJson<{ success: boolean; data: { items: any[]; page: number; page_size: number; total: number } }>(
    `/api/knowledge/bases/${id}/documents?page=${page}&page_size=${pageSize}`,
  )
}

export async function listKnowledgeDocumentsByTag(id: number, tagId: string, page = 1, pageSize = 20) {
  return requestJson<{ success: boolean; data: { items: any[]; page: number; page_size: number; total: number } }>(
    `/api/knowledge/bases/${id}/documents?page=${page}&page_size=${pageSize}&tag_id=${encodeURIComponent(tagId)}`,
  )
}

export async function uploadKnowledgeDocument(id: number, file: File, enableMultimodel = true, tagId?: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('enable_multimodel', String(enableMultimodel))
  if (tagId) form.append('tag_id', tagId)
  return requestForm<{ success: boolean; data: any }>(`/api/knowledge/bases/${id}/documents/upload`, form)
}

export async function listKnowledgeTags(id: number, keyword = '', page = 1, pageSize = 50) {
  return requestJson<{ success: boolean; data: { items: any[]; page: number; page_size: number; total: number } }>(
    `/api/knowledge/bases/${id}/tags?page=${page}&page_size=${pageSize}&keyword=${encodeURIComponent(keyword)}`,
  )
}

export async function createKnowledgeTag(id: number, payload: { name: string; color?: string; sort_order?: number }) {
  return requestJson<{ success: boolean; data: any }>(`/api/knowledge/bases/${id}/tags`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateKnowledgeTag(id: number, tagId: string, payload: { name?: string; color?: string; sort_order?: number }) {
  return requestJson<{ success: boolean; data: any }>(`/api/knowledge/bases/${id}/tags/${tagId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function deleteKnowledgeTag(id: number, tagId: string, force = false) {
  return requestJson<{ success: boolean; message: string }>(
    `/api/knowledge/bases/${id}/tags/${tagId}?force=${force ? 'true' : 'false'}`,
    { method: 'DELETE' },
  )
}

export async function batchUpdateKnowledgeDocumentTags(id: number, updates: Record<string, string | null>) {
  return requestJson<{ success: boolean; data: any }>(`/api/knowledge/bases/${id}/documents/tags`, {
    method: 'PUT',
    body: JSON.stringify({ updates }),
  })
}

export async function shareKnowledgeBaseToSpace(id: number, spaceId: number, permission = 'viewer') {
  return requestJson<{ success: boolean; data: any }>(`/api/knowledge/${id}/share-to-space`, {
    method: 'POST',
    body: JSON.stringify({ space_id: spaceId, permission }),
  })
}

export async function unshareKnowledgeBaseFromSpace(id: number) {
  return requestJson<{ success: boolean; data: any }>(`/api/knowledge/${id}/share-from-space`, {
    method: 'DELETE',
  })
}

export async function listSpaces() {
  return requestJson<{ success: boolean; data: Array<{ id: number; name: string }> }>('/api/spaces')
}

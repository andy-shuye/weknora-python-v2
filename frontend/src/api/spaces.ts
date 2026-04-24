import { requestJson } from './client'

export type SpaceItem = {
  id: number
  name: string
  description: string
  owner_user_id: number
  owner_department_id: number | null
  owner_name?: string
  member_count?: number
  kb_count?: number
  my_permission?: 'manage' | 'read'
  is_enabled: boolean
}

export type SpaceKnowledgeBase = {
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
}

export async function listSpaces() {
  return requestJson<{ success: boolean; data: SpaceItem[] }>('/api/spaces')
}

export async function createSpace(payload: { name: string; description?: string }) {
  return requestJson<{ success: boolean; data: SpaceItem }>('/api/spaces', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateSpace(spaceId: number, payload: { name?: string; description?: string; is_enabled?: boolean }) {
  return requestJson<{ success: boolean; data: SpaceItem }>(`/api/spaces/${spaceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function getSpaceMembers(spaceId: number) {
  return requestJson<{
    success: boolean
    data: {
      space: SpaceItem
      user_members: Array<{ id: number; user_id: number; login_name: string; full_name: string; department_id: number | null }>
      department_members: Array<{ id: number; department_id: number; department_name: string }>
    }
  }>(`/api/spaces/${spaceId}/members`)
}

export async function addSpaceUsers(spaceId: number, userIds: number[]) {
  return requestJson<{ success: boolean; data: any[] }>(`/api/spaces/${spaceId}/members/users`, {
    method: 'POST',
    body: JSON.stringify({ user_ids: userIds }),
  })
}

export async function removeSpaceUser(spaceId: number, userId: number) {
  return requestJson<{ success: boolean; message: string }>(`/api/spaces/${spaceId}/members/users/${userId}`, {
    method: 'DELETE',
  })
}

export async function addSpaceDepartments(spaceId: number, departmentIds: number[]) {
  return requestJson<{ success: boolean; data: any[] }>(`/api/spaces/${spaceId}/members/departments`, {
    method: 'POST',
    body: JSON.stringify({ department_ids: departmentIds }),
  })
}

export async function removeSpaceDepartment(spaceId: number, departmentId: number) {
  return requestJson<{ success: boolean; message: string }>(`/api/spaces/${spaceId}/members/departments/${departmentId}`, {
    method: 'DELETE',
  })
}

export async function listSpaceKnowledgeBases(spaceId: number) {
  return requestJson<{ success: boolean; data: SpaceKnowledgeBase[] }>(`/api/spaces/${spaceId}/knowledge-bases`)
}

export async function listUsers() {
  return requestJson<{ success: boolean; data: Array<{ id: number; full_name: string; login_name: string; department_name: string | null }> }>('/api/users')
}

export async function listDepartments() {
  return requestJson<{ success: boolean; data: Array<{ id: number; name: string }> }>('/api/departments')
}

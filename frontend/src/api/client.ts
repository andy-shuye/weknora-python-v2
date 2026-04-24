const TOKEN_KEY = 'weknora_token'

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY)
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(extra || {}),
  }
}

export async function requestJson<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(options.headers),
    },
  })

  const result = await response.json().catch(() => ({}))
  if (!response.ok || result?.success === false) {
    throw new Error(result?.message || `Request failed with ${response.status}`)
  }
  return result as T
}

export async function requestForm<T = any>(path: string, formData: FormData, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    method: options.method || 'POST',
    body: formData,
    headers: {
      ...authHeaders(options.headers),
    },
  })

  const result = await response.json().catch(() => ({}))
  if (!response.ok || result?.success === false) {
    throw new Error(result?.message || `Request failed with ${response.status}`)
  }
  return result as T
}

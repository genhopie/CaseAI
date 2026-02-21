export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8787/api'

export type Case = {
  id: string
  title: string
  jurisdiction: string
  tags: string[]
  created_at: number
  updated_at: number
  archived_at?: number | null
}

export type Document = {
  id: string
  case_id: string
  filename: string
  mime: string
  sha256: string
  imported_at: number
}

export type JournalEntry = {
  id: string
  case_id: string
  ts: number
  actor: string
  action_type: string
  payload: Record<string, unknown>
  payload_hash: string
}

export async function apiFetch(path: string, opts: RequestInit = {}, token?: string) {
  const headers = new Headers(opts.headers || {})
  headers.set('Content-Type', headers.get('Content-Type') || 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || `HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return await res.json()
  return await res.text()
}

export async function login(username: string, password: string): Promise<{token: string}> {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }) as Promise<{token: string}>
}

export async function listCases(token: string): Promise<Case[]> {
  return apiFetch('/cases', { method: 'GET' }, token) as Promise<Case[]>
}

export async function createCase(token: string, title: string, jurisdiction: string, tags: string[]): Promise<Case> {
  return apiFetch('/cases', {
    method: 'POST',
    body: JSON.stringify({ title, jurisdiction, tags }),
  }, token) as Promise<Case>
}

export async function listDocuments(token: string, caseId: string): Promise<Document[]> {
  return apiFetch(`/cases/${caseId}/documents`, { method: 'GET' }, token) as Promise<Document[]>
}

export async function uploadDocument(token: string, caseId: string, file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/cases/${caseId}/documents/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!res.ok) throw new Error(await res.text())
  return await res.json()
}

export async function listJournal(token: string, caseId: string): Promise<JournalEntry[]> {
  return apiFetch(`/cases/${caseId}/journal`, { method: 'GET' }, token) as Promise<JournalEntry[]>
}

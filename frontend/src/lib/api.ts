import { apiBaseUrl } from './env'
import type {
  CorrectionEmailDraft,
  Document,
  DocumentCorrections,
  GlAccount,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { credentials: 'include', ...init })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: string }
      if (typeof body.detail === 'string' && body.detail) {
        message = body.detail
      }
    } catch {
      // Keep the HTTP fallback when the server did not return JSON.
    }
    throw new Error(message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export function uploadDocument(file: File): Promise<Document> {
  const body = new FormData()
  body.append('file', file)
  return request<Document>('/api/documents', { method: 'POST', body })
}

export function listDocuments(): Promise<Document[]> {
  return request<Document[]>('/api/documents')
}

export function getDocument(id: string): Promise<Document> {
  return request<Document>(`/api/documents/${encodeURIComponent(id)}`)
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function documentFileUrl(id: string): string {
  return `${apiBaseUrl}/api/documents/${encodeURIComponent(id)}/file`
}

export function correctDocument(id: string, corrections: DocumentCorrections): Promise<Document> {
  return request<Document>(
    `/api/documents/${encodeURIComponent(id)}`,
    json('PUT', corrections),
  )
}

export function selectGlAccount(id: string, glAccountCode: string): Promise<Document> {
  return request<Document>(
    `/api/documents/${encodeURIComponent(id)}/accounting`,
    json('PUT', { gl_account_code: glAccountCode }),
  )
}

export function decideDocument(
  id: string,
  decision: 'approved' | 'rejected',
): Promise<Document> {
  return request<Document>(
    `/api/documents/${encodeURIComponent(id)}/decision`,
    json('POST', { decision }),
  )
}

export function draftCorrectionEmail(id: string): Promise<CorrectionEmailDraft> {
  return request<CorrectionEmailDraft>(
    `/api/documents/${encodeURIComponent(id)}/correction-email`,
    { method: 'POST' },
  )
}

export function listGlAccounts(): Promise<GlAccount[]> {
  return request<GlAccount[]>('/api/accounting/gl-accounts')
}

export interface AuthStatus {
  required: boolean
  authenticated: boolean
}

export function getAuthStatus(): Promise<AuthStatus> {
  return request<AuthStatus>('/api/auth/status')
}

export function login(password: string): Promise<AuthStatus> {
  return request<AuthStatus>('/api/auth/login', json('POST', { password }))
}

export function logout(): Promise<void> {
  return request<void>('/api/auth/logout', { method: 'POST' })
}

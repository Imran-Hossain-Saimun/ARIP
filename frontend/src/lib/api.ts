const API_URL = import.meta.env.VITE_API_URL

export interface ApiErrorBody {
  code: string
  message: string
  field_errors: unknown[]
  trace_id: string | null
}

export class ApiError extends Error {
  code: string
  fieldErrors: unknown[]
  traceId: string | null
  status: number

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.fieldErrors = body.field_errors
    this.traceId = body.trace_id
  }
}

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null
    throw new ApiError(response.status, body ?? { code: 'error', message: response.statusText, field_errors: [], trace_id: null })
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    // No Content-Type here — the browser sets multipart/form-data with the right boundary.
    headers: { ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) },
    body: formData,
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null
    throw new ApiError(response.status, body ?? { code: 'error', message: response.statusText, field_errors: [], trace_id: null })
  }
  return response.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, headers?: HeadersInit) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined, headers }),
  patch: <T>(path: string, body?: unknown, headers?: HeadersInit) =>
    request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined, headers }),
  put: <T>(path: string, body?: unknown, headers?: HeadersInit) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined, headers }),
  postForm: <T>(path: string, formData: FormData) => requestForm<T>(path, formData),
}

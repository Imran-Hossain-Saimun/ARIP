import { api } from '@/lib/api'
import type { AssignBody, Channel, RequestDetail, RequestListResponse, RequestStatus } from './types'

export function listRequests(params: { status?: RequestStatus; channel?: Channel; cursor?: string } = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.channel) query.set('channel', params.channel)
  if (params.cursor) query.set('cursor', params.cursor)
  const qs = query.toString()
  return api.get<RequestListResponse>(`/v1/requests${qs ? `?${qs}` : ''}`)
}

export function getRequest(id: string) {
  return api.get<RequestDetail>(`/v1/requests/${id}`)
}

export function assignRequest(id: string, body: AssignBody) {
  return api.patch<RequestDetail>(`/v1/requests/${id}/assign`, body)
}

/** §09 convention: sends/mutating POSTs carry a fresh Idempotency-Key per user action. */
export function approveRequest(id: string) {
  return api.post<RequestDetail>(`/v1/requests/${id}/approve`, undefined, { 'Idempotency-Key': crypto.randomUUID() })
}

export function escalateRequest(id: string, reason: string) {
  return api.post<RequestDetail>(`/v1/requests/${id}/escalate`, { reason }, { 'Idempotency-Key': crypto.randomUUID() })
}

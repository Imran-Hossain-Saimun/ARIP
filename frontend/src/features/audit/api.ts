import { api } from '@/lib/api'
import type { AuditEventOut, ChainVerifyResult } from './types'

export function listAuditEvents(filters: { type?: string; actor?: string } = {}) {
  const query = new URLSearchParams()
  if (filters.type) query.set('type', filters.type)
  if (filters.actor) query.set('actor', filters.actor)
  const qs = query.toString()
  return api.get<AuditEventOut[]>(`/v1/audit${qs ? `?${qs}` : ''}`)
}

export function verifyChain() {
  return api.get<ChainVerifyResult>('/v1/audit/verify')
}

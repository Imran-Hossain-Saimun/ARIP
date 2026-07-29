import { api } from '@/lib/api'
import type { DecisionTrace, ReplayResult } from './types'

export function getDecisionTrace(decisionId: string) {
  return api.get<DecisionTrace>(`/v1/decisions/${decisionId}/trace`)
}

export function replayDecision(decisionId: string) {
  return api.post<ReplayResult>(`/v1/decisions/${decisionId}/replay`, undefined, { 'Idempotency-Key': crypto.randomUUID() })
}

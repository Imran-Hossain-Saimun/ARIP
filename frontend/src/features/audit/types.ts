export interface AuditEventOut {
  id: string
  event_type: string
  actor: string
  object_ref: string
  payload: Record<string, unknown>
  prev_hash: string | null
  hash: string
  occurred_at: string
}

export interface ChainVerifyResult {
  valid: boolean
  event_count: number
  broken_at_id: string | null
}

export interface TraceEvidence {
  chunk_id: string | null
  article: string
  version: string
  locator: string
  mode: string
  score: number
}

export interface TraceRule {
  id: string
  outcome: string
  priority: number
}

export interface TraceStage {
  key: string
  ms: number
  meta: Record<string, unknown>
}

export interface DecisionTrace {
  decision_id: string
  request_id: string
  type: string
  confidence: number
  threshold: number
  signals: Record<string, number>
  stages: TraceStage[]
  evidence: TraceEvidence[]
  rules: TraceRule[]
  model: string
  prompt_version: string | null
  audit_hash: string | null
}

export interface ReplayResult {
  decision_id: string
  replayed: boolean
  message: string
}

export interface PipelineStageOut {
  key: string
  ms: number
  meta: Record<string, unknown>
}

export interface RunPipelineResponse {
  request_id: string
  reference: string
  decision_id: string
  decision_type: string
  confidence: number
  rule_overridden: boolean
  stages: PipelineStageOut[]
}

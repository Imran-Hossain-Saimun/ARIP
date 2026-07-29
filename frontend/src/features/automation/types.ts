export type ConfigResourceKind = 'workflow' | 'business_rule' | 'prompt_template' | 'routing_rule'
export type ConfigResourceStatus = 'draft' | 'active' | 'archived'

export interface ConfigResourceOut {
  id: string
  key: string
  name: string
  version: number
  status: ConfigResourceStatus
  config: Record<string, unknown>
  description: string | null
  activated_at: string | null
  created_at: string
}

export interface SimulateResult {
  window_days: number
  matched: number
  would_change_outcome: number
}

export interface WorkflowActionOut {
  id: string
  action_type: string
  status: 'succeeded' | 'failed' | 'retried'
  error_message: string | null
  executed_at: string
}

export interface WorkflowRunOut {
  id: string
  workflow_key: string
  request_id: string | null
  status: 'running' | 'succeeded' | 'failed'
  started_at: string
  finished_at: string | null
  actions: WorkflowActionOut[]
}

export type Channel = 'web' | 'email'

export type RequestStatus =
  | 'received'
  | 'processing'
  | 'awaiting_customer'
  | 'awaiting_approval'
  | 'answered'
  | 'held'
  | 'routed'
  | 'in_progress'
  | 'resolved'
  | 'reopened'

export type Priority = 'low' | 'medium' | 'high' | 'urgent'

export type MessageAuthor = 'customer' | 'agent' | 'ai' | 'system'

export type DecisionType = 'auto_reply' | 'draft_reply' | 'ask_clarification' | 'route' | 'hold'

export interface CustomerOut {
  id: string
  email: string
  full_name: string
}

export interface MessageOut {
  id: string
  author: MessageAuthor
  body: string
  created_at: string
}

export interface EvidenceOut {
  id: string
  retrieval_mode: string
  score: number
  locator: string
  article_ref: string
  version_ref: string
}

export interface RuleEvaluationOut {
  rule_code: string
  outcome: string
  priority: number
}

export interface DecisionOut {
  id: string
  type: DecisionType
  confidence: number
  threshold: number
  signals: Record<string, number>
  model: string
  latency_ms: number
  rule_overridden: boolean
  created_at: string
  evidence: EvidenceOut[]
  rule_evaluations: RuleEvaluationOut[]
}

export interface RequestListItem {
  id: string
  reference: string
  channel: Channel
  status: RequestStatus
  priority: Priority
  intent: string | null
  category: string | null
  department_id: string | null
  assignee_id: string | null
  sla_first_response_due: string | null
  created_at: string
  customer: CustomerOut
  latest_confidence: number | null
}

export interface RequestDetail extends RequestListItem {
  messages: MessageOut[]
  attachments: unknown[]
  decisions: DecisionOut[]
}

export interface RequestListResponse {
  items: RequestListItem[]
  next_cursor: string | null
}

export interface AssignBody {
  assignee_id?: string
  department_id?: string
}

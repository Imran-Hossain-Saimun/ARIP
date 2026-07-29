import type { KpiValue } from '@/features/analytics/types'

export interface SlaRiskItem {
  id: string
  reference: string
  subject: string | null
  sla_first_response_due: string | null
}

export interface DecisionMixSlice {
  type: string
  count: number
}

export interface SystemHealthTile {
  llm_provider_p50_ms: number | null
  pgvector_chunk_count: number | null
  email_queue_depth: number | null
  workflow_workers_healthy: string | null
}

export interface DashboardSummary {
  role: string
  role_scope: string
  system_health: SystemHealthTile

  awaiting_approval_count: number | null
  sla_breach_soon: SlaRiskItem[] | null
  decision_mix_24h: DecisionMixSlice[] | null

  open_gap_count: number | null
  top_gap_cluster_key: string | null
  top_gap_occurrence_count: number | null
  articles_expiring_30d: number | null

  kpis: KpiValue[] | null

  decision_volume_24h: number | null
  override_count_24h: number | null
  unresolved_exceptions: number | null
}

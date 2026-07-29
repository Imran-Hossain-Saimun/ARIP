export interface KpiValue {
  key: string
  label: string
  value: number | null
  target: number | null
  unit: string
}

export interface FunnelStage {
  type: string
  count: number
}

export interface CitedArticle {
  article_ref: string
  citation_count: number
}

export interface AnalyticsKpis {
  window_days: number
  kpis: KpiValue[]
  automation_funnel: FunnelStage[]
  most_cited_knowledge: CitedArticle[]
}

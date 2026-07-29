export type KnowledgeVersionStatus = 'draft' | 'review' | 'approved' | 'indexed' | 'archived'
export type AccessLevel = 'public' | 'internal' | 'restricted'

export interface KnowledgeVersionOut {
  id: string
  version: string
  status: KnowledgeVersionStatus
  effective_from: string
  expires_on: string | null
  access_level: AccessLevel
  indexed_at: string | null
  created_at: string
}

export interface KnowledgeArticleListItem {
  id: string
  title: string
  department_id: string | null
  category: string | null
  tags: string[]
  latest_version: KnowledgeVersionOut | null
}

export interface KnowledgeArticleDetail extends KnowledgeArticleListItem {
  versions: KnowledgeVersionOut[]
}

export interface KnowledgeGapOut {
  id: string
  cluster_key: string
  occurrence_count: number
  avg_confidence: number
  status: 'open' | 'drafting' | 'closed'
  sample_request_refs: string[]
  created_at: string
}

export interface IngestBody {
  title: string
  version?: string
  department_id?: string
  category?: string
  access_level?: AccessLevel
  content: string
}

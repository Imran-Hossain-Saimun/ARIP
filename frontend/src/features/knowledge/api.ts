import { api } from '@/lib/api'
import type { IngestBody, KnowledgeArticleDetail, KnowledgeArticleListItem, KnowledgeGapOut, KnowledgeVersionOut } from './types'

export function listKnowledge(params: { status?: string; departmentId?: string; q?: string } = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.departmentId) query.set('department_id', params.departmentId)
  if (params.q) query.set('q', params.q)
  const qs = query.toString()
  return api.get<KnowledgeArticleListItem[]>(`/v1/knowledge${qs ? `?${qs}` : ''}`)
}

export function getKnowledgeArticle(id: string) {
  return api.get<KnowledgeArticleDetail>(`/v1/knowledge/${id}`)
}

export function ingestKnowledge(body: IngestBody) {
  const form = new FormData()
  form.set('title', body.title)
  if (body.version) form.set('version', body.version)
  if (body.department_id) form.set('department_id', body.department_id)
  if (body.category) form.set('category', body.category)
  if (body.access_level) form.set('access_level', body.access_level)
  form.set('content', body.content)
  return api.postForm<{ article_id: string; version_id: string }>('/v1/knowledge/ingest', form)
}

export function approveKnowledgeVersion(articleId: string, version: string) {
  return api.post<KnowledgeVersionOut>(`/v1/knowledge/${articleId}/versions/${version}/approve`, {})
}

export function listKnowledgeGaps() {
  return api.get<KnowledgeGapOut[]>('/v1/gaps')
}

import { useQuery } from '@tanstack/react-query'
import { EmptyState, ErrorState, StatusBadge } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { listKnowledgeGaps } from './api'

export function KnowledgeGapsPage() {
  const { data: gaps, isLoading, error, refetch } = useQuery({ queryKey: ['knowledge-gaps'], queryFn: listKnowledgeGaps })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load knowledge gaps.'} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display font-bold text-text-primary">Knowledge gaps</h1>
        <p className="mt-1 text-body text-text-secondary">Clusters of requests the AI answered with low confidence — ranked by how often they occur.</p>
      </div>

      {isLoading && <div className="text-text-muted">Loading…</div>}
      {!isLoading && (gaps?.length ?? 0) === 0 && <EmptyState headline="No gaps detected" description="Every request cluster is answering with healthy confidence." />}

      <div className="space-y-2">
        {gaps?.map((gap) => (
          <div key={gap.id} className="flex items-center justify-between rounded-card border border-border bg-surface p-4">
            <div>
              <div className="font-medium text-text-primary">{gap.cluster_key.replace('_', ' ')}</div>
              <div className="text-small text-text-muted">
                {gap.occurrence_count} occurrences · avg confidence {Math.round(gap.avg_confidence * 100)}% · e.g. {gap.sample_request_refs[0]}
              </div>
            </div>
            <StatusBadge variant={gap.status === 'open' ? 'danger' : gap.status === 'drafting' ? 'warning' : 'success'} label={gap.status} />
          </div>
        ))}
      </div>
    </div>
  )
}

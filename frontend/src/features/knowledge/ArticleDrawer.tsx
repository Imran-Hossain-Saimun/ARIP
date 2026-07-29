import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { Drawer, ErrorState, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { usePermission } from '@/lib/usePermission'
import { approveKnowledgeVersion, getKnowledgeArticle } from './api'
import type { KnowledgeVersionStatus } from './types'

const LIFECYCLE: KnowledgeVersionStatus[] = ['draft', 'review', 'approved', 'indexed', 'archived']

const STATUS_VARIANT: Record<KnowledgeVersionStatus, BadgeVariant> = {
  draft: 'neutral',
  review: 'warning',
  approved: 'brand',
  indexed: 'success',
  archived: 'neutral',
}

function LifecycleStepper({ current }: { current: KnowledgeVersionStatus }) {
  const currentIndex = LIFECYCLE.indexOf(current)
  return (
    <div className="flex items-center gap-1">
      {LIFECYCLE.map((stage, i) => (
        <div key={stage} className="flex-1">
          <div className={`h-1.5 rounded-full ${i <= currentIndex ? 'bg-brand' : 'bg-surface-sunken'}`} />
        </div>
      ))}
      <span className="ml-2 shrink-0 text-small capitalize text-text-secondary">{current}</span>
    </div>
  )
}

export interface ArticleDrawerProps {
  articleId: string | null
  onClose: () => void
}

export function ArticleDrawer({ articleId, onClose }: ArticleDrawerProps) {
  const queryClient = useQueryClient()
  const canApprove = usePermission('knowledge_approval', 'approve')

  const { data: article, isLoading, error } = useQuery({
    queryKey: ['knowledge-article', articleId],
    queryFn: () => getKnowledgeArticle(articleId!),
    enabled: !!articleId,
  })

  const approveMutation = useMutation({
    mutationFn: (version: string) => approveKnowledgeVersion(articleId!, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-article', articleId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge'] })
    },
  })

  const latest = article?.versions[0]

  return (
    <Drawer open={!!articleId} onClose={onClose} title={article?.title ?? 'Article'}>
      <div className="space-y-4 p-4">
        {isLoading && <div className="text-text-muted">Loading…</div>}
        {error && <ErrorState message={error instanceof ApiError ? error.message : 'Could not load this article.'} />}
        {article && latest && (
          <>
            <LifecycleStepper current={latest.status} />

            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-small">
              <dt className="text-text-muted">Category</dt>
              <dd className="text-right text-text-primary">{article.category ?? '—'}</dd>
              <dt className="text-text-muted">Access level</dt>
              <dd className="text-right capitalize text-text-primary">{latest.access_level}</dd>
              <dt className="text-text-muted">Effective from</dt>
              <dd className="text-right text-text-primary">{latest.effective_from}</dd>
              <dt className="text-text-muted">Expires on</dt>
              <dd className="text-right text-text-primary">{latest.expires_on ?? '—'}</dd>
              <dt className="text-text-muted">Indexed at</dt>
              <dd className="text-right text-text-primary">{latest.indexed_at ? new Date(latest.indexed_at).toLocaleString() : '—'}</dd>
            </dl>

            {canApprove && (latest.status === 'draft' || latest.status === 'review') && (
              <button
                type="button"
                onClick={() => approveMutation.mutate(latest.version)}
                disabled={approveMutation.isPending}
                className="flex h-8 items-center gap-1.5 rounded-control bg-success px-3 text-small font-medium text-white hover:opacity-90 disabled:opacity-60"
              >
                <Check size={14} /> Approve &amp; index {latest.version}
              </button>
            )}

            <section>
              <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Version history</h3>
              <div className="space-y-1.5">
                {article.versions.map((v) => (
                  <div key={v.id} className="flex items-center justify-between rounded-control border border-border px-3 py-2 text-small">
                    <span className="font-mono">{v.version}</span>
                    <StatusBadge variant={STATUS_VARIANT[v.status]} label={v.status} />
                    <span className="text-text-muted">{new Date(v.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </Drawer>
  )
}

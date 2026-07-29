import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ShieldCheck, ShieldX } from 'lucide-react'
import { EmptyState, ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { listAuditEvents, verifyChain } from './api'

export function AuditLogPage() {
  const [typeFilter, setTypeFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')

  const { data: events, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-events', typeFilter, actorFilter],
    queryFn: () => listAuditEvents({ type: typeFilter || undefined, actor: actorFilter || undefined }),
  })

  const verifyMutation = useMutation({ mutationFn: verifyChain })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load the audit log.'} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display font-bold text-text-primary">Audit log</h1>
          <p className="mt-1 text-body text-text-secondary">Immutable, sha256 hash-chained event stream — every mutation in the system writes here.</p>
        </div>
        <button
          type="button"
          onClick={() => verifyMutation.mutate()}
          disabled={verifyMutation.isPending}
          className="flex h-8 items-center gap-1.5 rounded-control border border-border-strong px-3 text-small font-medium hover:bg-surface-sunken disabled:opacity-60"
        >
          {verifyMutation.data?.valid === false ? <ShieldX size={14} className="text-danger" /> : <ShieldCheck size={14} />}
          Verify chain
        </button>
      </div>

      {verifyMutation.data && (
        <div className={`rounded-card border p-3 text-small ${verifyMutation.data.valid ? 'border-success-border bg-success-tint text-success' : 'border-danger-border bg-danger-tint text-danger'}`}>
          {verifyMutation.data.valid
            ? `Chain verified: all ${verifyMutation.data.event_count} events form an unbroken hash chain.`
            : `Chain broken at event ${verifyMutation.data.broken_at_id} — investigate immediately.`}
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          placeholder="Filter by event type…"
          className="h-8 flex-1 rounded-control border border-border-strong px-2.5 text-small outline-none focus:border-brand"
        />
        <input
          value={actorFilter}
          onChange={(e) => setActorFilter(e.target.value)}
          placeholder="Filter by actor…"
          className="h-8 flex-1 rounded-control border border-border-strong px-2.5 text-small outline-none focus:border-brand"
        />
      </div>

      {isLoading && <div className="text-text-muted">Loading…</div>}
      {!isLoading && (events?.length ?? 0) === 0 && <EmptyState headline="No events match" description="Try clearing the filters." />}

      <div className="scroller max-h-[70vh] space-y-1 overflow-y-auto">
        {events?.map((e) => (
          <div key={e.id} className="rounded-control border border-border p-2.5 text-small">
            <div className="flex items-center justify-between">
              <span className="font-mono font-medium text-text-primary">{e.event_type}</span>
              <span className="text-text-muted">{new Date(e.occurred_at).toLocaleString()}</span>
            </div>
            <div className="text-text-secondary">
              {e.actor} → <span className="font-mono">{e.object_ref}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

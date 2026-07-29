import { EmptyState, SkeletonRow, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { cn } from '@/lib/cn'
import { getConfidenceBand } from '@/lib/confidence'
import type { RequestListItem, RequestStatus } from './types'

const STATUS_VARIANT: Record<RequestStatus, BadgeVariant> = {
  received: 'neutral',
  processing: 'brand',
  awaiting_customer: 'warning',
  awaiting_approval: 'brand',
  answered: 'success',
  held: 'ai',
  routed: 'danger',
  in_progress: 'brand',
  resolved: 'success',
  reopened: 'warning',
}

const BAND_VARIANT: Record<string, BadgeVariant> = {
  auto_reply: 'success',
  draft: 'brand',
  clarify: 'warning',
  escalate: 'danger',
}

export interface RequestListProps {
  requests: RequestListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  loading?: boolean
}

/**
 * §10 `RequestRow` — a compact 2-line card, not a wide data table. The 420px list pane
 * has no room for column headers; density comes from row height, not columns.
 */
export function RequestList({ requests, selectedId, onSelect, loading }: RequestListProps) {
  if (loading) {
    return (
      <div className="rounded-card border border-border bg-surface">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonRow key={i} height={52} columnWidths={['30%', '50%']} />
        ))}
      </div>
    )
  }

  if (requests.length === 0) {
    return <EmptyState headline="No requests" description="Nothing matches the current filters." />
  }

  return (
    <div className="flex flex-col gap-1">
      {requests.map((r) => {
        const selected = r.id === selectedId
        return (
          <button
            key={r.id}
            type="button"
            onClick={() => onSelect(r.id)}
            className={cn(
              'flex flex-col gap-1 rounded-control border px-3 py-2 text-left',
              selected ? 'border-l-2 border-brand bg-brand-tint' : 'border-transparent hover:bg-surface-sunken',
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-mono text-small text-text-muted">{r.reference}</span>
              <span className="shrink-0 text-small capitalize text-text-muted">{r.channel}</span>
            </div>
            <div className="truncate text-body font-medium text-text-primary">{r.customer.full_name}</div>
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-small text-text-secondary">
                {r.category ?? 'Uncategorized'}
                {r.intent ? ` · ${r.intent}` : ''}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusBadge variant={STATUS_VARIANT[r.status]} label={r.status.replace('_', ' ')} />
              {r.latest_confidence !== null && (
                <StatusBadge
                  variant={BAND_VARIANT[getConfidenceBand(r.latest_confidence)]}
                  label={getConfidenceBand(r.latest_confidence).replace('_', ' ')}
                  confidence={r.latest_confidence}
                />
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}

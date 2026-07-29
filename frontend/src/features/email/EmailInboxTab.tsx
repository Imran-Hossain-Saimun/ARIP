import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { EmptyState, ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { listRequests } from '@/features/requests/api'
import { RequestList } from '@/features/requests/RequestList'
import { RequestRecord } from '@/features/requests/RequestRecord'

/** The "unified inbox" is the same Request spine as the web channel, filtered to
 * `channel=email` — email doesn't get its own parallel data model (§09: everything hangs
 * off Request). Reuses the exact list/record components the request queue uses. */
export function EmailInboxTab() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['requests', { channel: 'email' }],
    queryFn: () => listRequests({ channel: 'email' }),
  })

  const items = data?.items ?? []

  useEffect(() => {
    if (!selectedId && items.length > 0) setSelectedId(items[0].id)
  }, [items, selectedId])

  if (error) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : 'Could not load the email inbox.'}
        traceId={error instanceof ApiError ? (error.traceId ?? undefined) : undefined}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="grid h-[calc(100vh-56px-42px)] grid-cols-[380px_minmax(0,1fr)] gap-4">
      <div className="scroller overflow-y-auto border-r border-border p-3">
        <div className="mb-2 px-1 text-small text-text-muted">{items.length} email thread{items.length === 1 ? '' : 's'}</div>
        <RequestList requests={items} selectedId={selectedId} onSelect={setSelectedId} loading={isLoading} />
      </div>
      <div className="min-w-0">
        {selectedId ? <RequestRecord requestId={selectedId} /> : <EmptyState headline="No thread selected" description="Choose an email thread from the list." />}
      </div>
    </div>
  )
}

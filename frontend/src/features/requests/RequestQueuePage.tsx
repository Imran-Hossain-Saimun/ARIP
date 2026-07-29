import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { EmptyState, ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { listRequests } from './api'
import { RequestList } from './RequestList'
import { RequestRecord } from './RequestRecord'

function isTypingInField(): boolean {
  const el = document.activeElement
  return el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement
}

export function RequestQueuePage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['requests'],
    queryFn: () => listRequests(),
  })

  const items = data?.items ?? []

  useEffect(() => {
    if (!selectedId && items.length > 0) setSelectedId(items[0].id)
  }, [items, selectedId])

  const selectedIndex = useMemo(() => items.findIndex((r) => r.id === selectedId), [items, selectedId])

  const selectNext = useCallback(() => {
    if (items.length === 0) return
    const next = items[Math.min(selectedIndex + 1, items.length - 1)]
    setSelectedId(next?.id ?? null)
  }, [items, selectedIndex])

  const selectPrev = useCallback(() => {
    if (items.length === 0) return
    const prev = items[Math.max(selectedIndex - 1, 0)]
    setSelectedId(prev?.id ?? null)
  }, [items, selectedIndex])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (isTypingInField()) return
      if (e.key === 'j' || e.key === 'ArrowDown') { e.preventDefault(); selectNext() }
      else if (e.key === 'k' || e.key === 'ArrowUp') { e.preventDefault(); selectPrev() }
      // Escape is NOT bound to deselecting the row here — the Drawer primitive already
      // owns Escape to close itself, and firing both on the same keypress deselected the
      // row out from under the drawer close. 'A'/'E' are handled inside RequestRecord's
      // own buttons — wiring global A/E shortcuts here would fight with typing "a"/"e" in
      // the escalate reason textarea; RequestRecord's isTypingInField guard covers it.
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectNext, selectPrev])

  if (error) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : 'Could not load the request queue.'}
        traceId={error instanceof ApiError ? (error.traceId ?? undefined) : undefined}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="grid h-[calc(100vh-56px-48px)] grid-cols-[420px_minmax(0,1fr)] gap-4 -m-6">
      <div className="scroller overflow-y-auto border-r border-border p-3">
        <div className="mb-2 px-1 text-small text-text-muted">
          {items.length} request{items.length === 1 ? '' : 's'} · <span className="font-mono">J</span>/<span className="font-mono">K</span> to navigate
        </div>
        <RequestList requests={items} selectedId={selectedId} onSelect={setSelectedId} loading={isLoading} />
      </div>
      <div className="min-w-0">
        {selectedId ? (
          <RequestRecord requestId={selectedId} onActionComplete={selectNext} />
        ) : (
          <EmptyState headline="Select a request" description="Choose a request from the list to see its details." />
        )}
      </div>
    </div>
  )
}

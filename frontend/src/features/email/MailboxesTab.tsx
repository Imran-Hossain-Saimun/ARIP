import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Check, RefreshCw } from 'lucide-react'
import { EmptyState, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { listMailboxes, listParseFailures, resolveParseFailure, syncMailbox } from './api'
import type { MailboxStatus } from './types'

const STATUS_VARIANT: Record<MailboxStatus, BadgeVariant> = {
  connected: 'success',
  disconnected: 'neutral',
  error: 'danger',
}

export function MailboxesTab() {
  const queryClient = useQueryClient()
  const { data: mailboxes } = useQuery({ queryKey: ['mailboxes'], queryFn: listMailboxes })
  const { data: failures } = useQuery({ queryKey: ['parse-failures'], queryFn: () => listParseFailures(false) })

  const syncMutation = useMutation({
    mutationFn: (id: string) => syncMailbox(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailboxes'] })
      queryClient.invalidateQueries({ queryKey: ['parse-failures'] })
      queryClient.invalidateQueries({ queryKey: ['requests'] })
    },
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => resolveParseFailure(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['parse-failures'] }),
  })

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-2 text-h1 font-semibold text-text-primary">Mailboxes</h2>
        <div className="space-y-2">
          {mailboxes?.map((mb) => (
            <div key={mb.id} className="flex items-center justify-between rounded-card border border-border bg-surface p-4">
              <div>
                <div className="font-medium text-text-primary">{mb.name}</div>
                <div className="text-small text-text-muted">{mb.email_address} · {mb.provider}</div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge variant={STATUS_VARIANT[mb.status]} label={mb.status} />
                <span className="text-small text-text-muted">
                  {mb.last_synced_at ? `Synced ${new Date(mb.last_synced_at).toLocaleTimeString()}` : 'Never synced'}
                </span>
                <button
                  type="button"
                  onClick={() => syncMutation.mutate(mb.id)}
                  disabled={syncMutation.isPending}
                  className="flex h-8 items-center gap-1.5 rounded-control border border-border-strong px-3 text-small font-medium hover:bg-surface-sunken disabled:opacity-60"
                >
                  <RefreshCw size={14} /> Sync now
                </button>
              </div>
            </div>
          ))}
        </div>
        {syncMutation.data && (
          <p className="mt-2 text-small text-text-muted">
            Last sync: {syncMutation.data.created} created, {syncMutation.data.threaded} threaded, {syncMutation.data.failed} failed.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-h1 font-semibold text-text-primary">Parse-failure queue</h2>
        {(failures?.length ?? 0) === 0 ? (
          <EmptyState headline="No parse failures" description="Every inbound message has been turned into a request." />
        ) : (
          <div className="space-y-2">
            {failures?.map((f) => (
              <div key={f.id} className="flex items-center justify-between gap-3 rounded-card border border-danger-border bg-danger-tint p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={16} className="mt-0.5 shrink-0 text-danger" />
                  <div>
                    <div className="text-body font-medium text-text-primary">{f.raw_subject || '(no subject)'}</div>
                    <div className="text-small text-text-muted">{f.raw_from || '(no sender)'} · {f.error_message}</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate(f.id)}
                  className="flex h-8 shrink-0 items-center gap-1.5 rounded-control border border-border-strong bg-surface px-3 text-small font-medium hover:bg-surface-sunken"
                >
                  <Check size={14} /> Resolve
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

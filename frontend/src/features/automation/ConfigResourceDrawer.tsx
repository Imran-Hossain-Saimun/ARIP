import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCcw } from 'lucide-react'
import { Drawer, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { usePermission } from '@/lib/usePermission'
import type { Module } from '@/lib/rbac'
import { listVersions, publishResource, rollbackResource } from './api'
import type { ConfigResourceKind, ConfigResourceStatus } from './types'

const STATUS_VARIANT: Record<ConfigResourceStatus, BadgeVariant> = {
  draft: 'neutral',
  active: 'success',
  archived: 'neutral',
}

export interface ConfigResourceDrawerProps {
  kind: ConfigResourceKind
  module: Module
  resourceKey: string | null
  onClose: () => void
}

export function ConfigResourceDrawer({ kind, module, resourceKey, onClose }: ConfigResourceDrawerProps) {
  const queryClient = useQueryClient()
  const canApprove = usePermission(module, 'approve')

  const { data: versions } = useQuery({
    queryKey: ['automation-versions', kind, resourceKey],
    queryFn: () => listVersions(kind, resourceKey!),
    enabled: !!resourceKey,
  })

  const publishMutation = useMutation({
    mutationFn: (id: string) => publishResource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automation-current', kind] })
      queryClient.invalidateQueries({ queryKey: ['automation-versions', kind, resourceKey] })
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: (version: number) => rollbackResource(kind, resourceKey!, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automation-current', kind] })
      queryClient.invalidateQueries({ queryKey: ['automation-versions', kind, resourceKey] })
    },
  })

  const latest = versions?.[0]

  return (
    <Drawer open={!!resourceKey} onClose={onClose} title={latest?.name ?? resourceKey ?? ''}>
      <div className="space-y-4 p-4">
        {latest?.description && <p className="text-body text-text-secondary">{latest.description}</p>}

        <section>
          <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Config</h3>
          <pre className="scroller max-h-64 overflow-auto rounded-control bg-surface-sunken p-3 font-mono text-small">
            {JSON.stringify(latest?.config, null, 2)}
          </pre>
        </section>

        <section>
          <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Version history</h3>
          <div className="space-y-1.5">
            {versions?.map((v) => (
              <div key={v.id} className="flex items-center justify-between rounded-control border border-border px-3 py-2 text-small">
                <span className="font-mono">v{v.version}</span>
                <StatusBadge variant={STATUS_VARIANT[v.status]} label={v.status} />
                <span className="text-text-muted">{new Date(v.created_at).toLocaleDateString()}</span>
                {canApprove && v.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => publishMutation.mutate(v.id)}
                    disabled={publishMutation.isPending}
                    className="h-7 rounded-control bg-success px-2 text-small font-medium text-white hover:opacity-90 disabled:opacity-60"
                  >
                    Publish
                  </button>
                )}
                {canApprove && v.status === 'archived' && (
                  <button
                    type="button"
                    onClick={() => rollbackMutation.mutate(v.version)}
                    disabled={rollbackMutation.isPending}
                    className="flex h-7 items-center gap-1 rounded-control border border-border-strong px-2 text-small font-medium hover:bg-surface-sunken disabled:opacity-60"
                  >
                    <RotateCcw size={12} /> Roll back
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </Drawer>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { EmptyState, ErrorState, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import type { Module } from '@/lib/rbac'
import { usePermission } from '@/lib/usePermission'
import { listCurrent } from './api'
import { ConfigResourceDrawer } from './ConfigResourceDrawer'
import { CreateDraftForm } from './CreateDraftForm'
import type { ConfigResourceKind, ConfigResourceStatus } from './types'

const STATUS_VARIANT: Record<ConfigResourceStatus, BadgeVariant> = {
  draft: 'neutral',
  active: 'success',
  archived: 'neutral',
}

export interface ConfigResourceListPageProps {
  kind: ConfigResourceKind
  module: Module
  title: string
  description: string
  configPlaceholder: string
  /** Extra content rendered above the list — e.g. the rule simulator or workflow runs. */
  extra?: React.ReactNode
}

/**
 * One generic list screen, reused for all four automation surfaces (workflows, business
 * rules, prompts, routing rules) — mirrors the backend's single ConfigResource table.
 */
export function ConfigResourceListPage({ kind, module, title, description, configPlaceholder, extra }: ConfigResourceListPageProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const canAuthor = usePermission(module, 'write')

  const { data: resources, isLoading, error, refetch } = useQuery({
    queryKey: ['automation-current', kind],
    queryFn: () => listCurrent(kind),
  })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : `Could not load ${title.toLowerCase()}.`} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display font-bold text-text-primary">{title}</h1>
          <p className="mt-1 text-body text-text-secondary">{description}</p>
        </div>
        {canAuthor && (
          <button
            type="button"
            onClick={() => setFormOpen(true)}
            className="flex h-8 shrink-0 items-center gap-1.5 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover"
          >
            <Plus size={14} /> New draft
          </button>
        )}
      </div>

      {extra}

      {isLoading && <div className="text-text-muted">Loading…</div>}
      {!isLoading && (resources?.length ?? 0) === 0 && (
        <EmptyState headline={`No ${title.toLowerCase()} yet`} description="Create the first draft to get started." />
      )}

      <div className="space-y-2">
        {resources?.map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => setSelectedKey(r.key)}
            className="flex w-full items-center justify-between rounded-card border border-border bg-surface p-4 text-left hover:bg-surface-sunken"
          >
            <div>
              <div className="font-medium text-text-primary">{r.name}</div>
              <div className="font-mono text-small text-text-muted">{r.key} · v{r.version}</div>
            </div>
            <StatusBadge variant={STATUS_VARIANT[r.status]} label={r.status} />
          </button>
        ))}
      </div>

      <ConfigResourceDrawer kind={kind} module={module} resourceKey={selectedKey} onClose={() => setSelectedKey(null)} />
      <CreateDraftForm kind={kind} open={formOpen} onClose={() => setFormOpen(false)} configPlaceholder={configPlaceholder} />
    </div>
  )
}

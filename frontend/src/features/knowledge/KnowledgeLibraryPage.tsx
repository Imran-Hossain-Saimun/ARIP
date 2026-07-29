import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { DataTable, EmptyState, ErrorState, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { usePermission } from '@/lib/usePermission'
import { listKnowledge } from './api'
import { ArticleDrawer } from './ArticleDrawer'
import { IngestArticleForm } from './IngestArticleForm'
import type { KnowledgeArticleListItem, KnowledgeVersionStatus } from './types'

const STATUS_VARIANT: Record<KnowledgeVersionStatus, BadgeVariant> = {
  draft: 'neutral',
  review: 'warning',
  approved: 'brand',
  indexed: 'success',
  archived: 'neutral',
}

export function KnowledgeLibraryPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const canAuthor = usePermission('knowledge_authoring', 'write')

  const { data: articles, isLoading, error, refetch } = useQuery({
    queryKey: ['knowledge'],
    queryFn: () => listKnowledge(),
  })

  const kpis = useMemo(() => {
    const list = articles ?? []
    const byStatus = (s: KnowledgeVersionStatus) => list.filter((a) => a.latest_version?.status === s).length
    return [
      { label: 'Total articles', value: list.length },
      { label: 'Draft / review', value: byStatus('draft') + byStatus('review') },
      { label: 'Indexed', value: byStatus('indexed') },
      { label: 'Archived', value: byStatus('archived') },
    ]
  }, [articles])

  const columns: ColumnDef<KnowledgeArticleListItem, any>[] = [
    { accessorKey: 'title', header: 'Title', size: 260 },
    { id: 'category', header: 'Category', size: 140, cell: ({ row }) => row.original.category ?? '—' },
    {
      id: 'status',
      header: 'Status',
      size: 140,
      cell: ({ row }) => {
        const v = row.original.latest_version
        return v ? <StatusBadge variant={STATUS_VARIANT[v.status]} label={v.status} /> : <span className="text-text-muted">—</span>
      },
    },
    { id: 'version', header: 'Version', size: 100, cell: ({ row }) => <span className="font-mono">{row.original.latest_version?.version ?? '—'}</span> },
  ]

  if (error) {
    return (
      <ErrorState message={error instanceof ApiError ? error.message : 'Could not load the knowledge library.'} onRetry={() => refetch()} />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-display font-bold text-text-primary">Knowledge base</h1>
        {canAuthor && (
          <button
            type="button"
            onClick={() => setFormOpen(true)}
            className="flex h-8 items-center gap-1.5 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover"
          >
            <Plus size={14} /> Add article
          </button>
        )}
      </div>

      <div className="grid grid-cols-4 gap-3">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-card border border-border bg-surface p-3">
            <div className="text-h1 font-bold text-text-primary">{kpi.value}</div>
            <div className="text-small text-text-muted">{kpi.label}</div>
          </div>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={articles ?? []}
        getRowId={(a) => a.id}
        selectedRowId={selectedId ?? undefined}
        onRowClick={(a) => setSelectedId(a.id)}
        loading={isLoading}
        emptyState={<EmptyState headline="No knowledge articles yet" description="Add the first article to start building the AI's knowledge base." />}
      />

      <ArticleDrawer articleId={selectedId} onClose={() => setSelectedId(null)} />
      <IngestArticleForm open={formOpen} onClose={() => setFormOpen(false)} />
    </div>
  )
}

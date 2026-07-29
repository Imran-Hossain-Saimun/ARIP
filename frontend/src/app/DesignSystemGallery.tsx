import { useState } from 'react'
import { AlertTriangle, Inbox } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import {
  CitationChip,
  ConfidenceMeter,
  DataTable,
  Drawer,
  EmptyState,
  ErrorState,
  SkeletonRow,
  StatusBadge,
} from '@/design-system/primitives'

/** Dev-only reference page (`/design-system`) for the §04 primitives — not part of the RBAC nav. */
interface DemoRequest {
  id: string
  subject: string
  channel: string
  confidence: number
}

const demoColumns: ColumnDef<DemoRequest, any>[] = [
  { accessorKey: 'id', header: 'Reference', size: 100 },
  { accessorKey: 'subject', header: 'Subject', size: 240 },
  { accessorKey: 'channel', header: 'Channel', size: 100 },
  {
    accessorKey: 'confidence',
    header: 'Confidence',
    size: 140,
    cell: (info) => <ConfidenceMeter value={info.getValue<number>()} />,
  },
]

const demoRows: DemoRequest[] = [
  { id: 'REQ-24817', subject: 'Card dispute — timing of refund', channel: 'Email', confidence: 0.91 },
  { id: 'REQ-24818', subject: 'Address change request', channel: 'Web', confidence: 0.97 },
  { id: 'REQ-24819', subject: 'Loan restructuring question', channel: 'Email', confidence: 0.52 },
]

export function DesignSystemGallery() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="mx-auto max-w-[var(--width-content-max)] space-y-10 p-8">
      <header>
        <h1 className="text-display font-bold text-text-primary">ARIP design system</h1>
        <p className="text-body text-text-secondary">§04 primitives</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-h1 font-semibold">StatusBadge</h2>
        <div className="flex flex-wrap gap-2">
          <StatusBadge variant="success" label="Auto reply" confidence={0.97} />
          <StatusBadge variant="brand" label="Draft" confidence={0.91} />
          <StatusBadge variant="warning" label="Clarify" confidence={0.74} />
          <StatusBadge variant="danger" label="Escalate" confidence={0.52} />
          <StatusBadge variant="ai" label="Held · rule" />
        </div>
      </section>

      <section className="max-w-sm space-y-3">
        <h2 className="text-h1 font-semibold">ConfidenceMeter</h2>
        <ConfidenceMeter value={0.91} threshold={0.95} label="Draft confidence" />
      </section>

      <section className="space-y-3">
        <h2 className="text-h1 font-semibold">CitationChip</h2>
        <div className="flex flex-wrap gap-2">
          <CitationChip mode="vector" articleId="KB-0412" locator="§3.1" score={0.912} />
          <CitationChip mode="vectorless" articleId="KB-0500" locator="§1" score={0.804} onClick={() => setDrawerOpen(true)} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-h1 font-semibold">DataTable</h2>
        <DataTable columns={demoColumns} data={demoRows} getRowId={(r) => r.id} onRowClick={() => setDrawerOpen(true)} />
      </section>

      <section className="grid grid-cols-2 gap-6">
        <div>
          <h2 className="mb-3 text-h1 font-semibold">EmptyState</h2>
          <div className="rounded-card border border-border bg-surface">
            <EmptyState
              icon={<Inbox size={32} />}
              headline="No requests yet"
              description="Requests will appear here once customers submit them."
              action={{ label: 'Create request', onClick: () => {} }}
            />
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-h1 font-semibold">ErrorState</h2>
          <ErrorState message="Could not load requests." traceId="trc_9f21ab" onRetry={() => {}} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-h1 font-semibold">SkeletonRow</h2>
        <div className="rounded-card border border-border bg-surface">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      </section>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Decision trace">
        <div className="space-y-3 p-4 text-body">
          <p className="flex items-center gap-2 text-warning">
            <AlertTriangle size={16} /> Held for review — BR-022
          </p>
          <p>Drawer content placeholder; replaced with the real DecisionTrace in increment 4.</p>
        </div>
      </Drawer>
    </div>
  )
}

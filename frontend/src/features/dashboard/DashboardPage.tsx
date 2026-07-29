import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { EmptyState, ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { getDashboardSummary } from './api'

function Tile({ label, value, sub, subClass }: { label: string; value: string; sub?: string; subClass?: string }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <div className="text-small font-semibold uppercase tracking-wide text-text-muted">{label}</div>
      <div className="mt-1.5 text-h1 font-bold text-text-primary tabular-nums">{value}</div>
      {sub && <div className={`mt-1 text-small ${subClass ?? 'text-text-muted'}`}>{sub}</div>}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <div className="mb-3 text-h2 font-semibold text-text-primary">{title}</div>
      {children}
    </div>
  )
}

const REQUESTS_PATH: string = '/requests'

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['dashboard-summary'], queryFn: getDashboardSummary })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load dashboard.'} onRetry={() => refetch()} />
  }

  if (isLoading || !data) {
    return <div className="text-text-muted">Loading…</div>
  }

  const health = data.system_health
  const hasAgentTiles = data.awaiting_approval_count !== null
  const hasKnowledgeTiles = data.open_gap_count !== null
  const hasExecutiveTiles = data.kpis !== null
  const hasAuditorTiles = data.decision_volume_24h !== null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-display font-bold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-body text-text-secondary">{data.role_scope}</p>
      </div>

      {hasAgentTiles && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Tile label="Awaiting your approval" value={String(data.awaiting_approval_count)} />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="SLA risk — next to breach">
              {!data.sla_breach_soon?.length && <EmptyState headline="No SLA risk" description="Nothing is close to breaching first-response SLA." />}
              <div className="space-y-1">
                {data.sla_breach_soon?.map((r) => (
                  <Link key={r.id} to={REQUESTS_PATH} className="flex items-center gap-2 rounded-control px-2 py-1.5 text-small hover:bg-surface-sunken">
                    <span className="font-mono text-text-muted">{r.reference}</span>
                    <span className="flex-1 truncate">{r.subject ?? '—'}</span>
                    <span className="font-mono text-warning">{r.sla_first_response_due ? new Date(r.sla_first_response_due).toLocaleTimeString() : '—'}</span>
                  </Link>
                ))}
              </div>
            </Card>
            <Card title="Decision mix · last 24h">
              {!data.decision_mix_24h?.length && <EmptyState headline="No decisions yet" description="No decisions recorded in the last 24 hours." />}
              <div className="space-y-1.5">
                {data.decision_mix_24h?.map((slice) => (
                  <div key={slice.type} className="flex items-center justify-between text-small">
                    <span className="capitalize text-text-secondary">{slice.type.replace('_', ' ')}</span>
                    <span className="font-mono font-semibold">{slice.count}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}

      {hasKnowledgeTiles && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Tile label="Open knowledge gaps" value={String(data.open_gap_count)} />
          <Tile
            label="Top gap"
            value={data.top_gap_cluster_key ? data.top_gap_cluster_key.replace(/_/g, ' ') : '—'}
            sub={data.top_gap_occurrence_count !== null ? `${data.top_gap_occurrence_count} occurrences` : undefined}
          />
          <Tile label="Articles expiring in 30d" value={String(data.articles_expiring_30d)} />
        </div>
      )}

      {hasExecutiveTiles && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {data.kpis?.map((kpi) => (
            <Tile
              key={kpi.key}
              label={kpi.label}
              value={kpi.value === null ? '—' : kpi.unit === 'ratio' ? `${Math.round(kpi.value * 100)}%` : String(kpi.value)}
              sub={kpi.target !== null ? `target ${kpi.unit === 'ratio' ? `${Math.round(kpi.target * 100)}%` : kpi.target}` : undefined}
            />
          ))}
        </div>
      )}

      {hasAuditorTiles && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Tile label="Decision volume · 24h" value={String(data.decision_volume_24h)} />
          <Tile label="Rule overrides · 24h" value={String(data.override_count_24h)} />
          <Tile label="Unresolved exceptions" value={String(data.unresolved_exceptions)} />
        </div>
      )}

      <Card title="System health">
        {health.llm_provider_p50_ms === null && health.pgvector_chunk_count === null && health.email_queue_depth === null && health.workflow_workers_healthy === null ? (
          <p className="text-small text-text-muted">No live health-check data wired up yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 text-small sm:grid-cols-4">
            <div>LLM provider · {health.llm_provider_p50_ms ?? '—'}ms p50</div>
            <div>pgvector · {health.pgvector_chunk_count ?? '—'} chunks</div>
            <div>Email queue · {health.email_queue_depth ?? '—'}</div>
            <div>Workflow workers · {health.workflow_workers_healthy ?? '—'}</div>
          </div>
        )}
      </Card>
    </div>
  )
}

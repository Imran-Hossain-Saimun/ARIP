import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { getKpis } from './api'

function KpiTile({ label, value, target, unit }: { label: string; value: number | null; target: number | null; unit: string }) {
  const display =
    value === null
      ? '—'
      : unit === 'ratio'
        ? `${Math.round(value * 100)}%`
        : unit === 'minutes'
          ? `${value}m`
          : unit.startsWith('stars')
            ? `${value} / 5`
            : value.toLocaleString()
  const onTarget = target !== null && value !== null && value >= target

  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <div className="text-h1 font-bold text-text-primary">{display}</div>
      <div className="mt-1 text-small text-text-muted">{label}</div>
      {target !== null && (
        <div className={`mt-2 text-small ${onTarget ? 'text-success' : 'text-warning'}`}>
          target: {unit === 'ratio' ? `${Math.round(target * 100)}%` : target}
        </div>
      )}
    </div>
  )
}

export function AnalyticsPage() {
  const [rangeDays, setRangeDays] = useState(30)
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['analytics-kpis', rangeDays], queryFn: () => getKpis(rangeDays) })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load analytics.'} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-display font-bold text-text-primary">Analytics</h1>
          <p className="mt-1 text-body text-text-secondary">Business outcomes (BO-001–BO-005) against the targets set at launch.</p>
        </div>
        <select
          value={rangeDays}
          onChange={(e) => setRangeDays(Number(e.target.value))}
          className="h-8 rounded-control border border-border-strong px-2.5 text-small outline-none focus:border-brand"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {isLoading && <div className="text-text-muted">Loading…</div>}

      {data && (
        <>
          <div className="grid grid-cols-5 gap-3">
            {data.kpis.map((kpi) => (
              <KpiTile key={kpi.key} label={kpi.label} value={kpi.value} target={kpi.target} unit={kpi.unit} />
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-card border border-border bg-surface p-4">
              <h2 className="mb-3 text-h2 font-semibold text-text-primary">Automation funnel</h2>
              <div className="space-y-2">
                {data.automation_funnel.map((stage) => {
                  const max = Math.max(...data.automation_funnel.map((s) => s.count), 1)
                  return (
                    <div key={stage.type}>
                      <div className="mb-1 flex justify-between text-small">
                        <span className="capitalize text-text-secondary">{stage.type.replace('_', ' ')}</span>
                        <span className="font-mono">{stage.count}</span>
                      </div>
                      <div className="h-2 rounded-full bg-surface-sunken">
                        <div className="h-full rounded-full bg-brand" style={{ width: `${(stage.count / max) * 100}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="rounded-card border border-border bg-surface p-4">
              <h2 className="mb-3 text-h2 font-semibold text-text-primary">Most-cited knowledge</h2>
              <div className="space-y-1.5">
                {data.most_cited_knowledge.length === 0 && <p className="text-small text-text-muted">No citations in this window.</p>}
                {data.most_cited_knowledge.map((a) => (
                  <div key={a.article_ref} className="flex items-center justify-between text-small">
                    <span className="font-mono text-brand">{a.article_ref}</span>
                    <span className="text-text-muted">{a.citation_count} citations</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

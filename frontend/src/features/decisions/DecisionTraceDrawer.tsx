import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, RotateCcw } from 'lucide-react'
import { CitationChip, ConfidenceMeter, Drawer, ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { getDecisionTrace, replayDecision } from './api'

export interface DecisionTraceDrawerProps {
  decisionId: string | null
  onClose: () => void
}

function PipelineStepper({ stages }: { stages: { key: string; ms: number; meta: Record<string, unknown> }[] }) {
  const total = stages.reduce((sum, s) => sum + s.ms, 0)
  return (
    <div className="space-y-2">
      {stages.map((stage) => (
        <div key={stage.key} className="flex items-center gap-3 text-body">
          <span className="w-24 shrink-0 capitalize text-text-secondary">{stage.key}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
            <div className="h-full rounded-full bg-brand" style={{ width: `${total ? (stage.ms / total) * 100 : 0}%` }} />
          </div>
          <span className="w-14 shrink-0 text-right font-mono text-small text-text-muted">{stage.ms}ms</span>
        </div>
      ))}
    </div>
  )
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function DecisionTraceDrawer({ decisionId, onClose }: DecisionTraceDrawerProps) {
  const { data: trace, isLoading, error } = useQuery({
    queryKey: ['decision-trace', decisionId],
    queryFn: () => getDecisionTrace(decisionId!),
    enabled: !!decisionId,
  })

  const replayMutation = useMutation({ mutationFn: () => replayDecision(decisionId!) })

  return (
    <Drawer open={!!decisionId} onClose={onClose} title={trace ? `Decision trace — ${trace.request_id}` : 'Decision trace'}>
      <div className="space-y-4 p-4">
        {isLoading && <div className="text-text-muted">Loading…</div>}
        {error && (
          <ErrorState message={error instanceof ApiError ? error.message : 'Could not load the decision trace.'} traceId={error instanceof ApiError ? (error.traceId ?? undefined) : undefined} />
        )}
        {trace && (
          <>
            <section>
              <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Why this decision</h3>
              <ConfidenceMeter value={trace.confidence} threshold={trace.threshold} label={trace.type.replace('_', ' ')} />
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-small">
                {Object.entries(trace.signals).map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="capitalize text-text-muted">{key.replace('_', ' ')}</dt>
                    <dd className="text-right font-mono text-text-primary">{Math.round(value * 100)}%</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section>
              <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Pipeline</h3>
              <PipelineStepper stages={trace.stages} />
            </section>

            {trace.evidence.length > 0 && (
              <section>
                <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Evidence</h3>
                <div className="flex flex-wrap gap-1.5">
                  {trace.evidence.map((e, i) => (
                    <CitationChip key={i} mode={e.mode as 'vector' | 'vectorless'} articleId={e.article} locator={e.locator} score={e.score} />
                  ))}
                </div>
              </section>
            )}

            {trace.rules.length > 0 && (
              <section>
                <h3 className="mb-2 text-overline uppercase tracking-wide text-text-muted">Rule evaluations</h3>
                <table className="w-full text-small">
                  <thead>
                    <tr className="text-left text-text-muted">
                      <th className="pb-1 font-medium">Rule</th>
                      <th className="pb-1 font-medium">Outcome</th>
                      <th className="pb-1 text-right font-medium">Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trace.rules.map((r) => (
                      <tr key={r.id} className="border-t border-border">
                        <td className="py-1 font-mono">{r.id}</td>
                        <td className="py-1">{r.outcome.replace('_', ' ')}</td>
                        <td className="py-1 text-right font-mono">{r.priority}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            <section className="border-t border-border pt-3 text-small text-text-muted">
              <div>Model: <span className="font-mono text-text-primary">{trace.model}</span></div>
              {trace.audit_hash && <div className="truncate">Audit hash: <span className="font-mono text-text-primary">{trace.audit_hash}</span></div>}
            </section>

            <div className="flex gap-2 border-t border-border pt-3">
              <button
                type="button"
                onClick={() => replayMutation.mutate()}
                disabled={replayMutation.isPending}
                className="flex h-8 items-center gap-1.5 rounded-control border border-border-strong px-3 text-small font-medium hover:bg-surface-sunken disabled:opacity-60"
              >
                <RotateCcw size={14} /> Replay
              </button>
              <button
                type="button"
                onClick={() => downloadJson(`${trace.request_id}-trace.json`, trace)}
                className="flex h-8 items-center gap-1.5 rounded-control border border-border-strong px-3 text-small font-medium hover:bg-surface-sunken"
              >
                <Download size={14} /> Export
              </button>
            </div>
            {replayMutation.data && <p className="text-small text-text-muted">{replayMutation.data.message}</p>}
          </>
        )}
      </div>
    </Drawer>
  )
}

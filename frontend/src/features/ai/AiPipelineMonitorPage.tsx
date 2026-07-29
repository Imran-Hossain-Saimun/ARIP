import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { ConfidenceMeter, StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { runPipeline } from './api'
import type { RunPipelineResponse } from './types'

const DECISION_VARIANT: Record<string, BadgeVariant> = {
  auto_reply: 'success',
  draft_reply: 'brand',
  ask_clarification: 'warning',
  route: 'danger',
  hold: 'ai',
}

const MIN_STAGE_DISPLAY_MS = 220

/**
 * Runs the real pipeline synchronously server-side (one request, full result) then
 * reveals stages one at a time client-side for a "live" feel — a real streaming pipeline
 * would push each stage as it completes; this increment's simplification keeps the
 * backend synchronous, matching how it's used by the customer portal, and only animates
 * the reveal. See task doc.
 */
export function AiPipelineMonitorPage() {
  const [customerEmail, setCustomerEmail] = useState('sandbox@example.com')
  const [customerName, setCustomerName] = useState('Sandbox Customer')
  const [subject, setSubject] = useState('Refund question')
  const [body, setBody] = useState('My refund for disputed card transactions has not arrived, can you check?')
  const [revealedCount, setRevealedCount] = useState(0)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  const mutation = useMutation({
    mutationFn: () => runPipeline({ customer_email: customerEmail, customer_name: customerName, subject, body }),
    onSuccess: (result) => scheduleReveal(result),
  })

  function scheduleReveal(result: RunPipelineResponse) {
    timers.current.forEach(clearTimeout)
    timers.current = []
    setRevealedCount(0)
    let cumulative = 0
    result.stages.forEach((stage, i) => {
      cumulative += Math.max(stage.ms, MIN_STAGE_DISPLAY_MS)
      timers.current.push(setTimeout(() => setRevealedCount(i + 1), cumulative))
    })
  }

  useEffect(() => () => timers.current.forEach(clearTimeout), [])

  const result = mutation.data
  const visibleStages = result?.stages.slice(0, revealedCount) ?? []
  const isRunning = mutation.isPending || (result && revealedCount < result.stages.length)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display font-bold text-text-primary">AI pipeline monitor</h1>
        <p className="mt-1 text-body text-text-secondary">Runs the real intake → classify → retrieve → score → rules → decide pipeline against a sample request.</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3 rounded-card border border-border bg-surface p-4">
          <div>
            <label className="mb-1 block text-small text-text-secondary">Customer email</label>
            <input value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Customer name</label>
            <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Message body</label>
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} className="w-full rounded-control border border-border-strong p-2.5 text-body outline-none focus:border-brand" />
          </div>
          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="flex h-8 items-center gap-1.5 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60"
          >
            <Play size={14} /> Run pipeline
          </button>
          {mutation.isError && <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Pipeline run failed.'}</p>}
        </div>

        <div className="rounded-card border border-border bg-surface p-4">
          <h2 className="mb-3 text-h2 font-semibold text-text-primary">Pipeline stages</h2>
          {!result && !mutation.isPending && <p className="text-small text-text-muted">Run the pipeline to see stage-by-stage timing.</p>}
          <div className="space-y-2">
            {visibleStages.map((stage) => (
              <div key={stage.key} className="flex items-center justify-between rounded-control border border-border px-3 py-2 text-small">
                <span className="capitalize text-text-primary">{stage.key}</span>
                <span className="font-mono text-text-muted">{stage.ms}ms</span>
              </div>
            ))}
          </div>

          {result && !isRunning && (
            <div className="mt-4 space-y-2 border-t border-border pt-4">
              <div className="flex items-center justify-between">
                <StatusBadge variant={DECISION_VARIANT[result.decision_type]} label={result.decision_type.replace('_', ' ')} />
                <span className="font-mono text-small text-text-muted">{result.reference}</span>
              </div>
              <ConfidenceMeter value={result.confidence} threshold={0.95} />
              {result.rule_overridden && <p className="text-small text-ai">Held for review — a business rule overrode the confidence-based decision.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

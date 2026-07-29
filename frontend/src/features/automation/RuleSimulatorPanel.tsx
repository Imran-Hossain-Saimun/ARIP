import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { simulateRule } from './api'

/** §13: "dry-run simulator against last 30 days of traffic" — real query against
 * Decision/Request data (see backend `simulate_business_rule`), no rows written. */
export function RuleSimulatorPanel() {
  const [whenText, setWhenText] = useState('{"category": "Legal"}')
  const [days, setDays] = useState(30)

  const mutation = useMutation({
    mutationFn: () => simulateRule(JSON.parse(whenText), days),
  })

  return (
    <div className="rounded-card border border-ai-border bg-ai-tint p-4">
      <h2 className="mb-2 text-h2 font-semibold text-text-primary">What-if simulator</h2>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-small text-text-secondary">WHEN clause (JSON)</label>
          <input
            value={whenText}
            onChange={(e) => setWhenText(e.target.value)}
            className="h-8 w-full rounded-control border border-border-strong px-2.5 font-mono text-small outline-none focus:border-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Days</label>
          <input
            type="number"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="h-8 w-20 rounded-control border border-border-strong px-2.5 text-small outline-none focus:border-brand"
          />
        </div>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="flex h-8 items-center gap-1.5 rounded-control bg-ai px-3 text-small font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          <Play size={14} /> Simulate
        </button>
      </div>
      {mutation.isError && (
        <p className="mt-2 text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Invalid WHEN clause.'}</p>
      )}
      {mutation.data && (
        <p className="mt-2 text-small text-text-secondary">
          Over the last {mutation.data.window_days} days: <strong>{mutation.data.matched}</strong> decisions match, of which{' '}
          <strong>{mutation.data.would_change_outcome}</strong> would change outcome under this rule.
        </p>
      )}
    </div>
  )
}

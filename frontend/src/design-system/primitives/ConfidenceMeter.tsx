import { cn } from '@/lib/cn'
import { formatConfidence, getConfidenceBand } from '@/lib/confidence'

const BAND_COLOR: Record<string, string> = {
  auto_reply: 'bg-success',
  draft: 'bg-brand',
  clarify: 'bg-warning',
  escalate: 'bg-danger',
}

export interface ConfidenceMeterProps {
  /** Decimal 0-1, from the API — never recomputed client-side. */
  value: number
  /** Decimal 0-1 threshold marker for the category in force (e.g. auto-reply cutoff). */
  threshold?: number
  label?: string
  className?: string
}

export function ConfidenceMeter({ value, threshold, label, className }: ConfidenceMeterProps) {
  const band = getConfidenceBand(value)
  const pct = Math.max(0, Math.min(1, value)) * 100

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <div className="mb-1 flex items-center justify-between text-small text-text-secondary">
          <span>{label}</span>
          <span className="font-mono tabular-nums text-text-primary">{formatConfidence(value)}</span>
        </div>
      )}
      <div
        role="meter"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken"
      >
        <div
          className={cn('h-full rounded-full transition-[width] duration-300 ease-out', BAND_COLOR[band])}
          style={{ width: `${pct}%` }}
        />
        {threshold !== undefined && (
          <div
            aria-hidden="true"
            className="absolute top-0 h-full w-px bg-text-primary/40"
            style={{ left: `${Math.max(0, Math.min(1, threshold)) * 100}%` }}
          />
        )}
      </div>
    </div>
  )
}

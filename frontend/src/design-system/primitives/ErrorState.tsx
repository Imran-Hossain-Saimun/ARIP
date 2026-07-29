import { cn } from '@/lib/cn'

export interface ErrorStateProps {
  headline?: string
  message: string
  traceId?: string
  onRetry?: () => void
  /** Full-screen failures get an assertive live region; partial/regional failures stay polite. */
  assertive?: boolean
  className?: string
}

/** §11: recoverable, shows trace_id, never blanks the whole screen for a partial failure. */
export function ErrorState({ headline = 'Something went wrong', message, traceId, onRetry, assertive, className }: ErrorStateProps) {
  return (
    <div
      role="alert"
      aria-live={assertive ? 'assertive' : 'polite'}
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-card border border-danger-border bg-danger-tint px-6 py-10 text-center',
        className,
      )}
    >
      <h3 className="text-h2 font-semibold text-danger">{headline}</h3>
      <p className="max-w-sm text-body text-text-secondary">{message}</p>
      {traceId && <p className="font-mono text-small text-text-muted">trace_id: {traceId}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 h-8 rounded-control border border-border-strong bg-surface px-3 text-small font-medium hover:bg-surface-sunken"
        >
          Retry
        </button>
      )}
    </div>
  )
}

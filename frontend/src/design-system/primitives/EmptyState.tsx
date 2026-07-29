import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface EmptyStateProps {
  icon?: ReactNode
  headline: string
  description?: string
  action?: { label: string; onClick: () => void }
  className?: string
}

/**
 * §11: distinguishes first-run (offers a create action) from filtered-empty (offers
 * "clear filters") purely by what the caller passes as `action` — same component either way.
 */
export function EmptyState({ icon, headline, description, action, className }: EmptyStateProps) {
  return (
    <div
      role="region"
      aria-label={headline}
      className={cn('flex flex-col items-center justify-center gap-2 px-6 py-16 text-center', className)}
    >
      {icon && (
        <div aria-hidden="true" className="mb-1 text-text-muted">
          {icon}
        </div>
      )}
      <h3 className="text-h2 font-semibold text-text-primary">{headline}</h3>
      {description && <p className="max-w-sm text-body text-text-secondary">{description}</p>}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-3 h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

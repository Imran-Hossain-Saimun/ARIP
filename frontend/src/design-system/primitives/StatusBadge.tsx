import { cn } from '@/lib/cn'

export type BadgeVariant = 'success' | 'brand' | 'warning' | 'danger' | 'ai' | 'neutral'

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  success: 'bg-success-tint text-success border-success-border',
  brand: 'bg-brand-tint text-brand border-brand-border',
  warning: 'bg-warning-tint text-warning border-warning-border',
  danger: 'bg-danger-tint text-danger border-danger-border',
  ai: 'bg-ai-tint text-ai border-ai-border',
  neutral: 'bg-surface-sunken text-text-secondary border-border',
}

const VARIANT_DOT: Record<BadgeVariant, string> = {
  success: 'bg-success',
  brand: 'bg-brand',
  warning: 'bg-warning',
  danger: 'bg-danger',
  ai: 'bg-ai',
  neutral: 'bg-text-muted',
}

export interface StatusBadgeProps {
  variant: BadgeVariant
  label: string
  /** Confidence 0-1, rendered as a formatted percentage next to the label. */
  confidence?: number
  className?: string
}

/**
 * §04/§11 non-negotiable: status is never color alone — dot + text label carry the
 * meaning, color is reinforcement only, so this remains legible for colorblind users
 * and when printed/exported in the audit trail.
 */
export function StatusBadge({ variant, label, confidence, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-[22px] items-center gap-1.5 rounded-chip border px-2 text-small font-medium leading-none',
        VARIANT_STYLES[variant],
        className,
      )}
    >
      <span aria-hidden="true" className={cn('h-1.5 w-1.5 rounded-full', VARIANT_DOT[variant])} />
      <span>{label}</span>
      {confidence !== undefined && (
        <span className="font-mono tabular-nums opacity-80">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  )
}

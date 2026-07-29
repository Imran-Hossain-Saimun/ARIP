import { cn } from '@/lib/cn'

export interface SkeletonRowProps {
  /** Column widths, so the skeleton matches the final row's geometry exactly (§13 DoD). */
  columnWidths?: string[]
  height?: number
  className?: string
}

export function SkeletonRow({ columnWidths = ['20%', '35%', '15%', '15%', '15%'], height = 36, className }: SkeletonRowProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('flex items-center gap-3 border-b border-border px-4', className)}
      style={{ height }}
    >
      {columnWidths.map((width, i) => (
        <div
          key={i}
          className="h-3 rounded-full bg-surface-sunken"
          style={{ width, animation: 'aripPulse 1.4s ease-in-out infinite' }}
        />
      ))}
    </div>
  )
}

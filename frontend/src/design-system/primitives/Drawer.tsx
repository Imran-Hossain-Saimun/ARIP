import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/cn'

export interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  /** Non-modal drawers (≥1600px per §06) don't dim/trap the page behind them. */
  modal?: boolean
  width?: number
  className?: string
}

const FOCUSABLE = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'

/** §04/§10 DecisionTrace drawer and friends — 560px right-side overlay, Esc closes, focus-trapped. */
export function Drawer({ open, onClose, title, children, modal = true, width = 560, className }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    const previouslyFocused = document.activeElement as HTMLElement | null
    panelRef.current?.focus()

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panelRef.current) return
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      {modal && (
        <div
          aria-hidden="true"
          onClick={onClose}
          className="absolute inset-0 bg-text-primary/30"
          style={{ animation: 'aripPulse 0s' }}
        />
      )}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal={modal}
        aria-label={title}
        tabIndex={-1}
        className={cn(
          'relative flex h-full flex-col bg-surface shadow-e2 outline-none',
          !modal && 'border-l border-border shadow-none',
          className,
        )}
        style={{ width }}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-h2 font-semibold text-text-primary">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-7 w-7 place-items-center rounded-control text-text-muted hover:bg-surface-sunken hover:text-text-primary"
          >
            ✕
          </button>
        </div>
        <div className="scroller flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

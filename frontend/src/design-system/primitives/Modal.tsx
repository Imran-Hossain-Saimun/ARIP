import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export interface ModalProps {
  onClose: () => void
  title: string
  children: ReactNode
  width?: number
}

const FOCUSABLE = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'

/** §04: centered dialog, max 640px — for short focused tasks; use Drawer for anything
 * that benefits from staying in context behind the record (traces, article detail). */
export function Modal({ onClose, title, children, width = 560 }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
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
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-text-primary/30" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="scroller relative max-h-[85vh] w-full overflow-y-auto rounded-card bg-surface shadow-e2 outline-none"
        style={{ maxWidth: width }}
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
        <div className="p-4">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

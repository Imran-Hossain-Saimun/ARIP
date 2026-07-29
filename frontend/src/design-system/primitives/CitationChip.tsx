import { cn } from '@/lib/cn'

export type RetrievalMode = 'vector' | 'vectorless'

export interface CitationChipProps {
  mode: RetrievalMode
  /** Knowledge article id, e.g. "KB-0412" */
  articleId: string
  /** Section/clause locator, e.g. "§3.1" */
  locator: string
  /** Retrieval score 0-1 */
  score: number
  onClick?: () => void
  className?: string
}

const MODE_GLYPH: Record<RetrievalMode, string> = {
  vector: '◆', // ◆
  vectorless: '▤', // ▤
}

const MODE_LABEL: Record<RetrievalMode, string> = {
  vector: 'Vector retrieval',
  vectorless: 'Vectorless (hierarchy) retrieval',
}

/** Every evidence link surfaced with an AI answer — draft knowledge can never appear here (FR-028). */
export function CitationChip({ mode, articleId, locator, score, onClick, className }: CitationChipProps) {
  const Tag = onClick ? 'button' : 'span'
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      title={MODE_LABEL[mode]}
      className={cn(
        'inline-flex h-6 items-center gap-1.5 rounded-full border border-brand-border bg-brand-tint px-2.5 font-mono text-small text-brand',
        onClick && 'cursor-pointer hover:bg-brand hover:text-white',
        className,
      )}
    >
      <span aria-hidden="true">{MODE_GLYPH[mode]}</span>
      <span>{articleId}</span>
      <span className="opacity-70">{locator}</span>
      <span className="tabular-nums opacity-70">{score.toFixed(3)}</span>
    </Tag>
  )
}

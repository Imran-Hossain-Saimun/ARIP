import { useRef } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { cn } from '@/lib/cn'
import { SkeletonRow } from './SkeletonRow'

export interface DataTableProps<T> {
  columns: ColumnDef<T, any>[]
  data: T[]
  getRowId?: (row: T) => string
  onRowClick?: (row: T) => void
  selectedRowId?: string
  loading?: boolean
  emptyState?: React.ReactNode
  sorting?: SortingState
  onSortingChange?: (sorting: SortingState) => void
  /** 36px comfortable (default) / 30px compact — §04 density toggle. */
  density?: 'comfortable' | 'compact'
  /** Virtualize beyond this many rows (§13 perf budget: 60fps at 10,000 rows). */
  virtualizeThreshold?: number
  maxHeight?: number
  className?: string
}

const ROW_HEIGHT = { comfortable: 36, compact: 30 }

/**
 * Generic virtualized table used across every module's list screen (queue, knowledge
 * library, rule registry, audit stream, ...). Grid-based rather than a native <table> so
 * virtualized (absolutely-positioned) rows stay column-aligned with the sticky header —
 * splitting header/body into two <table>s lets each compute independent column widths.
 */
export function DataTable<T>({
  columns,
  data,
  getRowId,
  onRowClick,
  selectedRowId,
  loading,
  emptyState,
  sorting,
  onSortingChange,
  density = 'comfortable',
  virtualizeThreshold = 100,
  maxHeight = 640,
  className,
}: DataTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null)
  const rowHeight = ROW_HEIGHT[density]

  const table = useReactTable({
    data,
    columns,
    state: sorting ? { sorting } : undefined,
    onSortingChange: onSortingChange
      ? (updater) => {
          const next = typeof updater === 'function' ? updater(sorting ?? []) : updater
          onSortingChange(next)
        }
      : undefined,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: getRowId as any,
  })

  const rows = table.getRowModel().rows
  const leafColumns = table.getAllLeafColumns()
  const gridTemplateColumns = leafColumns.map((c) => `minmax(0, ${c.getSize()}fr)`).join(' ')
  const shouldVirtualize = rows.length > virtualizeThreshold

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 12,
    enabled: shouldVirtualize,
  })

  if (loading) {
    return (
      <div className={cn('w-full', className)}>
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonRow key={i} height={rowHeight} />
        ))}
      </div>
    )
  }

  if (rows.length === 0 && emptyState) {
    return <>{emptyState}</>
  }

  const virtualItems = shouldVirtualize
    ? virtualizer.getVirtualItems()
    : rows.map((_, index) => ({ index, start: index * rowHeight, key: index }))
  const totalSize = shouldVirtualize ? virtualizer.getTotalSize() : rows.length * rowHeight

  return (
    <div
      role="table"
      aria-rowcount={rows.length}
      className={cn('w-full overflow-hidden rounded-card border border-border', className)}
    >
      <div
        role="row"
        style={{ display: 'grid', gridTemplateColumns }}
        className="sticky top-0 z-10 border-b border-border bg-surface-sunken"
      >
        {table.getFlatHeaders().map((header) => (
          <div
            key={header.id}
            role="columnheader"
            onClick={header.column.getToggleSortingHandler()}
            className={cn(
              'truncate px-4 py-2.5 text-left text-overline uppercase tracking-wide text-text-muted',
              header.column.getCanSort() && 'cursor-pointer select-none',
            )}
          >
            {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
            {{ asc: ' ▲', desc: ' ▼' }[header.column.getIsSorted() as string] ?? null}
          </div>
        ))}
      </div>

      <div ref={parentRef} className="scroller w-full overflow-y-auto bg-surface" style={{ maxHeight }}>
        <div style={{ height: totalSize, position: 'relative' }}>
          {virtualItems.map((virtualRow) => {
            const row = rows[virtualRow.index]
            const rowId = getRowId ? getRowId(row.original) : row.id
            return (
              <div
                key={row.id}
                role="row"
                onClick={() => onRowClick?.(row.original)}
                style={{
                  display: 'grid',
                  gridTemplateColumns,
                  height: rowHeight,
                  position: shouldVirtualize ? 'absolute' : undefined,
                  top: shouldVirtualize ? virtualRow.start : undefined,
                  width: '100%',
                }}
                className={cn(
                  'items-center border-b border-border',
                  onRowClick && 'cursor-pointer hover:bg-surface-sunken',
                  selectedRowId === rowId && 'border-l-2 border-l-brand bg-brand-tint',
                )}
              >
                {row.getVisibleCells().map((cell) => (
                  <div key={cell.id} role="cell" className="truncate px-4 text-body text-text-primary">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

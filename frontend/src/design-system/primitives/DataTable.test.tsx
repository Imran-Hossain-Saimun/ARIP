import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from './DataTable'
import { EmptyState } from './EmptyState'

interface Row {
  id: string
  subject: string
  confidence: number
}

const columns: ColumnDef<Row, any>[] = [
  { accessorKey: 'subject', header: 'Subject' },
  { accessorKey: 'confidence', header: 'Confidence' },
]

const data: Row[] = [
  { id: 'REQ-1', subject: 'Card dispute', confidence: 0.91 },
  { id: 'REQ-2', subject: 'Address change', confidence: 0.97 },
]

describe('DataTable', () => {
  it('renders headers and rows', () => {
    render(<DataTable columns={columns} data={data} getRowId={(r) => r.id} />)
    expect(screen.getByRole('columnheader', { name: 'Subject' })).toBeInTheDocument()
    expect(screen.getByText('Card dispute')).toBeInTheDocument()
    expect(screen.getByText('Address change')).toBeInTheDocument()
  })

  it('shows skeleton rows while loading instead of data', () => {
    render(<DataTable columns={columns} data={data} loading />)
    expect(screen.queryByText('Card dispute')).not.toBeInTheDocument()
  })

  it('renders the empty state when there is no data', () => {
    render(<DataTable columns={columns} data={[]} emptyState={<EmptyState headline="No requests" />} />)
    expect(screen.getByText('No requests')).toBeInTheDocument()
  })

  it('fires onRowClick with the row data', async () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={columns} data={data} getRowId={(r) => r.id} onRowClick={onRowClick} />)
    await userEvent.click(screen.getByText('Card dispute'))
    expect(onRowClick).toHaveBeenCalledWith(data[0])
  })
})

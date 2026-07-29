import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders headline, description, and fires the action', async () => {
    const onClick = vi.fn()
    render(
      <EmptyState
        headline="No requests yet"
        description="Requests will appear here once customers submit them."
        action={{ label: 'Create request', onClick }}
      />,
    )
    expect(screen.getByRole('region', { name: 'No requests yet' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Create request' }))
    expect(onClick).toHaveBeenCalledOnce()
  })
})

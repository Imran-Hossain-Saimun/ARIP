import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('shows the trace id and retries', async () => {
    const onRetry = vi.fn()
    render(<ErrorState message="Could not load requests." traceId="trc_abc123" onRetry={onRetry} />)
    expect(screen.getByText(/trc_abc123/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('defaults to a polite live region, assertive only when requested', () => {
    const { rerender } = render(<ErrorState message="oops" />)
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'polite')
    rerender(<ErrorState message="oops" assertive />)
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive')
  })
})

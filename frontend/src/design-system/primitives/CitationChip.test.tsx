import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CitationChip } from './CitationChip'

describe('CitationChip', () => {
  it('renders article id, locator and score', () => {
    render(<CitationChip mode="vector" articleId="KB-0412" locator="§3.1" score={0.912} />)
    expect(screen.getByText('KB-0412')).toBeInTheDocument()
    expect(screen.getByText('§3.1')).toBeInTheDocument()
    expect(screen.getByText('0.912')).toBeInTheDocument()
  })

  it('is clickable when onClick is provided', async () => {
    const onClick = vi.fn()
    render(<CitationChip mode="vectorless" articleId="KB-0500" locator="§1" score={0.8} onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})

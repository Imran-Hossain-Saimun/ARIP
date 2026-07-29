import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders label and formatted confidence', () => {
    render(<StatusBadge variant="success" label="Auto reply" confidence={0.97} />)
    expect(screen.getByText('Auto reply')).toBeInTheDocument()
    expect(screen.getByText('97%')).toBeInTheDocument()
  })

  it('renders without confidence', () => {
    render(<StatusBadge variant="danger" label="Escalate" />)
    expect(screen.getByText('Escalate')).toBeInTheDocument()
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })
})

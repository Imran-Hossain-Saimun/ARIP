import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceMeter } from './ConfidenceMeter'

describe('ConfidenceMeter', () => {
  it('exposes value via the meter aria attributes', () => {
    render(<ConfidenceMeter value={0.91} label="Confidence" />)
    const meter = screen.getByRole('meter')
    expect(meter).toHaveAttribute('aria-valuenow', '91')
    expect(screen.getByText('91%')).toBeInTheDocument()
  })

  it('clamps out-of-range values into 0-100', () => {
    render(<ConfidenceMeter value={1.4} />)
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100')
  })
})

import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Drawer } from './Drawer'

describe('Drawer', () => {
  it('renders nothing when closed', () => {
    render(
      <Drawer open={false} onClose={vi.fn()} title="Decision trace">
        content
      </Drawer>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders content and title when open', () => {
    render(
      <Drawer open onClose={vi.fn()} title="Decision trace">
        <p>trace content</p>
      </Drawer>,
    )
    expect(screen.getByRole('dialog', { name: 'Decision trace' })).toBeInTheDocument()
    expect(screen.getByText('trace content')).toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    const onClose = vi.fn()
    render(
      <Drawer open onClose={onClose} title="Decision trace">
        content
      </Drawer>,
    )
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes on backdrop click when modal', async () => {
    const onClose = vi.fn()
    render(
      <Drawer open onClose={onClose} title="Decision trace">
        content
      </Drawer>,
    )
    await userEvent.click(document.querySelector('[aria-hidden="true"]')!)
    expect(onClose).toHaveBeenCalledOnce()
  })
})

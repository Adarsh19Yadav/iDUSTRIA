/**
 * frontend/src/test/components/ErrorMessage.test.tsx
 * Tests for the ErrorMessage component.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorMessage, { InlineError } from '../../components/ErrorMessage'

describe('ErrorMessage', () => {
  it('renders default title and message', () => {
    render(<ErrorMessage />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders custom title and message', () => {
    render(<ErrorMessage title="Backend offline" message="Please restart the API." />)
    expect(screen.getByText('Backend offline')).toBeInTheDocument()
    expect(screen.getByText('Please restart the API.')).toBeInTheDocument()
  })

  it('renders retry button when onRetry is provided', () => {
    const onRetry = vi.fn()
    render(<ErrorMessage onRetry={onRetry} />)
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('does not render retry button when onRetry is absent', () => {
    render(<ErrorMessage />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<ErrorMessage onRetry={onRetry} />)
    await user.click(screen.getByRole('button', { name: /Retry/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})

describe('InlineError', () => {
  it('renders message', () => {
    render(<InlineError message="Something failed" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Something failed')).toBeInTheDocument()
  })
})

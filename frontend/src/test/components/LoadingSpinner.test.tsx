/**
 * frontend/src/test/components/LoadingSpinner.test.tsx
 * Tests for the LoadingSpinner component.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LoadingSpinner, { SkeletonCard } from '../../components/LoadingSpinner'

describe('LoadingSpinner', () => {
  it('renders default message', () => {
    render(<LoadingSpinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('renders custom message', () => {
    render(<LoadingSpinner message="Loading machines…" />)
    expect(screen.getByText('Loading machines…')).toBeInTheDocument()
  })

  it('has aria-live attribute for screen readers', () => {
    render(<LoadingSpinner />)
    const el = screen.getByRole('status')
    expect(el).toHaveAttribute('aria-live', 'polite')
  })
})

describe('SkeletonCard', () => {
  it('renders without errors', () => {
    const { container } = render(<SkeletonCard />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders correct number of skeleton lines', () => {
    const { container } = render(<SkeletonCard lines={3} />)
    // 1 header + 3 lines = 4 divs inside the card
    const divs = container.querySelectorAll('.bg-gray-100, .bg-gray-200')
    expect(divs.length).toBe(4)
  })
})

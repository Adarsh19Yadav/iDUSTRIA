/**
 * frontend/src/test/components/EmptyState.test.tsx
 * Tests for the EmptyState component.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EmptyState from '../../components/EmptyState'

describe('EmptyState', () => {
  it('renders default title and message', () => {
    render(<EmptyState />)
    expect(screen.getByText('No data')).toBeInTheDocument()
    expect(screen.getByText('Nothing to display yet.')).toBeInTheDocument()
  })

  it('renders custom title and message', () => {
    render(<EmptyState title="No machines" message="Register a machine first." />)
    expect(screen.getByText('No machines')).toBeInTheDocument()
    expect(screen.getByText('Register a machine first.')).toBeInTheDocument()
  })

  it('renders optional action', () => {
    render(<EmptyState action={<button>Add Machine</button>} />)
    expect(screen.getByRole('button', { name: 'Add Machine' })).toBeInTheDocument()
  })
})

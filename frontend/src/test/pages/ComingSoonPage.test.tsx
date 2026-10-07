/**
 * frontend/src/test/pages/ComingSoonPage.test.tsx
 * Tests for the ComingSoonPage component.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ComingSoonPage from '../../pages/ComingSoonPage'

describe('ComingSoonPage', () => {
  it('renders the title', () => {
    render(<ComingSoonPage title="Sustainability Analytics" description="Coming soon." />)
    expect(screen.getByText('Sustainability Analytics')).toBeInTheDocument()
  })

  it('renders the description', () => {
    render(<ComingSoonPage title="Title" description="Details about this feature." />)
    expect(screen.getByText('Details about this feature.')).toBeInTheDocument()
  })

  it('renders "Coming in next phase" label', () => {
    render(<ComingSoonPage title="Title" description="Desc." />)
    expect(screen.getByText(/Coming in next phase/i)).toBeInTheDocument()
  })
})

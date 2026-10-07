/**
 * frontend/src/test/components/RiskBadge.test.tsx
 * Tests for the RiskBadge component.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RiskBadge from '../../components/RiskBadge'

describe('RiskBadge', () => {
  it('renders Normal for NORMAL risk', () => {
    render(<RiskBadge level="NORMAL" />)
    expect(screen.getByText(/Normal/i)).toBeInTheDocument()
  })

  it('renders Warning for WARNING risk', () => {
    render(<RiskBadge level="WARNING" />)
    expect(screen.getByText(/Warning/i)).toBeInTheDocument()
  })

  it('renders Critical for CRITICAL risk', () => {
    render(<RiskBadge level="CRITICAL" />)
    expect(screen.getByText(/Critical/i)).toBeInTheDocument()
  })

  it('has accessible aria-label', () => {
    render(<RiskBadge level="CRITICAL" />)
    const badge = screen.getByLabelText(/Risk: Critical/i)
    expect(badge).toBeInTheDocument()
  })

  it('renders em-dash for null', () => {
    render(<RiskBadge level={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('renders em-dash for undefined', () => {
    render(<RiskBadge level={undefined} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

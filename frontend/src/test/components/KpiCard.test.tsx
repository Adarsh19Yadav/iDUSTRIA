/**
 * frontend/src/test/components/KpiCard.test.tsx
 * Tests for the KpiCard component.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import KpiCard from '../../components/KpiCard'

describe('KpiCard', () => {
  it('renders label and value', () => {
    render(<KpiCard label="Total Machines" value={42} />)
    expect(screen.getByText('Total Machines')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders subtext when provided', () => {
    render(<KpiCard label="Label" value={0} subtext="additional info" />)
    expect(screen.getByText('additional info')).toBeInTheDocument()
  })

  it('has accessible region label', () => {
    render(<KpiCard label="Critical" value={3} />)
    const region = screen.getByRole('region', { name: /Critical: 3/i })
    expect(region).toBeInTheDocument()
  })

  it('renders string values', () => {
    render(<KpiCard label="Status" value="OK" />)
    expect(screen.getByText('OK')).toBeInTheDocument()
  })
})

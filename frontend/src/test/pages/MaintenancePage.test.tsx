/**
 * frontend/src/test/pages/MaintenancePage.test.tsx
 * Tests for the Maintenance Center page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MaintenancePage from '../../pages/MaintenancePage'

// ── Mock APIs ──────────────────────────────────────────────────────────────

vi.mock('../../api/machines', () => ({
  machinesApi: {
    list: vi.fn(),
    listAssessments: vi.fn(),
    get: vi.fn(),
    assess: vi.fn(),
    create: vi.fn(),
  },
}))

import { machinesApi } from '../../api/machines'
const mockMachinesApi = vi.mocked(machinesApi)

// ── Helpers ────────────────────────────────────────────────────────────────

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MaintenancePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('MaintenancePage — empty state', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
  })

  it('shows empty state when no machines', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/No machines registered/i)).toBeInTheDocument()
    })
  })
})

describe('MaintenancePage — API error', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockRejectedValue(new Error('Network error'))
  })

  it('shows error alert', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})

describe('MaintenancePage — risk grouping', () => {
  const machines = [
    { id: 1, machine_identifier: 'CRITICAL-001', type: 'CNC', created_at: '', updated_at: '' },
    { id: 2, machine_identifier: 'WARNING-001', type: 'PUMP', created_at: '', updated_at: '' },
    { id: 3, machine_identifier: 'NORMAL-001', type: 'FAN', created_at: '', updated_at: '' },
  ]

  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue(machines)
    mockMachinesApi.listAssessments.mockImplementation((id: number) => {
      const risk: Record<number, string> = { 1: 'CRITICAL', 2: 'WARNING', 3: 'NORMAL' }
      return Promise.resolve([
        {
          id: id,
          machine_id: id,
          failure_probability: id === 1 ? 0.9 : 0.1,
          anomaly_score: id === 1 ? 1 : 0,
          risk_score: id === 1 ? 0.9 : 0.1,
          risk_level: risk[id] ?? 'NORMAL',
          model_version: '1.0',
          created_at: new Date().toISOString(),
        },
      ])
    })
  })

  it('renders Maintenance Center heading', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Maintenance Center')).toBeInTheDocument()
    })
  })

  it('renders critical group', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Critical machines/i)).toBeInTheDocument()
    })
  })

  it('renders warning group', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Warning machines/i)).toBeInTheDocument()
    })
  })

  it('renders normal group', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Normal machines/i)).toBeInTheDocument()
    })
  })

  it('uses "Recommended for maintenance review" wording, not fabricated claims', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText(/Recommended for maintenance review/i).length).toBeGreaterThan(0)
    })
    // Verify no fabricated failure claims
    expect(screen.queryByText(/will definitely fail/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/machine will fail/i)).not.toBeInTheDocument()
  })

  it('shows synthetic dataset label', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('SYNTHETIC DATASET')).toBeInTheDocument()
    })
  })

  it('shows safety disclaimer', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Decision-support/i) || screen.getByText(/Important/i)).toBeInTheDocument()
    })
  })
})

/**
 * frontend/src/test/pages/DashboardPage.test.tsx
 * Tests for the Executive Overview Dashboard page.
 * Mocks the API client to avoid real HTTP calls.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../../pages/DashboardPage'

// ── Mock the API modules ───────────────────────────────────────────────────

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

function makeAssessment(overrides = {}) {
  return {
    id: 1,
    machine_id: 1,
    failure_probability: 0.12,
    anomaly_score: 0,
    risk_score: 0.15,
    risk_level: 'NORMAL',
    model_version: '1.0',
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

function makeMachine(overrides = {}) {
  return {
    id: 1,
    machine_identifier: 'MACHINE-001',
    type: 'CNC_LATHE',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('DashboardPage — loading state', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockReturnValue(new Promise(() => {})) // never resolves
  })

  it('shows loading spinner', () => {
    renderDashboard()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('DashboardPage — API error', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockRejectedValue(new Error('Network error'))
  })

  it('shows error message with retry button', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('shows backend unavailable text', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/Backend unavailable/i)).toBeInTheDocument()
    })
  })
})

describe('DashboardPage — empty state', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
  })

  it('shows empty state when no machines', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/No machines registered/i)).toBeInTheDocument()
    })
  })

  it('shows KPI cards with zero values', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Total Machines: 0/i)).toBeInTheDocument()
    })
  })
})

describe('DashboardPage — with machines and assessments', () => {
  const machine1 = makeMachine({ id: 1, machine_identifier: 'MACHINE-001' })
  const machine2 = makeMachine({ id: 2, machine_identifier: 'MACHINE-002' })
  const assessment1 = makeAssessment({ machine_id: 1, risk_level: 'NORMAL' })
  const assessment2 = makeAssessment({ id: 2, machine_id: 2, risk_level: 'CRITICAL', risk_score: 0.9, failure_probability: 0.8 })

  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([machine1, machine2])
    mockMachinesApi.listAssessments.mockImplementation((id: number) => {
      if (id === 1) return Promise.resolve([assessment1])
      if (id === 2) return Promise.resolve([assessment2])
      return Promise.resolve([])
    })
  })

  it('shows correct total machine count KPI', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Total Machines: 2/i)).toBeInTheDocument()
    })
  })

  it('shows executive overview heading', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('Executive Overview')).toBeInTheDocument()
    })
  })

  it('shows synthetic dataset label', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('SYNTHETIC DATASET')).toBeInTheDocument()
    })
  })

  it('shows attention required section for critical machines', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Attention required/i)).toBeInTheDocument()
    })
  })

  it('shows recent assessments section', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Recent assessments/i)).toBeInTheDocument()
    })
  })

  it('KPI healthy count = 1 (1 NORMAL machine)', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Healthy: 1/i)).toBeInTheDocument()
    })
  })

  it('KPI critical count = 1 (1 CRITICAL machine)', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByLabelText(/Critical: 1/i)).toBeInTheDocument()
    })
  })
})

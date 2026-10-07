/**
 * frontend/src/test/pages/MachinesPage.test.tsx
 * Tests for the Machine Monitoring page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MachinesPage from '../../pages/MachinesPage'

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

function makeMachine(id: number, identifier: string, type = 'CNC') {
  return {
    id,
    machine_identifier: identifier,
    type,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

function makeAssessment(machineId: number, riskLevel = 'NORMAL') {
  return {
    id: machineId * 10,
    machine_id: machineId,
    failure_probability: riskLevel === 'CRITICAL' ? 0.85 : 0.12,
    anomaly_score: riskLevel === 'CRITICAL' ? 1 : 0,
    risk_score: riskLevel === 'CRITICAL' ? 0.9 : 0.15,
    risk_level: riskLevel,
    model_version: '1.0',
    created_at: new Date().toISOString(),
  }
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MachinesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('MachinesPage — loading state', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockReturnValue(new Promise(() => {}))
  })

  it('shows loading spinner', () => {
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('MachinesPage — API error', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockRejectedValue(new Error('Network error'))
  })

  it('shows error message', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows retry button', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
    })
  })
})

describe('MachinesPage — empty state', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
  })

  it('shows empty state message', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/No machines registered yet/i)).toBeInTheDocument()
    })
  })
})

describe('MachinesPage — machine list', () => {
  const machines = [
    makeMachine(1, 'MACHINE-001', 'CNC_LATHE'),
    makeMachine(2, 'MACHINE-002', 'PUMP'),
    makeMachine(3, 'MACHINE-003', 'COMPRESSOR'),
  ]

  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue(machines)
    mockMachinesApi.listAssessments.mockImplementation((id: number) => {
      if (id === 1) return Promise.resolve([makeAssessment(1, 'NORMAL')])
      if (id === 2) return Promise.resolve([makeAssessment(2, 'WARNING')])
      if (id === 3) return Promise.resolve([makeAssessment(3, 'CRITICAL')])
      return Promise.resolve([])
    })
  })

  it('renders machine identifiers', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('MACHINE-001')).toBeInTheDocument()
    })
    expect(screen.getByText('MACHINE-002')).toBeInTheDocument()
    expect(screen.getByText('MACHINE-003')).toBeInTheDocument()
  })

  it('renders machine types', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('CNC_LATHE')).toBeInTheDocument()
    })
    expect(screen.getByText('PUMP')).toBeInTheDocument()
  })

  it('renders search input', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('searchbox')).toBeInTheDocument()
    })
  })

  it('filters machines by search term', async () => {
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('MACHINE-001')).toBeInTheDocument()
    })
    await user.type(screen.getByRole('searchbox'), 'MACHINE-001')
    await waitFor(() => {
      expect(screen.queryByText('MACHINE-002')).not.toBeInTheDocument()
    })
    expect(screen.getByText('MACHINE-001')).toBeInTheDocument()
  })

  it('shows register machine button', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Register Machine/i })).toBeInTheDocument()
    })
  })

  it('renders risk filter buttons', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Normal/i, hidden: false })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Warning/i, hidden: false })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Critical/i, hidden: false })).toBeInTheDocument()
    })
  })
})

/**
 * frontend/src/test/pages/MachineDetailPage.test.tsx
 * Tests for the Machine Detail page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import MachineDetailPage from '../../pages/MachineDetailPage'

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

vi.mock('../../api/agent', () => ({
  agentApi: { query: vi.fn() },
  ragApi: { query: vi.fn(), status: vi.fn() },
}))

import { machinesApi } from '../../api/machines'
const mockMachinesApi = vi.mocked(machinesApi)

// ── Helpers ────────────────────────────────────────────────────────────────

const machine = {
  id: 1,
  machine_identifier: 'TEST-001',
  type: 'CNC_LATHE',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const assessment = {
  id: 10,
  machine_id: 1,
  failure_probability: 0.35,
  anomaly_score: 0,
  risk_score: 0.4,
  risk_level: 'WARNING',
  model_version: '1.0',
  created_at: new Date().toISOString(),
}

function renderPage(machineId = '1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/machines/${machineId}`]}>
        <Routes>
          <Route path="/machines/:id" element={<MachineDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('MachineDetailPage — loading', () => {
  beforeEach(() => {
    mockMachinesApi.get.mockReturnValue(new Promise(() => {}))
    mockMachinesApi.listAssessments.mockReturnValue(new Promise(() => {}))
  })

  it('shows loading spinner', () => {
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('MachineDetailPage — 404', () => {
  beforeEach(() => {
    const err = Object.assign(new Error('Not found'), { response: { status: 404 } })
    mockMachinesApi.get.mockRejectedValue(err)
    mockMachinesApi.listAssessments.mockResolvedValue([])
  })

  it('shows not found error', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(screen.getByText(/Machine not found/i)).toBeInTheDocument()
  })
})

describe('MachineDetailPage — with data', () => {
  beforeEach(() => {
    mockMachinesApi.get.mockResolvedValue(machine)
    mockMachinesApi.listAssessments.mockResolvedValue([assessment])
  })

  it('shows machine identifier', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('TEST-001')).toBeInTheDocument()
    })
  })

  it('shows machine type', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/CNC_LATHE/i)).toBeInTheDocument()
    })
  })

  it('shows risk level badge', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Risk: Warning/i)).toBeInTheDocument()
    })
  })

  it('shows assess machine button', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Assess Machine/i })).toBeInTheDocument()
    })
  })

  it('shows assessment history section', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Assessment history/i)).toBeInTheDocument()
    })
  })

  it('shows maintenance guidance section', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/Maintenance guidance/i)).toBeInTheDocument()
    })
  })

  it('shows synthetic dataset label', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('SYNTHETIC DATASET')).toBeInTheDocument()
    })
  })
})

describe('MachineDetailPage — no assessments', () => {
  beforeEach(() => {
    mockMachinesApi.get.mockResolvedValue(machine)
    mockMachinesApi.listAssessments.mockResolvedValue([])
  })

  it('shows "No assessment has been run yet" message', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/No assessment has been run yet/i)).toBeInTheDocument()
    })
  })
})

describe('MachineDetailPage — invalid ID', () => {
  it('shows invalid machine ID error for NaN IDs', async () => {
    renderPage('abc')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})

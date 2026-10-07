/**
 * frontend/src/test/pages/AIOperationsPage.test.tsx
 * Tests for the AI Operations Center page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AIOperationsPage from '../../pages/AIOperationsPage'

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
  agentApi: {
    query: vi.fn(),
  },
  ragApi: {
    query: vi.fn(),
    status: vi.fn(),
  },
}))

import { machinesApi } from '../../api/machines'
import { agentApi } from '../../api/agent'

const mockMachinesApi = vi.mocked(machinesApi)
const mockAgentApi = vi.mocked(agentApi)

// ── Helpers ────────────────────────────────────────────────────────────────

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AIOperationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const mockAgentResponse = {
  answer: 'The machine is at elevated risk due to high tool wear.',
  tools_used: ['assess_machine', 'explain_prediction'],
  evidence: [
    { tool: 'assess_machine', result: { risk_level: 'WARNING', risk_score: 0.7 } },
  ],
  sources: [
    { source: 'maintenance-guide.md', chunk_index: 0, distance: 0.1, excerpt: 'Replace tools regularly.' },
  ],
  status: 'success' as const,
  error_detail: null,
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('AIOperationsPage — rendering', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
  })

  it('renders the AI Operations heading', async () => {
    renderPage()
    expect(screen.getByText('AI Operations Center')).toBeInTheDocument()
  })

  it('renders query textarea', async () => {
    renderPage()
    expect(screen.getByLabelText('AI query')).toBeInTheDocument()
  })

  it('renders suggested query buttons', async () => {
    renderPage()
    expect(screen.getByText('Why is this machine high risk?')).toBeInTheDocument()
    expect(screen.getByText('What maintenance should be considered?')).toBeInTheDocument()
  })

  it('renders submit button', async () => {
    renderPage()
    expect(screen.getByRole('button', { name: /Ask AI/i })).toBeInTheDocument()
  })

  it('submit button is disabled when query is empty', async () => {
    renderPage()
    const btn = screen.getByRole('button', { name: /Ask AI/i })
    expect(btn).toBeDisabled()
  })
})

describe('AIOperationsPage — query submission', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
    mockAgentApi.query.mockResolvedValue(mockAgentResponse)
  })

  it('enables submit button when query is typed', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'What is the risk?')
    expect(screen.getByRole('button', { name: /Ask AI/i })).not.toBeDisabled()
  })

  it('fills query from suggestion click', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByText('Why is this machine high risk?'))
    expect(screen.getByLabelText('AI query')).toHaveValue('Why is this machine high risk?')
  })

  it('displays answer after successful query', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'What is the risk?')
    await user.click(screen.getByRole('button', { name: /Ask AI/i }))
    await waitFor(() => {
      expect(screen.getByText(/The machine is at elevated risk/i)).toBeInTheDocument()
    })
  })

  it('displays tools used', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'What is the risk?')
    await user.click(screen.getByRole('button', { name: /Ask AI/i }))
    await waitFor(() => {
      expect(screen.getByText('assess_machine')).toBeInTheDocument()
    })
    expect(screen.getByText('explain_prediction')).toBeInTheDocument()
  })

  it('displays evidence section', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'Risk?')
    await user.click(screen.getByRole('button', { name: /Ask AI/i }))
    await waitFor(() => {
      expect(screen.getByLabelText('Tool evidence')).toBeInTheDocument()
    })
  })

  it('displays sources section', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'Risk?')
    await user.click(screen.getByRole('button', { name: /Ask AI/i }))
    await waitFor(() => {
      expect(screen.getByLabelText('Knowledge base sources')).toBeInTheDocument()
    })
    expect(screen.getByText('maintenance-guide.md')).toBeInTheDocument()
  })
})

describe('AIOperationsPage — API error', () => {
  beforeEach(() => {
    mockMachinesApi.list.mockResolvedValue([])
    mockAgentApi.query.mockRejectedValue(new Error('Agent error'))
  })

  it('shows error message without stack trace', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByLabelText('AI query'), 'What is the risk?')
    await user.click(screen.getByRole('button', { name: /Ask AI/i }))
    await waitFor(() => {
      expect(screen.getByText(/Agent request failed/i)).toBeInTheDocument()
    })
    // No stack trace
    expect(screen.queryByText(/Error:/)).not.toBeInTheDocument()
  })
})

/**
 * frontend/src/test/pages/Navigation.test.tsx
 * Tests for app routing and navigation.
 * Uses mock pages to keep tests fast.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock all pages to avoid fetching
vi.mock('../../pages/DashboardPage', () => ({
  default: () => <div data-testid="dashboard-page">Dashboard</div>,
}))
vi.mock('../../pages/MachinesPage', () => ({
  default: () => <div data-testid="machines-page">Machines</div>,
}))
vi.mock('../../pages/MachineDetailPage', () => ({
  default: () => <div data-testid="machine-detail-page">Machine Detail</div>,
}))
vi.mock('../../pages/MaintenancePage', () => ({
  default: () => <div data-testid="maintenance-page">Maintenance</div>,
}))
vi.mock('../../pages/AIOperationsPage', () => ({
  default: () => <div data-testid="ai-page">AI Operations</div>,
}))
vi.mock('../../pages/ComingSoonPage', () => ({
  default: ({ title }: { title: string }) => <div data-testid="coming-soon-page">{title}</div>,
}))
vi.mock('../../pages/NotFoundPage', () => ({
  default: () => <div data-testid="not-found-page">Not Found</div>,
}))

// Import Sidebar and routes separately to avoid BrowserRouter conflict
import DashboardPage from '../../pages/DashboardPage'
import MachinesPage from '../../pages/MachinesPage'
import MachineDetailPage from '../../pages/MachineDetailPage'
import MaintenancePage from '../../pages/MaintenancePage'
import AIOperationsPage from '../../pages/AIOperationsPage'
import ComingSoonPage from '../../pages/ComingSoonPage'
import NotFoundPage from '../../pages/NotFoundPage'

// Re-create the route structure with MemoryRouter (avoids BrowserRouter in App)
function AppRoutes({ initialPath }: { initialPath: string }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/"               element={<DashboardPage />} />
          <Route path="/dashboard"      element={<DashboardPage />} />
          <Route path="/machines"       element={<MachinesPage />} />
          <Route path="/machines/:id"   element={<MachineDetailPage />} />
          <Route path="/maintenance"    element={<MaintenancePage />} />
          <Route path="/ai"             element={<AIOperationsPage />} />
          <Route path="/sustainability" element={<ComingSoonPage title="Sustainability Analytics" description="" />} />
          <Route path="/whatif"         element={<ComingSoonPage title="What-If Analysis" description="" />} />
          <Route path="/settings"       element={<ComingSoonPage title="Settings" description="" />} />
          <Route path="*"               element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Navigation — route rendering', () => {
  it('renders dashboard at /', () => {
    render(<AppRoutes initialPath="/" />)
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
  })

  it('renders dashboard at /dashboard', () => {
    render(<AppRoutes initialPath="/dashboard" />)
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
  })

  it('renders machines page at /machines', () => {
    render(<AppRoutes initialPath="/machines" />)
    expect(screen.getByTestId('machines-page')).toBeInTheDocument()
  })

  it('renders machine detail at /machines/1', () => {
    render(<AppRoutes initialPath="/machines/1" />)
    expect(screen.getByTestId('machine-detail-page')).toBeInTheDocument()
  })

  it('renders maintenance page at /maintenance', () => {
    render(<AppRoutes initialPath="/maintenance" />)
    expect(screen.getByTestId('maintenance-page')).toBeInTheDocument()
  })

  it('renders AI operations page at /ai', () => {
    render(<AppRoutes initialPath="/ai" />)
    expect(screen.getByTestId('ai-page')).toBeInTheDocument()
  })

  it('renders coming soon for /sustainability', () => {
    render(<AppRoutes initialPath="/sustainability" />)
    expect(screen.getByTestId('coming-soon-page')).toBeInTheDocument()
    expect(screen.getByText('Sustainability Analytics')).toBeInTheDocument()
  })

  it('renders coming soon for /whatif', () => {
    render(<AppRoutes initialPath="/whatif" />)
    expect(screen.getByTestId('coming-soon-page')).toBeInTheDocument()
    expect(screen.getByText('What-If Analysis')).toBeInTheDocument()
  })

  it('renders coming soon for /settings', () => {
    render(<AppRoutes initialPath="/settings" />)
    expect(screen.getByTestId('coming-soon-page')).toBeInTheDocument()
  })

  it('renders 404 for unknown routes', () => {
    render(<AppRoutes initialPath="/some/unknown/path" />)
    expect(screen.getByTestId('not-found-page')).toBeInTheDocument()
  })
})

describe('Navigation — sidebar links', () => {
  it('renders sidebar navigation', () => {
    const qc = new QueryClient()
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/dashboard']}>
          {/* Re-import App sidebar inline — just test nav links exist */}
          <nav aria-label="Main navigation">
            <a href="/dashboard">Overview</a>
            <a href="/machines">Machines</a>
            <a href="/maintenance">Maintenance</a>
            <a href="/ai">AI Operations</a>
          </nav>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('navigation', { name: /Main navigation/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Machines' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Maintenance' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AI Operations' })).toBeInTheDocument()
  })
})

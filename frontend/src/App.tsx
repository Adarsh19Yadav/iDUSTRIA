import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Cpu,
  Wrench,
  Bot,
  Zap,
  FlaskConical,
  Settings,
  Radio,
  ChevronRight,
} from 'lucide-react'

import DashboardPage from './pages/DashboardPage'
import MachinesPage from './pages/MachinesPage'
import MachineDetailPage from './pages/MachineDetailPage'
import MaintenancePage from './pages/MaintenancePage'
import AIOperationsPage from './pages/AIOperationsPage'
import ComingSoonPage from './pages/ComingSoonPage'
import SustainabilityPage from './pages/SustainabilityPage'
import WhatIfPage from './pages/WhatIfPage'
import SimulationPage from './pages/SimulationPage'
import NotFoundPage from './pages/NotFoundPage'

const navItems = [
  { to: '/dashboard',    label: 'Overview',       icon: LayoutDashboard },
  { to: '/machines',     label: 'Machines',        icon: Cpu },
  { to: '/maintenance',  label: 'Maintenance',     icon: Wrench },
  { to: '/ai',           label: 'AI Operations',   icon: Bot },
  { to: '/sustainability', label: 'Sustainability', icon: Zap },
  { to: '/whatif',       label: 'What-If',         icon: FlaskConical },
  { to: '/simulation',   label: 'Simulation',      icon: Radio },
  { to: '/settings',     label: 'Settings',        icon: Settings, comingSoon: true },
]

function Sidebar() {
  return (
    <aside
      className="w-60 bg-gray-900 text-gray-100 min-h-screen flex flex-col flex-shrink-0"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-700">
        <h1 className="text-base font-bold text-white tracking-widest uppercase leading-tight">INDUSTRIA‑X</h1>
        <p className="text-xs text-gray-400 mt-1">Predictive Maintenance AI</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2.5 py-4 space-y-0.5" aria-label="Primary">
        {navItems.map(({ to, label, icon: Icon, comingSoon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm transition-all duration-150 group ${
                isActive
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
            aria-label={comingSoon ? `${label} (coming soon)` : label}
          >
            <span className="flex items-center gap-3">
              <Icon size={17} aria-hidden="true" />
              {label}
            </span>
            {comingSoon && (
              <span className="text-xs text-gray-500 group-hover:text-gray-400">
                <ChevronRight size={13} aria-hidden="true" />
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Version / SDG footer */}
      <div className="px-5 py-4 border-t border-gray-700 space-y-1.5">
        <p className="text-xs text-gray-500">Phase 12 — Simulation</p>
        <p className="text-xs text-gray-500">UN SDG 9 Industry &amp; Innovation</p>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 px-7 py-6 overflow-auto min-w-0">
          <Routes>
            <Route path="/"               element={<DashboardPage />} />
            <Route path="/dashboard"      element={<DashboardPage />} />
            <Route path="/machines"       element={<MachinesPage />} />
            <Route path="/machines/:id"   element={<MachineDetailPage />} />
            <Route path="/maintenance"    element={<MaintenancePage />} />
            <Route path="/ai"             element={<AIOperationsPage />} />
            <Route path="/sustainability" element={<SustainabilityPage />} />
            <Route path="/whatif"         element={<WhatIfPage />} />
            <Route path="/simulation"     element={<SimulationPage />} />
            <Route path="/settings"       element={<ComingSoonPage title="Settings" description="Platform configuration, notification preferences, and team management coming soon." />} />
            <Route path="*"               element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

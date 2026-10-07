/**
 * frontend/src/pages/MachinesPage.tsx
 * Machine Monitoring — searchable, filterable, sortable table.
 * Data sourced from real backend APIs only.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronUp, ChevronDown, ExternalLink, Plus, X } from 'lucide-react'

import { machinesApi } from '../api/machines'
import type { Machine, Assessment } from '../types'
import {
  getRiskOrder,
  formatProbability,
  formatScore,
  formatTimestamp,
} from '../utils/risk'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'
import RegisterMachineModal from '../components/RegisterMachineModal'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MachineRow {
  machine: Machine
  assessment: Assessment | null
}

type SortKey = 'machine' | 'type' | 'risk' | 'riskScore' | 'failureProb' | 'lastAssessment'
type SortDir = 'asc' | 'desc'

// ---------------------------------------------------------------------------
// Fetch all machines + their latest assessments
// ---------------------------------------------------------------------------

async function fetchAllWithAssessments(machines: Machine[]): Promise<MachineRow[]> {
  return Promise.all(
    machines.map(async (machine) => {
      try {
        const assessments = await machinesApi.listAssessments(machine.id, 0, 1)
        return { machine, assessment: assessments[0] ?? null }
      } catch {
        return { machine, assessment: null }
      }
    }),
  )
}

// ---------------------------------------------------------------------------
// Sortable header cell
// ---------------------------------------------------------------------------

function SortHeader({
  label,
  sortKey,
  current,
  dir,
  onSort,
  align = 'left',
}: {
  label: string
  sortKey: SortKey
  current: SortKey
  dir: SortDir
  onSort: (k: SortKey) => void
  align?: 'left' | 'right'
}) {
  const active = current === sortKey
  return (
    <th
      className={`tbl-header cursor-pointer select-none hover:text-gray-800 transition-colors ${align === 'right' ? 'text-right' : 'text-left'}`}
      onClick={() => onSort(sortKey)}
      aria-sort={active ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <span className="flex items-center gap-1">
        {label}
        {active ? (
          dir === 'asc' ? <ChevronUp size={13} aria-hidden="true" /> : <ChevronDown size={13} aria-hidden="true" />
        ) : (
          <span className="text-gray-300"><ChevronDown size={13} aria-hidden="true" /></span>
        )}
      </span>
    </th>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function MachinesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState<string>('ALL')
  const [anomalyFilter, setAnomalyFilter] = useState<boolean | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('lastAssessment')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [showRegister, setShowRegister] = useState(false)

  // ── Fetch machines ────────────────────────────────────────────────────────

  const machinesQuery = useQuery({
    queryKey: ['machines'],
    queryFn: () => machinesApi.list(0, 200),
    refetchInterval: 60_000,
  })

  const machines = machinesQuery.data ?? []

  const rowsQuery = useQuery({
    queryKey: ['machine-rows', machines.map((m) => m.id).join(',')],
    queryFn: () => fetchAllWithAssessments(machines),
    enabled: machines.length > 0,
    refetchInterval: 60_000,
  })

  const rows: MachineRow[] = rowsQuery.data ?? machines.map((m) => ({ machine: m, assessment: null }))

  // ── Filtering ─────────────────────────────────────────────────────────────

  const filtered = useMemo(() => {
    return rows.filter(({ machine, assessment }) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        machine.machine_identifier.toLowerCase().includes(q) ||
        (machine.type ?? '').toLowerCase().includes(q)

      const matchesRisk =
        riskFilter === 'ALL' ||
        (assessment?.risk_level ?? 'UNKNOWN') === riskFilter ||
        (riskFilter === 'UNASSESSED' && !assessment)

      const matchesAnomaly =
        anomalyFilter === null ||
        (anomalyFilter && (assessment?.anomaly_score ?? 0) > 0) ||
        (!anomalyFilter && (assessment?.anomaly_score ?? 0) === 0)

      return matchesSearch && matchesRisk && matchesAnomaly
    })
  }, [rows, search, riskFilter, anomalyFilter])

  // ── Sorting ───────────────────────────────────────────────────────────────

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'machine':
          cmp = a.machine.machine_identifier.localeCompare(b.machine.machine_identifier)
          break
        case 'type':
          cmp = (a.machine.type ?? '').localeCompare(b.machine.type ?? '')
          break
        case 'risk':
          cmp = getRiskOrder(a.assessment?.risk_level) - getRiskOrder(b.assessment?.risk_level)
          break
        case 'riskScore':
          cmp = (a.assessment?.risk_score ?? -1) - (b.assessment?.risk_score ?? -1)
          break
        case 'failureProb':
          cmp = (a.assessment?.failure_probability ?? -1) - (b.assessment?.failure_probability ?? -1)
          break
        case 'lastAssessment':
          cmp =
            new Date(a.assessment?.created_at ?? 0).getTime() -
            new Date(b.assessment?.created_at ?? 0).getTime()
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  // ── States ────────────────────────────────────────────────────────────────

  if (machinesQuery.isLoading) {
    return <LoadingSpinner message="Loading machines…" size="lg" />
  }

  if (machinesQuery.isError) {
    return (
      <ErrorMessage
        title="Could not load machines"
        message="Backend may be unavailable. Please check the API service."
        onRetry={() => machinesQuery.refetch()}
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <PageHeader
        title="Machine Monitoring"
        subtitle={`${machines.length} machine${machines.length !== 1 ? 's' : ''} registered`}
        badge={
          <span className="simulated-label">SYNTHETIC DATASET</span>
        }
        actions={
          <button
            onClick={() => setShowRegister(true)}
            className="btn-primary btn-sm"
            aria-label="Register new machine"
          >
            <Plus size={15} aria-hidden="true" /> Register Machine
          </button>
        }
      />

      {/* ── Filters ─────────────────────────────────────────────────────── */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Search machines…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
              aria-label="Search machines"
            />
          </div>

          {/* Risk filter */}
          <div className="flex items-center gap-1.5" role="group" aria-label="Filter by risk level">
            <span className="text-sm text-gray-500 font-medium">Risk:</span>
            {['ALL', 'NORMAL', 'WARNING', 'CRITICAL', 'UNASSESSED'].map((r) => (
              <button
                key={r}
                onClick={() => setRiskFilter(r)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150 ${
                  riskFilter === r
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                    : 'border-gray-200 text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                }`}
                aria-pressed={riskFilter === r}
              >
                {r === 'ALL' ? 'All' : r.charAt(0) + r.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {/* Anomaly filter */}
          <div className="flex items-center gap-1.5" role="group" aria-label="Filter by anomaly status">
            <span className="text-sm text-gray-500 font-medium">Anomaly:</span>
            {[
              { key: null, label: 'All' },
              { key: true, label: 'Active' },
              { key: false, label: 'None' },
            ].map(({ key, label }) => (
              <button
                key={String(key)}
                onClick={() => setAnomalyFilter(key)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150 ${
                  anomalyFilter === key
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                    : 'border-gray-200 text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                }`}
                aria-pressed={anomalyFilter === key}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Clear filters */}
          {(search || riskFilter !== 'ALL' || anomalyFilter !== null) && (
            <button
              onClick={() => { setSearch(''); setRiskFilter('ALL'); setAnomalyFilter(null) }}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              aria-label="Clear all filters"
            >
              <X size={14} aria-hidden="true" /> Clear
            </button>
          )}

          <span className="ml-auto text-sm text-gray-400 tabular-nums">
            {sorted.length} result{sorted.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* ── Table ─────────────────────────────────────────────────────────── */}
      {machines.length === 0 ? (
        <EmptyState
          title="No machines registered yet"
          message="Register your first machine to start monitoring and assessments."
          action={
            <button
              onClick={() => setShowRegister(true)}
              className="btn-primary"
            >
              <Plus size={16} aria-hidden="true" /> Register Machine
            </button>
          }
        />
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No machines match filters"
          message="Try adjusting your search or filter criteria."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full" aria-label="Machine monitoring table">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="w-1 pl-5" />
                <SortHeader label="Machine" sortKey="machine" current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label="Type"    sortKey="type"    current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label="Risk"    sortKey="risk"    current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label="Risk Score" sortKey="riskScore" current={sortKey} dir={sortDir} onSort={handleSort} align="right" />
                <SortHeader label="P(Failure)" sortKey="failureProb" current={sortKey} dir={sortDir} onSort={handleSort} align="right" />
                <th className="tbl-header text-left">Anomaly</th>
                <SortHeader label="Last Assessment" sortKey="lastAssessment" current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="tbl-header text-left">Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(({ machine, assessment }) => (
                <tr
                  key={machine.id}
                  className="border-b border-gray-100 hover:bg-blue-50/30 transition-colors"
                >
                  <td className="w-1 pl-5" />
                  <td className="tbl-cell pl-0">
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">{machine.machine_identifier}</p>
                      <p className="text-gray-400 text-xs mt-0.5">ID #{machine.id}</p>
                    </div>
                  </td>
                  <td className="tbl-cell text-gray-600 text-sm">{machine.type ?? <span className="text-gray-300">—</span>}</td>
                  <td className="tbl-cell">
                    {assessment ? (
                      <RiskBadge level={assessment.risk_level} />
                    ) : (
                      <span className="badge badge-info">Unassessed</span>
                    )}
                  </td>
                  <td className="tbl-cell text-right tabular-nums text-gray-700">
                    {formatScore(assessment?.risk_score)}
                  </td>
                  <td className="tbl-cell text-right tabular-nums text-gray-700">
                    {formatProbability(assessment?.failure_probability)}
                  </td>
                  <td className="tbl-cell">
                    {assessment ? (
                      <span className={assessment.anomaly_score > 0 ? 'text-amber-700 font-semibold' : 'text-green-700'}>
                        {assessment.anomaly_score > 0 ? 'Anomalous' : 'Normal'}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="tbl-cell text-gray-400 text-sm">
                    {assessment ? formatTimestamp(assessment.created_at) : <span className="text-gray-300">Never</span>}
                  </td>
                  <td className="tbl-cell">
                    <button
                      onClick={() => navigate(`/machines/${machine.id}`)}
                      className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 font-semibold transition-colors"
                      aria-label={`View details for ${machine.machine_identifier}`}
                    >
                      Details <ExternalLink size={13} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Register machine modal ─────────────────────────────────────── */}
      {showRegister && (
        <RegisterMachineModal
          onClose={() => setShowRegister(false)}
          onSuccess={() => {
            setShowRegister(false)
            machinesQuery.refetch()
          }}
        />
      )}
    </div>
  )
}

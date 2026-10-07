/**
 * frontend/src/pages/MaintenancePage.tsx
 * Maintenance Priority Center — machines grouped by risk level.
 * Uses real assessment data only.
 */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertOctagon, AlertTriangle, ShieldCheck, ExternalLink } from 'lucide-react'

import { machinesApi } from '../api/machines'
import type { Machine, Assessment } from '../types'
import { formatProbability, formatScore, formatTimestamp, getRiskOrder } from '../utils/risk'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MachineRow {
  machine: Machine
  assessment: Assessment | null
}

// ---------------------------------------------------------------------------
// Fetch helpers
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
// Risk Group component
// ---------------------------------------------------------------------------

interface GroupProps {
  title: string
  icon: React.ReactNode
  rows: MachineRow[]
  headerClass: string
  recommendation: string
  emptyMessage: string
}

function RiskGroup({ title, icon, rows, headerClass, recommendation, emptyMessage }: GroupProps) {
  const navigate = useNavigate()

  return (
    <section aria-label={`${title} machines`}>
      <div className="card overflow-hidden p-0">
        <div className={`px-5 py-3.5 flex items-center gap-2.5 ${headerClass}`}>
          <span aria-hidden="true">{icon}</span>
          <h3 className="text-sm font-bold">{title}</h3>
          <span className="ml-auto text-sm opacity-75 tabular-nums">
            {rows.length} machine{rows.length !== 1 ? 's' : ''}
          </span>
        </div>

        {rows.length === 0 ? (
          <p className="text-sm text-gray-400 px-5 py-5 text-center">{emptyMessage}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" aria-label={`${title} machines table`}>
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="tbl-header text-left px-5">Machine</th>
                  <th className="tbl-header text-left">Risk</th>
                  <th className="tbl-header text-right pr-4">P(Failure)</th>
                  <th className="tbl-header text-left">Anomaly</th>
                  <th className="tbl-header text-left">Last Assessment</th>
                  <th className="tbl-header text-left">Recommendation</th>
                  <th className="tbl-header text-left">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ machine, assessment }) => (
                  <tr
                    key={machine.id}
                    className="border-b border-gray-100 hover:bg-blue-50/30 transition-colors"
                  >
                    <td className="tbl-cell px-5">
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{machine.machine_identifier}</p>
                        <p className="text-gray-400 text-xs mt-0.5">{machine.type ?? 'Unknown type'}</p>
                      </div>
                    </td>
                    <td className="tbl-cell">
                      {assessment ? (
                        <RiskBadge level={assessment.risk_level} />
                      ) : (
                        <span className="badge badge-info">Unassessed</span>
                      )}
                    </td>
                    <td className="tbl-cell text-right tabular-nums text-gray-700">
                      {assessment ? formatProbability(assessment.failure_probability) : '—'}
                    </td>
                    <td className="tbl-cell">
                      {assessment ? (
                        <span className={assessment.anomaly_score > 0 ? 'text-amber-700 font-semibold' : 'text-green-700'}>
                          {assessment.anomaly_score > 0
                            ? `Anomalous (${formatScore(assessment.anomaly_score)})`
                            : 'Normal'}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="tbl-cell text-gray-400 text-sm">
                      {assessment ? formatTimestamp(assessment.created_at) : 'Never'}
                    </td>
                    <td className="tbl-cell">
                      <span className="text-gray-600 italic text-sm">{recommendation}</span>
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
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function MaintenancePage() {
  const machinesQuery = useQuery({
    queryKey: ['machines'],
    queryFn: () => machinesApi.list(0, 200),
    refetchInterval: 60_000,
  })

  const machines = machinesQuery.data ?? []

  const rowsQuery = useQuery({
    queryKey: ['maintenance-rows', machines.map((m) => m.id).join(',')],
    queryFn: () => fetchAllWithAssessments(machines),
    enabled: machines.length > 0,
    refetchInterval: 60_000,
  })

  const rows: MachineRow[] = rowsQuery.data ?? machines.map((m) => ({ machine: m, assessment: null }))

  // ── States ────────────────────────────────────────────────────────────────

  if (machinesQuery.isLoading) {
    return <LoadingSpinner message="Loading maintenance data…" size="lg" />
  }

  if (machinesQuery.isError) {
    return (
      <ErrorMessage
        title="Could not load machines"
        message="Backend may be unavailable."
        onRetry={() => machinesQuery.refetch()}
      />
    )
  }

  if (machines.length === 0) {
    return (
      <div className="max-w-4xl mx-auto space-y-5">
        <PageHeader title="Maintenance Center" subtitle="Prioritised maintenance view by risk level." />
        <EmptyState
          title="No machines registered"
          message="Register machines and run assessments to see the maintenance priority view."
        />
      </div>
    )
  }

  // ── Group by risk ─────────────────────────────────────────────────────────

  const sortedRows = [...rows].sort((a, b) => {
    const riskDiff = getRiskOrder(a.assessment?.risk_level) - getRiskOrder(b.assessment?.risk_level)
    if (riskDiff !== 0) return riskDiff
    return (b.assessment?.risk_score ?? 0) - (a.assessment?.risk_score ?? 0)
  })

  const criticalRows = sortedRows.filter((r) => r.assessment?.risk_level === 'CRITICAL')
  const warningRows  = sortedRows.filter((r) => r.assessment?.risk_level === 'WARNING')
  const normalRows   = sortedRows.filter((r) => r.assessment?.risk_level === 'NORMAL')
  const unassessedRows = sortedRows.filter((r) => !r.assessment)

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <PageHeader
        title="Maintenance Center"
        subtitle="Machines grouped by risk priority. All recommendations require human review."
        badge={<span className="simulated-label">SYNTHETIC DATASET</span>}
      />

      {/* ── Summary banner ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Critical', count: criticalRows.length, color: 'text-red-700 bg-red-50 border-red-200' },
          { label: 'Warning',  count: warningRows.length,  color: 'text-yellow-700 bg-yellow-50 border-yellow-200' },
          { label: 'Normal',   count: normalRows.length,   color: 'text-green-700 bg-green-50 border-green-200' },
          { label: 'Unassessed', count: unassessedRows.length, color: 'text-gray-700 bg-gray-50 border-gray-200' },
        ].map(({ label, count, color }) => (
          <div key={label} className={`border rounded-xl px-5 py-4 shadow-sm ${color}`}>
            <p className="text-xs font-bold uppercase tracking-widest opacity-75">{label}</p>
            <p className="text-4xl font-bold mt-2 tabular-nums leading-none">{count}</p>
          </div>
        ))}
      </div>

      {/* ── Risk groups ───────────────────────────────────────────────────── */}
      <RiskGroup
        title="Critical — Immediate Attention"
        icon={<AlertOctagon size={16} className="text-red-100" />}
        rows={criticalRows}
        headerClass="bg-red-600 text-white"
        recommendation="Recommended for maintenance review"
        emptyMessage="No critical machines — good."
      />

      <RiskGroup
        title="Warning — Monitor Closely"
        icon={<AlertTriangle size={16} className="text-yellow-100" />}
        rows={warningRows}
        headerClass="bg-yellow-500 text-white"
        recommendation="Schedule maintenance review"
        emptyMessage="No warning-level machines."
      />

      <RiskGroup
        title="Normal — Healthy"
        icon={<ShieldCheck size={16} className="text-green-100" />}
        rows={normalRows}
        headerClass="bg-green-600 text-white"
        recommendation="Continue routine monitoring"
        emptyMessage="No normal-state machines assessed yet."
      />

      {unassessedRows.length > 0 && (
        <RiskGroup
          title="Unassessed"
          icon={<AlertTriangle size={16} className="text-gray-400" />}
          rows={unassessedRows}
          headerClass="bg-gray-200 text-gray-700"
          recommendation="Run initial assessment"
          emptyMessage=""
        />
      )}

      {/* ── Safety notice ─────────────────────────────────────────────────── */}
      <div className="card border border-amber-200 bg-amber-50">
        <p className="text-sm text-amber-800">
          <strong>Important:</strong> &ldquo;Recommended for maintenance review&rdquo; means the AI model
          has identified elevated risk indicators — it does <em>not</em> mean the machine will
          definitely fail. All assessments are based on the UCI AI4I 2020 synthetic dataset.
          Do not act on these recommendations without qualified human review.
        </p>
      </div>
    </div>
  )
}

/**
 * frontend/src/pages/DashboardPage.tsx
 * Executive Overview — KPIs, risk distribution, recent assessments, attention required.
 * All data is sourced from real backend APIs.
 */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Cpu, ShieldCheck, AlertTriangle, AlertOctagon, Activity, ArrowRight } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

import { machinesApi } from '../api/machines'
import type { Machine, Assessment } from '../types'
import {
  getRiskOrder,
  formatProbability,
  formatScore,
  formatTimestamp,
  getRiskBadgeClasses,
  getRiskLabel,
} from '../utils/risk'
import KpiCard from '../components/KpiCard'
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
// Hooks
// ---------------------------------------------------------------------------

function useDashboardData() {
  const machinesQuery = useQuery({
    queryKey: ['machines'],
    queryFn: () => machinesApi.list(0, 200),
    refetchInterval: 60_000,
  })

  return { machinesQuery }
}

// Fetch latest assessment for each machine (first in the list, which is newest)
async function fetchLatestForMachines(machines: Machine[]): Promise<MachineRow[]> {
  const rows = await Promise.all(
    machines.map(async (machine) => {
      try {
        const assessments = await machinesApi.listAssessments(machine.id, 0, 1)
        return { machine, assessment: assessments[0] ?? null }
      } catch {
        return { machine, assessment: null }
      }
    }),
  )
  return rows
}

// ---------------------------------------------------------------------------
// Risk distribution chart colors
// ---------------------------------------------------------------------------

const RISK_COLORS: Record<string, string> = {
  NORMAL: '#16a34a',
  WARNING: '#d97706',
  CRITICAL: '#dc2626',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const navigate = useNavigate()
  const { machinesQuery } = useDashboardData()

  const machines = machinesQuery.data ?? []

  const rowsQuery = useQuery({
    queryKey: ['dashboard-rows', machines.map((m) => m.id).join(',')],
    queryFn: () => fetchLatestForMachines(machines),
    enabled: machines.length > 0,
    refetchInterval: 60_000,
  })

  const rows: MachineRow[] = rowsQuery.data ?? machines.map((m) => ({ machine: m, assessment: null }))

  // ── KPI calculations ──────────────────────────────────────────────────────

  const total = machines.length
  const assessed = rows.filter((r) => r.assessment !== null)
  const healthy = assessed.filter((r) => r.assessment!.risk_level === 'NORMAL').length
  const warning = assessed.filter((r) => r.assessment!.risk_level === 'WARNING').length
  const critical = assessed.filter((r) => r.assessment!.risk_level === 'CRITICAL').length
  const anomalous = assessed.filter((r) => r.assessment!.anomaly_score > 0).length

  // ── Risk distribution for chart ───────────────────────────────────────────

  const riskDistribution = [
    { level: 'NORMAL',   count: healthy,  color: RISK_COLORS.NORMAL },
    { level: 'WARNING',  count: warning,  color: RISK_COLORS.WARNING },
    { level: 'CRITICAL', count: critical, color: RISK_COLORS.CRITICAL },
  ]

  // ── Recent assessments (last 10, sorted newest first) ────────────────────

  const recentRows = [...rows]
    .filter((r) => r.assessment !== null)
    .sort((a, b) =>
      new Date(b.assessment!.created_at).getTime() - new Date(a.assessment!.created_at).getTime(),
    )
    .slice(0, 10)

  // ── Attention required (CRITICAL or WARNING, sorted by risk score) ────────

  const attentionRows = rows
    .filter((r) => r.assessment && r.assessment.risk_level !== 'NORMAL')
    .sort((a, b) => {
      const orderDiff = getRiskOrder(a.assessment!.risk_level) - getRiskOrder(b.assessment!.risk_level)
      if (orderDiff !== 0) return orderDiff
      return (b.assessment?.risk_score ?? 0) - (a.assessment?.risk_score ?? 0)
    })
    .slice(0, 5)

  // ── Loading / Error states ────────────────────────────────────────────────

  if (machinesQuery.isLoading) {
    return <LoadingSpinner message="Loading dashboard…" size="lg" />
  }

  if (machinesQuery.isError) {
    return (
      <ErrorMessage
        title="Backend unavailable"
        message="Could not reach the INDUSTRIA-X API. Please check the backend service."
        onRetry={() => machinesQuery.refetch()}
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <PageHeader
        title="Executive Overview"
        subtitle="Live predictive maintenance status across all registered machines."
        badge={
          <span className="simulated-label" title="Data sourced from UCI AI4I 2020 synthetic dataset">
            SYNTHETIC DATASET
          </span>
        }
      />

      {/* ── KPI Cards ──────────────────────────────────────────────────────── */}
      <section aria-label="Key Performance Indicators">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <KpiCard
            label="Total Machines"
            value={total}
            icon={<Cpu size={24} />}
          />
          <KpiCard
            label="Healthy"
            value={healthy}
            variant="ok"
            icon={<ShieldCheck size={24} />}
          />
          <KpiCard
            label="Warning"
            value={warning}
            variant="warning"
            icon={<AlertTriangle size={24} />}
          />
          <KpiCard
            label="Critical"
            value={critical}
            variant="critical"
            icon={<AlertOctagon size={24} />}
          />
          <KpiCard
            label="Anomalies"
            value={anomalous}
            variant="info"
            subtext="anomaly score > 0"
            icon={<Activity size={24} />}
          />
        </div>
      </section>

      {/* ── Empty state ─────────────────────────────────────────────────────── */}
      {total === 0 && (
        <EmptyState
          title="No machines registered"
          message="Register a machine via the Machines page or the API to begin monitoring."
          action={
            <button
              onClick={() => navigate('/machines')}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
            >
              Go to Machines <ArrowRight size={14} aria-hidden="true" />
            </button>
          }
        />
      )}

      {total > 0 && (
        <>
          {/* ── Risk Distribution ─────────────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <section aria-label="Risk distribution">
              <div className="card h-full">
                <h3 className="section-title mb-4">Risk Distribution</h3>
                {assessed.length === 0 ? (
                  <p className="text-sm text-gray-400 py-4 text-center">
                    No assessments yet — assess machines to see distribution.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {riskDistribution.map(({ level, count, color }) => {
                      const pct = assessed.length > 0 ? (count / assessed.length) * 100 : 0
                      return (
                        <div key={level}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span
                              className={getRiskBadgeClasses(level)}
                              aria-label={`${getRiskLabel(level)}: ${count} machines`}
                            >
                              {getRiskLabel(level)}
                            </span>
                            <span className="text-sm text-gray-500 tabular-nums">
                              {count} / {assessed.length}
                            </span>
                          </div>
                          <div
                            className="h-2.5 bg-gray-100 rounded-full overflow-hidden"
                            role="progressbar"
                            aria-valuenow={Math.round(pct)}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`${level} distribution: ${Math.round(pct)}%`}
                          >
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: color }}
                            />
                          </div>
                        </div>
                      )
                    })}
                    <div className="mt-2 pt-4 border-t border-gray-100">
                      <ResponsiveContainer width="100%" height={100}>
                        <BarChart data={riskDistribution} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                          <XAxis dataKey="level" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                          <Tooltip
                            formatter={(value: number) => [value, 'Machines']}
                            contentStyle={{ fontSize: 13 }}
                          />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {riskDistribution.map((entry) => (
                              <Cell key={entry.level} fill={entry.color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* ── Attention Required ──────────────────────────────────────── */}
            <section aria-label="Attention required">
              <div className="card h-full">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="section-title">Attention Required</h3>
                  <button
                    onClick={() => navigate('/maintenance')}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 transition-colors"
                  >
                    View all <ArrowRight size={13} aria-hidden="true" />
                  </button>
                </div>
                {attentionRows.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <ShieldCheck size={32} className="text-green-500 mb-3" aria-hidden="true" />
                    <p className="text-sm text-gray-500">No machines require immediate attention.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {attentionRows.map(({ machine, assessment }) => (
                      <button
                        key={machine.id}
                        onClick={() => navigate(`/machines/${machine.id}`)}
                        className="w-full flex items-center justify-between p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors text-left group"
                        aria-label={`View details for ${machine.machine_identifier}`}
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-gray-900 truncate max-w-[160px] group-hover:text-blue-700 transition-colors">
                            {machine.machine_identifier}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">{machine.type ?? 'Unknown type'}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1 ml-2 flex-shrink-0">
                          <RiskBadge level={assessment?.risk_level} />
                          {assessment && (
                            <span className="text-xs text-gray-500 tabular-nums">
                              P(fail) {formatProbability(assessment.failure_probability)}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* ── Recent Assessments ─────────────────────────────────────────── */}
          <section aria-label="Recent assessments">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="section-title">Recent Assessments</h3>
                <button
                  onClick={() => navigate('/machines')}
                  className="text-sm text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 transition-colors"
                >
                  View all machines <ArrowRight size={13} aria-hidden="true" />
                </button>
              </div>

              {recentRows.length === 0 ? (
                <p className="text-sm text-gray-400 py-3">
                  No assessments found. Run an assessment from a machine page.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full" aria-label="Recent assessments table">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="tbl-header text-left">Machine</th>
                        <th className="tbl-header text-left">Risk</th>
                        <th className="tbl-header text-right pr-4">Risk Score</th>
                        <th className="tbl-header text-right pr-4">P(Failure)</th>
                        <th className="tbl-header text-left">Anomaly</th>
                        <th className="tbl-header text-left">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentRows.map(({ machine, assessment }) => (
                        <tr
                          key={`${machine.id}-${assessment!.id}`}
                          className="border-b border-gray-50 hover:bg-blue-50/40 cursor-pointer transition-colors"
                          onClick={() => navigate(`/machines/${machine.id}`)}
                          tabIndex={0}
                          onKeyDown={(e) => e.key === 'Enter' && navigate(`/machines/${machine.id}`)}
                          aria-label={`Open ${machine.machine_identifier} details`}
                        >
                          <td className="tbl-cell font-semibold text-gray-900 truncate max-w-[160px]">
                            {machine.machine_identifier}
                          </td>
                          <td className="tbl-cell">
                            <RiskBadge level={assessment!.risk_level} />
                          </td>
                          <td className="tbl-cell text-right text-gray-700 tabular-nums">
                            {formatScore(assessment!.risk_score)}
                          </td>
                          <td className="tbl-cell text-right text-gray-700 tabular-nums">
                            {formatProbability(assessment!.failure_probability)}
                          </td>
                          <td className="tbl-cell">
                            <span className={assessment!.anomaly_score > 0 ? 'text-amber-700 font-semibold' : 'text-green-700'}>
                              {assessment!.anomaly_score > 0 ? `Anomalous (${formatScore(assessment!.anomaly_score)})` : 'Normal'}
                            </span>
                          </td>
                          <td className="tbl-cell text-gray-400">
                            {formatTimestamp(assessment!.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>

          {/* ── Safety notice ─────────────────────────────────────────────── */}
          <div className="card border border-amber-200 bg-amber-50">
            <p className="text-sm text-amber-800">
              <strong>Decision-support only:</strong> INDUSTRIA-X assists maintenance planning but
              cannot control equipment. All recommendations require qualified human review.
              Risk assessments are based on the UCI AI4I 2020 synthetic dataset.
            </p>
          </div>
        </>
      )}
    </div>
  )
}

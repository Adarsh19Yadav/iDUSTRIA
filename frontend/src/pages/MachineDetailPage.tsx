/**
 * frontend/src/pages/MachineDetailPage.tsx
 * Detailed machine view: identity, risk, sensor data, assessment history,
 * AI explanation, and maintenance guidance.
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Cpu,
  AlertOctagon,
  BookOpen,
  Brain,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import toast from 'react-hot-toast'

import { machinesApi } from '../api/machines'
import { ragApi } from '../api/agent'
import type { AssessmentRequest } from '../types'
import {
  formatProbability,
  formatScore,
  formatTimestamp,
} from '../utils/risk'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PageHeader from '../components/PageHeader'
import AssessmentForm from '../components/AssessmentForm'

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function MachineDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const machineId = Number(id)

  const [showAssessForm, setShowAssessForm] = useState(false)
  const [showHistoryChart, setShowHistoryChart] = useState(true)
  const [ragQuestion, setRagQuestion] = useState('')
  const [ragQueried, setRagQueried] = useState(false)

  // ── Machine ────────────────────────────────────────────────────────────────

  const machineQuery = useQuery({
    queryKey: ['machine', machineId],
    queryFn: () => machinesApi.get(machineId),
    enabled: !isNaN(machineId),
    retry: (count, error: unknown) => {
      const status = (error as { response?: { status?: number } }).response?.status
      if (status === 404) return false
      return count < 2
    },
  })

  // ── Assessments ────────────────────────────────────────────────────────────

  const assessmentsQuery = useQuery({
    queryKey: ['assessments', machineId],
    queryFn: () => machinesApi.listAssessments(machineId, 0, 50),
    enabled: !isNaN(machineId),
  })

  const latestAssessment = assessmentsQuery.data?.[0] ?? null
  const assessmentHistory = assessmentsQuery.data ?? []

  // ── RAG query ──────────────────────────────────────────────────────────────

  const ragQuery = useQuery({
    queryKey: ['rag', ragQuestion],
    queryFn: () => ragApi.query({ question: ragQuestion, top_k: 4 }),
    enabled: ragQueried && ragQuestion.length > 0,
    staleTime: 5 * 60_000,
  })

  // ── Assess mutation ────────────────────────────────────────────────────────

  const assessMutation = useMutation({
    mutationFn: (req: AssessmentRequest) => machinesApi.assess(machineId, req),
    onSuccess: (assessment) => {
      toast.success(`Assessment complete — Risk: ${assessment.risk_level}`)
      queryClient.invalidateQueries({ queryKey: ['assessments', machineId] })
      queryClient.invalidateQueries({ queryKey: ['machines'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-rows'] })
      setShowAssessForm(false)
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } }).response?.status
      if (status === 503) {
        toast.error('ML model artifacts are unavailable.')
      } else if (status === 429) {
        toast.error('Rate limit reached. Please wait before re-assessing.')
      } else {
        toast.error('Assessment failed. Please check input values and try again.')
      }
    },
  })

  // ── RAG guidance trigger ───────────────────────────────────────────────────

  function triggerRagGuidance() {
    if (!machineQuery.data) return
    const question = `What maintenance should be considered for a ${
      machineQuery.data.type ?? 'industrial'
    } machine with risk level ${latestAssessment?.risk_level ?? 'unknown'}?`
    setRagQuestion(question)
    setRagQueried(true)
  }

  // ── Guard states ───────────────────────────────────────────────────────────

  if (isNaN(machineId)) {
    return (
      <ErrorMessage title="Invalid machine ID" message="The machine ID in the URL is not valid." />
    )
  }

  if (machineQuery.isLoading) {
    return <LoadingSpinner message="Loading machine details…" size="lg" />
  }

  if (machineQuery.isError) {
    const status = (machineQuery.error as { response?: { status?: number } }).response?.status
    return (
      <ErrorMessage
        title={status === 404 ? 'Machine not found' : 'Could not load machine'}
        message={
          status === 404
            ? `Machine with ID ${machineId} does not exist.`
            : 'Backend may be unavailable.'
        }
        onRetry={status !== 404 ? () => machineQuery.refetch() : undefined}
      />
    )
  }

  const machine = machineQuery.data!

  // ── Chart data ─────────────────────────────────────────────────────────────

  const chartData = [...assessmentHistory]
    .reverse()
    .slice(-20)
    .map((a, idx) => ({
      idx: idx + 1,
      risk_score: Number(a.risk_score.toFixed(3)),
      failure_probability: Number((a.failure_probability * 100).toFixed(1)),
      label: formatTimestamp(a.created_at),
    }))

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <PageHeader
        title={machine.machine_identifier}
        subtitle={machine.type ? `Type: ${machine.type}` : 'Type: unspecified'}
        badge={<span className="simulated-label">SYNTHETIC DATASET</span>}
        actions={
          <button
            onClick={() => navigate('/machines')}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors font-medium"
            aria-label="Back to machine list"
          >
            <ArrowLeft size={15} aria-hidden="true" /> Back to Machines
          </button>
        }
      />

      {/* ── Identity card ────────────────────────────────────────────────── */}
      <section aria-label="Machine identity">
        <div className="card grid grid-cols-2 md:grid-cols-4 gap-5">
          <div>
            <p className="text-xs text-gray-500 font-medium mb-1">Machine ID</p>
            <p className="text-sm font-semibold text-gray-900">#{machine.id}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 font-medium mb-1">Identifier</p>
            <p className="text-sm font-mono text-gray-900">{machine.machine_identifier}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 font-medium mb-1">Registered</p>
            <p className="text-sm text-gray-700">{formatTimestamp(machine.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 font-medium mb-1">Last updated</p>
            <p className="text-sm text-gray-700">{formatTimestamp(machine.updated_at)}</p>
          </div>
        </div>
      </section>

      {/* ── Current Risk ─────────────────────────────────────────────────── */}
      <section aria-label="Current risk assessment">
        <div className="card">
          <div className="flex items-center justify-between mb-5">
            <h3 className="section-title flex items-center gap-2">
              <AlertOctagon size={18} aria-hidden="true" className="text-gray-500" />
              Current Risk
            </h3>
            <button
              onClick={() => setShowAssessForm(!showAssessForm)}
              className="btn-primary btn-sm"
              aria-label="Run new assessment"
              aria-expanded={showAssessForm}
            >
              <RefreshCw size={14} aria-hidden="true" />
              Assess Machine
            </button>
          </div>

          {latestAssessment ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-5">
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1.5">Risk Level</p>
                <RiskBadge level={latestAssessment.risk_level} />
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1.5">Risk Score</p>
                <p className="text-lg font-bold tabular-nums text-gray-900">{formatScore(latestAssessment.risk_score)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1.5">P(Failure)</p>
                <p className="text-lg font-bold tabular-nums text-gray-900">{formatProbability(latestAssessment.failure_probability)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1.5">Anomaly Score</p>
                <p className={`text-lg font-bold tabular-nums ${latestAssessment.anomaly_score > 0 ? 'text-amber-700' : 'text-green-700'}`}>
                  {formatScore(latestAssessment.anomaly_score)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1.5">Anomaly Status</p>
                <span className={latestAssessment.anomaly_score > 0 ? 'badge badge-warn' : 'badge badge-ok'}>
                  {latestAssessment.anomaly_score > 0 ? 'Anomalous' : 'Normal'}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 text-center gap-3">
              <Cpu size={36} className="text-gray-300" aria-hidden="true" />
              <p className="text-sm text-gray-500">No assessment has been run yet.</p>
              <p className="text-sm text-gray-400">Click <strong>Assess Machine</strong> to run the first assessment.</p>
            </div>
          )}

          {latestAssessment && (
            <p className="text-sm text-gray-400 mt-4 pt-4 border-t border-gray-100">
              Latest assessment: {formatTimestamp(latestAssessment.created_at)} · Model: {latestAssessment.model_version}
            </p>
          )}
        </div>
      </section>

      {/* ── Assessment Form ───────────────────────────────────────────────── */}
      {showAssessForm && (
        <section aria-label="Assessment input form">
          <AssessmentForm
            onSubmit={(req) => assessMutation.mutate(req)}
            onCancel={() => setShowAssessForm(false)}
            isSubmitting={assessMutation.isPending}
            error={assessMutation.isError ? 'Assessment failed. Check input values and try again.' : null}
          />
        </section>
      )}

      {/* ── Assessment History ────────────────────────────────────────────── */}
      <section aria-label="Assessment history">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">Assessment History</h3>
            <button
              onClick={() => setShowHistoryChart(!showHistoryChart)}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              aria-label={showHistoryChart ? 'Show table view' : 'Show chart view'}
            >
              {showHistoryChart ? (
                <><ChevronUp size={14} aria-hidden="true" /> Chart</>
              ) : (
                <><ChevronDown size={14} aria-hidden="true" /> Chart</>
              )}
            </button>
          </div>

          {assessmentsQuery.isLoading && <LoadingSpinner message="Loading history…" size="sm" />}
          {assessmentsQuery.isError && <p className="text-sm text-red-500">Could not load history.</p>}

          {assessmentHistory.length === 0 && !assessmentsQuery.isLoading ? (
            <p className="text-sm text-gray-400 py-3 text-center">No assessments yet.</p>
          ) : (
            <>
              {/* Chart */}
              {showHistoryChart && chartData.length > 0 && (
                <div className="mb-5">
                  <p className="text-sm text-gray-500 mb-2">Risk Score &amp; Failure Probability over time (last 20)</p>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                      <XAxis dataKey="idx" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} domain={[0, 1]} />
                      <Tooltip
                        formatter={(value: number, name: string) => [
                          name === 'failure_probability' ? `${value}%` : value,
                          name === 'failure_probability' ? 'P(Failure)' : 'Risk Score',
                        ]}
                        contentStyle={{ fontSize: 13 }}
                      />
                      <ReferenceLine y={0.5} stroke="#d97706" strokeDasharray="3 3" />
                      <Line
                        type="monotone"
                        dataKey="risk_score"
                        stroke="#3b82f6"
                        dot={false}
                        strokeWidth={2}
                        name="risk_score"
                      />
                      <Line
                        type="monotone"
                        dataKey="failure_probability"
                        stroke="#ef4444"
                        dot={false}
                        strokeWidth={2}
                        name="failure_probability"
                        yAxisId={0}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  <p className="text-xs text-gray-400 text-center mt-1.5">
                    Blue = Risk Score · Red = P(Failure) × 100 · Dashed = 0.5 threshold
                  </p>
                </div>
              )}

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Assessment history table">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="tbl-header text-left">#</th>
                      <th className="tbl-header text-left">Risk</th>
                      <th className="tbl-header text-right pr-4">Score</th>
                      <th className="tbl-header text-right pr-4">P(Failure)</th>
                      <th className="tbl-header text-right pr-4">Anomaly</th>
                      <th className="tbl-header text-left">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assessmentHistory.slice(0, 20).map((a, idx) => (
                      <tr key={a.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="tbl-cell text-gray-500 font-medium">{idx === 0 ? '★ Latest' : `#${a.id}`}</td>
                        <td className="tbl-cell"><RiskBadge level={a.risk_level} /></td>
                        <td className="tbl-cell text-right tabular-nums text-gray-700">{formatScore(a.risk_score)}</td>
                        <td className="tbl-cell text-right tabular-nums text-gray-700">{formatProbability(a.failure_probability)}</td>
                        <td className={`tbl-cell text-right tabular-nums ${a.anomaly_score > 0 ? 'text-amber-700 font-semibold' : 'text-green-700'}`}>
                          {formatScore(a.anomaly_score)}
                        </td>
                        <td className="tbl-cell text-gray-400">{formatTimestamp(a.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {assessmentHistory.length > 20 && (
                  <p className="text-sm text-gray-400 text-center pt-3">
                    Showing 20 of {assessmentHistory.length} assessments.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </section>

      {/* ── Maintenance Guidance (RAG) ────────────────────────────────────── */}
      <section aria-label="Maintenance guidance">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title flex items-center gap-2">
              <BookOpen size={18} aria-hidden="true" className="text-gray-500" />
              Maintenance Guidance
            </h3>
            <button
              onClick={triggerRagGuidance}
              disabled={ragQuery.isFetching}
              className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold text-purple-700 border border-purple-200 rounded-lg hover:bg-purple-50 disabled:opacity-50 transition-colors shadow-sm"
              aria-label="Retrieve maintenance guidance from knowledge base"
            >
              {ragQuery.isFetching ? (
                <><RefreshCw size={13} className="animate-spin" aria-hidden="true" /> Searching…</>
              ) : (
                <><BookOpen size={13} aria-hidden="true" /> Get Guidance</>
              )}
            </button>
          </div>

          {!ragQueried && (
            <p className="text-sm text-gray-400 py-3">
              Click <strong>Get Guidance</strong> to retrieve relevant maintenance documentation
              from the knowledge base.
            </p>
          )}

          {ragQuery.isError && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
              Knowledge base is unavailable. Cannot retrieve maintenance guidance.
              Do not infer maintenance recommendations from unavailable sources.
            </div>
          )}

          {ragQuery.data && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500 italic">
                Query: &ldquo;{ragQuery.data.question}&rdquo; · {ragQuery.data.total_results} results
              </p>
              {ragQuery.data.results.map((chunk, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-700 truncate max-w-[220px]">
                      {chunk.source}
                    </span>
                    <span className="text-xs text-gray-400 tabular-nums ml-2 flex-shrink-0">
                      Relevance: {(1 - chunk.distance).toFixed(3)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">{chunk.content}</p>
                </div>
              ))}
              <p className="text-xs text-gray-400 pt-2 border-t border-gray-100">
                <Brain size={12} className="inline mr-1" aria-hidden="true" />
                Retrieved from maintenance knowledge base. Evidence-based guidance only.
                All recommendations require qualified human review.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── Safety notice ─────────────────────────────────────────────────── */}
      <div className="card border border-amber-200 bg-amber-50">
        <p className="text-sm text-amber-800">
          <strong>Decision-support only:</strong> This dashboard is a decision-support tool.
          Risk assessments are based on the UCI AI4I 2020 synthetic dataset.
          All maintenance decisions require review by qualified personnel.
          Do not act on these assessments without human oversight.
        </p>
      </div>
    </div>
  )
}

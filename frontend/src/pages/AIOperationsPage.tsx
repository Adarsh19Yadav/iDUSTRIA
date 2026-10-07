/**
 * frontend/src/pages/AIOperationsPage.tsx
 * AI Operations Center — submit queries to the agentic AI system.
 * Displays: answer, tools used, evidence, RAG sources.
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Send, Wrench, BookOpen, AlertTriangle, Info } from 'lucide-react'

import { agentApi } from '../api/agent'
import { machinesApi } from '../api/machines'
import type { AgentQuery, AgentResponse } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import RiskBadge from '../components/RiskBadge'

// ---------------------------------------------------------------------------
// Suggested queries
// ---------------------------------------------------------------------------

const SUGGESTED_QUERIES = [
  'Why is this machine high risk?',
  'Is this machine anomalous?',
  'What maintenance should be considered?',
  'What is the failure probability?',
  'Explain the main risk factors.',
]

// ---------------------------------------------------------------------------
// Tool evidence display
// ---------------------------------------------------------------------------

function EvidenceBlock({ tool, result }: { tool: string; result: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <Wrench size={14} aria-hidden="true" className="text-gray-400" />
          {tool}
        </span>
        <span className="text-gray-400 text-xs">{open ? '▲ collapse' : '▼ expand'}</span>
      </button>
      {open && (
        <div className="px-4 py-3 text-xs">
          <pre className="whitespace-pre-wrap text-gray-600 font-mono text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto max-h-48">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AIOperationsPage() {
  const [query, setQuery] = useState('')
  const [selectedMachineId, setSelectedMachineId] = useState<string>('')
  const [includeSensors, setIncludeSensors] = useState(false)
  const [sensorValues, setSensorValues] = useState({
    air_temperature_k: '300.0',
    process_temperature_k: '310.0',
    rotational_speed_rpm: '1500',
    torque_nm: '40.0',
    tool_wear_min: '100',
    type: 'M',
  })
  const [lastResponse, setLastResponse] = useState<AgentResponse | null>(null)

  // ── Fetch machines for selector ───────────────────────────────────────────

  const machinesQuery = useQuery({
    queryKey: ['machines'],
    queryFn: () => machinesApi.list(0, 200),
    staleTime: 30_000,
  })
  const machines = machinesQuery.data ?? []

  // ── Agent mutation ────────────────────────────────────────────────────────

  const agentMutation = useMutation({
    mutationFn: (body: AgentQuery) => agentApi.query(body),
    onSuccess: (data) => setLastResponse(data),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    const selectedMachine = machines.find((m) => String(m.id) === selectedMachineId)

    const body: AgentQuery = {
      query: query.trim(),
      machine_id: selectedMachine?.machine_identifier ?? null,
      machine_input:
        includeSensors
          ? {
              'Air temperature [K]': parseFloat(sensorValues.air_temperature_k),
              'Process temperature [K]': parseFloat(sensorValues.process_temperature_k),
              'Rotational speed [rpm]': parseFloat(sensorValues.rotational_speed_rpm),
              'Torque [Nm]': parseFloat(sensorValues.torque_nm),
              'Tool wear [min]': parseFloat(sensorValues.tool_wear_min),
              'Type': sensorValues.type,
            }
          : null,
    }
    agentMutation.mutate(body)
  }

  function applySuggestion(suggestion: string) {
    setQuery(suggestion)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <PageHeader
        title="AI Operations Center"
        subtitle="Ask the INDUSTRIA-X agentic AI about machine health and maintenance."
        badge={<span className="ai-label"><Bot size={13} aria-hidden="true" /> AI</span>}
      />

      {/* ── Query form ────────────────────────────────────────────────────── */}
      <section aria-label="AI query input">
        <div className="card space-y-4">
          {/* Machine selector */}
          <div>
            <label htmlFor="machine-select" className="block text-sm font-semibold text-gray-700 mb-1.5">
              Machine <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <select
              id="machine-select"
              value={selectedMachineId}
              onChange={(e) => setSelectedMachineId(e.target.value)}
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white transition-shadow"
            >
              <option value="">— No specific machine —</option>
              {machines.map((m) => (
                <option key={m.id} value={String(m.id)}>
                  {m.machine_identifier}{m.type ? ` (${m.type})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Include sensor toggle */}
          <div className="flex items-center gap-2.5">
            <input
              id="include-sensors"
              type="checkbox"
              checked={includeSensors}
              onChange={(e) => setIncludeSensors(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="include-sensors" className="text-sm text-gray-700 cursor-pointer">
              Include sensor readings for ML inference
            </label>
          </div>

          {/* Sensor inputs */}
          {includeSensors && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
              <p className="text-sm font-semibold text-amber-800 flex items-center gap-1.5">
                <Info size={13} aria-hidden="true" /> SIMULATED / SYNTHETIC DEMO DATA
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  { key: 'air_temperature_k', label: 'Air Temp [K]' },
                  { key: 'process_temperature_k', label: 'Process Temp [K]' },
                  { key: 'rotational_speed_rpm', label: 'Speed [rpm]' },
                  { key: 'torque_nm', label: 'Torque [Nm]' },
                  { key: 'tool_wear_min', label: 'Tool Wear [min]' },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <label htmlFor={`sensor-${key}`} className="block text-xs text-gray-600 mb-1">{label}</label>
                    <input
                      id={`sensor-${key}`}
                      type="number"
                      step="any"
                      value={sensorValues[key as keyof typeof sensorValues]}
                      onChange={(e) => setSensorValues((prev) => ({ ...prev, [key]: e.target.value }))}
                      className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-400 tabular-nums transition-shadow"
                    />
                  </div>
                ))}
                <div>
                  <label htmlFor="sensor-type" className="block text-xs text-gray-600 mb-1">Type</label>
                  <select
                    id="sensor-type"
                    value={sensorValues.type}
                    onChange={(e) => setSensorValues((prev) => ({ ...prev, type: e.target.value }))}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white transition-shadow"
                  >
                    <option>L</option>
                    <option>M</option>
                    <option>H</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Query input */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="agent-query" className="block text-sm font-semibold text-gray-700 mb-1.5">
                Question
              </label>
              <textarea
                id="agent-query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask about machine health, risk factors, or maintenance guidance…"
                rows={3}
                maxLength={1000}
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-shadow"
                aria-label="AI query"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Max 1000 characters</span>
                <span>{query.length}/1000</span>
              </div>
            </div>

            {/* Suggested queries */}
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUERIES.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => applySuggestion(suggestion)}
                  className="px-2.5 py-1.5 text-xs text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors font-medium"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!query.trim() || agentMutation.isPending}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                aria-disabled={agentMutation.isPending}
              >
                {agentMutation.isPending ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Processing…
                  </>
                ) : (
                  <><Send size={15} aria-hidden="true" /> Ask AI</>
                )}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* ── Loading ───────────────────────────────────────────────────────── */}
      {agentMutation.isPending && (
        <LoadingSpinner message="AI agent is processing your query…" size="md" />
      )}

      {/* ── Error ─────────────────────────────────────────────────────────── */}
      {agentMutation.isError && !agentMutation.isPending && (
        <div
          className="card border border-red-200 bg-red-50"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={15} className="text-red-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="text-sm font-semibold text-red-800">Agent request failed</p>
              <p className="text-xs text-red-600 mt-0.5">
                The AI agent could not process your query. Please check the backend service and try again.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Response ─────────────────────────────────────────────────────── */}
      {lastResponse && !agentMutation.isPending && (
        <div className="space-y-4" aria-live="polite" aria-label="AI response">
          {/* Status */}
          {lastResponse.status !== 'success' && (
            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-center gap-2">
              <AlertTriangle size={14} aria-hidden="true" />
              Agent completed with status: <strong>{lastResponse.status}</strong>
              {lastResponse.error_detail && ` — ${lastResponse.error_detail}`}
            </div>
          )}

          {/* AI Answer */}
          <section aria-label="AI answer">
            <div className="card border-l-4 border-blue-500">
              <div className="flex items-center gap-2.5 mb-3">
                <Bot size={18} className="text-blue-600" aria-hidden="true" />
                <h3 className="section-title">AI Answer</h3>
                <span className="ai-label ml-auto">AI-generated</span>
              </div>
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {lastResponse.answer}
              </p>
              <p className="text-xs text-gray-400 mt-4 pt-3 border-t border-gray-100">
                <strong>Decision-support only.</strong> This is an AI-generated response based on
                synthetic data. All maintenance decisions require qualified human review.
              </p>
            </div>
          </section>

          {/* Tools Used */}
          {lastResponse.tools_used.length > 0 && (
            <section aria-label="Tools used by agent">
              <div className="card">
                <h3 className="section-title mb-3 flex items-center gap-2">
                  <Wrench size={16} aria-hidden="true" className="text-gray-500" />
                  Tools Used
                </h3>
                <div className="flex flex-wrap gap-2">
                  {lastResponse.tools_used.map((tool) => (
                    <span key={tool} className="badge badge-info">{tool}</span>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Evidence */}
          {lastResponse.evidence.length > 0 && (
            <section aria-label="Tool evidence">
              <div className="card">
                <h3 className="section-title mb-3">Evidence</h3>
                <div className="space-y-2">
                  {lastResponse.evidence.map((ev, i) => (
                    <EvidenceBlock key={i} tool={ev.tool} result={ev.result} />
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Sources */}
          {lastResponse.sources.length > 0 && (
            <section aria-label="Knowledge base sources">
              <div className="card">
                <h3 className="section-title mb-3 flex items-center gap-2">
                  <BookOpen size={16} aria-hidden="true" className="text-gray-500" />
                  Retrieved Sources
                </h3>
                <div className="space-y-3">
                  {lastResponse.sources.map((src, i) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-semibold text-gray-700">{src.source}</span>
                        <span className="text-xs text-gray-400 tabular-nums">
                          Chunk #{src.chunk_index} · Dist {src.distance.toFixed(3)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 leading-relaxed">{src.excerpt}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Risk levels in evidence */}
          {lastResponse.evidence.some((ev) => ev.result.risk_level) && (
            <div className="flex flex-wrap gap-2 items-center text-sm text-gray-500">
              <span>Risk levels referenced:</span>
              {lastResponse.evidence
                .filter((ev) => ev.result.risk_level)
                .map((ev, i) => (
                  <RiskBadge key={i} level={String(ev.result.risk_level)} />
                ))}
            </div>
          )}
        </div>
      )}

      {/* ── Safety notice ─────────────────────────────────────────────────── */}
      <div className="card border border-amber-200 bg-amber-50">
        <p className="text-sm text-amber-800">
          <strong>Safety:</strong> The AI agent is a decision-support prototype using synthetic data
          from the UCI AI4I 2020 dataset. It cannot control industrial equipment.
          Never act on AI-generated recommendations without qualified human review.
          Chain-of-thought reasoning is not displayed.
        </p>
      </div>
    </div>
  )
}

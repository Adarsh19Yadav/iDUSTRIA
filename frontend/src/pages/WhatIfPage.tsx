/**
 * frontend/src/pages/WhatIfPage.tsx
 * Phase 11 — What-If Analysis: simulate machine parameter changes and
 * compare model-estimated outcomes between baseline and scenario.
 *
 * DISCLAIMER: Results are model simulations based on the AI4I 2020 synthetic
 * dataset — not guaranteed physical outcomes.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FlaskConical, TrendingUp, TrendingDown, Minus, AlertTriangle, Info } from 'lucide-react'

import { whatifApi } from '../api/whatif'
import type { WhatIfInputs, WhatIfResponse, AssessmentSnapshot } from '../types/whatif'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import RiskBadge from '../components/RiskBadge'
import { formatProbability, formatScore } from '../utils/risk'

// ── Default values (typical mid-range operating conditions) ───────────────────

const DEFAULT_INPUTS: WhatIfInputs = {
  'Air temperature [K]': 300,
  'Process temperature [K]': 310,
  'Rotational speed [rpm]': 1500,
  'Torque [Nm]': 45,
  'Tool wear [min]': 100,
  'Type': 'M',
}

// ── Delta indicator component ─────────────────────────────────────────────────

function DeltaIndicator({ delta, format }: { delta: number; format: (v: number) => string }) {
  const abs = Math.abs(delta)
  if (abs < 0.0005) {
    return <span className="flex items-center gap-1 text-gray-500"><Minus size={12} /> No change</span>
  }
  if (delta > 0) {
    return (
      <span className="flex items-center gap-1 text-red-600 font-semibold">
        <TrendingUp size={12} /> +{format(abs)}
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1 text-green-600 font-semibold">
      <TrendingDown size={12} /> -{format(abs)}
    </span>
  )
}

// ── Comparison table row ──────────────────────────────────────────────────────

function ComparisonRow({
  label,
  baseline,
  scenario,
  delta,
  format,
  isRiskLevel,
}: {
  label: string
  baseline: string | number
  scenario: string | number
  delta?: number
  format?: (v: number) => string
  isRiskLevel?: boolean
}) {
  const hasChange = delta !== undefined && Math.abs(delta) >= 0.0005

  return (
    <tr className={`border-b border-gray-100 ${hasChange ? 'bg-amber-50' : ''}`}>
      <td className="tbl-cell font-medium text-gray-700">{label}</td>
      <td className="tbl-cell text-right tabular-nums">
        {isRiskLevel ? (
          <RiskBadge level={baseline as string} />
        ) : (
          <span className="text-gray-700">{baseline}</span>
        )}
      </td>
      <td className="tbl-cell text-right tabular-nums">
        {isRiskLevel ? (
          <RiskBadge level={scenario as string} />
        ) : (
          <span className={hasChange ? 'font-semibold text-gray-900' : 'text-gray-700'}>
            {scenario}
          </span>
        )}
      </td>
      <td className="tbl-cell">
        {delta !== undefined && format ? (
          <DeltaIndicator delta={delta} format={format} />
        ) : isRiskLevel && baseline !== scenario ? (
          <span className="text-amber-700 font-semibold flex items-center gap-1">
            <AlertTriangle size={12} /> Changed
          </span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )}
      </td>
    </tr>
  )
}

// ── Parameter input row ───────────────────────────────────────────────────────

function ParameterInput({
  label,
  value,
  onChange,
  min,
  max,
  step,
  isSelect,
  options,
}: {
  label: string
  value: number | string
  onChange: (v: number | string) => void
  min?: number
  max?: number
  step?: number
  isSelect?: boolean
  options?: string[]
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-44 text-xs text-gray-600 font-medium shrink-0">{label}</label>
      {isSelect && options ? (
        <select
          value={value as string}
          onChange={(e) => onChange(e.target.value)}
          className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          aria-label={label}
        >
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      ) : (
        <input
          type="number"
          value={value as number}
          min={min}
          max={max}
          step={step ?? 1}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-32 px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 tabular-nums"
          aria-label={label}
        />
      )}
    </div>
  )
}

// ── Inputs panel ──────────────────────────────────────────────────────────────

function InputsPanel({
  title,
  inputs,
  onUpdate,
  readonly,
}: {
  title: string
  inputs: WhatIfInputs
  onUpdate?: (key: keyof WhatIfInputs, value: number | string) => void
  readonly?: boolean
}) {
  const fields: { key: keyof WhatIfInputs; label: string; min?: number; max?: number; step?: number; isSelect?: boolean; options?: string[] }[] = [
    { key: 'Air temperature [K]',       label: 'Air Temperature (K)',       min: 250, max: 400, step: 0.5 },
    { key: 'Process temperature [K]',   label: 'Process Temperature (K)',   min: 250, max: 400, step: 0.5 },
    { key: 'Rotational speed [rpm]',    label: 'Rotational Speed (rpm)',    min: 0,   max: 5000, step: 10 },
    { key: 'Torque [Nm]',               label: 'Torque (Nm)',               min: 0,   max: 200, step: 0.5 },
    { key: 'Tool wear [min]',           label: 'Tool Wear (min)',           min: 0,   max: 600, step: 1 },
    { key: 'Type',                      label: 'Type (L / M / H)',          isSelect: true, options: ['L', 'M', 'H'] },
  ]

  return (
    <div className="card space-y-3">
      <h3 className="section-title">{title}</h3>
      <div className="space-y-2">
        {fields.map(({ key, label, min, max, step, isSelect, options }) => (
          <ParameterInput
            key={key}
            label={label}
            value={inputs[key]}
            onChange={readonly ? () => {} : (v) => onUpdate?.(key, v)}
            min={min}
            max={max}
            step={step}
            isSelect={isSelect}
            options={options}
          />
        ))}
      </div>
      {readonly && (
        <p className="text-xs text-gray-400 italic">Edit in the Baseline panel, then modify for scenario.</p>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WhatIfPage() {
  const [baseline, setBaseline] = useState<WhatIfInputs>({ ...DEFAULT_INPUTS })
  const [scenario, setScenario] = useState<WhatIfInputs>({ ...DEFAULT_INPUTS })
  const [result, setResult] = useState<WhatIfResponse | null>(null)

  const mutation = useMutation({
    mutationFn: () => whatifApi.analyze({ baseline, scenario }),
    onSuccess: (data) => setResult(data),
  })

  function updateBaseline(key: keyof WhatIfInputs, value: number | string) {
    setBaseline((prev) => ({ ...prev, [key]: value }))
    setResult(null)
  }

  function updateScenario(key: keyof WhatIfInputs, value: number | string) {
    setScenario((prev) => ({ ...prev, [key]: value }))
    setResult(null)
  }

  function copyBaselineToScenario() {
    setScenario({ ...baseline })
    setResult(null)
  }

  const fp = (v: number) => formatProbability(v)
  const sc = (v: number) => formatScore(v)

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <PageHeader
        title="What-If Analysis"
        subtitle="Simulate machine parameter changes and compare model-estimated outcomes."
        badge={<span className="simulated-label">SYNTHETIC DATASET</span>}
      />

      {/* ── Disclaimer ───────────────────────────────────────────────────── */}
      <div className="card border border-blue-200 bg-blue-50 flex gap-3">
        <Info size={17} className="text-blue-600 shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-sm text-blue-800 leading-relaxed">
          <strong>What-if results are model simulations</strong> based on the AI4I 2020 synthetic
          training dataset. They represent model-estimated changes, not guaranteed physical outcomes.
          Do not use these results as a substitute for qualified engineering assessment.
        </p>
      </div>

      {/* ── Input panels ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <InputsPanel
          title="Baseline — Current Operating Conditions"
          inputs={baseline}
          onUpdate={updateBaseline}
        />
        <div className="space-y-3">
          <InputsPanel
            title="Scenario — Modified Conditions"
            inputs={scenario}
            onUpdate={updateScenario}
          />
          <button
            type="button"
            onClick={copyBaselineToScenario}
            className="text-sm text-blue-600 hover:text-blue-800 underline transition-colors"
          >
            Reset scenario to match baseline
          </button>
        </div>
      </div>

      {/* ── Run button ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Run what-if scenario"
        >
          <FlaskConical size={16} aria-hidden="true" />
          {mutation.isPending ? 'Running…' : 'Run Scenario'}
        </button>
        {mutation.isPending && <LoadingSpinner size="sm" message="" />}
        {mutation.isError && (
          <span className="text-sm text-red-600">
            {(mutation.error as Error)?.message ?? 'Analysis failed. Check inputs.'}
          </span>
        )}
      </div>

      {/* ── Results ──────────────────────────────────────────────────────── */}
      {result && (
        <div className="space-y-4">
          {/* OOD warning */}
          {result.out_of_distribution_warning && (
            <div className="card border border-amber-300 bg-amber-50 flex gap-3">
              <AlertTriangle size={17} className="text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
              <p className="text-sm text-amber-800 leading-relaxed">
                <strong>Out-of-distribution warning:</strong> {result.out_of_distribution_warning}
              </p>
            </div>
          )}

          {/* Comparison table */}
          <div className="card overflow-hidden p-0">
            <div className="px-5 py-4 bg-gray-800 text-white">
              <h3 className="text-base font-bold">Model-Estimated Comparison</h3>
              <p className="text-xs text-gray-300 mt-0.5">
                Model-estimated change — not a guaranteed outcome
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full" aria-label="What-if comparison table">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="tbl-header text-left px-5 w-48">Metric</th>
                    <th className="tbl-header text-right pr-4">Baseline</th>
                    <th className="tbl-header text-right pr-4">Scenario</th>
                    <th className="tbl-header text-left">Change</th>
                  </tr>
                </thead>
                <tbody>
                  <ComparisonRow
                    label="Failure Probability"
                    baseline={fp(result.baseline.failure_probability)}
                    scenario={fp(result.scenario.failure_probability)}
                    delta={result.change.failure_probability_delta}
                    format={fp}
                  />
                  <ComparisonRow
                    label="Anomaly Score"
                    baseline={sc(result.baseline.anomaly_score)}
                    scenario={sc(result.scenario.anomaly_score)}
                    delta={result.change.anomaly_score_delta}
                    format={sc}
                  />
                  <ComparisonRow
                    label="Risk Score"
                    baseline={sc(result.baseline.risk_score)}
                    scenario={sc(result.scenario.risk_score)}
                    delta={result.change.risk_score_delta}
                    format={sc}
                  />
                  <ComparisonRow
                    label="Risk Level"
                    baseline={result.baseline.risk_level}
                    scenario={result.scenario.risk_level}
                    isRiskLevel
                  />
                </tbody>
              </table>
            </div>
          </div>

          {/* Summary */}
          <div className="card border border-gray-200 bg-gray-50">
            <p className="text-sm text-gray-600 leading-relaxed">
              <strong>Summary:</strong>{' '}
              {result.change.risk_level_changed ? (
                <span className="text-amber-700 font-semibold">
                  Risk level changed from {result.baseline.risk_level} to{' '}
                  {result.scenario.risk_level}.{' '}
                </span>
              ) : (
                <span>Risk level unchanged ({result.baseline.risk_level}). </span>
              )}
              Failure probability{' '}
              {Math.abs(result.change.failure_probability_delta) < 0.0005
                ? 'unchanged'
                : result.change.failure_probability_delta > 0
                ? `increased by ${fp(Math.abs(result.change.failure_probability_delta))}`
                : `decreased by ${fp(Math.abs(result.change.failure_probability_delta))}`}
              .
            </p>
            <p className="text-xs text-gray-400 mt-1.5 italic">{result.disclaimer}</p>
          </div>
        </div>
      )}
    </div>
  )
}

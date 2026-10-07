/**
 * frontend/src/pages/SustainabilityPage.tsx
 * Phase 10 — Sustainability & Energy Intelligence Dashboard
 *
 * Displays engineering ESTIMATES of power, energy, and CO₂e based on
 * machine operating parameters. All values are clearly labelled as estimated.
 *
 * DISCLOSURE: The AI4I dataset contains no real electrical energy measurements.
 * All outputs are theoretical estimates from kinematic parameters.
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Zap, Clock, Wind, Flame, Info, ChevronDown, ChevronUp } from 'lucide-react'

import { sustainabilityApi } from '../api/sustainability'
import { machinesApi } from '../api/machines'
import type { SustainabilityEstimate, SustainabilityEstimateRequest } from '../types/sustainability'
import type { Machine } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number, decimals = 3): string {
  return n.toFixed(decimals)
}

// ---------------------------------------------------------------------------
// EstLabel — small pill badge for estimated values
// ---------------------------------------------------------------------------
function EstLabel() {
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-bold
                 bg-amber-100 text-amber-800 border border-amber-300 ml-1"
      aria-label="Estimated value"
    >
      EST.
    </span>
  )
}

// ---------------------------------------------------------------------------
// KPI Card for sustainability metrics
// ---------------------------------------------------------------------------
interface SustainKpiProps {
  label: string
  value: string
  unit: string
  icon: React.ReactNode
  colorClass: string
}

function SustainKpi({ label, value, unit, icon, colorClass }: SustainKpiProps) {
  return (
    <div className={`card card-hover border-l-4 ${colorClass}`} role="region" aria-label={`${label}: ${value} ${unit}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-widest leading-tight">
            {label} <EstLabel />
          </p>
          <p className="text-4xl font-bold mt-2 text-gray-900 leading-none tabular-nums">{value}</p>
          <p className="text-xs text-gray-400 mt-1.5">{unit}</p>
        </div>
        <div className="text-gray-300 mt-1 flex-shrink-0" aria-hidden="true">
          {icon}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Input form
// ---------------------------------------------------------------------------
interface FormState {
  machine_type: string
  rotational_speed_rpm: number
  torque_nm: number
  operating_hours: number
  efficiency: number
  emission_factor_kg_co2e_per_kwh: number
}

const DEFAULT_FORM: FormState = {
  machine_type: 'M',
  rotational_speed_rpm: 1500,
  torque_nm: 45,
  operating_hours: 8,
  efficiency: 0.88,
  emission_factor_kg_co2e_per_kwh: 0.4,
}

interface InputRowProps {
  label: string
  id: string
  value: number | string
  type?: string
  step?: string
  min?: number
  max?: number
  onChange: (v: string) => void
  hint?: string
  isSelect?: boolean
  options?: { value: string; label: string }[]
}

function InputRow({
  label, id, value, type = 'number', step, min, max, onChange, hint, isSelect, options,
}: InputRowProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-gray-600 uppercase tracking-widest">
        {label}
      </label>
      {isSelect && options ? (
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          step={step}
          min={min}
          max={max}
          onChange={(e) => onChange(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
        />
      )}
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Results panel
// ---------------------------------------------------------------------------
function ResultsPanel({ estimate }: { estimate: SustainabilityEstimate }) {
  const [showFormulas, setShowFormulas] = useState(false)

  return (
    <div className="space-y-4">
      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SustainKpi
          label="Est. Power"
          value={fmt(estimate.estimated_electrical_power_kw, 3)}
          unit="kW (electrical)"
          icon={<Zap size={24} />}
          colorClass="border-blue-400"
        />
        <SustainKpi
          label="Est. Energy"
          value={fmt(estimate.estimated_energy_kwh, 2)}
          unit="kWh"
          icon={<Flame size={24} />}
          colorClass="border-orange-400"
        />
        <SustainKpi
          label="Est. CO₂e"
          value={fmt(estimate.estimated_co2e_kg, 2)}
          unit="kg CO₂e"
          icon={<Wind size={24} />}
          colorClass="border-teal-400"
        />
        <SustainKpi
          label="Operating Hours"
          value={fmt(estimate.operating_hours, 1)}
          unit="hours"
          icon={<Clock size={24} />}
          colorClass="border-gray-300"
        />
      </div>

      {/* Energy estimate detail */}
      <div className="card">
        <h3 className="section-title mb-3">Energy Estimate Detail</h3>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="py-2.5 text-gray-500">Rotational Speed</td>
              <td className="py-2.5 font-mono text-right text-gray-900">
                {fmt(estimate.rotational_speed_rpm, 1)} RPM
              </td>
            </tr>
            <tr>
              <td className="py-2.5 text-gray-500">Torque</td>
              <td className="py-2.5 font-mono text-right text-gray-900">
                {fmt(estimate.torque_nm, 2)} Nm
              </td>
            </tr>
            <tr>
              <td className="py-2.5 text-gray-500 font-semibold">
                Est. Mechanical Power <EstLabel />
              </td>
              <td className="py-2.5 font-mono text-right text-blue-700 font-semibold">
                {fmt(estimate.estimated_mechanical_power_kw, 4)} kW
              </td>
            </tr>
            <tr>
              <td className="py-2.5 text-gray-500">Assumed Efficiency (η)</td>
              <td className="py-2.5 font-mono text-right text-gray-900">
                {(estimate.assumptions.efficiency * 100).toFixed(1)} %
              </td>
            </tr>
            <tr>
              <td className="py-2.5 text-gray-500 font-semibold">
                Est. Electrical Power <EstLabel />
              </td>
              <td className="py-2.5 font-mono text-right text-blue-700 font-semibold">
                {fmt(estimate.estimated_electrical_power_kw, 4)} kW
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Carbon estimate detail */}
      <div className="card">
        <h3 className="section-title mb-3">Carbon Estimate Detail</h3>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="py-2 text-gray-500 font-semibold">
                Est. Energy <EstLabel />
              </td>
              <td className="py-2 font-mono text-right text-orange-700 font-semibold">
                {fmt(estimate.estimated_energy_kwh, 4)} kWh
              </td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Emission Factor</td>
              <td className="py-2 font-mono text-right text-gray-900">
                {estimate.assumptions.emission_factor_kg_co2e_per_kwh} kg CO₂e / kWh
              </td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500 font-semibold">
                Est. CO₂e <EstLabel />
              </td>
              <td className="py-2 font-mono text-right text-teal-700 font-semibold">
                {fmt(estimate.estimated_co2e_kg, 4)} kg CO₂e
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Assumptions disclosure — REQUIRED */}
      <div className="card border border-amber-200 bg-amber-50">
        <div className="flex items-start gap-2">
          <Info size={16} className="text-amber-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <p className="text-xs font-bold text-amber-800 mb-1">Estimation Assumptions</p>
            <p className="text-xs text-amber-800">
              {estimate.assumptions.disclaimer}
            </p>
          </div>
        </div>
      </div>

      {/* Collapsible formulas */}
      <div className="card">
        <button
          onClick={() => setShowFormulas((s) => !s)}
          className="flex items-center gap-2 text-xs font-semibold text-gray-600 hover:text-gray-900 w-full text-left"
          aria-expanded={showFormulas}
        >
          {showFormulas ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          Formulas Used
        </button>
        {showFormulas && (
          <div className="mt-3 space-y-1.5 text-xs font-mono text-gray-700 bg-gray-50 rounded p-3">
            <p>{estimate.assumptions.formula_mechanical_power}</p>
            <p>{estimate.assumptions.formula_electrical_power}</p>
            <p>{estimate.assumptions.formula_energy}</p>
            <p>{estimate.assumptions.formula_co2e}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Insights panel
// ---------------------------------------------------------------------------
function InsightsPanel() {
  const insightsQuery = useQuery({
    queryKey: ['sustainability-insights'],
    queryFn: () => sustainabilityApi.insights(),
    staleTime: Infinity,
  })

  if (insightsQuery.isLoading) {
    return <div className="text-xs text-gray-400">Loading insights…</div>
  }

  if (!insightsQuery.data) return null

  return (
    <div className="card">
      <h3 className="text-sm font-bold text-gray-700 mb-3">Sustainability Insights</h3>
      <ul className="space-y-2">
        {insightsQuery.data.insights.map((insight, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
            <span className="text-teal-500 font-bold flex-shrink-0">→</span>
            {insight}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-gray-400 italic">{insightsQuery.data.disclaimer}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Machine selector
// ---------------------------------------------------------------------------
interface MachineSelectorProps {
  machines: Machine[]
  selectedId: number | null
  onSelect: (id: number | null, machine: Machine | null) => void
}

function MachineSelector({ machines, selectedId, onSelect }: MachineSelectorProps) {
  return (
    <div className="card">
      <label
        htmlFor="machine-select"
        className="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-1.5"
      >
        Associate with Machine (optional)
      </label>
      <select
        id="machine-select"
        value={selectedId ?? ''}
        onChange={(e) => {
          const id = e.target.value === '' ? null : Number(e.target.value)
          const machine = machines.find((m) => m.id === id) ?? null
          onSelect(id, machine)
        }}
        className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">— No machine selected —</option>
        {machines.map((m) => (
          <option key={m.id} value={m.id}>
            {m.machine_identifier} {m.type ? `(${m.type})` : ''}
          </option>
        ))}
      </select>
      {selectedId !== null && (
        <p className="text-xs text-gray-400 mt-1">
          Machine type pre-filled from registry.
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function SustainabilityPage() {
  const [form, setForm] = useState<FormState>({ ...DEFAULT_FORM })
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null)
  const [estimate, setEstimate] = useState<SustainabilityEstimate | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const machinesQuery = useQuery({
    queryKey: ['machines'],
    queryFn: () => machinesApi.list(0, 200),
    staleTime: 60_000,
  })

  const estimateMutation = useMutation({
    mutationFn: (req: SustainabilityEstimateRequest) => sustainabilityApi.estimate(req),
    onSuccess: (data) => {
      setEstimate(data)
      setFormError(null)
    },
    onError: () => {
      setFormError('Estimation failed. Check that all inputs are valid positive numbers.')
    },
  })

  function updateForm(key: keyof FormState, raw: string) {
    setForm((prev) => ({
      ...prev,
      [key]: key === 'machine_type' ? raw : parseFloat(raw) || prev[key],
    }))
  }

  function handleMachineSelect(id: number | null, machine: Machine | null) {
    setSelectedMachineId(id)
    if (machine?.type) {
      const t = machine.type.toUpperCase()
      if (['L', 'M', 'H'].includes(t)) {
        setForm((prev) => ({ ...prev, machine_type: t }))
      }
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    const req: SustainabilityEstimateRequest = {
      machine_type: form.machine_type || null,
      rotational_speed_rpm: form.rotational_speed_rpm,
      torque_nm: form.torque_nm,
      operating_hours: form.operating_hours,
      efficiency: form.efficiency,
      emission_factor_kg_co2e_per_kwh: form.emission_factor_kg_co2e_per_kwh,
    }
    estimateMutation.mutate(req)
  }

  const machines = machinesQuery.data ?? []

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <PageHeader
        title="Sustainability & Energy Intelligence"
        subtitle="Engineering estimates of power consumption and carbon footprint from machine operating parameters."
        badge={
          <span className="simulated-label">ESTIMATED — NOT MEASURED</span>
        }
      />

      {/* SDG banner */}
      <div className="card border border-blue-200 bg-blue-50">
        <div className="flex items-start gap-2">
          <Info size={15} className="text-blue-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs text-blue-800">
            <strong>SDG 9 — Industry, Innovation and Infrastructure · SDG 13 — Climate Action.</strong>{' '}
            This module provides engineering-based energy proxies derived from the AI4I 2020 synthetic dataset.
            All values are theoretical estimates and must not be used for regulatory compliance, carbon accounting,
            or financial reporting.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* ── Left: Input panel ──────────────────────────────────────────── */}
        <div className="lg:col-span-1 space-y-4">
          {/* Machine selector */}
          <MachineSelector
            machines={machines}
            selectedId={selectedMachineId}
            onSelect={handleMachineSelect}
          />

          {/* Parameter form */}
          <form onSubmit={handleSubmit} className="card space-y-4" noValidate>
            <h3 className="text-sm font-bold text-gray-700">Operating Parameters</h3>

            <InputRow
              label="Machine Type"
              id="machine_type"
              value={form.machine_type}
              isSelect
              options={[
                { value: 'L', label: 'L — Low quality' },
                { value: 'M', label: 'M — Medium quality' },
                { value: 'H', label: 'H — High quality' },
              ]}
              onChange={(v) => updateForm('machine_type', v)}
            />

            <InputRow
              label="Rotational Speed (RPM)"
              id="rotational_speed_rpm"
              value={form.rotational_speed_rpm}
              step="10"
              min={1}
              max={10000}
              onChange={(v) => updateForm('rotational_speed_rpm', v)}
              hint="Typical AI4I range: 1100–2900 RPM"
            />

            <InputRow
              label="Torque (Nm)"
              id="torque_nm"
              value={form.torque_nm}
              step="0.1"
              min={0.1}
              max={1000}
              onChange={(v) => updateForm('torque_nm', v)}
              hint="Typical AI4I range: 3–77 Nm"
            />

            <InputRow
              label="Operating Hours"
              id="operating_hours"
              value={form.operating_hours}
              step="0.5"
              min={0.1}
              max={8760}
              onChange={(v) => updateForm('operating_hours', v)}
              hint="Hours of operation in period"
            />

            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs text-gray-400 uppercase font-semibold tracking-wide mb-3">
                Configuration
              </p>

              <InputRow
                label="Drivetrain Efficiency (η)"
                id="efficiency"
                value={form.efficiency}
                step="0.01"
                min={0.01}
                max={1}
                onChange={(v) => updateForm('efficiency', v)}
                hint="Default 0.88 (illustrative)"
              />

              <div className="mt-3">
                <InputRow
                  label="Emission Factor (kg CO₂e/kWh)"
                  id="emission_factor"
                  value={form.emission_factor_kg_co2e_per_kwh}
                  step="0.01"
                  min={0}
                  max={5}
                  onChange={(v) => updateForm('emission_factor_kg_co2e_per_kwh', v)}
                  hint="Default 0.4 — generic illustrative value"
                />
              </div>
            </div>

            {formError && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5" role="alert">
                {formError}
              </p>
            )}

            <button
              type="submit"
              disabled={estimateMutation.isPending}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-4 rounded transition-colors disabled:opacity-50"
            >
              {estimateMutation.isPending ? 'Calculating…' : 'Calculate Estimates'}
            </button>
          </form>
        </div>

        {/* ── Right: Results ──────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">
          {estimateMutation.isPending && (
            <LoadingSpinner message="Computing estimates…" size="md" />
          )}

          {estimateMutation.isError && !estimateMutation.isPending && (
            <ErrorMessage
              title="Estimation error"
              message="Could not compute estimate. Ensure the backend is running and inputs are valid."
              onRetry={() => {
                setFormError(null)
                estimateMutation.reset()
              }}
            />
          )}

          {estimate && !estimateMutation.isPending && (
            <ResultsPanel estimate={estimate} />
          )}

          {!estimate && !estimateMutation.isPending && !estimateMutation.isError && (
            <div className="card border-dashed border-2 border-gray-200 flex items-center justify-center min-h-[160px]">
              <p className="text-sm text-gray-400">
                Set parameters and click <strong>Calculate Estimates</strong> to see results.
              </p>
            </div>
          )}

          {/* Insights */}
          <InsightsPanel />
        </div>
      </div>

      {/* Mandatory disclosure footer */}
      <div className="card border border-amber-200 bg-amber-50">
        <p className="text-xs text-amber-800">
          <strong>Important Disclosure:</strong> These values are engineering estimates based on
          available synthetic machine inputs (rotational speed and torque from the AI4I 2020
          dataset). They are <em>not</em> measured industrial energy data. The mechanical power
          formula (P&nbsp;=&nbsp;τ&nbsp;×&nbsp;ω) provides a theoretical shaft-power proxy only.
          Actual electrical consumption depends on additional losses not captured here.
          Do not use these estimates for energy audits, carbon accounting, or regulatory submissions.
          Real industrial energy intelligence requires calibrated electrical energy meters and
          site-specific emission factors.
        </p>
      </div>
    </div>
  )
}

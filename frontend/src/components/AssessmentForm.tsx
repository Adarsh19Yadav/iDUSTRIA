/**
 * frontend/src/components/AssessmentForm.tsx
 * Form for entering the six sensor readings required for an assessment.
 * Clearly labeled as synthetic/demo data entry.
 */
import { useState } from 'react'
import { X, Cpu, Info } from 'lucide-react'
import type { AssessmentRequest } from '../types'

interface Props {
  onSubmit: (req: AssessmentRequest) => void
  onCancel: () => void
  isSubmitting: boolean
  error: string | null
}

interface FormState {
  air_temperature_k: string
  process_temperature_k: string
  rotational_speed_rpm: string
  torque_nm: string
  tool_wear_min: string
  type: string
}

const DEFAULTS: FormState = {
  air_temperature_k: '300.0',
  process_temperature_k: '310.0',
  rotational_speed_rpm: '1500',
  torque_nm: '40.0',
  tool_wear_min: '100',
  type: 'M',
}

const FIELDS: {
  key: keyof FormState
  label: string
  unit: string
  min: number
  max: number
  step: number
  hint: string
}[] = [
  { key: 'air_temperature_k', label: 'Air Temperature', unit: 'K', min: 250, max: 350, step: 0.1, hint: 'Typical: 295–305 K' },
  { key: 'process_temperature_k', label: 'Process Temperature', unit: 'K', min: 250, max: 400, step: 0.1, hint: 'Typical: 305–315 K' },
  { key: 'rotational_speed_rpm', label: 'Rotational Speed', unit: 'rpm', min: 0, max: 5000, step: 1, hint: 'Typical: 1100–2900 rpm' },
  { key: 'torque_nm', label: 'Torque', unit: 'Nm', min: 0, max: 200, step: 0.1, hint: 'Typical: 3–77 Nm' },
  { key: 'tool_wear_min', label: 'Tool Wear', unit: 'min', min: 0, max: 300, step: 1, hint: '0–254 min cumulative' },
]

export default function AssessmentForm({ onSubmit, onCancel, isSubmitting, error }: Props) {
  const [form, setForm] = useState<FormState>(DEFAULTS)

  function handleChange(key: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      air_temperature_k: parseFloat(form.air_temperature_k),
      process_temperature_k: parseFloat(form.process_temperature_k),
      rotational_speed_rpm: parseFloat(form.rotational_speed_rpm),
      torque_nm: parseFloat(form.torque_nm),
      tool_wear_min: parseFloat(form.tool_wear_min),
      type: form.type,
    })
  }

  return (
    <div className="card border-l-4 border-blue-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title flex items-center gap-2">
          <Cpu size={17} aria-hidden="true" className="text-blue-600" />
          Assess Machine — Enter Sensor Readings
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded"
          aria-label="Cancel assessment"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="mb-4 p-3.5 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5">
        <Info size={15} className="text-amber-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-sm text-amber-800">
          <strong>SIMULATED / SYNTHETIC DEMO DATA:</strong> These sensor values are entered manually
          for demonstration purposes using the UCI AI4I 2020 synthetic dataset.
          Default values reflect typical synthetic observations.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FIELDS.map(({ key, label, unit, min, max, step, hint }) => (
            <div key={key}>
              <label
                htmlFor={`field-${key}`}
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                {label} <span className="font-normal text-gray-400">[{unit}]</span>
              </label>
              <input
                id={`field-${key}`}
                type="number"
                value={form[key]}
                onChange={(e) => handleChange(key, e.target.value)}
                min={min}
                max={max}
                step={step}
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 tabular-nums transition-shadow"
                aria-describedby={`hint-${key}`}
              />
              <p id={`hint-${key}`} className="text-xs text-gray-400 mt-1">{hint}</p>
            </div>
          ))}

          {/* Type field */}
          <div>
            <label htmlFor="field-type" className="block text-sm font-semibold text-gray-700 mb-1">
              Product Type <span className="font-normal text-gray-400">[L/M/H]</span>
            </label>
            <select
              id="field-type"
              value={form.type}
              onChange={(e) => handleChange('type', e.target.value)}
              required
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white transition-shadow"
              aria-describedby="hint-type"
            >
              <option value="L">L — Low quality</option>
              <option value="M">M — Medium quality</option>
              <option value="H">H — High quality</option>
            </select>
            <p id="hint-type" className="text-xs text-gray-400 mt-1">Product quality variant</p>
          </div>
        </div>

        {error && (
          <div
            className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2.5 pt-1">
          <button
            type="button"
            onClick={onCancel}
            className="btn-secondary btn-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
            aria-disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Running Assessment…
              </>
            ) : (
              'Run Assessment'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

/**
 * frontend/src/pages/SimulationPage.tsx
 * Phase 12 — Simulated Real-Time Monitoring Dashboard
 *
 * DISCLOSURE: This feature simulates sequential machine monitoring using
 * the AI4I 2020 synthetic historical dataset. It is NOT a live industrial
 * sensor connection. All sensor readings are synthetic.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import {
  Play, Pause, SkipForward, RotateCcw, Radio,
  AlertTriangle, AlertOctagon, ShieldCheck, Info,
} from 'lucide-react'

import { simulationApi } from '../api/simulation'
import type { SimulationEvent, SimulationAlert, SimulationStatus } from '../types/simulation'
import PageHeader from '../components/PageHeader'
import RiskBadge from '../components/RiskBadge'
import { formatProbability, formatScore } from '../utils/risk'

// ── Speed → polling interval (ms) ────────────────────────────────────────────
const SPEED_INTERVALS: Record<string, number> = {
  slow:   2000,
  normal: 800,
  fast:   200,
}

// ── Sensor display config ─────────────────────────────────────────────────────
const SENSOR_FIELDS: { key: keyof SimulationEvent['sensor_values']; label: string; unit: string }[] = [
  { key: 'Air temperature [K]',     label: 'Air Temperature',     unit: 'K'   },
  { key: 'Process temperature [K]', label: 'Process Temperature', unit: 'K'   },
  { key: 'Rotational speed [rpm]',  label: 'Rotational Speed',    unit: 'rpm' },
  { key: 'Torque [Nm]',             label: 'Torque',              unit: 'Nm'  },
  { key: 'Tool wear [min]',         label: 'Tool Wear',           unit: 'min' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function AlertIcon({ type }: { type: string }) {
  if (type === 'RISK_CRITICAL') return <AlertOctagon size={13} className="text-red-600 shrink-0" />
  if (type === 'RISK_WARNING')  return <AlertTriangle size={13} className="text-yellow-600 shrink-0" />
  return <AlertTriangle size={13} className="text-amber-500 shrink-0" />
}

function alertRowClass(type: string): string {
  if (type === 'RISK_CRITICAL') return 'border-l-2 border-red-500 bg-red-50'
  if (type === 'RISK_WARNING')  return 'border-l-2 border-yellow-400 bg-yellow-50'
  return 'border-l-2 border-amber-400 bg-amber-50'
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SensorCard({ event }: { event: SimulationEvent }) {
  return (
    <div className="card space-y-2">
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Current Sensor Values</h3>
      <div className="space-y-1">
        {SENSOR_FIELDS.map(({ key, label, unit }) => (
          <div key={key} className="flex items-center justify-between text-sm">
            <span className="text-gray-600">{label}</span>
            <span className="tabular-nums font-semibold text-gray-900">
              {typeof event.sensor_values[key] === 'number'
                ? (event.sensor_values[key] as number).toFixed(2)
                : String(event.sensor_values[key])}
              <span className="ml-1 text-xs text-gray-400 font-normal">{unit}</span>
            </span>
          </div>
        ))}
        <div className="flex items-center justify-between text-sm pt-1 border-t border-gray-100">
          <span className="text-gray-600">Type</span>
          <span className="font-semibold text-gray-900">{event.sensor_values['Type']}</span>
        </div>
      </div>
    </div>
  )
}

function AssessmentCard({ event }: { event: SimulationEvent }) {
  return (
    <div className="card space-y-2">
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wide">AI Assessment</h3>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Risk Level</span>
          <RiskBadge level={event.risk_level} />
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Failure Probability</span>
          <span className={`tabular-nums font-bold ${event.predicted_failure ? 'text-red-700' : 'text-gray-900'}`}>
            {formatProbability(event.failure_probability)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Risk Score</span>
          <span className="tabular-nums font-semibold text-gray-900">{formatScore(event.risk_score)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Anomaly Score</span>
          <span className={`tabular-nums font-semibold ${event.is_anomaly ? 'text-amber-700' : 'text-gray-900'}`}>
            {formatScore(event.anomaly_score)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Anomaly Detected</span>
          <span className={event.is_anomaly ? 'text-amber-700 font-bold' : 'text-green-700 font-semibold'}>
            {event.is_anomaly ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="pt-1 border-t border-gray-100">
          <p className="text-xs text-gray-400">Model: {event.model_version} · Threshold: {event.failure_threshold}</p>
        </div>
      </div>
    </div>
  )
}

function AlertPanel({ alerts }: { alerts: SimulationAlert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="card">
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Alert Panel</h3>
        <p className="text-sm text-gray-400 text-center py-2">No alerts yet.</p>
      </div>
    )
  }
  // Show most recent first, up to 8
  const shown = [...alerts].reverse().slice(0, 8)
  return (
    <div className="card space-y-2">
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
        Alert Panel <span className="ml-1 text-gray-400">({alerts.length} total)</span>
      </h3>
      <div className="space-y-1.5 max-h-56 overflow-y-auto">
        {shown.map((alert, i) => (
          <div
            key={`${alert.step}-${i}`}
            className={`flex items-start gap-2.5 px-3 py-2 rounded-lg text-sm ${alertRowClass(alert.alert_type)}`}
          >
            <AlertIcon type={alert.alert_type} />
            <div>
              <span className="font-semibold text-gray-800">Step {alert.step}: </span>
              <span className="text-gray-700">{alert.message}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function HistoryTable({ history }: { history: SimulationEvent[] }) {
  const shown = [...history].reverse().slice(0, 20)
  return (
    <div className="card overflow-hidden p-0">
      <div className="px-5 py-3 bg-gray-800 text-white flex items-center gap-2">
        <h3 className="text-sm font-bold uppercase tracking-wide">Recent Event History</h3>
        <span className="ml-auto text-xs text-gray-300">(last {shown.length} steps)</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full" aria-label="Simulation event history">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="tbl-header text-left px-4">Step</th>
              <th className="tbl-header text-left">Risk</th>
              <th className="tbl-header text-right pr-3">P(Failure)</th>
              <th className="tbl-header text-right pr-3">Risk Score</th>
              <th className="tbl-header text-left">Anomaly</th>
              <th className="tbl-header text-right pr-3">Torque</th>
              <th className="tbl-header text-right pr-3">Wear</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((evt) => (
              <tr
                key={evt.simulation_step}
                className={`border-b border-gray-100 ${
                  evt.risk_level === 'CRITICAL' ? 'bg-red-50' :
                  evt.risk_level === 'WARNING'  ? 'bg-yellow-50' : ''
                }`}
              >
                <td className="tbl-cell px-4 tabular-nums font-medium text-gray-700">{evt.simulation_step}</td>
                <td className="tbl-cell"><RiskBadge level={evt.risk_level} /></td>
                <td className="tbl-cell text-right tabular-nums pr-3">{formatProbability(evt.failure_probability)}</td>
                <td className="tbl-cell text-right tabular-nums pr-3">{formatScore(evt.risk_score)}</td>
                <td className={`tbl-cell ${evt.is_anomaly ? 'text-amber-700 font-semibold' : 'text-gray-400'}`}>
                  {evt.is_anomaly ? 'Yes' : 'No'}
                </td>
                <td className="tbl-cell text-right tabular-nums pr-3 text-gray-600">
                  {evt.sensor_values['Torque [Nm]'].toFixed(1)} Nm
                </td>
                <td className="tbl-cell text-right tabular-nums pr-3 text-gray-600">
                  {evt.sensor_values['Tool wear [min]'].toFixed(0)} min
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SimulationPage() {
  const [simState, setSimState] = useState<'idle' | 'running' | 'paused' | 'finished'>('idle')
  const [speed, setSpeed] = useState<'slow' | 'normal' | 'fast'>('normal')
  const [currentStep, setCurrentStep] = useState(0)
  const [totalSteps, setTotalSteps] = useState(0)
  const [currentEvent, setCurrentEvent] = useState<SimulationEvent | null>(null)
  const [alerts, setAlerts] = useState<SimulationAlert[]>([])
  const [history, setHistory] = useState<SimulationEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [datasetError, setDatasetError] = useState<string | null>(null)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isRunningRef = useRef(false)

  // ── Polling loop ───────────────────────────────────────────────────────────

  const doStep = useCallback(async () => {
    if (!isRunningRef.current) return
    try {
      const result = await simulationApi.step()
      setCurrentEvent(result.event)
      setCurrentStep(result.current_step)
      setTotalSteps(result.total_steps)
      setSimState(result.simulation_state as 'idle' | 'running' | 'paused' | 'finished')
      setAlerts((prev) => {
        const combined = [...prev, ...result.new_alerts]
        return combined.slice(-50)
      })
      setHistory((prev) => {
        const updated = [...prev, result.event]
        return updated.slice(-100)
      })
      if (result.simulation_state === 'finished') {
        isRunningRef.current = false
        stopInterval()
      }
      setError(null)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (msg?.includes('end of the dataset')) {
        setSimState('finished')
        isRunningRef.current = false
        stopInterval()
      } else {
        setError(msg ?? 'Step failed.')
        isRunningRef.current = false
        stopInterval()
      }
    }
  }, [speed])

  function stopInterval() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  function startInterval() {
    stopInterval()
    const ms = SPEED_INTERVALS[speed] ?? 800
    intervalRef.current = setInterval(doStep, ms)
  }

  useEffect(() => {
    return () => stopInterval()
  }, [])

  // ── Controls ───────────────────────────────────────────────────────────────

  async function handleStart() {
    setError(null)
    setDatasetError(null)
    try {
      const res = await simulationApi.start(speed)
      setTotalSteps(res.total_steps)
      setSimState('running')
      isRunningRef.current = true
      startInterval()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setDatasetError(msg ?? 'Failed to start simulation.')
    }
  }

  function handlePause() {
    isRunningRef.current = false
    stopInterval()
    simulationApi.pause().then(() => setSimState('paused'))
  }

  function handleResume() {
    isRunningRef.current = true
    setSimState('running')
    startInterval()
  }

  async function handleStep() {
    if (simState === 'idle') {
      // Need to start first
      await handleStart()
      isRunningRef.current = false
      stopInterval()
    }
    await doStep()
  }

  async function handleReset() {
    isRunningRef.current = false
    stopInterval()
    await simulationApi.reset()
    setSimState('idle')
    setCurrentStep(0)
    setCurrentEvent(null)
    setAlerts([])
    setHistory([])
    setError(null)
    setDatasetError(null)
  }

  // Restart interval when speed changes while running
  useEffect(() => {
    if (simState === 'running' && isRunningRef.current) {
      startInterval()
    }
  }, [speed])

  // ── Progress bar ───────────────────────────────────────────────────────────
  const progressPct = totalSteps > 0 ? Math.min(100, (currentStep / totalSteps) * 100) : 0

  // ── Status indicator ───────────────────────────────────────────────────────
  const statusColors: Record<string, string> = {
    idle:     'text-gray-400',
    running:  'text-green-500',
    paused:   'text-yellow-500',
    finished: 'text-blue-500',
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <PageHeader
        title="Live Simulation"
        subtitle="Simulated sequential machine monitoring — AI4I 2020 synthetic dataset."
        badge={<span className="simulated-label">SIMULATION · SYNTHETIC DATA</span>}
      />

      {/* ── Top status bar ──────────────────────────────────────────────── */}
      <div className="card flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Radio size={15} className={statusColors[simState]} aria-hidden="true" />
          <span className="text-sm font-bold uppercase text-gray-700">
            {simState === 'running' ? 'SIMULATION RUNNING' :
             simState === 'paused'  ? 'SIMULATION PAUSED'  :
             simState === 'finished' ? 'SIMULATION COMPLETE' :
             'SIMULATION IDLE'}
          </span>
        </div>
        <span className="text-xs text-gray-400 italic">Synthetic AI4I 2020 Data</span>

        {/* Speed selector */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-sm text-gray-500 font-medium">Speed:</span>
          {(['slow', 'normal', 'fast'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                speed === s
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {simState === 'idle' || simState === 'finished' ? (
            <button
              onClick={handleStart}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-green-600 text-white text-sm font-semibold rounded-lg hover:bg-green-700 transition-colors shadow-sm"
              aria-label="Start simulation"
            >
              <Play size={14} aria-hidden="true" />
              {simState === 'finished' ? 'Restart' : 'Start'}
            </button>
          ) : simState === 'running' ? (
            <button
              onClick={handlePause}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-yellow-500 text-white text-sm font-semibold rounded-lg hover:bg-yellow-600 transition-colors shadow-sm"
              aria-label="Pause simulation"
            >
              <Pause size={14} aria-hidden="true" />
              Pause
            </button>
          ) : (
            <button
              onClick={handleResume}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-green-600 text-white text-sm font-semibold rounded-lg hover:bg-green-700 transition-colors shadow-sm"
              aria-label="Resume simulation"
            >
              <Play size={14} aria-hidden="true" />
              Resume
            </button>
          )}

          <button
            onClick={handleStep}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            aria-label="Advance one step"
          >
            <SkipForward size={14} aria-hidden="true" />
            Step
          </button>

          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gray-500 text-white text-sm font-semibold rounded-lg hover:bg-gray-600 transition-colors shadow-sm"
            aria-label="Reset simulation"
          >
            <RotateCcw size={14} aria-hidden="true" />
            Reset
          </button>
        </div>
      </div>

      {/* ── Dataset error ────────────────────────────────────────────────── */}
      {datasetError && (
        <div className="card border border-red-200 bg-red-50 flex gap-3">
          <AlertOctagon size={17} className="text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <p className="text-sm font-bold text-red-800">Simulation Dataset Unavailable</p>
            <p className="text-sm text-red-700 mt-0.5">{datasetError}</p>
          </div>
        </div>
      )}

      {/* ── General error ────────────────────────────────────────────────── */}
      {error && (
        <div className="card border border-amber-200 bg-amber-50">
          <p className="text-sm text-amber-800"><strong>Error:</strong> {error}</p>
        </div>
      )}

      {/* ── Progress bar ─────────────────────────────────────────────────── */}
      {totalSteps > 0 && (
        <div className="card py-3 space-y-1.5">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Step <strong>{currentStep}</strong> / {totalSteps}
            </span>
            <span>{progressPct.toFixed(1)}% complete</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2" role="progressbar"
               aria-valuenow={currentStep} aria-valuemin={0} aria-valuemax={totalSteps}>
            <div
              className="h-2 rounded-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Main data grid ───────────────────────────────────────────────── */}
      {currentEvent ? (
        <>
          {/* Machine info header */}
          <div className="card py-3.5 flex flex-wrap gap-4 items-center">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-widest font-bold">Machine</p>
              <p className="text-base font-bold text-gray-900 mt-0.5">{currentEvent.machine_identifier}</p>
              <p className="text-xs text-gray-400 mt-0.5">Type: {currentEvent.sensor_values['Type']} · {currentEvent.simulated_time_label}</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              {currentEvent.risk_level === 'CRITICAL' && (
                <AlertOctagon size={18} className="text-red-600" aria-hidden="true" />
              )}
              {currentEvent.risk_level === 'WARNING' && (
                <AlertTriangle size={18} className="text-yellow-600" aria-hidden="true" />
              )}
              {currentEvent.risk_level === 'NORMAL' && (
                <ShieldCheck size={18} className="text-green-600" aria-hidden="true" />
              )}
              <RiskBadge level={currentEvent.risk_level} />
            </div>
          </div>

          {/* Data cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <SensorCard event={currentEvent} />
            <AssessmentCard event={currentEvent} />
          </div>

          {/* Alerts + history */}
          <AlertPanel alerts={alerts} />
          <HistoryTable history={history} />
        </>
      ) : (
        simState === 'idle' && !datasetError && (
          <div className="card border border-dashed border-gray-300 text-center py-12">
            <Radio size={36} className="text-gray-300 mx-auto mb-3" aria-hidden="true" />
            <p className="text-sm text-gray-500 font-semibold">Simulation not started</p>
            <p className="text-sm text-gray-400 mt-1">
              Press <strong>Start</strong> to begin stepping through the AI4I 2020 synthetic dataset.
            </p>
          </div>
        )
      )}

      {/* ── Disclaimer footer ────────────────────────────────────────────── */}
      <div className="card border border-blue-200 bg-blue-50 flex gap-3">
        <Info size={16} className="text-blue-600 shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-sm text-blue-800 leading-relaxed">
          <strong>SIMULATION DISCLOSURE:</strong> This feature simulates sequential machine monitoring
          using synthetic historical data from the UCI AI4I 2020 dataset (Matzka, 2021, CC BY 4.0).
          It is <em>not</em> a live industrial sensor connection. Sensor readings, failure events,
          and anomaly events are synthetic. All AI assessments are model-estimated and require
          qualified human review before any action is taken.
        </p>
      </div>
    </div>
  )
}

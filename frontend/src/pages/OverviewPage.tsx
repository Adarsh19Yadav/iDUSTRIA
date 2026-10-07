import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { apiClient } from '../api/client'
import type { HealthStatus, ReadinessStatus } from '../types/health'

async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>('/api/v1/health')
  return data
}

async function fetchReadiness(): Promise<ReadinessStatus> {
  const { data } = await apiClient.get<ReadinessStatus>('/api/v1/health/ready')
  return data
}

function StatusIcon({ ok }: { ok: boolean }) {
  return ok
    ? <CheckCircle size={16} className="text-green-600" />
    : <XCircle size={16} className="text-red-500" />
}

function ServiceRow({ name, status }: { name: string; status: string }) {
  const ok = status === 'ok'
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-700">{name}</span>
      <div className="flex items-center gap-1.5">
        <StatusIcon ok={ok} />
        <span className={`text-xs font-semibold ${ok ? 'text-green-700' : 'text-red-600'}`}>
          {status}
        </span>
      </div>
    </div>
  )
}

export default function OverviewPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, refetchInterval: 30_000 })
  const ready = useQuery({ queryKey: ['readiness'], queryFn: fetchReadiness, refetchInterval: 30_000 })

  const isLoading = health.isLoading || ready.isLoading

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">Platform Overview</h2>
        <p className="text-sm text-gray-500 mt-1">
          INDUSTRIA-X — Agentic AI for Predictive Maintenance &amp; Sustainable Industrial Operations
        </p>
      </div>

      {/* Phase progress banner */}
      <div className="card border-l-4 border-blue-500">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-gray-800">Phase 1 — Foundation (In Progress)</p>
            <p className="text-xs text-gray-500 mt-1">
              The project scaffold, configuration, and backend health endpoints are active.
              ML models, agents, RAG, and the full dashboard will be available from Phase 2 onwards.
            </p>
          </div>
        </div>
      </div>

      {/* System health cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Liveness */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-800">Backend — Liveness</h3>
            {isLoading
              ? <Clock size={16} className="text-gray-400 animate-spin" />
              : <StatusIcon ok={health.data?.status === 'ok'} />
            }
          </div>
          {health.data ? (
            <dl className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <dt className="text-gray-500">Status</dt>
                <dd className="font-semibold text-green-700">{health.data.status}</dd>
              </div>
              <div className="flex justify-between text-xs">
                <dt className="text-gray-500">Version</dt>
                <dd className="font-mono text-gray-700">{health.data.version}</dd>
              </div>
              <div className="flex justify-between text-xs">
                <dt className="text-gray-500">Environment</dt>
                <dd className="font-mono text-gray-700">{health.data.environment}</dd>
              </div>
              <div className="flex justify-between text-xs">
                <dt className="text-gray-500">Timestamp</dt>
                <dd className="font-mono text-gray-700">
                  {new Date(health.data.timestamp).toLocaleTimeString()}
                </dd>
              </div>
            </dl>
          ) : health.isError ? (
            <p className="text-xs text-red-500">Backend unreachable — is it running?</p>
          ) : (
            <p className="text-xs text-gray-400">Checking…</p>
          )}
        </div>

        {/* Readiness */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-800">Backend — Readiness</h3>
            {isLoading
              ? <Clock size={16} className="text-gray-400 animate-spin" />
              : <StatusIcon ok={ready.data?.status === 'ready'} />
            }
          </div>
          {ready.data ? (
            <div>
              <div className="mb-2">
                <span className={`badge ${ready.data.status === 'ready' ? 'badge-ok' : 'badge-warn'}`}>
                  {ready.data.status}
                </span>
              </div>
              <ServiceRow name="Database (PostgreSQL)" status={ready.data.checks.database} />
              <ServiceRow name="Cache (Redis)" status={ready.data.checks.redis} />
              <div className="mt-2 pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-1 font-semibold">Pending services</p>
                {ready.data.pending_services.map((svc) => (
                  <div key={svc} className="flex items-center gap-1.5 py-0.5">
                    <Clock size={12} className="text-amber-500" />
                    <span className="text-xs text-gray-500">{svc}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : ready.isError ? (
            <p className="text-xs text-red-500">Backend unreachable — is it running?</p>
          ) : (
            <p className="text-xs text-gray-400">Checking…</p>
          )}
        </div>
      </div>

      {/* Implementation roadmap */}
      <div className="card">
        <h3 className="text-sm font-bold text-gray-800 mb-3">Implementation Roadmap</h3>
        <div className="space-y-2">
          {[
            { phase: 1, label: 'Project Foundation', status: 'active', detail: 'Folder structure, config, backend shell, frontend shell' },
            { phase: 2, label: 'Data Pipeline & ML Models', status: 'pending', detail: 'UCI AI4I dataset, Random Forest, XGBoost, IsolationForest, SHAP' },
            { phase: 3, label: 'RAG Knowledge Base', status: 'pending', detail: 'ChromaDB, maintenance documents, grounded retrieval' },
            { phase: 4, label: 'Agentic AI Orchestration', status: 'pending', detail: 'LangGraph, 15 tools, human-in-the-loop approval' },
            { phase: 5, label: 'Frontend Dashboard', status: 'pending', detail: '10 dashboard pages, sensor streaming, SHAP visualisation' },
            { phase: 6, label: 'Sustainability & What-If', status: 'pending', detail: 'Energy analytics, CO₂e estimation, what-if simulation' },
            { phase: 7, label: 'Testing, Docs & CI', status: 'pending', detail: 'Full test suite, MkDocs, GitHub Actions' },
          ].map(({ phase, label, status, detail }) => (
            <div key={phase} className="flex items-start gap-3 p-2 rounded-md bg-gray-50">
              <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                status === 'active' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {phase}
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-800">{label}</p>
                <p className="text-xs text-gray-500">{detail}</p>
              </div>
              <div className="ml-auto">
                <span className={`badge ${status === 'active' ? 'badge-info' : 'badge-warn'} text-xs`}>
                  {status === 'active' ? 'IN PROGRESS' : 'PENDING'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Safety notice */}
      <div className="card border border-amber-200 bg-amber-50">
        <p className="text-xs text-amber-800">
          <strong>Safety:</strong> INDUSTRIA-X is a decision-support tool. It cannot control industrial
          equipment. All maintenance recommendations require human approval. Sensor data is simulated
          from the UCI AI4I 2020 synthetic dataset.
        </p>
      </div>
    </div>
  )
}

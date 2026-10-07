/**
 * frontend/src/types/whatif.ts
 * TypeScript interfaces for Phase 11 What-If Analysis and Maintenance Priority.
 */

// ── What-If Analysis ─────────────────────────────────────────────────────────

export interface WhatIfInputs {
  'Air temperature [K]': number
  'Process temperature [K]': number
  'Rotational speed [rpm]': number
  'Torque [Nm]': number
  'Tool wear [min]': number
  'Type': string
}

export interface WhatIfRequest {
  baseline: WhatIfInputs
  scenario: WhatIfInputs
}

export interface AssessmentSnapshot {
  failure_probability: number
  anomaly_score: number
  risk_score: number
  risk_level: string
}

export interface WhatIfChange {
  failure_probability_delta: number
  anomaly_score_delta: number
  risk_score_delta: number
  risk_level_changed: boolean
}

export interface WhatIfResponse {
  baseline: AssessmentSnapshot
  scenario: AssessmentSnapshot
  change: WhatIfChange
  out_of_distribution_warning: string | null
  disclaimer: string
}

// ── Maintenance Priority ──────────────────────────────────────────────────────

export interface MachinePriorityItem {
  machine_id: number
  machine_identifier: string
  machine_type: string | null
  risk_level: string
  risk_score: number
  failure_probability: number
  anomaly_score: number
  priority_score: number
  priority_rank: number
  recommended_review: string
  disclaimer: string
}

export interface MaintenancePriorityResponse {
  machines: MachinePriorityItem[]
  total: number
  disclaimer: string
}

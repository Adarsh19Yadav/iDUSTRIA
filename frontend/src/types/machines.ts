/**
 * frontend/src/types/machines.ts
 * TypeScript interfaces mirroring backend/schemas/machine.py
 */

export interface Machine {
  id: number
  machine_identifier: string
  type: string | null
  created_at: string
  updated_at: string
}

export interface MachineCreate {
  machine_identifier: string
  type?: string | null
}

export interface AssessmentRequest {
  air_temperature_k: number
  process_temperature_k: number
  rotational_speed_rpm: number
  torque_nm: number
  tool_wear_min: number
  type: string // 'L' | 'M' | 'H'
}

export interface Assessment {
  id: number
  machine_id: number
  failure_probability: number
  anomaly_score: number
  risk_score: number
  risk_level: string // 'NORMAL' | 'WARNING' | 'CRITICAL'
  model_version: string
  created_at: string
}

export type RiskLevel = 'NORMAL' | 'WARNING' | 'CRITICAL'

export interface MachineWithLatestAssessment {
  machine: Machine
  latestAssessment: Assessment | null
}

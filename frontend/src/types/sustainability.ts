/**
 * frontend/src/types/sustainability.ts
 * TypeScript interfaces mirroring backend/api/sustainability.py schemas.
 * Phase 10 — all values are ESTIMATED.
 */

export interface SustainabilityAssumptions {
  efficiency: number
  emission_factor_kg_co2e_per_kwh: number
  formula_mechanical_power: string
  formula_electrical_power: string
  formula_energy: string
  formula_co2e: string
  disclaimer: string
}

export interface SustainabilityEstimate {
  machine_type: string | null
  rotational_speed_rpm: number
  torque_nm: number
  operating_hours: number
  estimated_mechanical_power_kw: number
  estimated_electrical_power_kw: number
  estimated_energy_kwh: number
  estimated_co2e_kg: number
  assumptions: SustainabilityAssumptions
}

export interface SustainabilityEstimateRequest {
  machine_type?: string | null
  rotational_speed_rpm: number
  torque_nm: number
  operating_hours?: number
  efficiency?: number
  emission_factor_kg_co2e_per_kwh?: number
}

export interface SustainabilityInsightsResponse {
  insights: string[]
  disclaimer: string
}

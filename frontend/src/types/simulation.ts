/**
 * frontend/src/types/simulation.ts
 * TypeScript interfaces for Phase 12 Simulation endpoints.
 */

export interface SimulationSensorValues {
  'Air temperature [K]': number
  'Process temperature [K]': number
  'Rotational speed [rpm]': number
  'Torque [Nm]': number
  'Tool wear [min]': number
  'Type': string
  'Product ID': string
}

export interface SimulationEvent {
  simulation_step: number
  simulated_time_label: string
  machine_identifier: string
  sensor_values: SimulationSensorValues
  failure_probability: number
  anomaly_score: number
  risk_score: number
  risk_level: string
  is_anomaly: boolean
  predicted_failure: number
  failure_threshold: number
  model_version: string
  real_wall_time: string
}

export interface SimulationAlert {
  step: number
  alert_type: string
  message: string
  risk_level: string
  real_wall_time: string
}

export interface SimulationStatus {
  state: 'idle' | 'running' | 'paused' | 'finished'
  speed: string
  current_step: number
  total_steps: number
  current_event: SimulationEvent | null
  recent_alerts: SimulationAlert[]
  dataset_error: string | null
}

export interface SimulationStepResult {
  event: SimulationEvent
  simulation_state: string
  current_step: number
  total_steps: number
  new_alerts: SimulationAlert[]
}

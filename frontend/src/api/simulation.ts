/**
 * frontend/src/api/simulation.ts
 * API client for Phase 12 Simulation endpoints.
 */
import { apiClient } from './client'
import type {
  SimulationStatus,
  SimulationStepResult,
} from '../types/simulation'

export const simulationApi = {
  /** POST /api/v1/simulation/start */
  start: async (speed = 'normal'): Promise<{ status: string; total_steps: number; speed: string }> => {
    const { data } = await apiClient.post('/api/v1/simulation/start', { speed })
    return data
  },

  /** POST /api/v1/simulation/pause */
  pause: async (): Promise<{ status: string }> => {
    const { data } = await apiClient.post('/api/v1/simulation/pause')
    return data
  },

  /** POST /api/v1/simulation/reset */
  reset: async (): Promise<{ status: string }> => {
    const { data } = await apiClient.post('/api/v1/simulation/reset')
    return data
  },

  /** POST /api/v1/simulation/step — advance one row */
  step: async (): Promise<SimulationStepResult> => {
    const { data } = await apiClient.post<SimulationStepResult>('/api/v1/simulation/step')
    return data
  },

  /** GET /api/v1/simulation/status */
  status: async (): Promise<SimulationStatus> => {
    const { data } = await apiClient.get<SimulationStatus>('/api/v1/simulation/status')
    return data
  },
}

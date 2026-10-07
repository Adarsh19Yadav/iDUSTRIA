/**
 * frontend/src/api/sustainability.ts
 * API service for the sustainability estimation endpoints.
 * Phase 10 — Sustainability & Energy Intelligence
 */
import { apiClient } from './client'
import type {
  SustainabilityEstimate,
  SustainabilityEstimateRequest,
  SustainabilityInsightsResponse,
} from '../types/sustainability'

export const sustainabilityApi = {
  /**
   * POST /api/v1/sustainability/estimate
   * Compute estimated power, energy, and CO₂e from machine parameters.
   * All returned values are ENGINEERING ESTIMATES.
   */
  estimate: async (
    body: SustainabilityEstimateRequest,
  ): Promise<SustainabilityEstimate> => {
    const { data } = await apiClient.post<SustainabilityEstimate>(
      '/api/v1/sustainability/estimate',
      body,
    )
    return data
  },

  /**
   * GET /api/v1/sustainability/insights
   * Return deterministic sustainability insights.
   */
  insights: async (): Promise<SustainabilityInsightsResponse> => {
    const { data } = await apiClient.get<SustainabilityInsightsResponse>(
      '/api/v1/sustainability/insights',
    )
    return data
  },
}

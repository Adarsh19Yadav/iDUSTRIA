/**
 * frontend/src/api/machines.ts
 * API service for machine and assessment endpoints.
 */
import { apiClient } from './client'
import type { Machine, MachineCreate, Assessment, AssessmentRequest } from '../types'

export const machinesApi = {
  /** GET /api/v1/machines — list all machines */
  list: async (skip = 0, limit = 100): Promise<Machine[]> => {
    const { data } = await apiClient.get<Machine[]>('/api/v1/machines', {
      params: { skip, limit },
    })
    return data
  },

  /** GET /api/v1/machines/:id — get one machine */
  get: async (id: number): Promise<Machine> => {
    const { data } = await apiClient.get<Machine>(`/api/v1/machines/${id}`)
    return data
  },

  /** POST /api/v1/machines — register a machine */
  create: async (body: MachineCreate): Promise<Machine> => {
    const { data } = await apiClient.post<Machine>('/api/v1/machines', body)
    return data
  },

  /** POST /api/v1/machines/:id/assess — run an assessment */
  assess: async (id: number, body: AssessmentRequest): Promise<Assessment> => {
    const { data } = await apiClient.post<Assessment>(
      `/api/v1/machines/${id}/assess`,
      body,
    )
    return data
  },

  /** GET /api/v1/machines/:id/assessments — list assessment history */
  listAssessments: async (
    id: number,
    skip = 0,
    limit = 50,
  ): Promise<Assessment[]> => {
    const { data } = await apiClient.get<Assessment[]>(
      `/api/v1/machines/${id}/assessments`,
      { params: { skip, limit } },
    )
    return data
  },
}

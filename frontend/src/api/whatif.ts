/**
 * frontend/src/api/whatif.ts
 * API service for Phase 11 What-If Analysis and Maintenance Priority endpoints.
 */
import { apiClient } from './client'
import type {
  WhatIfRequest,
  WhatIfResponse,
  MaintenancePriorityResponse,
} from '../types/whatif'

export const whatifApi = {
  /** POST /api/v1/whatif/analyze — run a what-if scenario comparison */
  analyze: async (body: WhatIfRequest): Promise<WhatIfResponse> => {
    const { data } = await apiClient.post<WhatIfResponse>('/api/v1/whatif/analyze', body)
    return data
  },
}

export const maintenanceApi = {
  /** GET /api/v1/maintenance/priority — ranked maintenance priority list */
  getPriority: async (): Promise<MaintenancePriorityResponse> => {
    const { data } = await apiClient.get<MaintenancePriorityResponse>('/api/v1/maintenance/priority')
    return data
  },
}

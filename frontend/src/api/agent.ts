/**
 * frontend/src/api/agent.ts
 * API service for the agent and RAG endpoints.
 */
import { apiClient } from './client'
import type {
  AgentQuery,
  AgentResponse,
  RAGQueryRequest,
  RAGQueryResponse,
  RAGStatus,
} from '../types'

export const agentApi = {
  /** POST /api/v1/agent/query — run the AI agent */
  query: async (body: AgentQuery): Promise<AgentResponse> => {
    const { data } = await apiClient.post<AgentResponse>('/api/v1/agent/query', body)
    return data
  },
}

export const ragApi = {
  /** POST /api/v1/rag/query — query the maintenance knowledge base */
  query: async (body: RAGQueryRequest): Promise<RAGQueryResponse> => {
    const { data } = await apiClient.post<RAGQueryResponse>('/api/v1/rag/query', body)
    return data
  },

  /** GET /api/v1/rag/status — check if knowledge base is ready */
  status: async (): Promise<RAGStatus> => {
    const { data } = await apiClient.get<RAGStatus>('/api/v1/rag/status')
    return data
  },
}

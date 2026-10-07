/**
 * frontend/src/types/agent.ts
 * TypeScript interfaces mirroring backend/agent/schemas.py
 */

export interface MachineInput {
  'Air temperature [K]': number
  'Process temperature [K]': number
  'Rotational speed [rpm]': number
  'Torque [Nm]': number
  'Tool wear [min]': number
  'Type': string
}

export interface AgentQuery {
  query: string
  machine_input?: MachineInput | null
  session_id?: string | null
  machine_id?: string | null
}

export interface ToolEvidence {
  tool: string
  result: Record<string, unknown>
}

export interface RAGSource {
  source: string
  chunk_index: number
  distance: number
  excerpt: string
}

export interface AgentResponse {
  answer: string
  tools_used: string[]
  evidence: ToolEvidence[]
  sources: RAGSource[]
  status: 'success' | 'error' | 'partial'
  error_detail: string | null
}

export interface RAGQueryRequest {
  question: string
  top_k?: number
}

export interface RAGChunk {
  content: string
  source: string
  chunk_index: number
  distance: number
}

export interface RAGQueryResponse {
  question: string
  results: RAGChunk[]
  total_results: number
}

export interface RAGStatus {
  ready: boolean
  message: string
}

/**
 * TypeScript interfaces for health check API responses.
 * These mirror the Pydantic schemas in backend/api/health.py.
 */

export interface HealthStatus {
  status: 'ok'
  timestamp: string
  app: string
  version: string
  environment: string
  python: string
  platform: string
}

export interface ReadinessStatus {
  status: 'ready' | 'degraded'
  timestamp: string
  checks: {
    database: 'ok' | 'unavailable'
    redis: 'ok' | 'unavailable'
  }
  pending_services: string[]
}

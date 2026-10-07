/**
 * frontend/src/utils/risk.ts
 * Risk level utilities — colors, labels, ordering.
 */
import type { RiskLevel } from '../types'

export type RiskColor = 'normal' | 'warning' | 'critical'

const riskMap: Record<string, RiskColor> = {
  NORMAL: 'normal',
  WARNING: 'warning',
  CRITICAL: 'critical',
}

export function getRiskColor(level: string | null | undefined): RiskColor {
  if (!level) return 'normal'
  return riskMap[level.toUpperCase()] ?? 'normal'
}

export function getRiskBadgeClasses(level: string | null | undefined): string {
  const color = getRiskColor(level)
  const base = 'badge'
  if (color === 'critical') return `${base} badge-error`
  if (color === 'warning') return `${base} badge-warn`
  return `${base} badge-ok`
}

/** Returns a human-readable label with accessible text (not just color) */
export function getRiskLabel(level: string | null | undefined): string {
  if (!level) return '—'
  const upper = level.toUpperCase() as RiskLevel
  const labels: Record<RiskLevel, string> = {
    NORMAL: 'Normal',
    WARNING: 'Warning',
    CRITICAL: 'Critical',
  }
  return labels[upper] ?? level
}

/** Sort order: CRITICAL first, then WARNING, then NORMAL */
export function getRiskOrder(level: string | null | undefined): number {
  const color = getRiskColor(level)
  if (color === 'critical') return 0
  if (color === 'warning') return 1
  return 2
}

export function formatProbability(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function formatScore(value: number | null | undefined): string {
  if (value == null) return '—'
  return value.toFixed(3)
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

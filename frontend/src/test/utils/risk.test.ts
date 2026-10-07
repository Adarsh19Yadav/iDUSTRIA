/**
 * frontend/src/test/utils/risk.test.ts
 * Tests for risk utility functions.
 */
import { describe, it, expect } from 'vitest'
import {
  getRiskColor,
  getRiskBadgeClasses,
  getRiskLabel,
  getRiskOrder,
  formatProbability,
  formatScore,
} from '../../utils/risk'

describe('getRiskColor', () => {
  it('returns normal for NORMAL', () => {
    expect(getRiskColor('NORMAL')).toBe('normal')
  })
  it('returns warning for WARNING', () => {
    expect(getRiskColor('WARNING')).toBe('warning')
  })
  it('returns critical for CRITICAL', () => {
    expect(getRiskColor('CRITICAL')).toBe('critical')
  })
  it('is case-insensitive', () => {
    expect(getRiskColor('critical')).toBe('critical')
    expect(getRiskColor('Warning')).toBe('warning')
  })
  it('returns normal for null/undefined', () => {
    expect(getRiskColor(null)).toBe('normal')
    expect(getRiskColor(undefined)).toBe('normal')
  })
  it('returns normal for unknown values', () => {
    expect(getRiskColor('UNKNOWN')).toBe('normal')
  })
})

describe('getRiskBadgeClasses', () => {
  it('includes badge-ok for NORMAL', () => {
    expect(getRiskBadgeClasses('NORMAL')).toContain('badge-ok')
  })
  it('includes badge-warn for WARNING', () => {
    expect(getRiskBadgeClasses('WARNING')).toContain('badge-warn')
  })
  it('includes badge-error for CRITICAL', () => {
    expect(getRiskBadgeClasses('CRITICAL')).toContain('badge-error')
  })
})

describe('getRiskLabel', () => {
  it('returns Normal for NORMAL', () => {
    expect(getRiskLabel('NORMAL')).toBe('Normal')
  })
  it('returns Warning for WARNING', () => {
    expect(getRiskLabel('WARNING')).toBe('Warning')
  })
  it('returns Critical for CRITICAL', () => {
    expect(getRiskLabel('CRITICAL')).toBe('Critical')
  })
  it('returns em-dash for null', () => {
    expect(getRiskLabel(null)).toBe('—')
  })
})

describe('getRiskOrder', () => {
  it('orders CRITICAL first (0)', () => {
    expect(getRiskOrder('CRITICAL')).toBe(0)
  })
  it('orders WARNING second (1)', () => {
    expect(getRiskOrder('WARNING')).toBe(1)
  })
  it('orders NORMAL last (2)', () => {
    expect(getRiskOrder('NORMAL')).toBe(2)
  })
})

describe('formatProbability', () => {
  it('formats 0.5 as 50.0%', () => {
    expect(formatProbability(0.5)).toBe('50.0%')
  })
  it('formats 0 as 0.0%', () => {
    expect(formatProbability(0)).toBe('0.0%')
  })
  it('formats 1 as 100.0%', () => {
    expect(formatProbability(1)).toBe('100.0%')
  })
  it('returns em-dash for null', () => {
    expect(formatProbability(null)).toBe('—')
  })
  it('returns em-dash for undefined', () => {
    expect(formatProbability(undefined)).toBe('—')
  })
})

describe('formatScore', () => {
  it('formats 0.12345 as 0.123', () => {
    expect(formatScore(0.12345)).toBe('0.123')
  })
  it('returns em-dash for null', () => {
    expect(formatScore(null)).toBe('—')
  })
  it('returns em-dash for undefined', () => {
    expect(formatScore(undefined)).toBe('—')
  })
})

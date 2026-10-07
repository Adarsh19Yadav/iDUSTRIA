/**
 * frontend/src/components/RiskBadge.tsx
 * Accessible risk level badge.
 */
import { getRiskBadgeClasses, getRiskLabel } from '../utils/risk'

interface Props {
  level: string | null | undefined
  showIcon?: boolean
}

const ICONS: Record<string, string> = {
  CRITICAL: '●',
  WARNING: '◆',
  NORMAL: '●',
}

export default function RiskBadge({ level, showIcon = true }: Props) {
  const label = getRiskLabel(level)
  const classes = getRiskBadgeClasses(level)
  const icon = level ? (ICONS[level.toUpperCase()] ?? '●') : null

  return (
    <span className={classes} aria-label={`Risk: ${label}`}>
      {showIcon && icon && <span aria-hidden="true" className="mr-1">{icon}</span>}
      {label}
    </span>
  )
}

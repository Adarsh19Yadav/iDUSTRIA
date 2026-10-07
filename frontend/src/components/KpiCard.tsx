/**
 * frontend/src/components/KpiCard.tsx
 * KPI card for the executive overview.
 */
interface Props {
  label: string
  value: number | string
  subtext?: string
  icon?: React.ReactNode
  variant?: 'default' | 'critical' | 'warning' | 'ok' | 'info'
}

const variantClasses: Record<string, string> = {
  default: 'border-gray-200',
  critical: 'border-l-4 border-red-500 bg-red-50',
  warning: 'border-l-4 border-yellow-500 bg-yellow-50',
  ok: 'border-l-4 border-green-500 bg-green-50',
  info: 'border-l-4 border-blue-500 bg-blue-50',
}

const valueClasses: Record<string, string> = {
  default: 'text-gray-900',
  critical: 'text-red-700',
  warning: 'text-yellow-700',
  ok: 'text-green-700',
  info: 'text-blue-700',
}

const iconClasses: Record<string, string> = {
  default: 'text-gray-300',
  critical: 'text-red-300',
  warning: 'text-yellow-300',
  ok: 'text-green-300',
  info: 'text-blue-300',
}

export default function KpiCard({ label, value, subtext, icon, variant = 'default' }: Props) {
  return (
    <div
      className={`card card-hover ${variantClasses[variant]}`}
      role="region"
      aria-label={`${label}: ${value}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-widest leading-tight">{label}</p>
          <p className={`text-4xl font-bold mt-2 leading-none tabular-nums ${valueClasses[variant]}`}>{value}</p>
          {subtext && <p className="text-xs text-gray-400 mt-1.5 leading-tight">{subtext}</p>}
        </div>
        {icon && (
          <div className={`mt-1 flex-shrink-0 ${iconClasses[variant]}`} aria-hidden="true">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}

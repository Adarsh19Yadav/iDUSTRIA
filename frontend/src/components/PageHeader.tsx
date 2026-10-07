/**
 * frontend/src/components/PageHeader.tsx
 * Reusable page header with title, subtitle, and optional actions.
 */
interface Props {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  badge?: React.ReactNode
}

export default function PageHeader({ title, subtitle, actions, badge }: Props) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h2 className="text-2xl font-bold text-gray-900 leading-tight">{title}</h2>
          {badge}
        </div>
        {subtitle && (
          <p className="text-sm text-gray-500 mt-1 leading-snug">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">{actions}</div>}
    </div>
  )
}

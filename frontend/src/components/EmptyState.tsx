/**
 * frontend/src/components/EmptyState.tsx
 * Empty state component for no-data scenarios.
 */
import { Inbox } from 'lucide-react'

interface Props {
  title?: string
  message?: string
  action?: React.ReactNode
}

export default function EmptyState({
  title = 'No data',
  message = 'Nothing to display yet.',
  action,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14">
      <Inbox size={32} className="text-gray-300" aria-hidden="true" />
      <div className="text-center max-w-sm">
        <p className="text-sm font-semibold text-gray-600">{title}</p>
        <p className="text-xs text-gray-400 mt-1">{message}</p>
      </div>
      {action}
    </div>
  )
}

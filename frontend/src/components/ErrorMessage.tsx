/**
 * frontend/src/components/ErrorMessage.tsx
 * Professional error state component.
 */
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  title?: string
  message?: string
  onRetry?: () => void
}

export default function ErrorMessage({
  title = 'Something went wrong',
  message = 'The backend may be unavailable. Please check the API service.',
  onRetry,
}: Props) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10"
      role="alert"
      aria-live="assertive"
    >
      <AlertTriangle size={28} className="text-red-500" aria-hidden="true" />
      <div className="text-center max-w-sm">
        <p className="text-sm font-semibold text-gray-800">{title}</p>
        <p className="text-xs text-gray-500 mt-1">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 border border-blue-300 rounded-md hover:bg-blue-50 transition-colors"
          aria-label="Retry"
        >
          <RefreshCw size={13} aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  )
}

/** Inline (compact) error for use inside cards */
export function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-red-600 py-2" role="alert">
      <AlertTriangle size={13} aria-hidden="true" />
      <span>{message}</span>
    </div>
  )
}

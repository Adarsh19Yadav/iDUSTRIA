/**
 * frontend/src/components/LoadingSpinner.tsx
 * Professional loading skeleton/spinner.
 */
interface Props {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function LoadingSpinner({ message = 'Loading…', size = 'md' }: Props) {
  const spinnerSize = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-10 w-10' : 'h-6 w-6'
  const textSize = size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm'

  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10"
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      <svg
        className={`animate-spin ${spinnerSize} text-blue-600`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <p className={`${textSize} text-gray-500`}>{message}</p>
    </div>
  )
}

/** Skeleton placeholder for card-sized content */
export function SkeletonCard({ lines = 4 }: { lines?: number }) {
  return (
    <div className="card animate-pulse space-y-3" aria-hidden="true">
      <div className="h-4 bg-gray-200 rounded w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-3 bg-gray-100 rounded ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  )
}

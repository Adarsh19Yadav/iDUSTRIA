/**
 * frontend/src/pages/ComingSoonPage.tsx
 * Polished placeholder for routes not yet implemented.
 */
import { Clock } from 'lucide-react'

interface Props {
  title: string
  description: string
}

export default function ComingSoonPage({ title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center max-w-md mx-auto">
      <div
        className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-4"
        aria-hidden="true"
      >
        <Clock size={22} className="text-blue-600" />
      </div>
      <h2 className="text-lg font-bold text-gray-800 mb-2">{title}</h2>
      <p className="text-sm text-gray-500 mb-4 leading-relaxed">{description}</p>
      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-full border border-blue-200">
        <Clock size={11} aria-hidden="true" />
        Coming in next phase
      </span>
    </div>
  )
}

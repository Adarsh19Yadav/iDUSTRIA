/**
 * frontend/src/components/RegisterMachineModal.tsx
 * Modal dialog for registering a new machine.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { X, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { machinesApi } from '../api/machines'
import { InlineError } from './ErrorMessage'

interface Props {
  onClose: () => void
  onSuccess: () => void
}

export default function RegisterMachineModal({ onClose, onSuccess }: Props) {
  const [identifier, setIdentifier] = useState('')
  const [type, setType] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      machinesApi.create({
        machine_identifier: identifier.trim(),
        type: type.trim() || null,
      }),
    onSuccess: (machine) => {
      toast.success(`Machine "${machine.machine_identifier}" registered successfully.`)
      onSuccess()
    },
    onError: (err: unknown) => {
      // axios error
      const status = (err as { response?: { status?: number } }).response?.status
      if (status === 409) {
        toast.error('A machine with that identifier already exists.')
      } else {
        toast.error('Failed to register machine. Please try again.')
      }
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!identifier.trim()) return
    mutation.mutate()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Register new machine"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-bold text-gray-900">Register Machine</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded"
            aria-label="Close modal"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label htmlFor="machine-identifier" className="block text-sm font-semibold text-gray-700 mb-1.5">
              Machine Identifier <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="machine-identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. MACHINE-001"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
              required
              pattern="[A-Za-z0-9_\-\.]{1,128}"
              title="Letters, digits, hyphens, underscores, and dots only (1–128 characters)."
              aria-required="true"
            />
            <p className="text-xs text-gray-400 mt-1">
              Alphanumeric, dash, underscore, dot — max 128 characters.
            </p>
          </div>

          <div>
            <label htmlFor="machine-type" className="block text-sm font-semibold text-gray-700 mb-1.5">
              Type <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              id="machine-type"
              type="text"
              value={type}
              onChange={(e) => setType(e.target.value)}
              placeholder="e.g. CNC_LATHE, PUMP, COMPRESSOR"
              maxLength={64}
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
            />
          </div>

          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Note:</strong> This demo uses the UCI AI4I 2020 synthetic dataset.
              Registered machines will use simulated sensor data for assessments.
              Label data as <strong>SIMULATED / SYNTHETIC DEMO DATA</strong>.
            </p>
          </div>

          {mutation.isError && (
            <InlineError message="Registration failed. Please check your input and try again." />
          )}

          {/* Footer */}
          <div className="flex justify-end gap-2.5 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary btn-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || !identifier.trim()}
              className="btn-primary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
              aria-disabled={mutation.isPending}
            >
              {mutation.isPending ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Registering…
                </>
              ) : (
                <>
                  <Plus size={14} aria-hidden="true" /> Register
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

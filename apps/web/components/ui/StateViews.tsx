'use client'

/**
 * Reusable loading, empty, and error state components.
 * Used across all dashboard pages for consistent UX.
 */

import { Loader2, AlertTriangle, Inbox, RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

// ── Loading ────────────────────────────────────────────────────────────────

interface LoadingProps {
  message?: string
  /** Number of skeleton rows to show (default 3) */
  rows?: number
}

export function LoadingState({ message = 'Loading…', rows = 3 }: LoadingProps) {
  return (
    <div className="space-y-3">
      {message && (
        <div className="flex items-center gap-2 text-text-muted text-sm py-2">
          <Loader2 size={14} className="animate-spin text-agent" />
          <span>{message}</span>
        </div>
      )}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="glass-card p-5 shimmer h-20 rounded-xl" />
      ))}
    </div>
  )
}

/** Inline spinner for buttons and small areas */
export function Spinner({ size = 16, className = '' }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={`animate-spin ${className}`} />
}

// ── Empty ──────────────────────────────────────────────────────────────────

interface EmptyProps {
  icon?: React.ReactNode
  title?: string
  message: string
  action?: {
    label: string
    href?: string
    onClick?: () => void
  }
}

export function EmptyState({ icon, title, message, action }: EmptyProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-12 text-center"
    >
      <div className="flex justify-center mb-3 text-text-muted">
        {icon || <Inbox size={32} />}
      </div>
      {title && <h3 className="text-white font-semibold mb-1">{title}</h3>}
      <p className="text-text-muted text-sm max-w-sm mx-auto">{message}</p>
      {action && (
        <div className="mt-4">
          {action.href ? (
            <a href={action.href} className="btn-primary text-sm py-2 px-4 inline-flex">
              {action.label}
            </a>
          ) : (
            <button onClick={action.onClick} className="btn-primary text-sm py-2 px-4">
              {action.label}
            </button>
          )}
        </div>
      )}
    </motion.div>
  )
}

// ── Error ──────────────────────────────────────────────────────────────────

interface ErrorProps {
  message: string
  onRetry?: () => void
  /** Show a compact inline variant instead of the full card */
  inline?: boolean
}

export function ErrorState({ message, onRetry, inline }: ErrorProps) {
  if (inline) {
    return (
      <div className="flex items-center gap-2 bg-danger/10 border border-danger/20 rounded-xl p-3">
        <AlertTriangle size={14} className="text-danger flex-shrink-0" />
        <span className="text-xs text-danger flex-1">{message}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-danger hover:text-white text-xs flex items-center gap-1 transition-colors"
          >
            <RefreshCw size={12} /> Retry
          </button>
        )}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-8 text-center"
    >
      <AlertTriangle size={28} className="text-danger mx-auto mb-3" />
      <p className="text-danger text-sm mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost text-sm py-2 px-4 mx-auto">
          <RefreshCw size={14} /> Try again
        </button>
      )}
    </motion.div>
  )
}

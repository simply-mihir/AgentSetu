'use client'

/**
 * Reusable loading, empty, and error state components.
 * Green/mint themed with neumorphic styling.
 */

import { Loader2, AlertTriangle, Inbox, RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

// ── Loading ────────────────────────────────────────────────────────────────

interface LoadingProps {
  message?: string
  rows?: number
}

export function LoadingState({ message = 'Loading…', rows = 3 }: LoadingProps) {
  return (
    <div className="space-y-3">
      {message && (
        <div className="flex items-center gap-2 text-[var(--text-muted)] text-sm py-2">
          <Loader2 size={14} className="animate-spin text-[var(--accent)]" />
          <span>{message}</span>
        </div>
      )}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="neo-card p-5 shimmer h-20" />
      ))}
    </div>
  )
}

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
      className="neo-card p-12 text-center"
    >
      <div className="flex justify-center mb-4 text-[var(--text-muted)]">
        {icon || <Inbox size={36} />}
      </div>
      {title && <h3 className="text-[var(--text-primary)] font-semibold mb-1">{title}</h3>}
      <p className="text-[var(--text-muted)] text-sm max-w-sm mx-auto">{message}</p>
      {action && (
        <div className="mt-5">
          {action.href ? (
            <a href={action.href} className="btn-primary text-sm py-2.5 px-5 inline-flex">
              {action.label}
            </a>
          ) : (
            <button onClick={action.onClick} className="btn-primary text-sm py-2.5 px-5">
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
  inline?: boolean
}

export function ErrorState({ message, onRetry, inline }: ErrorProps) {
  if (inline) {
    return (
      <div className="flex items-center gap-2 bg-[var(--danger-bg)] border border-[var(--danger-border)] rounded-xl p-3">
        <AlertTriangle size={14} className="text-[var(--danger)] flex-shrink-0" />
        <span className="text-xs text-[var(--danger)] flex-1">{message}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-[var(--danger)] hover:text-[var(--text-primary)] text-xs flex items-center gap-1 transition-colors"
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
      className="neo-card p-8 text-center"
    >
      <div className="w-12 h-12 rounded-full bg-[var(--danger-bg)] flex items-center justify-center mx-auto mb-4">
        <AlertTriangle size={22} className="text-[var(--danger)]" />
      </div>
      <p className="text-[var(--danger)] text-sm mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost text-sm py-2 px-4 mx-auto">
          <RefreshCw size={14} /> Try again
        </button>
      )}
    </motion.div>
  )
}

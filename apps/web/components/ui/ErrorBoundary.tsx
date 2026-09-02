'use client'

/**
 * React Error Boundary — catches unhandled errors in the component tree
 * and renders a fallback UI instead of crashing the whole page.
 */

import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: React.ReactNode
  fallbackMessage?: string
}

interface State {
  hasError: boolean
  errorMessage: string
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error.message || 'An unexpected error occurred.',
    }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // In production, this would report to Sentry or similar
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card p-8 text-center my-6">
          <AlertTriangle size={28} className="text-danger mx-auto mb-3" />
          <h3 className="text-white font-semibold mb-1">Something went wrong</h3>
          <p className="text-text-muted text-sm mb-4">
            {this.props.fallbackMessage || this.state.errorMessage}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, errorMessage: '' })
              window.location.reload()
            }}
            className="btn-ghost text-sm py-2 px-4 mx-auto"
          >
            <RefreshCw size={14} /> Reload page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

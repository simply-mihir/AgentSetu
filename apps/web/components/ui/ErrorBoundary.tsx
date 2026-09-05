'use client'

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
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-8" style={{ background: 'var(--bg)' }}>
          <div className="neo-card p-10 text-center max-w-md w-full">
            <div className="w-14 h-14 rounded-full bg-[var(--danger-bg)] flex items-center justify-center mx-auto mb-4">
              <AlertTriangle size={26} className="text-[var(--danger)]" />
            </div>
            <h3 className="text-[var(--text-primary)] font-semibold text-lg mb-2">Something went wrong</h3>
            <p className="text-[var(--text-muted)] text-sm mb-6">
              {this.props.fallbackMessage || this.state.errorMessage}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, errorMessage: '' })
                window.location.reload()
              }}
              className="btn-primary text-sm py-2.5 px-5 mx-auto"
            >
              <RefreshCw size={14} /> Reload page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

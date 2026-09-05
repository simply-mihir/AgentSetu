import type { Metadata } from 'next'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '@/lib/auth'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'

export const metadata: Metadata = {
  title: 'AgentSetu — Agentic Commerce Infrastructure',
  description: 'The authorization and interoperability layer for agentic commerce. Make Razorpay merchants machine-readable, discoverable, and safely transactable by AI agents.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <ErrorBoundary>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ErrorBoundary>
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'var(--surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-lg)',
              fontSize: '14px',
            },
            success: {
              iconTheme: { primary: 'var(--success)', secondary: '#FFFFFF' },
            },
            error: {
              iconTheme: { primary: 'var(--danger)', secondary: '#FFFFFF' },
            },
          }}
        />
      </body>
    </html>
  )
}

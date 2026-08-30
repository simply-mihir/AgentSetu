import type { Metadata } from 'next'
import './globals.css'
import { Toaster } from 'react-hot-toast'

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
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'rgba(15, 21, 36, 0.95)',
              color: '#F8FAFC',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '12px',
              backdropFilter: 'blur(20px)',
              fontSize: '14px',
            },
            success: {
              iconTheme: { primary: '#35D07F', secondary: '#0A1F12' },
            },
            error: {
              iconTheme: { primary: '#FF6675', secondary: '#1F0A0D' },
            },
          }}
        />
      </body>
    </html>
  )
}

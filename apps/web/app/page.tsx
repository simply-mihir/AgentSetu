'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-20 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-agent/08 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-2xl w-full text-center space-y-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center">
            <span className="text-2xl">⚡</span>
          </div>
          <h1 className="text-3xl font-bold text-white">AgentSetu</h1>
        </div>

        <p className="text-text-secondary text-lg leading-relaxed">
          The authorization and interoperability layer for agentic commerce.
          <br />
          <span className="text-text-muted text-sm">Merchant manifests · AI buyer · bounded payment · audit</span>
        </p>

        {/* Feature chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {['ARM Manifests', 'AI Discovery', 'Policy Engine', 'Razorpay Payments', 'Audit Trail'].map(f => (
            <span key={f} className="chip-agent">{f}</span>
          ))}
        </div>

        {/* Navigation cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
          <Link href="/buyer" className="glass-card p-6 text-left hover:scale-[1.02] transition-all duration-200 block">
            <div className="text-2xl mb-3">🛒</div>
            <h3 className="font-semibold text-white mb-1">Buyer</h3>
            <p className="text-text-muted text-sm">Natural-language purchase intent with AI discovery and bounded payments</p>
          </Link>

          <Link href="/merchant" className="glass-card p-6 text-left hover:scale-[1.02] transition-all duration-200 block">
            <div className="text-2xl mb-3">🏪</div>
            <h3 className="font-semibold text-white mb-1">Merchant</h3>
            <p className="text-text-muted text-sm">Catalog import, ARM preview, agent spend policy controls</p>
          </Link>

          <Link href="/audit" className="glass-card p-6 text-left hover:scale-[1.02] transition-all duration-200 block">
            <div className="text-2xl mb-3">📋</div>
            <h3 className="font-semibold text-white mb-1">Audit Center</h3>
            <p className="text-text-muted text-sm">Complete transaction timelines, policy decisions, payment evidence</p>
          </Link>
        </div>

        {/* Trust badge */}
        <div className="glass-card p-4 flex items-center gap-3 text-sm text-text-muted">
          <span className="chip-trust">Bounded</span>
          <span>Every money action is policy-checked, consent-gated and audit-logged</span>
        </div>
      </div>
    </div>
  )
}

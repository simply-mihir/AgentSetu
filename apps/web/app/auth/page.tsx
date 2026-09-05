'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Mail, Lock, User, ArrowRight, Loader2, AlertCircle, ShieldCheck } from 'lucide-react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { useAuth } from '@/lib/auth'
import AmbientBackground from '@/components/ui/AmbientBackground'

const AgentSetuOrb = dynamic(() => import('@/components/agent/AgentSetuOrb'), {
  ssr: false,
  loading: () => (
    <div className="w-[240px] h-[240px] flex items-center justify-center">
      <div className="w-36 h-36 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] opacity-25 animate-pulse" />
    </div>
  ),
})

type Mode = 'login' | 'signup'

function AuthForm() {
  const { login, signup, isAuthenticated } = useAuth()
  const router = useRouter()
  const params = useSearchParams()
  const redirect = params.get('redirect') || '/buyer'
  const expired = params.get('expired')

  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState('BUYER')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated) router.push(redirect)
  }, [isAuthenticated, redirect, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        if (password.length < 8) {
          setError('Password must be at least 8 characters')
          setLoading(false)
          return
        }
        await signup(email, password, role, displayName)
      }
      router.push(redirect)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'object' && detail?.error?.message) {
        setError(detail.error.message)
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError(mode === 'login' ? 'Invalid email or password' : 'Signup failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8 relative">
      <AmbientBackground variant="auth" />

      {/* ═══ Large rounded container ═══ */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="
          relative z-10 w-full max-w-5xl
          bg-[var(--surface)]/80 backdrop-blur-xl
          border border-[var(--border)]
          rounded-[32px] shadow-xl
          overflow-hidden
          flex flex-col lg:flex-row
          min-h-[600px] lg:min-h-[640px]
        "
      >
        {/* ── Left: Visual panel ──────────────────────────────── */}
        <div className="
          hidden lg:flex lg:w-[48%]
          bg-gradient-to-br from-[var(--pale-green)] via-[var(--surface-soft)] to-[var(--light-aqua)]
          flex-col items-center justify-center
          p-10 relative overflow-hidden
        ">
          {/* Ambient glow behind orb */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(circle at 50% 40%, var(--green-200) 0%, transparent 60%)',
              opacity: 0.3,
            }}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="relative z-10"
          >
            <AgentSetuOrb variant="auth" status="idle" />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="relative z-10 mt-6 text-center max-w-sm"
          >
            <h2 className="text-xl font-bold text-[var(--text-primary)] leading-snug mb-3">
              AI commerce,{' '}
              <span className="bg-gradient-to-r from-[var(--sea-green)] to-[var(--mint)] bg-clip-text text-transparent">
                still under your
              </span>{' '}
              control.
            </h2>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              AgentSetu lets AI discover and purchase products while policies and
              one-time authorization keep every transaction within your rules.
            </p>
          </motion.div>
        </div>

        {/* ── Right: Auth form ────────────────────────────────── */}
        <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-14 py-10 lg:py-0">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center shadow-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.5" opacity="0.5"/>
              </svg>
            </div>
            <span className="text-lg font-bold text-[var(--text-primary)]">AgentSetu</span>
          </Link>

          {/* Heading */}
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-sm text-[var(--text-muted)] mb-7">
            {mode === 'login'
              ? 'Sign in to continue to AgentSetu.'
              : 'Get started with agentic commerce.'}
          </p>

          {/* Session expired notice */}
          {expired && mode === 'login' && (
            <div className="flex items-center gap-2 bg-[var(--warning-bg)] border border-[var(--warning-border)] rounded-2xl p-3 mb-5">
              <AlertCircle size={14} className="text-[var(--warning)] flex-shrink-0" />
              <span className="text-xs text-[var(--warning)]">Your session has expired. Please sign in again.</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 bg-[var(--danger-bg)] border border-[var(--danger-border)] rounded-2xl p-3 mb-5">
              <AlertCircle size={14} className="text-[var(--danger)] flex-shrink-0" />
              <span className="text-xs text-[var(--danger)]">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Display Name</label>
                <div className="relative">
                  <User size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    placeholder="Your name"
                    className="neo-input pl-11 text-sm rounded-[18px]"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Email</label>
              <div className="relative">
                <Mail size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="neo-input pl-11 text-sm rounded-[18px]"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="neo-input pl-11 text-sm rounded-[18px]"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
              </div>
            </div>

            {mode === 'signup' && (
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">I am a…</label>
                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    { value: 'BUYER', label: 'Buyer', desc: 'Purchase via AI agent', icon: '🛒' },
                    { value: 'MERCHANT_OWNER', label: 'Merchant', desc: 'List products & policies', icon: '🏪' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setRole(opt.value)}
                      className={`p-3.5 text-left rounded-2xl border transition-all ${
                        role === opt.value
                          ? 'border-[var(--accent)]/30 bg-[var(--accent-soft)] shadow-sm'
                          : 'border-[var(--border)] hover:border-[var(--border-strong)]'
                      }`}
                    >
                      <div className="text-sm font-medium text-[var(--text-primary)]">{opt.icon} {opt.label}</div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="btn-primary w-full justify-center py-3.5 rounded-[18px] text-sm"
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign in' : 'Create account'}
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError('') }}
              className="text-sm text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors"
            >
              {mode === 'login'
                ? "Don't have an account? Sign up"
                : 'Already have an account? Sign in'}
            </button>
          </div>

          {/* Security footer */}
          <div className="mt-8 flex items-center justify-center gap-2 text-[10px] text-[var(--text-muted)]">
            <ShieldCheck size={11} className="text-[var(--success)]" />
            <span>Protected by authenticated, policy-aware access.</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
        <Loader2 className="animate-spin text-[var(--accent)]" size={24} />
      </div>
    }>
      <AuthForm />
    </Suspense>
  )
}

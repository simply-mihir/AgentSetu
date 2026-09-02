'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Zap, Mail, Lock, User, ArrowRight, Loader2, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'

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

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirect)
    }
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
    <div className="min-h-screen flex items-center justify-center p-4">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-20 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-agent/08 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center">
            <Zap size={20} className="text-primary" />
          </div>
          <span className="text-2xl font-bold text-white">AgentSetu</span>
        </Link>

        {/* Card */}
        <div className="glass-card p-8">
          <h2 className="text-xl font-bold text-white text-center mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-text-muted text-sm text-center mb-6">
            {mode === 'login'
              ? 'Sign in to your AgentSetu account'
              : 'Get started with agentic commerce'}
          </p>

          {/* Session expired notice */}
          {expired && mode === 'login' && (
            <div className="flex items-center gap-2 bg-warning/10 border border-warning/20 rounded-xl p-3 mb-4">
              <AlertCircle size={14} className="text-warning flex-shrink-0" />
              <span className="text-xs text-warning">Your session has expired. Please sign in again.</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 bg-danger/10 border border-danger/20 rounded-xl p-3 mb-4">
              <AlertCircle size={14} className="text-danger flex-shrink-0" />
              <span className="text-xs text-danger">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="text-xs text-text-muted mb-1.5 block">Display Name</label>
                <div className="relative">
                  <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    placeholder="Your name"
                    className="glass-input pl-9 text-sm"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-xs text-text-muted mb-1.5 block">Email</label>
              <div className="relative">
                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="glass-input pl-9 text-sm"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-text-muted mb-1.5 block">Password</label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="glass-input pl-9 text-sm"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
              </div>
            </div>

            {mode === 'signup' && (
              <div>
                <label className="text-xs text-text-muted mb-1.5 block">I am a…</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: 'BUYER', label: '🛒 Buyer', desc: 'Purchase via AI agent' },
                    { value: 'MERCHANT_OWNER', label: '🏪 Merchant', desc: 'List products & policies' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setRole(opt.value)}
                      className={`glass-card p-3 text-left transition-all ${
                        role === opt.value
                          ? 'border-primary/50 bg-primary/10'
                          : 'hover:border-white/15'
                      }`}
                      style={{ borderRadius: 12 }}
                    >
                      <div className="text-sm font-medium text-white">{opt.label}</div>
                      <div className="text-[10px] text-text-muted mt-0.5">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="btn-primary w-full justify-center"
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
              className="text-sm text-text-muted hover:text-primary transition-colors"
            >
              {mode === 'login'
                ? "Don't have an account? Sign up"
                : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>

        {/* Trust badge */}
        <div className="mt-4 text-center text-xs text-text-muted">
          <span className="chip-trust" style={{ fontSize: 9 }}>Secure</span>
          {' '}Passwords hashed with Argon2 · JWT auth · No secrets in browser
        </div>
      </motion.div>
    </div>
  )
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={24} />
      </div>
    }>
      <AuthForm />
    </Suspense>
  )
}

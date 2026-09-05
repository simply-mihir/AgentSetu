'use client'

import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Sparkles, ArrowRight, Store, FileText, ShieldCheck, Shield,
  ShoppingCart, Eye, Play, Zap, ChevronDown, Lock, Search,
  CreditCard, Radar, KeyRound, BookOpen, MessageSquareText,
  CheckCircle2, Fingerprint, Package,
} from 'lucide-react'
import toast from 'react-hot-toast'
import AmbientBackground from '@/components/ui/AmbientBackground'
import AgentComposer from '@/components/ui/AgentComposer'
import { useAuth } from '@/lib/auth'

const AgentSetuOrb = dynamic(() => import('@/components/agent/AgentSetuOrb'), {
  ssr: false,
  loading: () => (
    <div className="w-[280px] h-[280px] flex items-center justify-center">
      <div className="w-44 h-44 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] opacity-30 animate-pulse" />
    </div>
  ),
})

const Pillar3DObject = dynamic(() => import('@/components/landing/Pillar3DObject'), {
  ssr: false,
  loading: () => (
    <div className="w-[140px] h-[140px] flex items-center justify-center">
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] opacity-20 animate-pulse" />
    </div>
  ),
})

/* ── Animations ─────────────────────────────────────────────────────────── */

const depthFadeUp = {
  hidden: { opacity: 0, y: 40, scale: 0.88, filter: 'blur(12px)' },
  visible: {
    opacity: 1, y: 0, scale: 1, filter: 'blur(0px)',
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
  },
}

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
}

/* ── Data ───────────────────────────────────────────────────────────────── */

const FEATURES = [
  {
    shape: 'search' as const,
    color: '#67D8B5', emissive: '#168F79',
    title: 'AI Discovery',
    desc: 'Natural-language intent parsing finds the right merchants, products, and prices across the entire registry in milliseconds.',
    icon: Radar,
    bg: 'linear-gradient(145deg, #E8FFF5 0%, #D4FEF0 50%, #C2F5E3 100%)',
    bgDark: 'linear-gradient(145deg, #0A2E22 0%, #0D3D2D 50%, #0A2E22 100%)',
    accent: '#168F79',
    tagline: 'Find anything',
    dotPattern: true,
  },
  {
    shape: 'shield' as const,
    color: '#A5EBD3', emissive: '#2EAF91',
    title: 'Policy Engine',
    desc: 'Deterministic rules gate every spend. Auto-approve within limits, escalate above thresholds, deny when policy says no.',
    icon: ShieldCheck,
    bg: 'linear-gradient(145deg, #F0F4FF 0%, #E4EAFF 50%, #D8E0FF 100%)',
    bgDark: 'linear-gradient(145deg, #141830 0%, #1A1F3D 50%, #141830 100%)',
    accent: '#5B6BCF',
    tagline: 'Always enforced',
    dotPattern: false,
  },
  {
    shape: 'token' as const,
    color: '#5FE9C8', emissive: '#14B898',
    title: 'Bounded Authorization',
    desc: 'One-time, scoped purchase tokens. The AI gets exactly enough access and no more — no open-ended credit cards.',
    icon: KeyRound,
    bg: 'linear-gradient(145deg, #FFF8EC 0%, #FFF0D4 50%, #FFE8BD 100%)',
    bgDark: 'linear-gradient(145deg, #2A2210 0%, #332A14 50%, #2A2210 100%)',
    accent: '#C4890C',
    tagline: 'Scoped access',
    dotPattern: true,
  },
  {
    shape: 'ledger' as const,
    color: '#99F6E0', emissive: '#0D9479',
    title: 'Immutable Audit',
    desc: 'SHA-256 fingerprinted, append-only event trail. Every intent, decision, and payment is evidence-grade.',
    icon: BookOpen,
    bg: 'linear-gradient(145deg, #F5F0FF 0%, #ECE4FF 50%, #E2D8FF 100%)',
    bgDark: 'linear-gradient(145deg, #1C1430 0%, #221A3D 50%, #1C1430 100%)',
    accent: '#8B5CF6',
    tagline: 'Evidence-grade',
    dotPattern: false,
  },
]

const STEPS = [
  {
    num: '01', title: 'Express Intent',
    desc: '"Buy organic honey under ₹500, deliver in 2 days"',
    icon: MessageSquareText,
    accent: '#168F79',
    bg: 'linear-gradient(145deg, #E8FFF5 0%, #D4FEF0 100%)',
    bgDark: 'linear-gradient(145deg, #0A2E22 0%, #0D3D2D 100%)',
    illustration: '💬',
  },
  {
    num: '02', title: 'AI Discovers',
    desc: 'Agents search merchants via ARM manifests, rank by fit',
    icon: Search,
    accent: '#5B6BCF',
    bg: 'linear-gradient(145deg, #F0F4FF 0%, #E4EAFF 100%)',
    bgDark: 'linear-gradient(145deg, #141830 0%, #1A1F3D 100%)',
    illustration: '🔍',
  },
  {
    num: '03', title: 'Policy Gates',
    desc: 'Deterministic rules check limits, auto-approve or escalate',
    icon: Shield,
    accent: '#C4890C',
    bg: 'linear-gradient(145deg, #FFF8EC 0%, #FFF0D4 100%)',
    bgDark: 'linear-gradient(145deg, #2A2210 0%, #332A14 100%)',
    illustration: '🛡️',
  },
  {
    num: '04', title: 'Secure Payment',
    desc: 'Bounded auth token → Razorpay → receipt & audit trail',
    icon: CreditCard,
    accent: '#8B5CF6',
    bg: 'linear-gradient(145deg, #F5F0FF 0%, #ECE4FF 100%)',
    bgDark: 'linear-gradient(145deg, #1C1430 0%, #221A3D 100%)',
    illustration: '💳',
  },
]

const ROLES = [
  {
    title: 'Buyer',
    desc: 'Tell the AI what you want. It discovers, compares, and purchases — bounded by your rules.',
    icon: ShoppingCart,
    href: '/buyer',
    accent: '#168F79',
    bg: 'linear-gradient(160deg, #E8FFF5 0%, #D4FEF0 40%, #C2F5E3 100%)',
    bgDark: 'linear-gradient(160deg, #0A2E22 0%, #0D3D2D 40%, #0A2E22 100%)',
    features: [
      { text: 'Natural language shopping', icon: MessageSquareText },
      { text: 'Policy-bounded spending', icon: Shield },
      { text: 'One-tap approval', icon: CheckCircle2 },
    ],
    illustration: '🛒',
    decorPattern: 'dots',
  },
  {
    title: 'Merchant',
    desc: 'Import your catalog, set policies, and become discoverable to every AI agent on the network.',
    icon: Store,
    href: '/merchant',
    accent: '#5B6BCF',
    bg: 'linear-gradient(160deg, #F0F4FF 0%, #E4EAFF 40%, #D8E0FF 100%)',
    bgDark: 'linear-gradient(160deg, #141830 0%, #1A1F3D 40%, #141830 100%)',
    features: [
      { text: 'ARM manifest generation', icon: Package },
      { text: 'Policy controls', icon: ShieldCheck },
      { text: 'Real-time AI discovery', icon: Radar },
    ],
    illustration: '🏪',
    decorPattern: 'arcs',
  },
  {
    title: 'Auditor',
    desc: 'Review the full transaction trail. Every decision, policy check, and payment — cryptographically sealed.',
    icon: Eye,
    href: '/audit',
    accent: '#8B5CF6',
    bg: 'linear-gradient(160deg, #F5F0FF 0%, #ECE4FF 40%, #E2D8FF 100%)',
    bgDark: 'linear-gradient(160deg, #1C1430 0%, #221A3D 40%, #1C1430 100%)',
    features: [
      { text: 'Event timeline', icon: Sparkles },
      { text: 'SHA-256 fingerprints', icon: Fingerprint },
      { text: 'Correlation tracking', icon: Search },
    ],
    illustration: '🔎',
    decorPattern: 'grid',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   HOME PAGE — public landing
   ═══════════════════════════════════════════════════════════════════════════ */

export default function Home() {
  const router = useRouter()
  const { startDemo, demoAvailable } = useAuth()

  const handleDemo = () => {
    if (!demoAvailable) {
      toast.error('Demo already used on this device. Sign up for full access.')
      return
    }
    const ok = startDemo()
    if (ok) {
      toast.success('Welcome to demo mode!')
      router.push('/buyer')
    } else {
      toast.error('Demo already used. Sign up for full access.')
    }
  }

  return (
    <div className="min-h-screen relative overflow-x-hidden">
      <AmbientBackground variant="hero" />

      {/* ═══ STICKY NAV ═══ */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[var(--bg)]/70 border-b border-[var(--border)]/50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center shadow-sm">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.5" opacity="0.5"/>
                <circle cx="12" cy="12" r="11.5" stroke="white" strokeWidth="1" opacity="0.25"/>
              </svg>
            </div>
            <span className="font-bold text-[var(--text-primary)]">AgentSetu</span>
          </Link>

          <div className="flex items-center gap-4">
            <a href="#features" className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors hidden sm:block">
              Features
            </a>
            <a href="#how-it-works" className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors hidden sm:block">
              How It Works
            </a>
            <a href="#get-started" className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors hidden sm:block">
              Get Started
            </a>
            <Link href="/auth" className="btn-primary text-xs py-2 px-4">
              Sign In <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══ HERO ═══ */}
      <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 relative">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <AgentSetuOrb variant="hero" status="idle" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="text-4xl sm:text-5xl lg:text-[58px] font-extrabold text-[var(--text-primary)] tracking-tight leading-[1.08] text-center mt-6 mb-4"
        >
          Let AI shop.{' '}
          <span className="bg-gradient-to-r from-[var(--sea-green)] to-[var(--mint)] bg-clip-text text-transparent">
            You stay in control.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.5 }}
          className="text-base sm:text-lg text-[var(--text-secondary)] text-center max-w-lg mb-8 leading-relaxed"
        >
          AgentSetu is the authorization &amp; interoperability layer for AI-native
          agentic commerce. Agents discover, policies gate, you approve.
        </motion.p>

        {/* AI Composer CTA */}
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.95, filter: 'blur(8px)' }}
          animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
          transition={{ delay: 0.6, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-2xl mt-4 mb-6 relative z-10"
        >
          <AgentComposer
            onSubmit={(val) => {
              toast.success('Demo mode started!')
              router.push(`/buyer?intent=${encodeURIComponent(val)}`)
            }}
            showQuickActions={false}
            placeholder="Ask AgentSetu to find something..."
          />
        </motion.div>

        {/* Action Links */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.5 }}
          className="flex flex-col sm:flex-row items-center gap-4 text-sm font-medium"
        >
          <button onClick={handleDemo} className="text-[var(--text-secondary)] hover:text-[var(--accent)] transition-colors flex items-center gap-2">
            <Play size={14} />
            {demoAvailable ? 'Try Demo Without Account' : 'Demo Used'}
          </button>
          <span className="hidden sm:block text-[var(--border-strong)]">|</span>
          <Link href="/auth" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            Sign In for Full Access
          </Link>
        </motion.div>

        {/* Trust strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 mt-10 text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider"
        >
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={12} className="text-[var(--success)]" />
            Policy-aware
          </span>
          <span className="w-px h-3 bg-[var(--border)] hidden sm:block" />
          <span className="flex items-center gap-1.5">
            <Lock size={12} className="text-[var(--sea-green)]" />
            Bounded
          </span>
          <span className="w-px h-3 bg-[var(--border)] hidden sm:block" />
          <span className="flex items-center gap-1.5">
            <FileText size={12} className="text-[var(--mint)]" />
            Auditable
          </span>
          <span className="w-px h-3 bg-[var(--border)] hidden sm:block" />
          <span className="flex items-center gap-1.5">
            <Zap size={12} className="text-[var(--warning)]" />
            Razorpay Powered
          </span>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.4 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8"
        >
          <ChevronDown size={20} className="text-[var(--text-muted)] animate-bounce" />
        </motion.div>
      </section>

      {/* ═══ CORE INVARIANT ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            variants={depthFadeUp}
          >
            <p className="text-xs uppercase tracking-widest text-[var(--sea-green)] font-semibold mb-3">
              The Core Invariant
            </p>
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-[var(--text-primary)] mb-4">
              The LLM reasons.{' '}
              <span className="bg-gradient-to-r from-[var(--sea-green)] to-[var(--mint)] bg-clip-text text-transparent">
                Deterministic code decides.
              </span>
            </h2>
            <p className="text-[var(--text-secondary)] max-w-2xl mx-auto leading-relaxed">
              AI agents are brilliant at finding what you want, but they should never
              have direct access to your money. AgentSetu puts a policy engine between
              the AI and the payment — every transaction is bounded, auditable, and
              under your control.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ═══ FEATURES WITH 3D OBJECTS ═══ */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={depthFadeUp}
            className="text-center mb-14"
          >
            <p className="text-xs uppercase tracking-widest text-[var(--sea-green)] font-semibold mb-3">
              Capabilities
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              Four pillars of safe AI commerce
            </h2>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.15 }}
            variants={stagger}
            className="grid grid-cols-1 sm:grid-cols-2 gap-6"
          >
            {FEATURES.map((f, idx) => {
              const Icon = f.icon
              const isEven = idx % 2 === 0
              return (
                <motion.div key={f.title} variants={depthFadeUp}>
                  <div
                    className="relative rounded-3xl overflow-hidden h-full group hover:-translate-y-1 transition-all duration-400"
                    style={{
                      boxShadow: '0 2px 20px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04)',
                    }}
                  >
                    {/* Card background — unique per card */}
                    <div
                      className="absolute inset-0 feature-card-bg"
                      style={{ background: f.bg }}
                    />
                    <div
                      className="absolute inset-0 feature-card-bg-dark"
                      style={{ background: f.bgDark }}
                    />

                    {/* Decorative dot pattern */}
                    {f.dotPattern && (
                      <div className="absolute bottom-4 right-4 opacity-[0.12] pointer-events-none">
                        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                          {Array.from({ length: 36 }).map((_, i) => (
                            <circle
                              key={i}
                              cx={(i % 6) * 12 + 4}
                              cy={Math.floor(i / 6) * 12 + 4}
                              r="2"
                              fill={f.accent}
                            />
                          ))}
                        </svg>
                      </div>
                    )}

                    {/* Decorative corner arc (cards without dots) */}
                    {!f.dotPattern && (
                      <div className="absolute -top-12 -right-12 opacity-[0.08] pointer-events-none">
                        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                          <circle cx="60" cy="60" r="55" stroke={f.accent} strokeWidth="3" />
                          <circle cx="60" cy="60" r="40" stroke={f.accent} strokeWidth="2" />
                          <circle cx="60" cy="60" r="25" stroke={f.accent} strokeWidth="1.5" />
                        </svg>
                      </div>
                    )}

                    <div className={`relative z-10 p-6 sm:p-7 flex ${isEven ? 'flex-col' : 'flex-col-reverse'} gap-3`}>
                      {/* 3D scene area */}
                      <div className="flex justify-center group-hover:scale-105 transition-transform duration-500">
                        <Pillar3DObject
                          shape={f.shape}
                          color={f.color}
                          emissive={f.emissive}
                          size={170}
                        />
                      </div>

                      {/* Content */}
                      <div className={isEven ? '' : 'pt-1'}>
                        {/* Tagline chip */}
                        <span
                          className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full mb-3"
                          style={{
                            background: `color-mix(in srgb, ${f.accent} 12%, transparent)`,
                            color: f.accent,
                          }}
                        >
                          <Icon size={11} />
                          {f.tagline}
                        </span>

                        <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2 leading-snug">
                          {f.title}
                        </h3>
                        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                          {f.desc}
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      <section id="how-it-works" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={depthFadeUp}
            className="text-center mb-14"
          >
            <p className="text-xs uppercase tracking-widest text-[var(--sea-green)] font-semibold mb-3">
              Flow
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              How AgentSetu works
            </h2>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.15 }}
            variants={stagger}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {STEPS.map((step, i) => {
              const StepIcon = step.icon
              return (
                <motion.div key={step.num} variants={depthFadeUp}>
                  <div
                    className="relative rounded-2xl overflow-hidden h-full group hover:-translate-y-1 transition-all duration-300"
                    style={{ boxShadow: '0 2px 16px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.03)' }}
                  >
                    {/* Per-card background */}
                    <div className="absolute inset-0 feature-card-bg" style={{ background: step.bg }} />
                    <div className="absolute inset-0 feature-card-bg-dark" style={{ background: step.bgDark }} />

                    <div className="relative z-10 p-5 h-full flex flex-col">
                      {/* Illustration area */}
                      <div className="flex items-center justify-between mb-4">
                        <div
                          className="w-11 h-11 rounded-xl flex items-center justify-center text-lg"
                          style={{ background: `color-mix(in srgb, ${step.accent} 14%, transparent)` }}
                        >
                          <StepIcon size={20} style={{ color: step.accent }} />
                        </div>
                        {/* Step number */}
                        <span
                          className="text-4xl font-black select-none opacity-[0.08]"
                          style={{ color: step.accent }}
                        >
                          {step.num}
                        </span>
                      </div>

                      <h3 className="font-bold text-[var(--text-primary)] text-sm mb-1.5">{step.title}</h3>
                      <p className="text-xs text-[var(--text-muted)] leading-relaxed flex-1">{step.desc}</p>

                      {/* Connector arrow (desktop only) */}
                      {i < STEPS.length - 1 && (
                        <div className="hidden lg:flex absolute top-1/2 -right-3 -translate-y-1/2 z-20">
                          <div
                            className="w-6 h-6 rounded-full flex items-center justify-center"
                            style={{ background: `color-mix(in srgb, ${step.accent} 15%, var(--bg))` }}
                          >
                            <ArrowRight size={11} style={{ color: step.accent }} />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        </div>
      </section>

      {/* ═══ CHOOSE YOUR PATH ═══ */}
      <section id="get-started" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={depthFadeUp}
            className="text-center mb-14"
          >
            <p className="text-xs uppercase tracking-widest text-[var(--sea-green)] font-semibold mb-3">
              Get Started
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-2">
              Choose your path
            </h2>
            <p className="text-sm text-[var(--text-muted)]">
              Sign up required · or try the one-time demo
            </p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.15 }}
            variants={stagger}
            className="grid grid-cols-1 sm:grid-cols-3 gap-5"
          >
            {ROLES.map((role) => {
              const RoleIcon = role.icon
              return (
                <motion.div key={role.title} variants={depthFadeUp}>
                  <div
                    className="relative rounded-3xl overflow-hidden h-full flex flex-col group hover:-translate-y-1 transition-all duration-400"
                    style={{ boxShadow: '0 2px 20px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04)' }}
                  >
                    {/* Per-card background */}
                    <div className="absolute inset-0 feature-card-bg" style={{ background: role.bg }} />
                    <div className="absolute inset-0 feature-card-bg-dark" style={{ background: role.bgDark }} />

                    {/* Decorative elements */}
                    {role.decorPattern === 'dots' && (
                      <div className="absolute bottom-4 right-4 opacity-[0.10] pointer-events-none">
                        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
                          {Array.from({ length: 25 }).map((_, di) => (
                            <circle key={di} cx={(di % 5) * 13 + 4} cy={Math.floor(di / 5) * 13 + 4} r="2" fill={role.accent} />
                          ))}
                        </svg>
                      </div>
                    )}
                    {role.decorPattern === 'arcs' && (
                      <div className="absolute -bottom-10 -left-10 opacity-[0.06] pointer-events-none">
                        <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
                          <circle cx="50" cy="50" r="45" stroke={role.accent} strokeWidth="2.5" />
                          <circle cx="50" cy="50" r="32" stroke={role.accent} strokeWidth="2" />
                          <circle cx="50" cy="50" r="19" stroke={role.accent} strokeWidth="1.5" />
                        </svg>
                      </div>
                    )}
                    {role.decorPattern === 'grid' && (
                      <div className="absolute top-4 right-4 opacity-[0.08] pointer-events-none">
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                          <rect x="2" y="2" width="18" height="18" rx="3" stroke={role.accent} strokeWidth="1.5" />
                          <rect x="28" y="2" width="18" height="18" rx="3" stroke={role.accent} strokeWidth="1.5" />
                          <rect x="2" y="28" width="18" height="18" rx="3" stroke={role.accent} strokeWidth="1.5" />
                          <rect x="28" y="28" width="18" height="18" rx="3" stroke={role.accent} strokeWidth="1.5" />
                        </svg>
                      </div>
                    )}

                    <div className="relative z-10 p-6 flex flex-col h-full">
                      {/* Illustration header area */}
                      <div
                        className="w-full h-28 rounded-2xl flex items-center justify-center mb-5 text-4xl relative overflow-hidden"
                        style={{ background: `color-mix(in srgb, ${role.accent} 8%, transparent)` }}
                      >
                        <div className="absolute inset-0 opacity-[0.04]" style={{
                          backgroundImage: `radial-gradient(circle at 2px 2px, ${role.accent} 1px, transparent 0)`,
                          backgroundSize: '16px 16px',
                        }} />
                        <RoleIcon size={40} style={{ color: role.accent, opacity: 0.7 }} />
                      </div>

                      <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">{role.title}</h3>
                      <p className="text-sm text-[var(--text-secondary)] leading-relaxed mb-5 flex-1">
                        {role.desc}
                      </p>

                      {/* Feature bullets with icons */}
                      <div className="space-y-2 mb-6">
                        {role.features.map((feat, fi) => {
                          const FeatIcon = feat.icon
                          return (
                            <div key={fi} className="flex items-center gap-2.5 text-xs text-[var(--text-muted)]">
                              <FeatIcon size={13} className="flex-shrink-0" style={{ color: role.accent }} />
                              <span>{feat.text}</span>
                            </div>
                          )
                        })}
                      </div>

                      <Link
                        href={role.href}
                        className="flex items-center justify-center gap-2 text-sm font-semibold py-2.5 w-full rounded-xl text-white transition-all duration-200 hover:opacity-90"
                        style={{ background: role.accent }}
                      >
                        Enter as {role.title} <ArrowRight size={13} />
                      </Link>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>

          {/* Demo CTA */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={depthFadeUp}
            className="mt-10 text-center"
          >
            <button
              onClick={handleDemo}
              className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors"
            >
              <Play size={14} />
              {demoAvailable
                ? 'Or try the demo — one-time access, no sign-up'
                : 'Demo already used on this device'}
            </button>
          </motion.div>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="py-10 px-6 border-t border-[var(--border)]">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.5" opacity="0.5"/>
              </svg>
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)]">AgentSetu</span>
            <span className="text-xs text-[var(--text-muted)]">· Razorpay AI Buildathon 2025</span>
          </div>

          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <ShieldCheck size={12} className="text-[var(--success)]" />
            <span>Every financial action is auditable and idempotent</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

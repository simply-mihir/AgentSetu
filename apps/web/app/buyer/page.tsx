'use client'

import { useState, useRef, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, ArrowRight, History, Sparkles, Package, Shield, Settings } from 'lucide-react'
import toast from 'react-hot-toast'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { transactionsApi, paymentsApi, extractErrorMessage, type Product, type IntentResponse } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import MerchantCard from '@/components/buyer/MerchantCard'
import ApprovalSheet from '@/components/buyer/ApprovalSheet'
import PaymentStatus from '@/components/buyer/PaymentStatus'
import ConstraintChips from '@/components/buyer/ConstraintChips'
import AmbientBackground from '@/components/ui/AmbientBackground'
import AgentComposer from '@/components/ui/AgentComposer'

const AgentSetuOrb = dynamic(() => import('@/components/agent/AgentSetuOrb'), {
  ssr: false,
  loading: () => (
    <div className="w-[160px] h-[160px] flex items-center justify-center">
      <div className="w-24 h-24 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] opacity-25 animate-pulse" />
    </div>
  ),
})

type Step = 'idle' | 'parsing' | 'discovering' | 'comparing' | 'selecting' | 'policy' | 'approving' | 'paying' | 'done' | 'failed'

interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: Date
  data?: any
}

const QUICK_INTENTS = [
  { emoji: '🍯', label: 'Best price', text: 'Buy organic honey under ₹500, deliver in 2 days' },
  { emoji: '🛒', label: 'Groceries', text: 'Find turmeric powder under ₹200' },
  { emoji: '📦', label: 'Under ₹500', text: 'USB-C cable under ₹400' },
  { emoji: '🚀', label: 'Fast delivery', text: 'Garam masala under ₹200, deliver in 3 days' },
]

const STEP_TO_ORB: Record<Step, 'idle' | 'thinking' | 'processing' | 'success' | 'error' | 'payment' | 'approval'> = {
  idle: 'idle',
  parsing: 'thinking',
  discovering: 'processing',
  comparing: 'idle',
  selecting: 'processing',
  policy: 'processing',
  approving: 'approval',
  paying: 'payment',
  done: 'success',
  failed: 'error',
}

/* ── Rail icons ─────────────────────────────────────────────── */
const railItems = [
  { icon: Sparkles, label: 'AI', href: '/buyer', active: true },
  { icon: Package, label: 'Orders', href: '/buyer/orders', active: false },
  { icon: Shield, label: 'Policy', href: '/merchant/policy', active: false },
  { icon: Settings, label: 'Settings', href: '/merchant', active: false },
]

function BuyerContent() {
  const { user, isDemoMode } = useAuth()
  const searchParams = useSearchParams()
  const initialIntent = searchParams.get('intent')

  const [input, setInput] = useState('')
  const [step, setStep] = useState<Step>('idle')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [intentResult, setIntentResult] = useState<IntentResponse | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [policyResult, setPolicyResult] = useState<any>(null)
  const [paymentResult, setPaymentResult] = useState<any>(null)
  const [currentTxnId, setCurrentTxnId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const processedIntent = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  // Process initial intent from landing page
  useEffect(() => {
    if (initialIntent && !processedIntent.current) {
      processedIntent.current = true
      handleSubmit(initialIntent)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialIntent])

  const addMessage = (role: 'user' | 'agent', content: string, data?: any) => {
    setMessages(prev => [...prev, {
      id: Math.random().toString(36).slice(2),
      role,
      content,
      timestamp: new Date(),
      data,
    }])
  }

  const handleSubmit = async (text?: string) => {
    const query = typeof text === 'string' ? text : input.trim()
    if (!query || step !== 'idle') return

    setInput('')
    addMessage('user', query)
    setStep('parsing')

    try {
      addMessage('agent', 'Searching merchants across the registry…')
      setStep('discovering')

      const result = await transactionsApi.processIntent(query)
      setIntentResult(result)
      setCurrentTxnId(result.transaction_id)

      setMessages(prev => prev.filter(m => m.content !== 'Searching merchants across the registry…'))

      if (result.no_results || result.candidates.length === 0) {
        addMessage('agent',
          result.relaxation_hint ||
          'No merchants match all your constraints. Try relaxing your budget or delivery preference.',
          { type: 'no_results' }
        )
        setStep('idle')
        return
      }

      addMessage('agent', result.explanation || `Found ${result.total_found} matching products.`, {
        type: 'candidates',
        candidates: result.candidates,
        constraints: result.constraints,
      })
      setStep('comparing')

    } catch (err: any) {
      const msg = extractErrorMessage(err, 'Failed to process your request.')
      toast.error(msg)
      addMessage('agent', msg)
      setStep('idle')
    }
  }

  const handleSelectProduct = async (product: Product) => {
    if (!currentTxnId) return
    setSelectedProduct(product)
    setStep('policy')

    try {
      await transactionsApi.select(currentTxnId, product.product_id, product.merchant_id!)

      const policy = await transactionsApi.evaluatePolicy({
        merchant_id: product.merchant_id!,
        product_id: product.product_id,
        amount_inr: product.price_inr,
      })
      setPolicyResult(policy)

      if (policy.is_denied) {
        addMessage('agent', policy.message, { type: 'denied', policy })
        setStep('idle')
        return
      }

      if (policy.needs_approval) {
        addMessage('agent',
          `This transaction (₹${product.price_inr}) exceeds the autonomous limit of ₹${policy.requires_approval_above}. Your approval is required to proceed.`,
          { type: 'needs_approval', product, policy }
        )
        setStep('approving')
        return
      }

      setStep('paying')
      await handleCreatePayment(false)

    } catch (err: any) {
      const msg = extractErrorMessage(err, 'Policy evaluation failed.')
      toast.error(msg)
      addMessage('agent', msg)
      setStep('idle')
    }
  }

  const handleApprove = async () => {
    if (!currentTxnId) return
    setStep('paying')

    try {
      await transactionsApi.approve(currentTxnId)
      addMessage('agent', 'Your approval has been recorded. Creating payment link…')
      await handleCreatePayment(true)
    } catch (err) {
      const msg = extractErrorMessage(err, 'Approval failed.')
      toast.error(msg)
      setStep('idle')
    }
  }

  const handleCreatePayment = async (wasApproved: boolean) => {
    if (!currentTxnId) return

    try {
      const payment = await paymentsApi.createPaymentLink(currentTxnId)
      setPaymentResult(payment)

      if (payment.needs_approval) {
        addMessage('agent', payment.message, { type: 'needs_approval' })
        setStep('approving')
        return
      }

      addMessage('agent', 'Payment link created. Complete your purchase securely.', {
        type: 'payment_ready',
        payment,
        product: selectedProduct,
      })
      setStep('done')

    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'object' && detail?.blocked) {
        addMessage('agent', `Payment blocked: ${detail.reason}`, { type: 'blocked', detail })
      } else if (typeof detail === 'object' && detail?.payment_failed) {
        addMessage('agent',
          'Payment did not complete. Your transaction is held safely — no retry has been attempted.',
          { type: 'payment_failed' }
        )
      } else {
        addMessage('agent', `Payment failed: ${err.message}`)
      }
      setStep('failed')
    }
  }

  const handleReset = () => {
    setStep('idle')
    setIntentResult(null)
    setSelectedProduct(null)
    setPolicyResult(null)
    setPaymentResult(null)
    setCurrentTxnId(null)
    setMessages([])
  }

  const isLoading = ['parsing', 'discovering', 'policy', 'paying'].includes(step)
  const orbStatus = STEP_TO_ORB[step]
  const hasMessages = messages.length > 0

  // Greeting
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const userName = user?.display_name?.split(' ')[0] || 'there'

  return (
    <div className="h-screen flex flex-col overflow-hidden relative">
      {/* Demo mode banner */}
      {isDemoMode && (
        <div className="flex-shrink-0 bg-gradient-to-r from-[var(--sea-green)] to-[var(--mint)] text-white text-center text-xs py-1.5 px-4 flex items-center justify-center gap-3 relative z-50">
          <span>🎮 Demo Mode — one-time access</span>
          <Link href="/auth" className="underline font-semibold">Sign up for full access →</Link>
        </div>
      )}
      <div className="flex-1 flex overflow-hidden relative">
      <AmbientBackground variant="subtle" />

      {/* ═══ LEFT RAIL ═══ */}
      <aside className="hidden lg:flex flex-col items-center py-6 px-3 gap-1 relative z-20 w-16">
        <Link href="/" className="mb-6">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center shadow-sm">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
              <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.5" opacity="0.5"/>
              <circle cx="12" cy="12" r="11.5" stroke="white" strokeWidth="1" opacity="0.25"/>
            </svg>
          </div>
        </Link>

        {railItems.map(item => {
          const Icon = item.icon
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`
                group relative w-10 h-10 flex items-center justify-center
                rounded-xl transition-all duration-200
                ${item.active
                  ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)]'
                }
              `}
              title={item.label}
            >
              <Icon size={18} />
              <span className="absolute left-14 px-2 py-1 rounded-lg bg-[var(--surface)] border border-[var(--border)] shadow-md text-[10px] font-medium text-[var(--text-primary)] opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
                {item.label}
              </span>
            </Link>
          )
        })}
      </aside>

      {/* ═══ MAIN ═══ */}
      <main className="flex-1 flex flex-col min-w-0 relative z-10">
        {/* ── Header ─────────────────────────────────────────── */}
        <header className="flex items-center justify-between px-6 lg:px-8 py-4 relative z-20">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 lg:hidden">
            <Link href="/" className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center shadow-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.5" opacity="0.5"/>
              </svg>
            </Link>
            <span className="font-bold text-sm text-[var(--text-primary)]">AgentSetu</span>
          </div>

          {/* Status */}
          <div className="hidden lg:flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
            <span className="text-xs text-[var(--text-muted)] font-medium">Agent online</span>
          </div>

          {/* Right */}
          <div className="flex items-center gap-2">
            <Link href="/buyer/orders" className="btn-ghost text-xs py-2 px-3 rounded-xl">
              <History size={13} /> Orders
            </Link>
            {hasMessages && (
              <button onClick={handleReset} className="btn-ghost text-xs py-2 px-3 rounded-xl">
                New
              </button>
            )}
          </div>
        </header>

        {/* ── Content area ───────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 lg:px-8">
            <div className="max-w-2xl mx-auto w-full">
              {/* ── Empty state: orb + greeting + quick actions ─── */}
              {!hasMessages && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center justify-center pt-8 lg:pt-16 pb-8"
                >
                  <AgentSetuOrb variant="compact" status={orbStatus} />

                  <div className="text-center mt-4 mb-6">
                    <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">
                      {greeting}, {userName}.
                    </h2>
                    <p className="text-sm text-[var(--text-muted)]">
                      What would you like me to find?
                    </p>
                  </div>

                  {/* Quick chips */}
                  <div className="flex flex-wrap gap-2 justify-center max-w-md">
                    {QUICK_INTENTS.map(q => (
                      <button
                        key={q.label}
                        onClick={() => handleSubmit(q.text)}
                        className="
                          flex items-center gap-1.5 px-4 py-2
                          bg-[var(--surface)] border border-[var(--border)]
                          rounded-full text-xs font-medium text-[var(--text-secondary)]
                          hover:border-[var(--accent)]/30 hover:text-[var(--accent)]
                          hover:bg-[var(--accent-soft)] hover:shadow-sm
                          transition-all duration-200
                        "
                      >
                        <span>{q.emoji}</span>
                        <span>{q.label}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* ── Chat messages ─────────────────────────────────── */}
              {hasMessages && (
                <div className="py-6 space-y-5">
                  {/* Small orb status indicator when chatting */}
                  <div className="flex justify-center mb-2">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--surface-soft)] border border-[var(--border)]">
                      <div className={`w-2 h-2 rounded-full ${
                        isLoading ? 'bg-[var(--teal-400)] animate-pulse' :
                        step === 'done' ? 'bg-[var(--success)]' :
                        step === 'failed' ? 'bg-[var(--danger)]' :
                        'bg-[var(--accent)]'
                      }`} />
                      <span className="text-[10px] text-[var(--text-muted)] font-medium">
                        {isLoading ? 'Processing…' :
                         step === 'done' ? 'Complete' :
                         step === 'failed' ? 'Failed' :
                         step === 'approving' ? 'Awaiting approval' :
                         'Ready'}
                      </span>
                    </div>
                  </div>

                  <AnimatePresence initial={false}>
                    {messages.map((msg) => (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.2 }}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-[90%] ${msg.role === 'user' ? 'w-auto' : 'w-full'}`}>
                          {/* User message */}
                          {msg.role === 'user' && (
                            <div className="
                              bg-gradient-to-r from-[var(--accent-soft)] to-[var(--green-50)]
                              border border-[var(--accent)]/10
                              rounded-2xl rounded-br-md px-4 py-3
                              text-sm text-[var(--text-primary)]
                            ">
                              {msg.content}
                            </div>
                          )}

                          {/* Agent message */}
                          {msg.role === 'agent' && (
                            <div className="space-y-3">
                              <div className="flex items-start gap-2.5">
                                <div className="
                                  w-7 h-7 rounded-full flex-shrink-0 mt-0.5
                                  bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)]
                                  flex items-center justify-center shadow-sm
                                ">
                                  <Sparkles size={11} className="text-[var(--accent)]" />
                                </div>
                                <div className="
                                  bg-[var(--surface)] border border-[var(--border)]
                                  rounded-2xl rounded-bl-md px-4 py-3
                                  text-sm text-[var(--text-secondary)] flex-1
                                  shadow-xs
                                ">
                                  {msg.content}
                                </div>
                              </div>

                              {/* Constraint chips */}
                              {msg.data?.type === 'candidates' && msg.data?.constraints && (
                                <div className="ml-9">
                                  <ConstraintChips constraints={msg.data.constraints} />
                                </div>
                              )}

                              {/* Product candidates */}
                              {msg.data?.type === 'candidates' && msg.data?.candidates && (
                                <div className="ml-9 space-y-3">
                                  {msg.data.candidates.slice(0, 3).map((p: Product, i: number) => (
                                    <MerchantCard
                                      key={p.product_id}
                                      product={p}
                                      rank={i}
                                      isBest={i === 0}
                                      disabled={step !== 'comparing'}
                                      onSelect={handleSelectProduct}
                                    />
                                  ))}
                                </div>
                              )}

                              {/* Approval sheet */}
                              {msg.data?.type === 'needs_approval' && step === 'approving' && (
                                <div className="ml-9">
                                  <ApprovalSheet
                                    product={selectedProduct!}
                                    policyResult={policyResult}
                                    onApprove={handleApprove}
                                    onCancel={() => {
                                      addMessage('agent', 'Transaction cancelled. No payment was attempted.')
                                      setStep('idle')
                                    }}
                                  />
                                </div>
                              )}

                              {/* Payment ready */}
                              {msg.data?.type === 'payment_ready' && (
                                <div className="ml-9">
                                  <PaymentStatus
                                    payment={msg.data.payment}
                                    product={msg.data.product}
                                    transactionId={currentTxnId!}
                                    onVerify={async () => {
                                      try {
                                        const res = await paymentsApi.verify(currentTxnId!)
                                        addMessage('agent',
                                          res.state === 'RECEIPT_ISSUED'
                                            ? 'Payment confirmed! Your receipt is ready.'
                                            : res.recovery_message || 'Payment state updated.',
                                          { type: 'verified', result: res }
                                        )
                                      } catch { toast.error('Verification failed') }
                                    }}
                                  />
                                </div>
                              )}

                              {/* Policy denied */}
                              {msg.data?.type === 'denied' && (
                                <div className="ml-9 p-4 rounded-2xl border border-[var(--danger)]/20 bg-[var(--danger-bg)]">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="chip chip-danger">Blocked</span>
                                    <span className="text-xs text-[var(--text-muted)]">Policy engine decision</span>
                                  </div>
                                  <div className="flex flex-wrap gap-1.5 mt-2">
                                    {msg.data.policy?.reason_codes?.map((code: string) => (
                                      <span key={code} className="text-xs bg-[var(--danger-bg)] text-[var(--danger)] border border-[var(--danger-border)] rounded-lg px-2 py-0.5 font-mono">
                                        {code}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Receipt link */}
                              {msg.data?.type === 'verified' && msg.data?.result?.receipt && (
                                <div className="ml-9">
                                  <Link
                                    href={`/buyer/receipt?txn=${currentTxnId}`}
                                    className="btn-trust text-sm py-2 px-4 rounded-xl"
                                  >
                                    View Receipt <ArrowRight size={14} />
                                  </Link>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {/* Loading indicator */}
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-3 ml-9"
                    >
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] flex items-center justify-center shadow-sm">
                        <Loader2 size={11} className="animate-spin text-[var(--accent)]" />
                      </div>
                      <span className="text-xs text-[var(--text-muted)]">
                        {step === 'parsing' ? 'Parsing your intent…' :
                         step === 'discovering' ? 'Searching merchants…' :
                         step === 'policy' ? 'Evaluating policy…' :
                         'Creating payment link…'}
                      </span>
                    </motion.div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* ── Bottom composer ───────────────────────────────── */}
          <div className="px-6 lg:px-8 pb-5 pt-3 relative z-10">
            <div className="max-w-2xl mx-auto">
              <AgentComposer
                onSubmit={handleSubmit}
                showQuickActions={false}
                placeholder="What would you like to buy?"
                disabled={isLoading || step === 'approving'}
                loading={isLoading}
                autoFocus={!initialIntent}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
    </div>
  )
}

export default function BuyerPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
        <Loader2 className="animate-spin text-[var(--accent)]" size={24} />
      </div>
    }>
      <BuyerContent />
    </Suspense>
  )
}

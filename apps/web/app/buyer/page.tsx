'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, ShoppingBag, ArrowRight, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import Link from 'next/link'
import { transactionsApi, paymentsApi, extractErrorMessage, type Product, type IntentResponse } from '@/lib/api'
import Nav from '@/components/ui/Nav'
import MerchantCard from '@/components/buyer/MerchantCard'
import ApprovalSheet from '@/components/buyer/ApprovalSheet'
import PaymentStatus from '@/components/buyer/PaymentStatus'
import ConstraintChips from '@/components/buyer/ConstraintChips'

type Step = 'idle' | 'parsing' | 'discovering' | 'comparing' | 'selecting' | 'policy' | 'approving' | 'paying' | 'done' | 'failed'

interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: Date
  data?: any
}

const QUICK_INTENTS = [
  '🍯 Buy organic honey under ₹500, deliver in 2 days',
  '📦 Find turmeric powder under ₹200',
  '💻 USB-C cable under ₹400',
  '🌶️ Garam masala under ₹200, deliver in 3 days',
]

export default function BuyerPage() {
  const [input, setInput] = useState('')
  const [step, setStep] = useState<Step>('idle')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [intentResult, setIntentResult] = useState<IntentResponse | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [policyResult, setPolicyResult] = useState<any>(null)
  const [paymentResult, setPaymentResult] = useState<any>(null)
  const [currentTxnId, setCurrentTxnId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

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
    const query = text || input.trim()
    if (!query || step !== 'idle') return

    setInput('')
    addMessage('user', query)
    setStep('parsing')

    try {
      // ── Parse intent + discover + rank ─────────────────────────────────────
      addMessage('agent', '🔍 Checking merchants across the registry…')
      setStep('discovering')

      const result = await transactionsApi.processIntent(query)
      setIntentResult(result)
      setCurrentTxnId(result.transaction_id)

      // Remove the loading message
      setMessages(prev => prev.filter(m => m.content !== '🔍 Checking merchants across the registry…'))

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
      addMessage('agent', `⚠️ ${msg}`)
      setStep('idle')
    }
  }

  const handleSelectProduct = async (product: Product) => {
    if (!currentTxnId) return
    setSelectedProduct(product)
    setStep('policy')

    try {
      // Select product
      await transactionsApi.select(currentTxnId, product.product_id, product.merchant_id!)

      // Evaluate policy
      const policy = await transactionsApi.evaluatePolicy({
        merchant_id: product.merchant_id!,
        product_id: product.product_id,
        amount_inr: product.price_inr,
      })
      setPolicyResult(policy)

      if (policy.is_denied) {
        addMessage('agent', `❌ ${policy.message}`, { type: 'denied', policy })
        setStep('idle')
        return
      }

      if (policy.needs_approval) {
        addMessage('agent',
          `⚠️ This transaction (₹${product.price_inr}) exceeds the autonomous limit of ₹${policy.requires_approval_above}. Your approval is required to proceed.`,
          { type: 'needs_approval', product, policy }
        )
        setStep('approving')
        return
      }

      // Auto-approved
      setStep('paying')
      await handleCreatePayment(false)

    } catch (err: any) {
      const msg = extractErrorMessage(err, 'Policy evaluation failed.')
      toast.error(msg)
      addMessage('agent', `⚠️ ${msg}`)
      setStep('idle')
    }
  }

  const handleApprove = async () => {
    if (!currentTxnId) return
    setStep('paying')

    try {
      await transactionsApi.approve(currentTxnId)
      addMessage('agent', '✅ Your approval has been recorded. Creating payment link…')
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
        addMessage('agent', `⚠️ ${payment.message}`, { type: 'needs_approval' })
        setStep('approving')
        return
      }

      addMessage('agent', `🔗 Payment link created! Complete your purchase securely.`, {
        type: 'payment_ready',
        payment,
        product: selectedProduct,
      })
      setStep('done')

    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'object' && detail?.blocked) {
        addMessage('agent', `🚫 Payment blocked: ${detail.reason}`, { type: 'blocked', detail })
      } else if (typeof detail === 'object' && detail?.payment_failed) {
        addMessage('agent',
          '⚠️ Payment did not complete. I have not retried — your transaction is held safely.',
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
    setTimeout(() => inputRef.current?.focus(), 100)
  }

  const isLoading = ['parsing', 'discovering', 'policy', 'paying'].includes(step)

  return (
    <div className="min-h-screen flex flex-col">
      <Nav active="buyer" />

      <div className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">AI Buyer</h1>
            <p className="text-text-muted text-sm">State your intent in natural language</p>
          </div>
          {(step !== 'idle' || messages.length > 0) && (
            <button onClick={handleReset} className="btn-ghost text-sm py-2 px-4">
              New Purchase
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 flex flex-col gap-4 min-h-[400px]">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex-1 flex flex-col items-center justify-center gap-6 py-12"
            >
              <div className="text-5xl">🛒</div>
              <p className="text-text-secondary text-center max-w-sm">
                Tell me what you want to buy — I'll find the best options and handle the payment safely.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {QUICK_INTENTS.map(q => (
                  <button
                    key={q}
                    onClick={() => handleSubmit(q.replace(/^[^\s]+\s/, ''))}
                    className="glass-card p-3 text-left text-sm text-text-secondary hover:text-white transition-colors text-xs"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[85%] ${msg.role === 'user' ? 'w-auto' : 'w-full'}`}>
                  {/* User message */}
                  {msg.role === 'user' && (
                    <div className="bg-primary/20 border border-primary/25 rounded-2xl rounded-br-sm px-4 py-3 text-sm text-white">
                      {msg.content}
                    </div>
                  )}

                  {/* Agent message */}
                  {msg.role === 'agent' && (
                    <div className="space-y-3">
                      <div className="flex items-start gap-2">
                        <div className="w-6 h-6 rounded-full bg-agent/20 border border-agent/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-xs">⚡</span>
                        </div>
                        <div className="glass-card px-4 py-3 text-sm text-text-secondary flex-1">
                          {msg.content}
                        </div>
                      </div>

                      {/* Constraint chips */}
                      {msg.data?.type === 'candidates' && msg.data?.constraints && (
                        <div className="ml-8">
                          <ConstraintChips constraints={msg.data.constraints} />
                        </div>
                      )}

                      {/* Product candidates */}
                      {msg.data?.type === 'candidates' && msg.data?.candidates && (
                        <div className="ml-8 space-y-3">
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
                        <div className="ml-8">
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
                        <div className="ml-8">
                          <PaymentStatus
                            payment={msg.data.payment}
                            product={msg.data.product}
                            transactionId={currentTxnId!}
                            onVerify={async () => {
                              try {
                                const res = await paymentsApi.verify(currentTxnId!)
                                addMessage('agent',
                                  res.state === 'RECEIPT_ISSUED'
                                    ? '✅ Payment confirmed! Your receipt is ready.'
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
                        <div className="ml-8 glass-card p-4 border-danger/30">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="chip-danger">Blocked</span>
                            <span className="text-xs text-text-muted">Policy engine decision</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {msg.data.policy?.reason_codes?.map((code: string) => (
                              <span key={code} className="text-xs bg-danger/10 text-danger border border-danger/20 rounded px-2 py-0.5 font-mono">
                                {code}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Receipt */}
                      {msg.data?.type === 'verified' && msg.data?.result?.receipt && (
                        <div className="ml-8">
                          <Link
                            href={`/buyer/receipt?txn=${currentTxnId}`}
                            className="btn-trust text-sm py-2 px-4"
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
              className="flex items-center gap-2 text-text-muted text-sm pl-8"
            >
              <Loader2 size={14} className="animate-spin text-agent" />
              <span>
                {step === 'parsing' ? 'Parsing your intent…' :
                 step === 'discovering' ? 'Searching merchants…' :
                 step === 'policy' ? 'Evaluating policy…' :
                 'Creating payment link…'}
              </span>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="glass-card p-2 flex items-center gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
            placeholder="What would you like to buy? (e.g. organic honey under ₹500, deliver in 2 days)"
            className="glass-input border-0 bg-transparent rounded-xl flex-1 text-sm"
            disabled={isLoading || step === 'approving'}
            autoFocus
          />
          <button
            onClick={() => handleSubmit()}
            disabled={!input.trim() || isLoading || step === 'approving'}
            className="btn-primary py-2.5 px-4 rounded-xl"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}

'use client'

import { useSearchParams } from 'next/navigation'
import { useEffect, useState, Suspense } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, ArrowLeft, ShieldCheck } from 'lucide-react'
import Link from 'next/link'
import { paymentsApi } from '@/lib/api'
import Nav from '@/components/ui/Nav'
import AmbientBackground from '@/components/ui/AmbientBackground'
import EventTimeline from '@/components/audit/EventTimeline'

function ReceiptContent() {
  const params = useSearchParams()
  const txnId = params.get('txn')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!txnId) return
    paymentsApi.getReceipt(txnId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [txnId])

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-[var(--text-muted)] animate-pulse">Loading receipt…</div>
    </div>
  )

  if (!data) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-[var(--text-muted)]">Receipt not found</div>
    </div>
  )

  const { receipt, audit_events } = data

  return (
    <div className="max-w-2xl mx-auto w-full px-4 py-6 space-y-6 relative z-10">
      {/* Success header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-8 text-center border-[var(--success)]/20 bg-[var(--success-bg)]"
      >
        <div className="w-16 h-16 rounded-full bg-[var(--success-bg)] border-2 border-[var(--success-border)] flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="text-[var(--success)]" size={32} />
        </div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Transaction Receipt</h1>
        <p className="text-[var(--text-muted)] text-sm font-mono">{receipt.transaction_id}</p>
      </motion.div>

      {/* Receipt details */}
      <div className="neo-card p-6 space-y-4">
        <h2 className="font-semibold text-[var(--text-primary)]">Transaction Details</h2>
        <div className="space-y-3">
          {[
            { label: 'Intent', value: receipt.buyer_intent },
            { label: 'Merchant', value: receipt.merchant_name },
            { label: 'Product', value: receipt.product_name },
            { label: 'Amount', value: `₹${receipt.amount_inr}`, highlight: true },
            { label: 'Policy Decision', value: receipt.policy_decision },
            { label: 'Approval ID', value: receipt.approval_id || 'Auto-authorized' },
            { label: 'Payment Link ID', value: receipt.payment_link_id || 'N/A' },
            { label: 'Status', value: receipt.state.replace('_', ' '), highlight: true },
          ].map(item => (
            <div key={item.label} className="flex justify-between items-start gap-4 py-2.5 border-b border-[var(--border)] last:border-0">
              <span className="text-[var(--text-muted)] text-sm">{item.label}</span>
              <span className={`text-sm text-right max-w-[60%] ${item.highlight ? 'text-[var(--text-primary)] font-semibold' : 'text-[var(--text-secondary)]'}`}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Audit timeline */}
      {audit_events?.length > 0 && (
        <div className="neo-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck size={16} className="text-[var(--success)]" />
            <h2 className="font-semibold text-[var(--text-primary)]">Audit Trail</h2>
          </div>
          <EventTimeline events={audit_events} />
        </div>
      )}

      {/* JSON tab */}
      <details className="neo-card overflow-hidden">
        <summary className="p-4 cursor-pointer text-[var(--text-secondary)] text-sm font-medium hover:text-[var(--text-primary)] transition-colors">
          Machine-Readable Receipt (JSON)
        </summary>
        <pre className="p-4 text-xs text-[var(--text-muted)] overflow-x-auto font-mono border-t border-[var(--border)] bg-[var(--surface-inset)]">
          {JSON.stringify(receipt, null, 2)}
        </pre>
      </details>

      <div className="flex gap-3">
        <Link href="/buyer" className="btn-ghost flex-1 justify-center">
          <ArrowLeft size={15} /> New Purchase
        </Link>
        <Link href="/audit" className="btn-ghost flex-1 justify-center">
          View All Audits
        </Link>
      </div>
    </div>
  )
}

export default function ReceiptPage() {
  return (
    <div className="min-h-screen flex flex-col relative">
      <AmbientBackground variant="subtle" />
      <Nav active="buyer" />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-[var(--text-muted)]">Loading…</div>}>
        <ReceiptContent />
      </Suspense>
    </div>
  )
}

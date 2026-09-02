'use client'

import { useSearchParams } from 'next/navigation'
import { useEffect, useState, Suspense } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, Download, ArrowLeft, Clock, User, Bot, Zap } from 'lucide-react'
import Link from 'next/link'
import { paymentsApi } from '@/lib/api'
import Nav from '@/components/ui/Nav'
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
      <div className="text-text-muted animate-pulse">Loading receipt…</div>
    </div>
  )

  if (!data) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-text-muted">Receipt not found</div>
    </div>
  )

  const { receipt, audit_events } = data

  return (
    <div className="max-w-2xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Success header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6 text-center border-trust/25 bg-trust/5"
      >
        <CheckCircle2 className="text-trust mx-auto mb-3" size={40} />
        <h1 className="text-2xl font-bold text-white mb-1">Transaction Receipt</h1>
        <p className="text-text-muted text-sm">{receipt.transaction_id}</p>
      </motion.div>

      {/* Receipt details */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-semibold text-white">Transaction Details</h2>
        <div className="space-y-3">
          {[
            { label: 'Intent', value: receipt.buyer_intent, highlight: false },
            { label: 'Merchant', value: receipt.merchant_name, highlight: false },
            { label: 'Product', value: receipt.product_name, highlight: false },
            { label: 'Amount', value: `₹${receipt.amount_inr}`, highlight: true },
            { label: 'Policy Decision', value: receipt.policy_decision, highlight: false },
            { label: 'Approval ID', value: receipt.approval_id || 'Auto-authorized', highlight: false },
            { label: 'Payment Link ID', value: receipt.payment_link_id || 'N/A', highlight: false },
            { label: 'Status', value: receipt.state.replace('_', ' '), highlight: true },
          ].map(item => (
            <div key={item.label} className="flex justify-between items-start gap-4 py-2 border-b border-white/5 last:border-0">
              <span className="text-text-muted text-sm">{item.label}</span>
              <span className={`text-sm text-right max-w-[60%] ${item.highlight ? 'text-white font-semibold' : 'text-text-secondary'}`}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Audit timeline */}
      {audit_events?.length > 0 && (
        <div className="glass-card p-5">
          <h2 className="font-semibold text-white mb-4">Audit Trail</h2>
          <EventTimeline events={audit_events} />
        </div>
      )}

      {/* JSON tab */}
      <details className="glass-card overflow-hidden">
        <summary className="p-4 cursor-pointer text-text-secondary text-sm font-medium hover:text-white">
          Machine-Readable Receipt (JSON)
        </summary>
        <pre className="p-4 text-xs text-text-muted overflow-x-auto font-mono border-t border-white/05">
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
    <div className="min-h-screen flex flex-col">
      <Nav active="buyer" />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-muted">Loading…</div>}>
        <ReceiptContent />
      </Suspense>
    </div>
  )
}

'use client'

import { motion } from 'framer-motion'
import { ExternalLink, RefreshCw, CheckCircle2, Lock, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import Link from 'next/link'

interface Props {
  payment: any
  product: any
  transactionId: string
  onVerify: () => Promise<void>
}

export default function PaymentStatus({ payment, product, transactionId, onVerify }: Props) {
  const [verifying, setVerifying] = useState(false)

  const handleVerify = async () => {
    setVerifying(true)
    try { await onVerify() } finally { setVerifying(false) }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-6 border-[var(--success)]/20 bg-[var(--success-bg)]"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-5">
        <div className="w-9 h-9 rounded-xl bg-[var(--success-bg)] border border-[var(--success-border)] flex items-center justify-center">
          <CheckCircle2 className="text-[var(--success)]" size={18} />
        </div>
        <div>
          <span className="font-semibold text-[var(--text-primary)] block text-sm">Payment Link Ready</span>
          <span className="text-[var(--text-muted)] text-xs">One-time authorization</span>
        </div>
        <span className="chip chip-success ml-auto text-[10px]">Authorized</span>
      </div>

      {/* Amount */}
      <div className="text-center py-5 mb-5 rounded-2xl bg-[var(--surface-soft)] border border-[var(--border)]">
        <p className="text-[var(--text-muted)] text-sm mb-1">Authorized Amount</p>
        <div className="text-4xl font-extrabold text-[var(--text-primary)] tracking-tight">₹{payment.amount_inr}</div>
        <p className="text-[var(--text-muted)] text-xs mt-2">{product?.name} · {product?.merchant_name}</p>
      </div>

      {/* Payment link */}
      {payment.payment_link_url && (
        <a
          href={payment.payment_link_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary w-full justify-center mb-4"
        >
          <Lock size={15} />
          Complete Payment on Razorpay
          <ExternalLink size={14} />
        </a>
      )}

      {/* Verify + Audit */}
      <div className="flex gap-2">
        <button onClick={handleVerify} disabled={verifying} className="btn-ghost flex-1 justify-center text-sm py-2.5">
          {verifying ? (
            <><RefreshCw size={14} className="animate-spin" /> Verifying…</>
          ) : (
            <><RefreshCw size={14} /> Verify Status</>
          )}
        </button>
        <Link href={`/audit?txn=${transactionId}`} className="btn-ghost text-sm py-2.5 px-4">
          View Audit
        </Link>
      </div>

      {/* Trust note */}
      <div className="mt-4 flex items-center justify-center gap-1.5 text-[var(--text-muted)] text-xs">
        <ShieldCheck size={10} className="text-[var(--success)]" />
        <span>Bound to this purchase · Cannot be reused · Payment link ID: {payment.payment_link_id}</span>
      </div>
    </motion.div>
  )
}

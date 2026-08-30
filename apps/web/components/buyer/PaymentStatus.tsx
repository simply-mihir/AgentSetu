'use client'

import { motion } from 'framer-motion'
import { ExternalLink, RefreshCw, CheckCircle2, Lock } from 'lucide-react'
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
      className="glass-card p-5 border-trust/20 bg-trust/5"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle2 className="text-trust" size={20} />
        <span className="font-semibold text-white">Payment Link Ready</span>
        <span className="chip-trust ml-auto">Authorized</span>
      </div>

      {/* Amount */}
      <div className="text-center py-4 mb-4 border border-trust/15 rounded-2xl">
        <p className="text-text-muted text-sm mb-1">Authorized Amount</p>
        <div className="amount-display text-trust">₹{payment.amount_inr}</div>
        <p className="text-text-muted text-xs mt-2">{product?.name} · {product?.merchant_name}</p>
      </div>

      {/* Payment link */}
      {payment.payment_link_url && (
        <a
          href={payment.payment_link_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary w-full justify-center mb-3"
        >
          <Lock size={15} />
          Complete Payment on Razorpay
          <ExternalLink size={14} />
        </a>
      )}

      {/* Verify */}
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
      <p className="text-text-muted text-xs text-center mt-3 flex items-center justify-center gap-1">
        <Lock size={10} />
        Payment link ID: {payment.payment_link_id}
      </p>
    </motion.div>
  )
}

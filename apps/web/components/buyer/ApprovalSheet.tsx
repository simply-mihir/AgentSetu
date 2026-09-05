'use client'

import { motion } from 'framer-motion'
import { ShieldAlert, CheckCircle, XCircle } from 'lucide-react'
import type { Product } from '@/lib/api'

interface Props {
  product: Product
  policyResult: any
  onApprove: () => void
  onCancel: () => void
}

export default function ApprovalSheet({ product, policyResult, onApprove, onCancel }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="neo-card p-6 border-[var(--warning)]/20 bg-[var(--warning-bg)]"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-5">
        <div className="w-9 h-9 rounded-xl bg-[var(--warning-bg)] border border-[var(--warning-border)] flex items-center justify-center">
          <ShieldAlert className="text-[var(--warning)]" size={18} />
        </div>
        <div>
          <span className="font-semibold text-[var(--text-primary)] block text-sm">Approval Required</span>
          <span className="text-[var(--text-muted)] text-xs">Above autonomous spending limit</span>
        </div>
        <span className="chip chip-warning ml-auto text-[10px]">Action needed</span>
      </div>

      {/* Amount — the star of the show */}
      <div className="text-center py-5 mb-5 rounded-2xl bg-[var(--surface-soft)] border border-[var(--border)]">
        <p className="text-[var(--text-muted)] text-sm mb-1">Transaction Amount</p>
        <div className="text-4xl font-extrabold text-[var(--text-primary)] tracking-tight">₹{product.price_inr}</div>
        <p className="text-[var(--text-muted)] text-xs mt-2">
          Above autonomous limit of ₹{policyResult?.requires_approval_above || 500}
        </p>
      </div>

      {/* Product details */}
      <div className="space-y-2.5 mb-5">
        {[
          { label: 'Product', value: product.name },
          { label: 'Merchant', value: product.merchant_name },
          { label: 'Delivery', value: `${product.delivery_sla_days_min}–${product.delivery_sla_days_max} days` },
          { label: 'Return', value: product.return_policy.replace('_', ' ') },
        ].map(row => (
          <div key={row.label} className="flex justify-between text-sm">
            <span className="text-[var(--text-muted)]">{row.label}</span>
            <span className="text-[var(--text-primary)] font-medium text-right max-w-[60%] truncate">{row.value}</span>
          </div>
        ))}
      </div>

      {/* Policy reason */}
      {policyResult?.reason_codes?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-5">
          {policyResult.reason_codes.map((code: string) => (
            <span key={code} className="text-xs bg-[var(--warning-bg)] text-[var(--warning)] border border-[var(--warning-border)] rounded-lg px-2 py-0.5 font-mono">
              {code}
            </span>
          ))}
        </div>
      )}

      {/* Trust note */}
      <p className="text-[var(--text-muted)] text-xs text-center mb-5 leading-relaxed">
        This approval is scoped to this exact amount, merchant, and product.<br />No other action is authorized.
      </p>

      {/* Actions */}
      <div className="flex gap-3">
        <button onClick={onCancel} className="btn-ghost flex-1 justify-center py-3">
          <XCircle size={16} />
          Cancel
        </button>
        <button onClick={onApprove} className="btn-trust flex-1 justify-center py-3">
          <CheckCircle size={16} />
          Approve ₹{product.price_inr}
        </button>
      </div>
    </motion.div>
  )
}

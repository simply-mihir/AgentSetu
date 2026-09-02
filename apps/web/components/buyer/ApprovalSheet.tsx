'use client'

import { motion } from 'framer-motion'
import { ShieldAlert, CheckCircle, XCircle, Truck, Star } from 'lucide-react'
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
      className="glass-card p-5 border-warning/25 bg-warning/5"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert className="text-warning" size={20} />
        <span className="font-semibold text-white">Approval Required</span>
        <span className="chip-warning ml-auto">Above Auto-Limit</span>
      </div>

      {/* Amount — the star of the show */}
      <div className="text-center py-4 mb-4 border border-warning/15 rounded-2xl bg-warning/5">
        <p className="text-text-muted text-sm mb-1">Transaction Amount</p>
        <div className="amount-display text-warning">₹{product.price_inr}</div>
        <p className="text-text-muted text-xs mt-2">
          Above autonomous limit of ₹{policyResult?.requires_approval_above || 500}
        </p>
      </div>

      {/* Product details */}
      <div className="space-y-2 mb-4">
        <div className="flex justify-between text-sm">
          <span className="text-text-muted">Product</span>
          <span className="text-white font-medium text-right max-w-[60%] truncate">{product.name}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-muted">Merchant</span>
          <span className="text-white">{product.merchant_name}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-muted">Delivery</span>
          <span className="text-agent">{product.delivery_sla_days_min}–{product.delivery_sla_days_max} days</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-muted">Return</span>
          <span className="text-white">{product.return_policy.replace('_', ' ')}</span>
        </div>
      </div>

      {/* Policy reason */}
      {policyResult?.reason_codes?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {policyResult.reason_codes.map((code: string) => (
            <span key={code} className="text-xs bg-warning/10 text-warning border border-warning/20 rounded px-2 py-0.5 font-mono">
              {code}
            </span>
          ))}
        </div>
      )}

      {/* Trust note */}
      <p className="text-text-muted text-xs text-center mb-4">
        This approval is scoped to this exact amount, merchant and cart. No other action is authorized.
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

'use client'

import { motion } from 'framer-motion'
import { Star, Truck, Clock, ShieldCheck, ChevronRight } from 'lucide-react'
import type { Product } from '@/lib/api'

interface Props {
  product: Product
  rank: number
  isBest: boolean
  disabled: boolean
  onSelect: (p: Product) => void
}

export default function MerchantCard({ product, rank, isBest, disabled, onSelect }: Props) {
  const withinAutoLimit = product.price_inr <= (product.max_autonomous_spend_inr || 500)
  const needsApproval = !withinAutoLimit && product.price_inr <= (product.approval_threshold_inr || 1500)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.06 }}
      className={`neo-card p-5 ${isBest ? 'border-[var(--success)]/25 bg-[var(--success-bg)]' : ''} ${disabled ? 'opacity-60' : 'cursor-pointer neo-card-interactive'} transition-all`}
      onClick={() => !disabled && onSelect(product)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            {isBest && <span className="chip chip-success text-[10px]">Best Match</span>}
            {rank === 1 && !isBest && <span className="chip chip-mint text-[10px]">Runner Up</span>}
            <span className="text-xs text-[var(--text-muted)]">{product.merchant_name}</span>
          </div>

          <h3 className="font-semibold text-[var(--text-primary)] text-sm mb-1 truncate">{product.name}</h3>
          <p className="text-[var(--text-muted)] text-xs mb-3 line-clamp-2">{product.description}</p>

          {/* Attributes */}
          <div className="flex flex-wrap gap-3 text-xs text-[var(--text-secondary)]">
            <div className="flex items-center gap-1">
              <Truck size={11} className="text-[var(--teal-500)]" />
              <span>{product.delivery_sla_days_min}–{product.delivery_sla_days_max} days</span>
            </div>
            <div className="flex items-center gap-1">
              <Star size={11} className="text-[var(--warning)] fill-[var(--warning)]" />
              <span>{product.merchant_rating}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock size={11} className="text-[var(--text-muted)]" />
              <span>{product.return_policy.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Score breakdown */}
          {product._score !== undefined && (
            <div className="mt-3 space-y-1.5">
              <ScoreBar label="Price" value={product._price_score || 0} color="var(--success)" />
              <ScoreBar label="Delivery" value={product._delivery_score || 0} color="var(--teal-500)" />
              <ScoreBar label="Rating" value={product._rating_score || 0} color="var(--warning)" />
            </div>
          )}
        </div>

        {/* Price + CTA */}
        <div className="flex flex-col items-end gap-3 flex-shrink-0">
          <div className="text-right">
            <div className="text-2xl font-bold text-[var(--text-primary)]">₹{product.price_inr}</div>
            {withinAutoLimit ? (
              <div className="flex items-center gap-1 text-[var(--success)] text-xs mt-0.5">
                <ShieldCheck size={10} />
                <span>Auto-approved</span>
              </div>
            ) : needsApproval ? (
              <div className="text-[var(--warning)] text-xs mt-0.5">Needs approval</div>
            ) : (
              <div className="text-[var(--danger)] text-xs mt-0.5">Over limit</div>
            )}
          </div>
          {!disabled && (
            <button
              className={`${isBest ? 'btn-trust' : 'btn-ghost'} text-xs py-2 px-3`}
              style={{ borderRadius: 'var(--radius-md)' }}
              onClick={(e) => { e.stopPropagation(); onSelect(product) }}
            >
              Select <ChevronRight size={12} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-[var(--text-muted)] w-12 shrink-0">{label}</span>
      <div className="score-bar flex-1">
        <div
          className="score-bar-fill"
          style={{ width: `${Math.round(value * 100)}%`, background: color }}
        />
      </div>
      <span className="text-[10px] text-[var(--text-muted)] w-6 text-right">{Math.round(value * 100)}%</span>
    </div>
  )
}

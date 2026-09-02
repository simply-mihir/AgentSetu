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
      className={`glass-card p-4 ${isBest ? 'border-trust/30 bg-trust/5' : ''} ${disabled ? 'opacity-60' : 'cursor-pointer hover:scale-[1.01]'} transition-all`}
      onClick={() => !disabled && onSelect(product)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {isBest && <span className="chip-trust text-[10px]">Best Match</span>}
            {rank === 1 && !isBest && <span className="chip-agent text-[10px]">Runner Up</span>}
            <span className="text-xs text-text-muted">{product.merchant_name}</span>
          </div>

          <h3 className="font-semibold text-white text-sm mb-1 truncate">{product.name}</h3>
          <p className="text-text-muted text-xs mb-3 line-clamp-2">{product.description}</p>

          {/* Attributes */}
          <div className="flex flex-wrap gap-3 text-xs text-text-secondary">
            <div className="flex items-center gap-1">
              <Truck size={11} className="text-agent" />
              <span>{product.delivery_sla_days_min}–{product.delivery_sla_days_max} days</span>
            </div>
            <div className="flex items-center gap-1">
              <Star size={11} className="text-warning fill-warning" />
              <span>{product.merchant_rating}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock size={11} className="text-text-muted" />
              <span>{product.return_policy.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Score breakdown */}
          {product._score !== undefined && (
            <div className="mt-3 space-y-1">
              <ScoreBar label="Price" value={product._price_score || 0} color="var(--trust)" />
              <ScoreBar label="Delivery" value={product._delivery_score || 0} color="var(--agent)" />
              <ScoreBar label="Rating" value={product._rating_score || 0} color="var(--warning)" />
            </div>
          )}
        </div>

        {/* Price + CTA */}
        <div className="flex flex-col items-end gap-3 flex-shrink-0">
          <div className="text-right">
            <div className="text-2xl font-bold text-white">₹{product.price_inr}</div>
            {withinAutoLimit ? (
              <div className="flex items-center gap-1 text-trust text-xs mt-0.5">
                <ShieldCheck size={10} />
                <span>Auto-approved</span>
              </div>
            ) : needsApproval ? (
              <div className="text-warning text-xs mt-0.5">Needs approval</div>
            ) : (
              <div className="text-danger text-xs mt-0.5">Over limit</div>
            )}
          </div>
          {!disabled && (
            <button
              className={`${isBest ? 'btn-trust' : 'btn-ghost'} text-xs py-2 px-3 rounded-xl`}
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
      <span className="text-[10px] text-text-muted w-12 shrink-0">{label}</span>
      <div className="score-bar flex-1">
        <div
          className="score-bar-fill"
          style={{ width: `${Math.round(value * 100)}%`, background: color }}
        />
      </div>
      <span className="text-[10px] text-text-muted w-6 text-right">{Math.round(value * 100)}%</span>
    </div>
  )
}

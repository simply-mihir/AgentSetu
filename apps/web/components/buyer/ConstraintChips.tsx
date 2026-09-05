'use client'

interface Props {
  constraints: Record<string, any>
}

export default function ConstraintChips({ constraints }: Props) {
  const chips = []

  if (constraints.category) {
    chips.push({ label: `📦 ${constraints.category}`, type: 'mint' })
  }
  if (constraints.max_budget_inr) {
    chips.push({ label: `💰 under ₹${constraints.max_budget_inr}`, type: 'accent' })
  }
  if (constraints.delivery_sla_days) {
    chips.push({ label: `🚚 in ${constraints.delivery_sla_days}d`, type: 'mint' })
  }
  if (constraints.quantity && constraints.quantity > 1) {
    chips.push({ label: `x${constraints.quantity}`, type: 'accent' })
  }
  if (constraints.quality_preferences?.length) {
    constraints.quality_preferences.slice(0, 2).forEach((q: string) =>
      chips.push({ label: `✨ ${q}`, type: 'mint' })
    )
  }

  if (!chips.length) return null

  const typeClass: Record<string, string> = {
    mint: 'chip chip-mint',
    accent: 'chip chip-accent',
    success: 'chip chip-success',
  }

  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      <span className="text-xs text-[var(--text-muted)] self-center">Constraints:</span>
      {chips.map((c, i) => (
        <span key={i} className={typeClass[c.type] || 'chip chip-mint'} style={{ fontSize: 11 }}>
          {c.label}
        </span>
      ))}
      {constraints.confidence !== undefined && (
        <span className="chip chip-success" style={{ fontSize: 10 }}>
          {Math.round(constraints.confidence * 100)}% conf
        </span>
      )}
    </div>
  )
}

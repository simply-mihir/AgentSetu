'use client'

interface Props {
  constraints: Record<string, any>
}

export default function ConstraintChips({ constraints }: Props) {
  const chips = []

  if (constraints.category) {
    chips.push({ label: `📦 ${constraints.category}`, type: 'agent' })
  }
  if (constraints.max_budget_inr) {
    chips.push({ label: `💰 under ₹${constraints.max_budget_inr}`, type: 'primary' })
  }
  if (constraints.delivery_sla_days) {
    chips.push({ label: `🚚 in ${constraints.delivery_sla_days}d`, type: 'agent' })
  }
  if (constraints.quantity && constraints.quantity > 1) {
    chips.push({ label: `x${constraints.quantity}`, type: 'primary' })
  }
  if (constraints.quality_preferences?.length) {
    constraints.quality_preferences.slice(0, 2).forEach((q: string) =>
      chips.push({ label: `✨ ${q}`, type: 'agent' })
    )
  }

  if (!chips.length) return null

  const typeClass: Record<string, string> = {
    agent: 'chip-agent',
    primary: 'chip-primary',
    trust: 'chip-trust',
  }

  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      <span className="text-xs text-text-muted self-center">Constraints:</span>
      {chips.map((c, i) => (
        <span key={i} className={typeClass[c.type] || 'chip-agent'} style={{ fontSize: 11 }}>
          {c.label}
        </span>
      ))}
      {constraints.confidence !== undefined && (
        <span className="chip-trust" style={{ fontSize: 10 }}>
          {Math.round(constraints.confidence * 100)}% conf
        </span>
      )}
    </div>
  )
}

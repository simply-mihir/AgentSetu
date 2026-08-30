'use client'

import { motion } from 'framer-motion'
import { format } from 'date-fns'

interface AuditEvent {
  event_id: string
  event_type: string
  actor: string
  timestamp: string
  decision?: string
  result?: string
  next_state?: string
  reason_codes?: string[]
  input_summary?: Record<string, any>
  payment_reference?: string
}

interface Props {
  events: AuditEvent[]
  compact?: boolean
}

const EVENT_ICONS: Record<string, string> = {
  'intent.received': '💬',
  'catalog.discovered': '🔍',
  'recommendation.made': '🎯',
  'policy.decision': '🛡️',
  'approval.granted': '✅',
  'payment.created': '💳',
  'payment.status': '📊',
  'receipt.issued': '🧾',
  'recovery.executed': '🔄',
}

const ACTOR_COLORS: Record<string, string> = {
  buyer: 'var(--primary)',
  agentsetu: 'var(--agent)',
  razorpay: 'var(--trust)',
  merchant: 'var(--warning)',
}

const DECISION_COLORS: Record<string, string> = {
  ALLOW: 'var(--trust)',
  APPROVED: 'var(--trust)',
  SUCCESS: 'var(--trust)',
  DENY: 'var(--danger)',
  FAILED: 'var(--danger)',
  NEEDS_APPROVAL: 'var(--warning)',
}

export default function EventTimeline({ events, compact = false }: Props) {
  return (
    <div className="space-y-0">
      {events.map((event, i) => {
        const icon = EVENT_ICONS[event.event_type] || '⚡'
        const actorColor = ACTOR_COLORS[event.actor] || 'var(--text-muted)'
        const decisionColor = event.decision ? DECISION_COLORS[event.decision] || 'var(--text-muted)' : undefined

        return (
          <motion.div
            key={event.event_id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="flex gap-3"
          >
            {/* Timeline line */}
            <div className="flex flex-col items-center">
              <div
                className="timeline-dot"
                style={{ background: actorColor }}
              />
              {i < events.length - 1 && (
                <div className="w-px flex-1 bg-white/08 my-1" />
              )}
            </div>

            {/* Content */}
            <div className={`pb-4 flex-1 ${compact ? 'pb-2' : ''}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm">{icon}</span>
                <span className="text-sm text-white font-medium">
                  {event.event_type.replace(/\./g, ' ')}
                </span>
                <span
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                  style={{ background: `${actorColor}20`, color: actorColor }}
                >
                  {event.actor}
                </span>
                {event.decision && (
                  <span
                    className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                    style={{ color: decisionColor, background: `${decisionColor}20` }}
                  >
                    {event.decision}
                  </span>
                )}
                <span className="text-text-muted text-[10px] ml-auto">
                  {format(new Date(event.timestamp), 'HH:mm:ss')}
                </span>
              </div>

              {!compact && (
                <div className="mt-1.5 space-y-1">
                  {event.result && (
                    <p className="text-text-muted text-xs">{event.result.replace(/_/g, ' ')}</p>
                  )}
                  {event.next_state && (
                    <span className="text-[10px] font-mono text-text-muted">→ {event.next_state}</span>
                  )}
                  {event.payment_reference && (
                    <p className="text-[10px] font-mono text-agent">{event.payment_reference}</p>
                  )}
                  {event.reason_codes && event.reason_codes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {event.reason_codes.map(code => (
                        <span key={code} className="text-[9px] font-mono px-1 py-0.5 bg-white/05 text-text-muted rounded">
                          {code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

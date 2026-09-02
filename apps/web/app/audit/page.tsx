'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, RefreshCw, Search, ChevronDown, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import Nav from '@/components/ui/Nav'
import { auditApi, transactionsApi, type Transaction } from '@/lib/api'
import EventTimeline from '@/components/audit/EventTimeline'

const EVENT_TYPE_COLORS: Record<string, string> = {
  'intent.received': 'var(--primary)',
  'catalog.discovered': 'var(--agent)',
  'recommendation.made': 'var(--agent)',
  'policy.decision': 'var(--trust)',
  'approval.granted': 'var(--trust)',
  'payment.created': 'var(--trust)',
  'payment.status': 'var(--warning)',
  'receipt.issued': 'var(--trust)',
  'recovery.executed': 'var(--danger)',
}

const STATE_CHIPS: Record<string, string> = {
  DRAFT: 'chip-primary',
  PENDING_APPROVAL: 'chip-warning',
  APPROVED: 'chip-trust',
  PAYMENT_LINK_CREATED: 'chip-agent',
  PAYMENT_SUCCESS: 'chip-trust',
  PAYMENT_FAILED: 'chip-danger',
  PAYMENT_UNKNOWN: 'chip-warning',
  RECEIPT_ISSUED: 'chip-trust',
  RECOVERY_PROPOSED: 'chip-warning',
  CANCELLED: 'chip-danger',
}

function AuditContent() {
  const params = useSearchParams()
  const txnParam = params.get('txn')

  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [expandedTxn, setExpandedTxn] = useState<string | null>(txnParam)
  const [txnEvents, setTxnEvents] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    try {
      const [txns, evts] = await Promise.all([
        transactionsApi.list(),
        auditApi.list(100),
      ])
      setTransactions(Array.isArray(txns) ? txns : [])
      setEvents(evts.events || [])
    } catch { } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const loadTxnEvents = async (txnId: string, correlationId?: string) => {
    // Skip only when we have real cached events (not a stale empty-array placeholder)
    if (txnEvents[txnId] && txnEvents[txnId].length > 0) return
    const queryId = correlationId || txnId
    if (!queryId) return
    try {
      const data = await auditApi.getTimeline(queryId)
      if (data.events?.length > 0) {
        setTxnEvents(prev => ({ ...prev, [txnId]: data.events }))
      }
    } catch { }
  }

  const toggleExpand = async (txnId: string, correlationId?: string) => {
    if (expandedTxn === txnId) {
      setExpandedTxn(null)
    } else {
      setExpandedTxn(txnId)
      loadTxnEvents(txnId, correlationId)
    }
  }

  const filteredTxns = transactions.filter(t =>
    !search ||
    t.transaction_id.includes(search) ||
    (t.buyer_intent || '').toLowerCase().includes(search.toLowerCase()) ||
    (t.merchant_name || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-5xl mx-auto w-full px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Audit Center</h1>
          <p className="text-text-muted text-sm">Complete transaction evidence — append-only event trail</p>
        </div>
        <button
          onClick={() => { setRefreshing(true); loadData() }}
          disabled={refreshing}
          className="btn-ghost text-sm py-2 px-4"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Transactions', value: transactions.length, color: 'var(--primary)' },
          { label: 'Audit Events', value: events.length, color: 'var(--agent)' },
          { label: 'Successful', value: transactions.filter(t => t.state === 'RECEIPT_ISSUED' || t.state === 'PAYMENT_SUCCESS').length, color: 'var(--trust)' },
          { label: 'Money Actions', value: events.filter(e => e.event_type?.includes('payment')).length, color: 'var(--warning)' },
        ].map(stat => (
          <div key={stat.label} className="glass-card p-4">
            <div className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value}</div>
            <div className="text-text-muted text-xs mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search transactions by ID, intent or merchant…"
          className="glass-input pl-9 text-sm"
        />
      </div>

      {/* Transaction list */}
      <div className="space-y-2">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="glass-card p-4 shimmer h-16" />
            ))}
          </div>
        ) : filteredTxns.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <FileText className="text-text-muted mx-auto mb-3" size={32} />
            <p className="text-text-muted">No transactions yet. Start a purchase in the Buyer tab.</p>
          </div>
        ) : (
          filteredTxns.map((txn, i) => (
            <motion.div
              key={txn.transaction_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="glass-card overflow-hidden"
            >
              {/* Transaction row */}
              <button
                onClick={() => toggleExpand(txn.transaction_id, txn.correlation_id)}
                className="w-full p-4 flex items-start gap-4 text-left hover:bg-white/02 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-mono text-xs text-text-muted">{txn.transaction_id}</span>
                    <span className={STATE_CHIPS[txn.state] || 'chip-primary'} style={{ fontSize: 10 }}>
                      {txn.state.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-white truncate">{txn.buyer_intent}</p>
                  <div className="flex gap-3 text-xs text-text-muted mt-1">
                    {txn.merchant_name && <span>{txn.merchant_name}</span>}
                    {txn.amount_inr && <span>₹{txn.amount_inr}</span>}
                    <span>{format(new Date(txn.created_at), 'MMM d, HH:mm')}</span>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  {expandedTxn === txn.transaction_id
                    ? <ChevronDown size={16} className="text-text-muted" />
                    : <ChevronRight size={16} className="text-text-muted" />
                  }
                </div>
              </button>

              {/* Expanded timeline */}
              <AnimatePresence>
                {expandedTxn === txn.transaction_id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden border-t border-white/06"
                  >
                    <div className="p-5">
                      {txnEvents[txn.transaction_id] ? (
                        <EventTimeline events={txnEvents[txn.transaction_id]} />
                      ) : (
                        <div className="text-text-muted text-sm animate-pulse">Loading events…</div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}

export default function AuditPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Nav active="audit" />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-muted">Loading…</div>}>
        <AuditContent />
      </Suspense>
    </div>
  )
}

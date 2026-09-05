'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, RefreshCw, Search, ChevronDown, ChevronRight, Filter, ShieldCheck } from 'lucide-react'
import { format } from 'date-fns'
import Nav from '@/components/ui/Nav'
import AmbientBackground from '@/components/ui/AmbientBackground'
import { auditApi, transactionsApi, extractErrorMessage, type Transaction } from '@/lib/api'
import EventTimeline from '@/components/audit/EventTimeline'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/StateViews'

const STATE_CHIPS: Record<string, string> = {
  DRAFT: 'chip chip-neutral',
  PENDING_APPROVAL: 'chip chip-warning',
  APPROVED: 'chip chip-success',
  PAYMENT_LINK_CREATED: 'chip chip-mint',
  PAYMENT_SUCCESS: 'chip chip-success',
  PAYMENT_FAILED: 'chip chip-danger',
  PAYMENT_UNKNOWN: 'chip chip-warning',
  RECEIPT_ISSUED: 'chip chip-success',
  RECOVERY_PROPOSED: 'chip chip-warning',
  CANCELLED: 'chip chip-danger',
}

function AuditContent() {
  const params = useSearchParams()
  const txnParam = params.get('txn')

  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [expandedTxn, setExpandedTxn] = useState<string | null>(txnParam)
  const [txnEvents, setTxnEvents] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [stateFilter, setStateFilter] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    setError(null)
    try {
      const [txns, evts] = await Promise.all([
        transactionsApi.list(),
        auditApi.list(100),
      ])
      setTransactions(Array.isArray(txns) ? txns : [])
      setEvents(evts.events || [])
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load audit data.'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const loadTxnEvents = async (txnId: string, correlationId?: string) => {
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

  const filteredTxns = transactions.filter(t => {
    if (stateFilter && t.state !== stateFilter) return false
    if (search) {
      const q = search.toLowerCase()
      return t.transaction_id.includes(search) ||
        (t.buyer_intent || '').toLowerCase().includes(q) ||
        (t.merchant_name || '').toLowerCase().includes(q)
    }
    return true
  })

  const statesPresent = [...new Set(transactions.map(t => t.state))]

  return (
    <div className="max-w-5xl mx-auto w-full px-4 py-6 space-y-6 relative z-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Audit Center</h1>
            <ShieldCheck size={16} className="text-[var(--success)]" />
          </div>
          <p className="text-[var(--text-muted)] text-sm">Complete transaction evidence — append-only event trail</p>
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
          { label: 'Transactions', value: transactions.length, color: 'var(--accent)' },
          { label: 'Audit Events', value: events.length, color: 'var(--teal-500)' },
          { label: 'Successful', value: transactions.filter(t => t.state === 'RECEIPT_ISSUED' || t.state === 'PAYMENT_SUCCESS').length, color: 'var(--success)' },
          { label: 'Money Actions', value: events.filter(e => e.event_type?.includes('payment')).length, color: 'var(--warning)' },
        ].map(stat => (
          <div key={stat.label} className="neo-card p-4">
            <div className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value}</div>
            <div className="text-[var(--text-muted)] text-xs mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search transactions by ID, intent or merchant…"
          className="neo-input pl-11 text-sm"
        />
      </div>

      {/* State filters */}
      {statesPresent.length > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter size={12} className="text-[var(--text-muted)]" />
          <button
            onClick={() => setStateFilter(null)}
            className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
              !stateFilter ? 'bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-soft)]'
            }`}
          >
            All
          </button>
          {statesPresent.map(state => (
            <button
              key={state}
              onClick={() => setStateFilter(stateFilter === state ? null : state)}
              className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
                stateFilter === state ? 'bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-soft)]'
              }`}
            >
              {state.replace(/_/g, ' ')}
              <span className="ml-1 opacity-60">
                {transactions.filter(t => t.state === state).length}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Transaction list */}
      <div className="space-y-2">
        {loading ? (
          <LoadingState message="Loading transactions…" rows={3} />
        ) : error ? (
          <ErrorState message={error} onRetry={() => { setRefreshing(true); loadData() }} />
        ) : filteredTxns.length === 0 ? (
          <EmptyState
            icon={<FileText size={32} />}
            message={search
              ? 'No transactions match your search.'
              : 'No transactions yet. Start a purchase in the Buyer tab.'}
            action={search ? { label: 'Clear search', onClick: () => setSearch('') } : { label: 'Go to Buyer', href: '/buyer' }}
          />
        ) : (
          filteredTxns.map((txn, i) => (
            <motion.div
              key={txn.transaction_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="neo-card overflow-hidden"
            >
              <button
                onClick={() => toggleExpand(txn.transaction_id, txn.correlation_id)}
                className="w-full p-4 flex items-start gap-4 text-left hover:bg-[var(--surface-soft)] transition-colors rounded-t-[var(--radius-lg)]"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-mono text-xs text-[var(--text-muted)]">{txn.transaction_id}</span>
                    <span className={STATE_CHIPS[txn.state] || 'chip chip-neutral'} style={{ fontSize: 10 }}>
                      {txn.state.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--text-primary)] truncate">{txn.buyer_intent}</p>
                  <div className="flex gap-3 text-xs text-[var(--text-muted)] mt-1">
                    {txn.merchant_name && <span>{txn.merchant_name}</span>}
                    {txn.amount_inr && <span>₹{txn.amount_inr}</span>}
                    <span>{format(new Date(txn.created_at), 'MMM d, HH:mm')}</span>
                  </div>
                </div>
                <div className="flex-shrink-0 mt-1">
                  {expandedTxn === txn.transaction_id
                    ? <ChevronDown size={16} className="text-[var(--text-muted)]" />
                    : <ChevronRight size={16} className="text-[var(--text-muted)]" />
                  }
                </div>
              </button>

              <AnimatePresence>
                {expandedTxn === txn.transaction_id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden border-t border-[var(--border)]"
                  >
                    <div className="p-5">
                      {txnEvents[txn.transaction_id] ? (
                        <EventTimeline events={txnEvents[txn.transaction_id]} />
                      ) : (
                        <div className="text-[var(--text-muted)] text-sm animate-pulse">Loading events…</div>
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
    <div className="min-h-screen flex flex-col relative">
      <AmbientBackground variant="subtle" />
      <Nav active="audit" />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-[var(--text-muted)]">Loading…</div>}>
        <AuditContent />
      </Suspense>
    </div>
  )
}

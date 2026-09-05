'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Package, ArrowLeft, Receipt, Eye } from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'
import Nav from '@/components/ui/Nav'
import AmbientBackground from '@/components/ui/AmbientBackground'
import { transactionsApi, extractErrorMessage, type Transaction } from '@/lib/api'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/StateViews'
import { useAuth } from '@/lib/auth'

const STATE_LABELS: Record<string, { label: string; chip: string }> = {
  DRAFT: { label: 'Draft', chip: 'chip chip-neutral' },
  PENDING_APPROVAL: { label: 'Needs Approval', chip: 'chip chip-warning' },
  APPROVED: { label: 'Approved', chip: 'chip chip-success' },
  PAYMENT_LINK_CREATED: { label: 'Payment Pending', chip: 'chip chip-mint' },
  PAYMENT_SUCCESS: { label: 'Paid', chip: 'chip chip-success' },
  PAYMENT_FAILED: { label: 'Payment Failed', chip: 'chip chip-danger' },
  PAYMENT_UNKNOWN: { label: 'Unknown', chip: 'chip chip-warning' },
  RECEIPT_ISSUED: { label: 'Completed', chip: 'chip chip-success' },
  RECOVERY_PROPOSED: { label: 'Recovery', chip: 'chip chip-warning' },
  CANCELLED: { label: 'Cancelled', chip: 'chip chip-danger' },
}

export default function OrdersPage() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadOrders = () => {
    setLoading(true)
    setError(null)
    transactionsApi.list()
      .then(data => setTransactions(Array.isArray(data) ? data : []))
      .catch(err => setError(extractErrorMessage(err, 'Failed to load orders.')))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (isAuthenticated) loadOrders()
    else if (!authLoading) setLoading(false)
  }, [isAuthenticated, authLoading])

  const activeOrders = transactions.filter(t =>
    !['RECEIPT_ISSUED', 'CANCELLED', 'RECOVERY_PROPOSED'].includes(t.state)
  )
  const completedOrders = transactions.filter(t =>
    ['RECEIPT_ISSUED', 'CANCELLED', 'RECOVERY_PROPOSED'].includes(t.state)
  )

  return (
    <div className="min-h-screen flex flex-col relative">
      <AmbientBackground variant="subtle" />
      <Nav active="buyer" />

      <div className="max-w-4xl mx-auto w-full px-4 py-6 space-y-6 relative z-10">
        <div className="flex items-center gap-3">
          <Link href="/buyer" className="btn-ghost text-sm py-1.5 px-3">
            <ArrowLeft size={14} /> Back
          </Link>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Order History</h1>
            <p className="text-[var(--text-muted)] text-sm">Your transactions — all states, policy decisions, and receipts</p>
          </div>
        </div>

        {/* Summary stats */}
        {!loading && !error && transactions.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total Orders', value: transactions.length, color: 'var(--accent)' },
              { label: 'Active', value: activeOrders.length, color: 'var(--teal-500)' },
              { label: 'Completed', value: transactions.filter(t => t.state === 'RECEIPT_ISSUED').length, color: 'var(--success)' },
              { label: 'Total Spent', value: `₹${transactions.filter(t => t.state === 'RECEIPT_ISSUED' || t.state === 'PAYMENT_SUCCESS').reduce((s, t) => s + (t.amount_inr || 0), 0)}`, color: 'var(--warning)' },
            ].map(stat => (
              <div key={stat.label} className="neo-card p-4">
                <div className="text-xl font-bold" style={{ color: stat.color }}>{stat.value}</div>
                <div className="text-[var(--text-muted)] text-xs mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <LoadingState message="Loading orders…" />
        ) : error ? (
          <ErrorState message={error} onRetry={loadOrders} />
        ) : !isAuthenticated ? (
          <EmptyState
            message="Sign in to view your order history."
            action={{ label: 'Sign in', href: '/auth?redirect=/buyer/orders' }}
          />
        ) : transactions.length === 0 ? (
          <EmptyState
            icon={<Package size={32} />}
            message="No orders yet. Start a purchase to see your order history here."
            action={{ label: 'Start Shopping', href: '/buyer' }}
          />
        ) : (
          <div className="space-y-6">
            {activeOrders.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">Active ({activeOrders.length})</h2>
                <div className="space-y-2">
                  {activeOrders.map((txn, i) => (
                    <OrderRow key={txn.transaction_id} txn={txn} index={i} />
                  ))}
                </div>
              </div>
            )}

            {completedOrders.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">Completed ({completedOrders.length})</h2>
                <div className="space-y-2">
                  {completedOrders.map((txn, i) => (
                    <OrderRow key={txn.transaction_id} txn={txn} index={i} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function OrderRow({ txn, index }: { txn: Transaction; index: number }) {
  const stateInfo = STATE_LABELS[txn.state] || { label: txn.state, chip: 'chip chip-neutral' }
  const isCompleted = txn.state === 'RECEIPT_ISSUED' || txn.state === 'PAYMENT_SUCCESS'

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
    >
      <div className="neo-card p-4 flex items-center gap-4 hover:bg-[var(--surface-soft)] transition-colors">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={stateInfo.chip} style={{ fontSize: 10 }}>
              {stateInfo.label}
            </span>
            {txn.amount_inr && (
              <span className="text-[var(--text-primary)] font-semibold text-sm">₹{txn.amount_inr}</span>
            )}
          </div>
          <p className="text-sm text-[var(--text-secondary)] truncate">{txn.buyer_intent}</p>
          <div className="flex gap-3 text-xs text-[var(--text-muted)] mt-1">
            {txn.merchant_name && <span>{txn.merchant_name}</span>}
            <span>{format(new Date(txn.created_at), 'MMM d, HH:mm')}</span>
          </div>
        </div>

        <div className="flex gap-2 flex-shrink-0">
          {isCompleted && (
            <Link
              href={`/buyer/receipt?txn=${txn.transaction_id}`}
              className="btn-ghost text-xs py-1.5 px-3"
            >
              <Receipt size={12} /> Receipt
            </Link>
          )}
          <Link
            href={`/audit?txn=${txn.transaction_id}`}
            className="btn-ghost text-xs py-1.5 px-3"
          >
            <Eye size={12} /> Audit
          </Link>
        </div>
      </div>
    </motion.div>
  )
}

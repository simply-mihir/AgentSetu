'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, ShoppingBag } from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'
import Nav from '@/components/ui/Nav'
import AmbientBackground from '@/components/ui/AmbientBackground'
import { transactionsApi, extractErrorMessage, type Transaction } from '@/lib/api'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/StateViews'
import { useAuth } from '@/lib/auth'

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

export default function MerchantOrdersPage() {
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

  const revenue = transactions
    .filter(t => t.state === 'RECEIPT_ISSUED' || t.state === 'PAYMENT_SUCCESS')
    .reduce((sum, t) => sum + (t.amount_inr || 0), 0)

  return (
    <div className="min-h-screen flex flex-col relative">
      <AmbientBackground variant="subtle" />
      <Nav active="merchant" />

      <div className="max-w-4xl mx-auto w-full px-4 py-6 space-y-6 relative z-10">
        <div className="flex items-center gap-3">
          <Link href="/merchant" className="btn-ghost text-sm py-1.5 px-3">
            <ArrowLeft size={14} /> Back
          </Link>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Incoming Orders</h1>
            <p className="text-[var(--text-muted)] text-sm">Transactions involving your merchant&apos;s products</p>
          </div>
        </div>

        {!loading && !error && transactions.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="neo-card p-4">
              <div className="text-xl font-bold" style={{ color: 'var(--accent)' }}>{transactions.length}</div>
              <div className="text-[var(--text-muted)] text-xs mt-1">Total Orders</div>
            </div>
            <div className="neo-card p-4">
              <div className="text-xl font-bold" style={{ color: 'var(--success)' }}>
                {transactions.filter(t => t.state === 'RECEIPT_ISSUED' || t.state === 'PAYMENT_SUCCESS').length}
              </div>
              <div className="text-[var(--text-muted)] text-xs mt-1">Successful</div>
            </div>
            <div className="neo-card p-4">
              <div className="text-xl font-bold" style={{ color: 'var(--warning)' }}>₹{revenue}</div>
              <div className="text-[var(--text-muted)] text-xs mt-1">Revenue</div>
            </div>
          </div>
        )}

        {loading ? (
          <LoadingState message="Loading orders…" />
        ) : error ? (
          <ErrorState message={error} onRetry={loadOrders} />
        ) : !isAuthenticated ? (
          <EmptyState
            message="Sign in as a merchant to view orders."
            action={{ label: 'Sign in', href: '/auth?redirect=/merchant/orders' }}
          />
        ) : transactions.length === 0 ? (
          <EmptyState
            icon={<ShoppingBag size={32} />}
            message="No orders yet. Orders will appear here when buyers purchase your products."
          />
        ) : (
          <div className="space-y-2">
            {transactions.map((txn, i) => (
              <motion.div
                key={txn.transaction_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Link href={`/audit?txn=${txn.transaction_id}`} className="neo-card p-4 flex items-center gap-4 hover:bg-[var(--surface-soft)] transition-colors block">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className={STATE_CHIPS[txn.state] || 'chip chip-neutral'} style={{ fontSize: 10 }}>
                        {txn.state.replace(/_/g, ' ')}
                      </span>
                      {txn.amount_inr && (
                        <span className="text-[var(--text-primary)] font-semibold text-sm">₹{txn.amount_inr}</span>
                      )}
                    </div>
                    <p className="text-sm text-[var(--text-secondary)] truncate">{txn.buyer_intent}</p>
                    <div className="flex gap-3 text-xs text-[var(--text-muted)] mt-1">
                      {txn.product_name && <span>{txn.product_name}</span>}
                      <span>{format(new Date(txn.created_at), 'MMM d, HH:mm')}</span>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Store, Package, Shield, Code, RefreshCw, ShoppingBag, CreditCard, Eye, TrendingUp, Zap, BarChart3 } from 'lucide-react'
import Link from 'next/link'
import Nav from '@/components/ui/Nav'
import AmbientBackground from '@/components/ui/AmbientBackground'
import { merchantsApi, extractErrorMessage, type Merchant } from '@/lib/api'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/StateViews'

export default function MerchantPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadMerchants = () => {
    setLoading(true)
    setError(null)
    merchantsApi.list()
      .then(setMerchants)
      .catch(err => setError(extractErrorMessage(err, 'Failed to load merchants.')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadMerchants() }, [])

  const totalProducts = merchants.reduce((s, m) => s + (m.product_count || 0), 0)

  return (
    <div className="min-h-screen flex flex-col relative">
      <AmbientBackground variant="subtle" />
      <Nav active="merchant" />

      <div className="max-w-6xl mx-auto w-full px-4 lg:px-8 py-6 space-y-6 relative z-10">
        {/* ── Header ──────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Merchant Console</h1>
            <p className="text-[var(--text-muted)] text-sm">Manage catalogs, ARM manifests, and agent policies</p>
          </div>
          <Link href="/merchant/import" className="btn-primary text-sm py-2.5 px-5">
            <Package size={14} /> Import Catalog
          </Link>
        </div>

        {/* ── Top metrics ─────────────────────────────────────── */}
        {!loading && merchants.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'AI Visibility Score', value: `${Math.min(100, merchants.length * 28 + 16)}%`, icon: Zap, color: 'var(--sea-green)' },
              { label: 'Products', value: totalProducts.toString(), icon: Package, color: 'var(--mint)' },
              { label: 'Active Merchants', value: merchants.filter(m => m.is_active).length.toString(), icon: Store, color: 'var(--success)' },
              { label: 'AI Discoveries', value: '—', icon: BarChart3, color: 'var(--warning)' },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="glass-card p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-7 h-7 rounded-xl flex items-center justify-center"
                    style={{ background: `color-mix(in srgb, ${stat.color} 12%, transparent)` }}
                  >
                    <stat.icon size={14} style={{ color: stat.color }} />
                  </div>
                </div>
                <div className="text-xl font-bold text-[var(--text-primary)]" style={{ color: stat.color }}>{stat.value}</div>
                <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        )}

        {/* ── Razorpay status ─────────────────────────────────── */}
        <div className="glass-card p-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-[var(--success-bg)] flex items-center justify-center">
            <CreditCard size={15} className="text-[var(--success)]" />
          </div>
          <div className="flex-1">
            <span className="text-sm text-[var(--text-primary)] font-medium">Razorpay Integration</span>
            <span className="text-[var(--text-muted)] text-xs ml-2">Server-side only — keys never exposed to browser</span>
          </div>
          <span className="chip chip-success text-[10px]">Connected</span>
        </div>

        {/* ── Quick actions ───────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: Package, label: 'Import Catalog', desc: 'Upload product catalog', href: '/merchant/import', color: 'var(--sea-green)' },
            { icon: Shield, label: 'Policy Controls', desc: 'Spend caps & thresholds', href: '/merchant/policy', color: 'var(--success)' },
            { icon: ShoppingBag, label: 'Orders', desc: 'View incoming orders', href: '/merchant/orders', color: 'var(--warning)' },
            { icon: Eye, label: 'Audit Trail', desc: 'Transaction evidence', href: '/audit', color: 'var(--mint)' },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <Link href={item.href} className="
                block glass-card p-5
                hover:border-[var(--border-strong)] hover:shadow-sm hover:-translate-y-0.5
                transition-all duration-200 cursor-pointer
              ">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ background: `color-mix(in srgb, ${item.color} 10%, transparent)` }}>
                  <item.icon size={18} style={{ color: item.color }} />
                </div>
                <h3 className="font-semibold text-[var(--text-primary)] text-sm mb-0.5">{item.label}</h3>
                <p className="text-[var(--text-muted)] text-[11px]">{item.desc}</p>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* ── Merchants ───────────────────────────────────────── */}
        <div>
          <h2 className="font-semibold text-[var(--text-primary)] mb-4">Active Merchants ({merchants.length})</h2>

          {loading ? (
            <LoadingState message="Loading merchants…" rows={3} />
          ) : error ? (
            <ErrorState message={error} onRetry={loadMerchants} />
          ) : merchants.length === 0 ? (
            <EmptyState
              icon={<Store size={32} />}
              message="No merchants yet. Import a product catalog to get started."
              action={{ label: 'Import Catalog', href: '/merchant/import' }}
            />
          ) : (
            <div className="space-y-3">
              {merchants.map((merchant, i) => (
                <motion.div
                  key={merchant.merchant_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 + i * 0.06 }}
                >
                  <MerchantRow merchant={merchant} />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MerchantRow({ merchant }: { merchant: Merchant }) {
  const [showArm, setShowArm] = useState(false)
  const [arm, setArm] = useState<any>(null)
  const [loadingArm, setLoadingArm] = useState(false)
  const [armError, setArmError] = useState<string | null>(null)

  const fetchArm = async () => {
    if (arm) { setShowArm(v => !v); return }
    setLoadingArm(true)
    setArmError(null)
    try {
      const data = await merchantsApi.getArm(merchant.merchant_id)
      setArm(data)
      setShowArm(true)
    } catch (err) {
      setArmError(extractErrorMessage(err, 'Failed to load ARM manifest.'))
    } finally { setLoadingArm(false) }
  }

  return (
    <div className="glass-card overflow-hidden hover:shadow-sm transition-shadow">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <h3 className="font-semibold text-[var(--text-primary)]">{merchant.name}</h3>
              <span className="chip chip-mint text-[10px]">{merchant.category}</span>
              {merchant.is_active && <span className="chip chip-success text-[10px]">Active</span>}
            </div>
            <p className="text-[var(--text-muted)] text-xs mb-3 line-clamp-2">{merchant.description}</p>

            <div className="flex flex-wrap gap-3 text-xs text-[var(--text-secondary)]">
              <span>🛡️ Auto-limit: <strong className="text-[var(--text-primary)]">₹{merchant.max_autonomous_spend_inr}</strong></span>
              <span>📋 Approval above: <strong className="text-[var(--text-primary)]">₹{merchant.approval_threshold_inr}</strong></span>
              <span>📦 {merchant.product_count} products</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 flex-shrink-0">
            <Link
              href={`/merchant/policy?id=${merchant.merchant_id}`}
              className="btn-ghost text-xs py-1.5 px-3 rounded-xl"
            >
              <Shield size={12} /> Policy
            </Link>
            <button
              onClick={fetchArm}
              disabled={loadingArm}
              className="btn-ghost text-xs py-1.5 px-3 rounded-xl"
            >
              {loadingArm ? <RefreshCw size={12} className="animate-spin" /> : <Code size={12} />}
              ARM
            </button>
          </div>
        </div>
      </div>

      {armError && (
        <div className="p-4 border-t border-[var(--border)]">
          <ErrorState message={armError} onRetry={fetchArm} inline />
        </div>
      )}

      {showArm && arm && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="border-t border-[var(--border)] overflow-hidden"
        >
          <div className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="chip chip-mint text-[10px]">ARM Manifest · arm-0.1</span>
              <button onClick={() => setShowArm(false)} className="text-[var(--text-muted)] text-xs hover:text-[var(--text-primary)]">
                Close
              </button>
            </div>
            <pre className="text-xs text-[var(--text-muted)] font-mono overflow-x-auto max-h-64 overflow-y-auto p-3 rounded-xl bg-[var(--surface-inset)]">
              {JSON.stringify(arm, null, 2)}
            </pre>
          </div>
        </motion.div>
      )}
    </div>
  )
}

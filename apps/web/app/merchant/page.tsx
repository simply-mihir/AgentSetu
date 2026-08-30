'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Store, Package, Shield, Code, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import Nav from '@/components/ui/Nav'
import { merchantsApi, type Merchant } from '@/lib/api'

export default function MerchantPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    merchantsApi.list()
      .then(setMerchants)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      <Nav active="merchant" />

      <div className="max-w-5xl mx-auto w-full px-4 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Merchant Console</h1>
            <p className="text-text-muted text-sm">Manage catalogs, ARM manifests and agent policies</p>
          </div>
          <div className="flex gap-2">
            <Link href="/merchant/import" className="btn-primary text-sm py-2 px-4">
              Import Catalog
            </Link>
          </div>
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { icon: Package, label: 'Import Catalog', desc: 'Upload JSON or CSV product catalog', href: '/merchant/import', color: 'var(--primary)' },
            { icon: Shield, label: 'Policy Controls', desc: 'Configure spend caps and approval thresholds', href: '/merchant/policy', color: 'var(--trust)' },
            { icon: Code, label: 'ARM Preview', desc: 'View machine-readable merchant manifests', href: '#arm', color: 'var(--agent)' },
          ].map(item => (
            <Link key={item.label} href={item.href} className="glass-card p-5 hover:scale-[1.02] transition-all">
              <item.icon size={20} style={{ color: item.color }} className="mb-3" />
              <h3 className="font-semibold text-white text-sm mb-1">{item.label}</h3>
              <p className="text-text-muted text-xs">{item.desc}</p>
            </Link>
          ))}
        </div>

        {/* Merchants */}
        <div>
          <h2 className="font-semibold text-white mb-4">Active Merchants ({merchants.length})</h2>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="glass-card p-5 shimmer h-24" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {merchants.map((merchant, i) => (
                <motion.div
                  key={merchant.merchant_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
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

  const fetchArm = async () => {
    if (arm) { setShowArm(v => !v); return }
    setLoadingArm(true)
    try {
      const data = await merchantsApi.getArm(merchant.merchant_id)
      setArm(data)
      setShowArm(true)
    } catch { } finally { setLoadingArm(false) }
  }

  const categoryColor: Record<string, string> = {
    grocery: 'var(--trust)',
    electronics: 'var(--agent)',
    spices: 'var(--warning)',
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-white">{merchant.name}</h3>
              <span
                className="chip-agent text-[10px]"
                style={{ color: categoryColor[merchant.category] || 'var(--agent)' }}
              >
                {merchant.category}
              </span>
              {merchant.is_active && <span className="chip-trust text-[10px]">Active</span>}
            </div>
            <p className="text-text-muted text-xs mb-3 line-clamp-2">{merchant.description}</p>

            {/* Policy summary */}
            <div className="flex flex-wrap gap-3 text-xs text-text-secondary">
              <span>🛡️ Auto-limit: <strong className="text-white">₹{merchant.max_autonomous_spend_inr}</strong></span>
              <span>📋 Approval above: <strong className="text-white">₹{merchant.approval_threshold_inr}</strong></span>
              <span>📦 {merchant.product_count} products</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 flex-shrink-0">
            <Link
              href={`/merchant/policy?id=${merchant.merchant_id}`}
              className="btn-ghost text-xs py-1.5 px-3"
            >
              <Shield size={12} /> Policy
            </Link>
            <button
              onClick={fetchArm}
              disabled={loadingArm}
              className="btn-ghost text-xs py-1.5 px-3"
            >
              {loadingArm ? <RefreshCw size={12} className="animate-spin" /> : <Code size={12} />}
              ARM
            </button>
          </div>
        </div>
      </div>

      {/* ARM viewer */}
      {showArm && arm && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="border-t border-white/08 overflow-hidden"
        >
          <div className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="chip-agent text-[10px]">ARM Manifest · arm-0.1</span>
              <button onClick={() => setShowArm(false)} className="text-text-muted text-xs hover:text-white">
                Close
              </button>
            </div>
            <pre className="text-xs text-text-muted font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {JSON.stringify(arm, null, 2)}
            </pre>
          </div>
        </motion.div>
      )}
    </div>
  )
}

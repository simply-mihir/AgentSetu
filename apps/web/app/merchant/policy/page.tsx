'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Shield, Save, ArrowLeft, Plus, X, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import Nav from '@/components/ui/Nav'
import { merchantsApi, type Merchant } from '@/lib/api'

function PolicyContent() {
  const params = useSearchParams()
  const merchantId = params.get('id')
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [selected, setSelected] = useState<Merchant | null>(null)
  const [form, setForm] = useState({
    max_autonomous_spend_inr: 500,
    approval_threshold_inr: 1500,
    restricted_categories: [] as string[],
    refund_authority: 'human_only',
  })
  const [newCategory, setNewCategory] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    merchantsApi.list().then(list => {
      setMerchants(list)
      const m = merchantId ? list.find(m => m.merchant_id === merchantId) : list[0]
      if (m) selectMerchant(m)
    })
  }, [merchantId])

  const selectMerchant = (m: Merchant) => {
    setSelected(m)
    setForm({
      max_autonomous_spend_inr: m.max_autonomous_spend_inr,
      approval_threshold_inr: m.approval_threshold_inr,
      restricted_categories: m.restricted_categories || [],
      refund_authority: m.refund_authority,
    })
    setSaved(false)
  }

  const handleSave = async () => {
    if (!selected) return
    setSaving(true)
    try {
      await merchantsApi.updatePolicy(selected.merchant_id, form)
      toast.success('Policy updated and ARM regenerated')
      setSaved(true)
    } catch (err: any) {
      toast.error('Failed to save policy')
    } finally {
      setSaving(false)
    }
  }

  const addCategory = () => {
    if (!newCategory.trim()) return
    setForm(f => ({ ...f, restricted_categories: [...f.restricted_categories, newCategory.trim()] }))
    setNewCategory('')
  }

  const removeCategory = (cat: string) => {
    setForm(f => ({ ...f, restricted_categories: f.restricted_categories.filter(c => c !== cat) }))
  }

  return (
    <div className="max-w-3xl mx-auto w-full px-4 py-6 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/merchant" className="btn-ghost text-sm py-1.5 px-3">
          <ArrowLeft size={14} /> Back
        </Link>
        <div>
          <h1 className="text-xl font-bold text-white">Policy Controls</h1>
          <p className="text-text-muted text-sm">Configure agent spend authority and restrictions</p>
        </div>
      </div>

      {/* Merchant selector */}
      {merchants.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {merchants.map(m => (
            <button
              key={m.merchant_id}
              onClick={() => selectMerchant(m)}
              className={`px-3 py-1.5 rounded-xl text-sm transition-all ${
                selected?.merchant_id === m.merchant_id ? 'nav-active' : 'btn-ghost py-1.5'
              }`}
            >
              {m.name}
            </button>
          ))}
        </div>
      )}

      {selected && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
          {/* Policy summary */}
          <div className="glass-card p-5 border-agent/20">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="text-agent" size={18} />
              <span className="font-semibold text-white">{selected.name} · Agent Policy</span>
            </div>

            {/* Spend cap slider */}
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm text-text-secondary">Autonomous Spend Limit</label>
                  <span className="text-white font-semibold">₹{form.max_autonomous_spend_inr}</span>
                </div>
                <input
                  type="range"
                  min={100}
                  max={5000}
                  step={50}
                  value={form.max_autonomous_spend_inr}
                  onChange={e => setForm(f => ({ ...f, max_autonomous_spend_inr: +e.target.value }))}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-text-muted mt-1">
                  <span>₹100</span>
                  <span className="text-agent">Agent can transact without approval below this</span>
                  <span>₹5000</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm text-text-secondary">Approval Threshold</label>
                  <span className="text-white font-semibold">₹{form.approval_threshold_inr}</span>
                </div>
                <input
                  type="range"
                  min={form.max_autonomous_spend_inr}
                  max={10000}
                  step={100}
                  value={form.approval_threshold_inr}
                  onChange={e => setForm(f => ({ ...f, approval_threshold_inr: +e.target.value }))}
                  className="w-full accent-warning"
                />
                <div className="flex justify-between text-xs text-text-muted mt-1">
                  <span>₹{form.max_autonomous_spend_inr}</span>
                  <span className="text-warning">Buyer consent required above auto-limit, up to this</span>
                  <span>₹10000</span>
                </div>
              </div>

              {/* Visual policy zones */}
              <div className="mt-2 p-3 bg-white/03 rounded-xl">
                <div className="text-xs text-text-muted mb-2">Policy zones:</div>
                <div className="flex gap-2 text-xs flex-wrap">
                  <span className="chip-trust text-[10px]">Auto-approve: ₹0–₹{form.max_autonomous_spend_inr}</span>
                  <span className="chip-warning text-[10px]">Needs approval: ₹{form.max_autonomous_spend_inr}–₹{form.approval_threshold_inr}</span>
                  <span className="chip-danger text-[10px]">Blocked: &gt;₹{form.approval_threshold_inr}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Restricted categories */}
          <div className="glass-card p-5">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <AlertTriangle size={16} className="text-warning" />
              Restricted Categories
            </h3>
            <p className="text-text-muted text-xs mb-3">
              Products in these categories cannot be purchased autonomously — not even with buyer approval.
            </p>

            <div className="flex flex-wrap gap-2 mb-3">
              {form.restricted_categories.length === 0 ? (
                <span className="text-text-muted text-sm">No restrictions set</span>
              ) : (
                form.restricted_categories.map(cat => (
                  <span key={cat} className="chip-danger flex items-center gap-1">
                    {cat}
                    <button onClick={() => removeCategory(cat)} className="hover:opacity-70">
                      <X size={10} />
                    </button>
                  </span>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCategory()}
                placeholder="e.g. alcohol, tobacco, pharmacy"
                className="glass-input text-sm flex-1"
              />
              <button onClick={addCategory} className="btn-ghost text-sm py-2.5 px-4">
                <Plus size={14} />
              </button>
            </div>
          </div>

          {/* Refund authority */}
          <div className="glass-card p-5">
            <h3 className="font-semibold text-white mb-3">Refund Authority</h3>
            <div className="flex gap-3">
              {['human_only', 'agent_allowed'].map(opt => (
                <label key={opt} className={`flex items-center gap-2 cursor-pointer p-3 rounded-xl border transition-all flex-1 ${
                  form.refund_authority === opt
                    ? 'border-primary/40 bg-primary/10'
                    : 'border-white/10 hover:border-white/20'
                }`}>
                  <input
                    type="radio"
                    name="refund"
                    value={opt}
                    checked={form.refund_authority === opt}
                    onChange={() => setForm(f => ({ ...f, refund_authority: opt }))}
                    className="accent-primary"
                  />
                  <div>
                    <div className="text-sm text-white">{opt === 'human_only' ? 'Human Only' : 'Agent Allowed'}</div>
                    <div className="text-xs text-text-muted">
                      {opt === 'human_only' ? 'Refunds require human authorization' : 'Agent can initiate refunds'}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className={`${saved ? 'btn-trust' : 'btn-primary'} w-full justify-center py-3`}
          >
            <Save size={16} />
            {saving ? 'Saving…' : saved ? 'Saved! ARM Regenerated ✓' : 'Save Policy & Regenerate ARM'}
          </button>
        </motion.div>
      )}
    </div>
  )
}

export default function PolicyPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Nav active="merchant" />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-text-muted">Loading…</div>}>
        <PolicyContent />
      </Suspense>
    </div>
  )
}

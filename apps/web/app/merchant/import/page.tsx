'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, CheckCircle2, AlertCircle, ArrowLeft, FileJson } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import Nav from '@/components/ui/Nav'
import { merchantsApi } from '@/lib/api'

const EXAMPLE_CATALOG = {
  merchant_id: "my-store-01",
  merchant_name: "My Store",
  currency: "INR",
  description: "Quality products with fast delivery",
  category: "grocery",
  max_autonomous_spend_inr: 500,
  approval_threshold_inr: 1500,
  restricted_categories: [],
  products: [
    {
      product_id: "prod-001",
      name: "Product Name",
      category: "grocery",
      price_inr: 299,
      inventory_count: 50,
      availability: true,
      delivery_sla_days: [1, 3],
      return_policy: "7_days",
      merchant_rating: 4.5,
      description: "Product description here"
    }
  ]
}

export default function ImportPage() {
  const [json, setJson] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleImport = async () => {
    setError(null)
    let parsed
    try {
      parsed = JSON.parse(json)
    } catch {
      setError('Invalid JSON — please check your format')
      return
    }

    setLoading(true)
    try {
      const res = await merchantsApi.import(parsed)
      setResult(res)
      toast.success(`Imported ${res.products_imported} products for ${parsed.merchant_name}`)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const loadExample = () => {
    setJson(JSON.stringify(EXAMPLE_CATALOG, null, 2))
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Nav active="merchant" />

      <div className="max-w-3xl mx-auto w-full px-4 py-6 space-y-5">
        <div className="flex items-center gap-3">
          <Link href="/merchant" className="btn-ghost text-sm py-1.5 px-3">
            <ArrowLeft size={14} /> Back
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white">Import Catalog</h1>
            <p className="text-text-muted text-sm">Upload your product catalog to generate an ARM manifest</p>
          </div>
        </div>

        {/* Required fields */}
        <div className="glass-card p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Required Fields</h3>
          <div className="grid grid-cols-2 gap-2 text-xs text-text-muted">
            {[
              'merchant_id (unique string)',
              'merchant_name',
              'products[].product_id',
              'products[].name',
              'products[].price_inr (integer)',
              'products[].category',
            ].map(f => (
              <div key={f} className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-agent" />
                <span className="font-mono">{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* JSON editor */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm text-text-secondary">Catalog JSON</label>
            <button onClick={loadExample} className="text-xs text-agent hover:underline">
              Load example
            </button>
          </div>
          <textarea
            value={json}
            onChange={e => setJson(e.target.value)}
            placeholder={JSON.stringify(EXAMPLE_CATALOG, null, 2)}
            className="glass-input font-mono text-xs h-80 resize-y"
            spellCheck={false}
          />
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 p-3 bg-danger/10 border border-danger/25 rounded-xl text-danger text-sm">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Success */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-5 border-trust/25 bg-trust/5"
          >
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="text-trust" size={20} />
              <span className="font-semibold text-white">Import Successful</span>
            </div>
            <div className="space-y-2 text-sm">
              <p className="text-text-secondary">✅ {result.products_imported} products imported</p>
              <p className="text-text-secondary">🔧 ARM manifest generated: {result.arm_generated ? 'Yes' : 'No'}</p>
              {result.errors?.length > 0 && (
                <div>
                  <p className="text-warning">⚠️ {result.errors.length} rows had errors:</p>
                  {result.errors.map((e: any, i: number) => (
                    <p key={i} className="text-text-muted text-xs pl-4">• {e.product_id}: {e.error}</p>
                  ))}
                </div>
              )}
            </div>
            <div className="flex gap-2 mt-4">
              <Link href="/merchant" className="btn-primary text-sm py-2 px-4">
                View Merchant
              </Link>
            </div>
          </motion.div>
        )}

        <button
          onClick={handleImport}
          disabled={!json.trim() || loading}
          className="btn-primary w-full justify-center py-3"
        >
          {loading ? (
            <><span className="animate-spin">⚡</span> Generating ARM…</>
          ) : (
            <><Upload size={16} /> Import & Generate ARM</>
          )}
        </button>
      </div>
    </div>
  )
}

import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// ── Phase 24: Re-export error utilities for pages ──────────────────────────
export { extractErrorMessage, extractApiError, isApiErrorCode } from './errors'

// Types
export interface Merchant {
  merchant_id: string
  name: string
  currency: string
  description: string
  category: string
  max_autonomous_spend_inr: number
  approval_threshold_inr: number
  restricted_categories: string[]
  refund_authority: string
  is_active: boolean
  product_count?: number
  products?: Product[]
}

export interface Product {
  product_id: string
  merchant_id: string
  merchant_name?: string
  name: string
  category: string
  price_inr: number
  inventory_count: number
  availability: boolean
  delivery_sla_days_min?: number
  delivery_sla_days_max?: number
  delivery_sla_days?: number[]
  return_policy: string
  merchant_rating: number
  description: string
  max_autonomous_spend_inr?: number
  approval_threshold_inr?: number
  _score?: number
  _price_score?: number
  _delivery_score?: number
  _rating_score?: number
  _policy_fit?: number
}

export interface IntentResponse {
  transaction_id: string
  correlation_id: string
  state: string
  constraints: Record<string, any>
  candidates: Product[]
  total_found: number
  explanation: string
  no_results: boolean
  relaxation_hint?: string
}

export interface Transaction {
  transaction_id: string
  correlation_id: string
  state: string
  buyer_intent: string
  parsed_constraints: Record<string, any>
  merchant_id?: string
  merchant_name?: string
  product_id?: string
  product_name?: string
  amount_inr?: number
  policy_result?: string
  policy_reason_codes: string[]
  approval_id?: string
  approved_at?: string
  razorpay_payment_link_id?: string
  razorpay_payment_link_url?: string
  fingerprint?: string
  failure_reason?: string
  recovery_action?: string
  created_at: string
}

export interface PolicyResult {
  decision: 'ALLOW' | 'DENY' | 'NEEDS_APPROVAL'
  reason_codes: string[]
  effective_limit_inr?: number
  message: string
  requires_approval_above?: number
  can_proceed: boolean
  needs_approval: boolean
  is_denied: boolean
}

export interface AuditEvent {
  event_id: string
  transaction_id: string
  correlation_id?: string
  timestamp: string
  actor: string
  event_type: string
  input_summary?: Record<string, any>
  decision?: string
  reason_codes?: string[]
  policy_result?: string
  payment_reference?: string
  next_state?: string
  result?: string
  error_code?: string
}

// ── Merchants ─────────────────────────────────────────────────────────────────
export const merchantsApi = {
  list: () => api.get<Merchant[]>('/merchants/').then(r => r.data),
  get: (id: string) => api.get<Merchant>(`/merchants/${id}`).then(r => r.data),
  getArm: (id: string) => api.get(`/merchants/${id}/arm`).then(r => r.data),
  import: (data: any) => api.post('/merchants/import', data).then(r => r.data),
  updatePolicy: (id: string, policy: any) =>
    api.put(`/merchants/${id}/policy`, policy).then(r => r.data),
}

// ── Discovery ─────────────────────────────────────────────────────────────────
export const discoveryApi = {
  search: (params: {
    category?: string
    max_price?: number
    delivery_sla?: number
    keyword?: string
    merchant_id?: string
  }) => api.get('/discover/', { params }).then(r => r.data),
  categories: () => api.get('/discover/categories').then(r => r.data),
}

// ── Transactions ──────────────────────────────────────────────────────────────
export const transactionsApi = {
  processIntent: (message: string) =>
    api.post<IntentResponse>('/transactions/intent', {
      message,
    }).then(r => r.data),

  select: (transaction_id: string, product_id: string, merchant_id: string) =>
    api.post('/transactions/select', { transaction_id, product_id, merchant_id }).then(r => r.data),

  evaluatePolicy: (data: {
    merchant_id: string
    product_id: string
    amount_inr: number
    buyer_limit_inr?: number
    is_approved?: boolean
  }) => api.post<PolicyResult>('/transactions/policy/evaluate', data).then(r => r.data),

  // H1 FIX: approved_by is derived server-side from JWT, never sent by client
  approve: (transaction_id: string) =>
    api.post('/transactions/approve', { transaction_id }).then(r => r.data),

  get: (id: string) => api.get<Transaction>(`/transactions/${id}`).then(r => r.data),

  list: () => api.get<Transaction[]>('/transactions/').then(r => r.data),
}

// ── Payments ──────────────────────────────────────────────────────────────────
export const paymentsApi = {
  // C5 FIX: buyer_limit_inr removed — loaded server-side from BuyerProfile
  createPaymentLink: (transaction_id: string) =>
    api.post('/payments/payment-link', { transaction_id }).then(r => r.data),

  verify: (transaction_id: string) =>
    api.post(`/payments/verify/${transaction_id}`).then(r => r.data),

  getReceipt: (transaction_id: string) =>
    api.get(`/payments/receipt/${transaction_id}`).then(r => r.data),
}

// ── Audit ─────────────────────────────────────────────────────────────────────
export const auditApi = {
  getTimeline: (correlation_id: string) =>
    api.get(`/audit/${correlation_id}`).then(r => r.data),
  list: (limit = 50) =>
    api.get('/audit/', { params: { limit } }).then(r => r.data),
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }).then(r => r.data),
  signup: (data: { email: string; password: string; role: string; display_name?: string }) =>
    api.post('/auth/signup', data).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
}

export default api

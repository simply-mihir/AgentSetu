'use client'

import Link from 'next/link'
import { ShoppingBag, Store, FileText, LogOut, User } from 'lucide-react'
import { useAuth } from '@/lib/auth'

interface Props {
  active: 'buyer' | 'merchant' | 'audit'
}

const navItems = [
  { href: '/buyer', label: 'Buyer', icon: ShoppingBag, key: 'buyer' },
  { href: '/merchant', label: 'Merchant', icon: Store, key: 'merchant' },
  { href: '/audit', label: 'Audit', icon: FileText, key: 'audit' },
]

const ROLE_LABELS: Record<string, string> = {
  BUYER: 'Buyer',
  MERCHANT_OWNER: 'Merchant',
  MERCHANT_ADMIN: 'Admin',
  MERCHANT_OPERATOR: 'Operator',
  PLATFORM_ADMIN: 'Platform',
}

export default function Nav({ active }: Props) {
  const { user, isAuthenticated, isDemoMode, logout } = useAuth()

  return (
    <>
      {/* Demo mode banner */}
      {isDemoMode && (
        <div className="sticky top-0 z-[60] bg-gradient-to-r from-[var(--sea-green)] to-[var(--mint)] text-white text-center text-xs py-1.5 px-4 flex items-center justify-center gap-3">
          <span>🎮 Demo Mode — one-time access</span>
          <Link href="/auth" className="underline font-semibold">Sign up for full access →</Link>
        </div>
      )}
    <nav className="sticky top-0 z-50 bg-[var(--bg)]/80 backdrop-blur-xl border-b border-[var(--border)] px-4 lg:px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--mint)] to-[var(--sea-green)] flex items-center justify-center shadow-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-white">
              <circle cx="12" cy="12" r="5" fill="currentColor" opacity="0.9"/>
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" opacity="0.5"/>
              <circle cx="12" cy="12" r="11.5" stroke="currentColor" strokeWidth="1" opacity="0.25"/>
            </svg>
          </div>
          <span className="font-bold text-[var(--text-primary)] text-sm tracking-tight">AgentSetu</span>
          <span className="hidden md:inline text-[var(--text-muted)] text-xs">agentic commerce</span>
        </Link>

        {/* Nav items */}
        <div className="flex items-center gap-1">
          {navItems.map(item => {
            const Icon = item.icon
            const isActive = active === item.key
            return (
              <Link
                key={item.key}
                href={item.href}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-[var(--accent-soft)] text-[var(--accent)] shadow-sm'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-soft)]'
                }`}
              >
                <Icon size={15} />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            )
          })}

          {/* Auth section */}
          <div className="ml-3 pl-3 border-l border-[var(--border)] flex items-center gap-2">
            {isAuthenticated && user ? (
              <>
                <div className="hidden sm:flex items-center gap-2 text-xs">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--green-200)] to-[var(--teal-200)] flex items-center justify-center">
                    <User size={12} className="text-[var(--accent)]" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[var(--text-primary)] font-medium text-xs max-w-[100px] truncate leading-tight">
                      {user.display_name}
                    </span>
                    <span className="text-[var(--text-muted)] text-[10px] leading-tight">
                      {ROLE_LABELS[user.role] || user.role}
                    </span>
                  </div>
                </div>
                <button
                  onClick={logout}
                  className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-all text-xs"
                  title="Sign out"
                >
                  <LogOut size={13} />
                </button>
              </>
            ) : (
              <Link
                href="/auth"
                className="btn-primary text-xs py-2 px-4"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
    </>
  )
}

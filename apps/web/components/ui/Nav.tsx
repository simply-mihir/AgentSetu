'use client'

import Link from 'next/link'
import { ShoppingBag, Store, FileText, Zap, LogOut, User } from 'lucide-react'
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
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <nav className="sticky top-0 z-50 glass-card rounded-none border-x-0 border-t-0 px-4 py-3 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2 group">
        <div className="w-7 h-7 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
          <Zap size={14} className="text-primary" />
        </div>
        <span className="font-bold text-white text-sm">AgentSetu</span>
        <span className="hidden sm:inline text-text-muted text-xs">agentic commerce</span>
      </Link>

      <div className="flex items-center gap-1">
        {navItems.map(item => {
          const Icon = item.icon
          const isActive = active === item.key
          return (
            <Link
              key={item.key}
              href={item.href}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'nav-active'
                  : 'text-text-muted hover:text-white hover:bg-white/05'
              }`}
            >
              <Icon size={14} />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          )
        })}

        {/* Auth section */}
        <div className="ml-2 pl-2 border-l border-white/10 flex items-center gap-2">
          {isAuthenticated && user ? (
            <>
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-text-muted">
                <div className="w-5 h-5 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                  <User size={10} className="text-primary" />
                </div>
                <span className="max-w-[120px] truncate">{user.display_name}</span>
                <span className="chip-agent" style={{ fontSize: 9, padding: '1px 6px' }}>
                  {ROLE_LABELS[user.role] || user.role}
                </span>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-text-muted hover:text-danger hover:bg-danger/10 transition-all text-xs"
                title="Sign out"
              >
                <LogOut size={12} />
                <span className="hidden sm:inline">Out</span>
              </button>
            </>
          ) : (
            <Link
              href="/auth"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium text-primary hover:bg-primary/10 transition-all"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  )
}

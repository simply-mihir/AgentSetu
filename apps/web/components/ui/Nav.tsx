'use client'

import Link from 'next/link'
import { ShoppingBag, Store, FileText, Zap } from 'lucide-react'

interface Props {
  active: 'buyer' | 'merchant' | 'audit'
}

const navItems = [
  { href: '/buyer', label: 'Buyer', icon: ShoppingBag, key: 'buyer' },
  { href: '/merchant', label: 'Merchant', icon: Store, key: 'merchant' },
  { href: '/audit', label: 'Audit', icon: FileText, key: 'audit' },
]

export default function Nav({ active }: Props) {
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
      </div>
    </nav>
  )
}

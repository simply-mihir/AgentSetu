'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic } from 'lucide-react'

interface QuickAction {
  emoji: string
  label: string
  text: string
}

interface AgentComposerProps {
  onSubmit: (text: string) => void
  quickActions?: QuickAction[]
  placeholder?: string
  disabled?: boolean
  loading?: boolean
  className?: string
  showQuickActions?: boolean
  autoFocus?: boolean
}

const DEFAULT_QUICK_ACTIONS: QuickAction[] = [
  { emoji: '💰', label: 'Find the best price', text: 'Find the best price for organic honey' },
  { emoji: '🛒', label: 'Shop groceries', text: 'Buy turmeric powder under ₹200' },
  { emoji: '📦', label: 'Buy under ₹500', text: 'Buy organic honey under ₹500, deliver in 2 days' },
  { emoji: '🔍', label: 'Compare merchants', text: 'Compare USB-C cables across merchants' },
]

export default function AgentComposer({
  onSubmit,
  quickActions = DEFAULT_QUICK_ACTIONS,
  placeholder = 'Ask AgentSetu to find something...',
  disabled = false,
  loading = false,
  className = '',
  showQuickActions = true,
  autoFocus = false,
}: AgentComposerProps) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus()
  }, [autoFocus])

  const handleSubmit = () => {
    const text = input.trim()
    if (!text || disabled || loading) return
    onSubmit(text)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className={`w-full ${className}`}>
      {/* Quick action chips */}
      {showQuickActions && quickActions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4 justify-center">
          {quickActions.map(q => (
            <button
              key={q.label}
              onClick={() => onSubmit(q.text)}
              disabled={disabled || loading}
              className="
                flex items-center gap-1.5 px-4 py-2
                bg-[var(--surface)] border border-[var(--border)]
                rounded-full text-xs font-medium text-[var(--text-secondary)]
                hover:border-[var(--accent)]/30 hover:text-[var(--accent)]
                hover:bg-[var(--accent-soft)] hover:shadow-sm
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              <span>{q.emoji}</span>
              <span>{q.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Composer input */}
      <div className="
        relative flex items-end gap-2 p-2 pl-4
        bg-[var(--surface)] border border-[var(--border)]
        rounded-2xl shadow-neo
        transition-all duration-200
        focus-within:border-[var(--accent)]/30
        focus-within:shadow-[0_0_0_3px_var(--accent-ring),var(--shadow-neo)]
      ">
        {/* Left icon */}
        <button
          className="
            flex-shrink-0 w-8 h-8 flex items-center justify-center
            rounded-xl text-[var(--text-muted)]
            hover:text-[var(--text-secondary)] hover:bg-[var(--surface-soft)]
            transition-colors mb-0.5
          "
          aria-label="Attach"
          tabIndex={-1}
        >
          <Paperclip size={16} />
        </button>

        {/* Input */}
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || loading}
          rows={1}
          className="
            flex-1 resize-none bg-transparent
            text-sm text-[var(--text-primary)]
            placeholder:text-[var(--text-muted)]
            outline-none py-2 leading-relaxed
            max-h-32 min-h-[36px]
            disabled:opacity-50
          "
          style={{
            height: 'auto',
            overflowY: input.split('\n').length > 3 ? 'auto' : 'hidden',
          }}
          onInput={(e) => {
            const el = e.target as HTMLTextAreaElement
            el.style.height = 'auto'
            el.style.height = Math.min(el.scrollHeight, 128) + 'px'
          }}
        />

        {/* Right icons */}
        <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
          <button
            className="
              w-8 h-8 flex items-center justify-center
              rounded-xl text-[var(--text-muted)]
              hover:text-[var(--text-secondary)] hover:bg-[var(--surface-soft)]
              transition-colors
            "
            aria-label="Voice"
            tabIndex={-1}
          >
            <Mic size={16} />
          </button>

          <button
            onClick={handleSubmit}
            disabled={!input.trim() || disabled || loading}
            className="
              w-9 h-9 flex items-center justify-center
              rounded-xl
              bg-gradient-to-br from-[var(--sea-green)] to-[var(--mint)]
              text-white shadow-sm
              hover:shadow-[var(--shadow-glow-accent)]
              hover:scale-105
              active:scale-95
              transition-all duration-200
              disabled:opacity-30 disabled:hover:scale-100 disabled:hover:shadow-sm
            "
            aria-label="Send"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send size={15} />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

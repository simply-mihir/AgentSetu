import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── Surfaces ────────────────────────────────────────
        bg: {
          DEFAULT: 'var(--bg)',
          warm: 'var(--bg-warm)',
        },
        surface: {
          DEFAULT: 'var(--surface)',
          raised: 'var(--surface-raised)',
          soft: 'var(--surface-soft)',
          muted: 'var(--surface-muted)',
          inset: 'var(--surface-inset)',
          glass: 'var(--surface-glass)',
        },

        // ── Green / Mint ────────────────────────────────────
        green: {
          50: 'var(--green-50)',
          100: 'var(--green-100)',
          200: 'var(--green-200)',
          300: 'var(--green-300)',
          400: 'var(--green-400)',
          500: 'var(--green-500)',
          600: 'var(--green-600)',
        },
        teal: {
          50: 'var(--teal-50)',
          100: 'var(--teal-100)',
          200: 'var(--teal-200)',
          300: 'var(--teal-300)',
          400: 'var(--teal-400)',
          500: 'var(--teal-500)',
          600: 'var(--teal-600)',
        },

        // ── Accent ──────────────────────────────────────────
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          soft: 'var(--accent-soft)',
        },

        // ── Semantic ────────────────────────────────────────
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger: 'var(--danger)',
        info: 'var(--info)',

        // ── Text ────────────────────────────────────────────
        tx: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },

        // ── Border ──────────────────────────────────────────
        bdr: {
          DEFAULT: 'var(--border)',
          strong: 'var(--border-strong)',
        },

        // Legacy aliases
        canvas: { DEFAULT: 'var(--bg)', light: 'var(--bg-warm)' },
        primary: 'var(--accent)',
        trust: 'var(--success)',
        agent: 'var(--green-500)',
        // Keep pink/lilac aliases pointing to green equivalents
        pink: {
          50: 'var(--green-50)',
          100: 'var(--green-100)',
          200: 'var(--green-200)',
          300: 'var(--green-300)',
          400: 'var(--green-400)',
          500: 'var(--green-500)',
          600: 'var(--green-600)',
        },
        lilac: {
          50: 'var(--teal-50)',
          100: 'var(--teal-100)',
          200: 'var(--teal-200)',
          300: 'var(--teal-300)',
          400: 'var(--teal-400)',
          500: 'var(--teal-500)',
          600: 'var(--teal-600)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        border: 'var(--border)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'sm':  '10px',
        'md':  '16px',
        'lg':  '22px',
        'xl':  '28px',
        '2xl': '16px',
        '3xl': '22px',
        '4xl': '28px',
      },
      boxShadow: {
        neo: 'var(--shadow-neo)',
        'neo-inset': 'var(--shadow-neo-inset)',
        'neo-pressed': 'var(--shadow-neo-pressed)',
        glass: 'var(--shadow-md)',
        glow: 'var(--shadow-glow)',
        'glow-accent': 'var(--shadow-glow-accent)',
        'glow-trust': '0 0 30px rgba(42, 168, 118, 0.20)',
        soft: 'var(--shadow-soft)',
        liquid: 'var(--shadow-liquid)',
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'pulse-slow': 'pulse 3s infinite',
        shimmer: 'shimmer 1.5s infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow-pulse': 'glowPulse 4s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        glowPulse: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config

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
        // AgentSetu Design System
        canvas: {
          DEFAULT: '#070B14',
          light: '#0F1524',
        },
        glass: 'rgba(255,255,255,0.08)',
        primary: '#6C63FF',
        trust: '#35D07F',
        agent: '#3DD6D0',
        warning: '#FFB454',
        danger: '#FF6675',
        text: {
          primary: '#F8FAFC',
          secondary: '#AEB7C8',
          muted: '#6B7A99',
        },
        border: 'rgba(255,255,255,0.10)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '28px',
      },
      boxShadow: {
        glass: '0 12px 40px rgba(0,0,0,0.24)',
        glow: '0 0 40px rgba(108,99,255,0.15)',
        'glow-trust': '0 0 30px rgba(53,208,127,0.20)',
      },
      backdropBlur: {
        glass: '20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'pulse-slow': 'pulse 3s infinite',
        shimmer: 'shimmer 1.5s infinite',
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
      },
    },
  },
  plugins: [],
}

export default config

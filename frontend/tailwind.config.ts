import type { Config } from 'tailwindcss'

/**
 * Design tokens do mockup aprovado (manutencao-veicular-ultra-mockup.html)
 * Paleta navy/sky da logo Napel + Archivo (display) / Inter (corpo).
 * Aliases legados (naval/noite/ceu/gelo) mantidos para páginas ainda não migradas.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#06283d', 900: '#082E49', 800: '#0A3C5F',
          700: '#0F405F', 500: '#1d6489',
        },
        sky: {
          700: '#2f7cbf', 600: '#3f8bcf', 500: '#74A9D7',
          400: '#93bce0', 300: '#bcd7ec', bg: '#EAF3FB',
        },
        steel: '#7DA4C6',
        ink: {
          50: '#F6FBFC', 100: '#EBF7FA', 200: '#D6E7F1', 300: '#B5D4E8',
          400: '#93a7b6', 500: '#62798c', 600: '#33495b', 700: '#33495b',
          800: '#0c2433', 900: '#0c2433',
        },
        line: { DEFAULT: '#E8EFF4', strong: '#D6E4EE' },
        'page-bg': '#F4F8FB',
        ok:     { DEFAULT: '#10B981', bg: '#ECFDF5', fg: '#047857' },
        warn:   { DEFAULT: '#F59E0B', bg: '#FEF6E7', fg: '#9a6400' },
        err:    { DEFAULT: '#EF4444', bg: '#FEF2F2', fg: '#c1352f' },
        // aliases legados
        naval: '#0A3C5F', noite: '#06283d', ceu: '#74A9D7',
        'ceu-claro': '#bcd7ec', gelo: '#EAF3FB',
        border: { DEFAULT: '#E8EFF4', strong: '#D6E4EE' },
        success: { DEFAULT: '#10B981', fg: '#047857', bg: '#ECFDF5' },
        danger:  { DEFAULT: '#EF4444', fg: '#c1352f', bg: '#FEF2F2' },
        info:    { DEFAULT: '#74A9D7', fg: '#0A3C5F', bg: '#EAF3FB' },
      },
      fontFamily: {
        display: ['Archivo', 'sans-serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(8,46,73,.04), 0 8px 24px -14px rgba(8,46,73,.22)',
        lift: '0 12px 32px -18px rgba(8,46,73,.32)',
        sm: '0 1px 2px rgba(4,44,72,0.06)',
        md: '0 4px 12px rgba(4,44,72,0.08)',
      },
      borderRadius: { sm: '6px', md: '10px', lg: '12px', xl: '16px' },
    },
  },
  plugins: [],
} satisfies Config

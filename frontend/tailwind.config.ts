import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand Napel (Design System oficial)
        naval: '#113C58',
        noite: '#042C48',
        ceu: '#7DA4C6',
        'ceu-claro': '#B5D4E8',
        gelo: '#EBF7FA',
        'page-bg': '#FAFCFD',
        border: { DEFAULT: '#E4EEF3', strong: '#CFDEE7' },
        // Escala ink
        ink: {
          50:  '#F6FBFC', 100: '#EBF7FA', 200: '#D6E7F1',
          300: '#B5D4E8', 400: '#7DA4C6', 500: '#3D6889',
          600: '#27557A', 700: '#113C58', 800: '#0A3450', 900: '#042C48',
        },
        // Semânticas
        success: { DEFAULT: '#10B981', fg: '#065F46', bg: '#D1FAE5' },
        warn:    { DEFAULT: '#F59E0B', fg: '#92400E', bg: '#FEF3C7' },
        danger:  { DEFAULT: '#EF4444', fg: '#991B1B', bg: '#FEE2E2' },
        info:    { DEFAULT: '#7DA4C6', fg: '#113C58', bg: '#EBF7FA' },
        // Acentos parceiros
        'ml-amarelo': '#FFE600',
        'ml-azul':    '#3483FA',
      },
      fontFamily: {
        sans: ['Saira', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        tiny:      ['10px',   '14px'],
        caption:   ['11px',   '16px'],
        label:     ['12px',   '16px'],
        'body-sm': ['12.5px', '18px'],
        body:      ['13.5px', '20px'],
        'body-lg': ['15px',   '22px'],
        h3:        ['16px',   '22px'],
        h2:        ['18px',   '24px'],
        h1:        ['24px',   '30px'],
      },
      borderRadius: {
        sm: '6px', md: '8px', lg: '12px', xl: '16px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(4,44,72,0.06), 0 1px 3px rgba(4,44,72,0.04)',
        md: '0 4px 12px rgba(4,44,72,0.08), 0 2px 4px rgba(4,44,72,0.04)',
        lg: '0 10px 30px rgba(4,44,72,0.12), 0 4px 10px rgba(4,44,72,0.06)',
      },
    },
  },
  plugins: [],
} satisfies Config

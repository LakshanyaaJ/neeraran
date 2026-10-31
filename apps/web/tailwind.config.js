/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        sky: {
          50: '#EAF3FD',
          100: '#D9E9FB',
          300: '#8FC0EE',
          500: '#3A8FDA',
          700: '#1E5FA8',
        },
        ink: {
          900: '#0F2236',
          600: '#4A5F75',
          300: '#94A7B8',
        },
        mist: '#F2F6FA',
        aqua: '#2FB8AA',
        leaf: '#4CBF86',
        amber: '#F2A33A',
        coral: '#E5594F',
        night: {
          bg: '#0B1622',
          card: 'rgba(20, 36, 54, 0.65)',
          border: 'rgba(255, 255, 255, 0.08)',
        }
      },
      fontFamily: {
        sans: ['Onest', 'sans-serif'],
        tamil: ['"Anek Tamil"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '22px',
        btn: '12px',
        pill: '999px',
      },
      backdropBlur: {
        glass: '18px',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(30, 95, 168, 0.07)',
        'glass-hover': '0 12px 40px 0 rgba(30, 95, 168, 0.12)',
        'hero-card': '0 24px 64px -12px rgba(15, 34, 54, 0.12)',
      }
    },
  },
  plugins: [],
}

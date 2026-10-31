/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    // Replaces the entire default Tailwind color palette to prevent non-token colors
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: 'var(--color-white)',
      black: 'var(--color-black)',
      sky: {
        50: 'var(--color-sky-50)',
        100: 'var(--color-sky-100)',
        300: 'var(--color-sky-300)',
        500: 'var(--color-sky-500)',
        700: 'var(--color-sky-700)',
      },
      ink: {
        900: 'var(--color-ink-900)',
        600: 'var(--color-ink-600)',
      },
      mist: 'var(--color-mist)',
      aqua: 'var(--color-aqua)',
      leaf: 'var(--color-leaf)',
      amber: 'var(--color-amber)',
      coral: 'var(--color-coral)',
    },
    borderRadius: {
      none: '0px',
      sm: '4px',
      DEFAULT: '8px',
      md: '12px',
      lg: '16px',
      btn: 'var(--radius-btn)',
      card: 'var(--radius-card)',
      pill: 'var(--radius-pill)',
      full: '9999px',
    },
    fontFamily: {
      sans: ['var(--font-sans)', 'sans-serif'],
      tamil: ['var(--font-tamil)', 'sans-serif'],
      mono: ['var(--font-mono)', 'monospace'],
    },
    boxShadow: {
      none: 'none',
      sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      glass: 'var(--shadow-glass)',
      'glass-hover': 'var(--shadow-glass-hover)',
      'hero-card': 'var(--shadow-hero-card)',
    },
    backdropBlur: {
      none: '0',
      sm: '4px',
      glass: 'var(--blur-glass)',
    },
  },
  plugins: [],
}

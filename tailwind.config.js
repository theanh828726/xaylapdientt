/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#12201C',
        brand: { DEFAULT: '#0F5C55', light: '#2E8C7E', soft: '#DCEBE8' },
        amber2: '#E8A317',
        danger: '#A1281A',
        paper: '#F3F4F0',
      },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

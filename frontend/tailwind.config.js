/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // INDUSTRIA-X design system colours
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          500: '#3b82d4',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        surface: '#f7f8fa',
        border: '#e5e7eb',
        muted: '#57606a',
        accent: '#3b82d4',
        // Risk level colours
        risk: {
          low:    '#1a7f4b',
          medium: '#b45309',
          high:   '#b91c1c',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Code', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

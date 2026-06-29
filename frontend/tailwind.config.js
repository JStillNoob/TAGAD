/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js}',
  ],
  theme: {
    extend: {
      colors: {
        brand:          '#465FF1',
        'brand-light':  '#EEF2FF',
        navy:           '#1D2A3B',
        teal:           '#2EC4B6',
        'orange-brand': '#FFB703',
        danger:         '#EF476F',
        'bg-main':      '#F9FAFB',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

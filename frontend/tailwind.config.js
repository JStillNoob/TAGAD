/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js}',
  ],
  theme: {
    extend: {
      colors: {
        brand:          'var(--primary)',
        'brand-light':  'var(--primary-tint)',
        navy:           'var(--text)',
        teal:           'var(--primary-dark)',
        'orange-brand': 'var(--alert)',
        danger:         'var(--alert)',
        'bg-main':      'var(--bg)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

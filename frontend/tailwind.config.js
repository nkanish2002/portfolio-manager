/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: '#000000',
        'off-white': '#E2E8F0',
        'slate-dark': '#1E293B',
        'gray-900': '#111827',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eefcf6',
          100: '#d7f7e9',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          900: '#064e3b',
        }
      }
    },
  },
  plugins: [],
}

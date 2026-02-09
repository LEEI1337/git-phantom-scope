/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'gps-bg': '#0D1117',
        'gps-surface': '#161B22',
        'gps-border': '#30363D',
        'gps-text': '#C9D1D9',
        'gps-text-secondary': '#8B949E',
        'gps-accent': '#58A6FF',
        'gps-green': '#238636',
        'gps-purple': '#8B5CF6',
        'gps-orange': '#F97316',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

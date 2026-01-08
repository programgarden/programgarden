/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Node category colors
        'node-infra': '#6366f1',
        'node-realtime': '#8b5cf6',
        'node-data': '#3b82f6',
        'node-symbol': '#06b6d4',
        'node-trigger': '#14b8a6',
        'node-condition': '#f59e0b',
        'node-risk': '#ef4444',
        'node-order': '#10b981',
        'node-event': '#f97316',
        'node-display': '#ec4899',
        'node-group': '#6b7280',
        'node-backtest': '#8b5cf6',
        'node-job': '#64748b',
        'node-calculation': '#0ea5e9',
      },
    },
  },
  plugins: [],
}

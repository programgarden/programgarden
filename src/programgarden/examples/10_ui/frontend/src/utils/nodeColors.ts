// Node categories and their colors
export const CATEGORY_COLORS: Record<string, string> = {
  infra: '#6366f1',      // indigo
  realtime: '#8b5cf6',   // violet
  data: '#3b82f6',       // blue
  symbol: '#06b6d4',     // cyan
  trigger: '#14b8a6',    // teal
  condition: '#f59e0b',  // amber
  risk: '#ef4444',       // red
  order: '#10b981',      // emerald
  event: '#f97316',      // orange
  display: '#ec4899',    // pink
  group: '#6b7280',      // gray
  backtest: '#8b5cf6',   // violet
  job: '#64748b',        // slate
  calculation: '#0ea5e9', // sky
};

export const CATEGORY_ICONS: Record<string, string> = {
  infra: '🏗️',
  realtime: '📡',
  data: '📊',
  symbol: '🎯',
  trigger: '⏰',
  condition: '🔀',
  risk: '🛡️',
  order: '📦',
  event: '🔔',
  display: '📺',
  group: '📁',
  backtest: '📈',
  job: '⚙️',
  calculation: '🔢',
};

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || '#6b7280';
}

export function getCategoryIcon(category: string): string {
  return CATEGORY_ICONS[category] || '📦';
}

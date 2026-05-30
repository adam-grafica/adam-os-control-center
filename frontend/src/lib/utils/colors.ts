/**
 * Color utility functions for the ADAM OS Dashboard.
 */

const HEALTH_COLORS: Record<string, string> = {
  high: '#10b981',
  medium: '#f59e0b',
  low: '#ef4444'
};

const STATUS_COLORS: Record<string, string> = {
  healthy: '#10b981',
  degraded: '#f59e0b',
  critical: '#ef4444',
  offline: '#6b7280'
};

const MOOD_COLORS: Record<string, string> = {
  calm: '#10b981',
  alert: '#f59e0b',
  stressed: '#ef4444',
  resting: '#3b82f6',
  dreaming: '#8b5cf6',
  focused: '#06b6d4',
  unknown: '#9ca3af'
};

const MOOD_EMOJIS: Record<string, string> = {
  calm: '😌',
  alert: '⚠️',
  stressed: '😰',
  resting: '😴',
  dreaming: '💭',
  focused: '🎯',
  happy: '😊',
  curious: '🤔',
  tired: '😫',
  unknown: '❓'
};

/**
 * Get hex color for a health value (0-100).
 * Green > 80, Amber > 50, Red < 50.
 */
export function getHealthColor(health: number): string {
  if (health >= 80) return HEALTH_COLORS.high;
  if (health >= 50) return HEALTH_COLORS.medium;
  return HEALTH_COLORS.low;
}

/**
 * Get hex color for an organ status string.
 */
export function getStatusColor(status: string): string {
  const key = status.toLowerCase();
  return STATUS_COLORS[key] ?? STATUS_COLORS.offline;
}

/**
 * Get hex color for a mood string.
 */
export function getMoodColor(mood: string): string {
  const key = mood.toLowerCase();
  return MOOD_COLORS[key] ?? MOOD_COLORS.unknown;
}

/**
 * Get emoji for a mood string.
 */
export function getMoodEmoji(mood: string): string {
  const key = mood.toLowerCase();
  return MOOD_EMOJIS[key] ?? MOOD_EMOJIS.unknown;
}

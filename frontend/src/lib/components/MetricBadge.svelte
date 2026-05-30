<script lang="ts">
  /**
   * MetricBadge - Compact single line metric display.
   * Props:
   *   label - metric label text
   *   value - metric value
   *   color (optional) - CSS color string
   *   icon (optional) - emoji icon prefix
   */
  let { label = '', value = '', color = 'var(--color-text-secondary)', icon = '' }: {
    label: string;
    value: string | number;
    color?: string;
    icon?: string;
  } = $props();
</script>

<div class="metric-badge" style="--badge-color: {color};">
  {#if icon}
    <span class="metric-icon">{icon}</span>
  {/if}
  <span class="metric-label">{label}</span>
  <span class="metric-value">{value}</span>
</div>

<style>
  .metric-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--color-bg-tertiary, #111827);
    border: 1px solid var(--color-border, #374151);
    border-radius: var(--radius-md, 8px);
    font-size: 0.8125rem;
    line-height: 1.4;
    white-space: nowrap;
    transition: background var(--transition-fast, 150ms ease);
  }

  .metric-badge:hover {
    background: var(--color-bg-secondary, #1f2937);
  }

  .metric-icon {
    font-size: 0.875rem;
    line-height: 1;
  }

  .metric-label {
    color: var(--color-text-tertiary, #9ca3af);
    font-weight: 500;
  }

  .metric-value {
    color: var(--badge-color, var(--color-text-secondary, #e5e7eb));
    font-family: var(--font-mono, monospace);
    font-weight: 600;
    letter-spacing: -0.01em;
  }
</style>

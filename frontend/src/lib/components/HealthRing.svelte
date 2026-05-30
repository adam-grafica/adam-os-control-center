<script lang="ts">
  /**
   * HealthRing - SVG circular health indicator.
   * Props:
   *   health (0-100) - health percentage
   *   size (default 80) - diameter in pixels
   *   strokeWidth (default 6) - ring thickness
   */
  import { getHealthColor } from '$lib/utils/colors';

  let { health = 100, size = 80, strokeWidth = 6 }: {
    health?: number;
    size?: number;
    strokeWidth?: number;
  } = $props();

  // Clamp health to 0-100
  const clampedHealth = $derived(Math.max(0, Math.min(100, health)));

  // SVG ring calculations
  const radius = $derived((size - strokeWidth) / 2);
  const circumference = $derived(2 * Math.PI * radius);
  const offset = $derived(circumference - (clampedHealth / 100) * circumference);
  const color = $derived(getHealthColor(clampedHealth));
  const center = $derived(size / 2);

  // Determine if we should show the text (only for rings >= 60px)
  const showText = $derived(size >= 60);
  // Font size scales with ring size
  const fontSize = $derived(Math.max(10, Math.floor(size * 0.2)));
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 {size} {size}"
  class="health-ring"
  role="progressbar"
  aria-valuenow={clampedHealth}
  aria-valuemin={0}
  aria-valuemax={100}
>
  <!-- Background track -->
  <circle
    cx={center}
    cy={center}
    r={radius}
    fill="none"
    stroke="var(--color-bg-tertiary, #111827)"
    stroke-width={strokeWidth}
  />
  <!-- Animated arc -->
  <circle
    cx={center}
    cy={center}
    r={radius}
    fill="none"
    stroke={color}
    stroke-width={strokeWidth}
    stroke-linecap="round"
    stroke-dasharray={circumference}
    stroke-dashoffset={offset}
    transform="rotate(-90, {center}, {center})"
    class="health-ring-arc"
    style="transition: stroke-dashoffset 0.8s ease, stroke 0.5s ease;"
  />
  <!-- Center text -->
  {#if showText}
    <text
      x={center}
      y={center}
      text-anchor="middle"
      dominant-baseline="central"
      fill="var(--color-text-primary, #f3f4f6)"
      font-size={fontSize}
      font-family="var(--font-mono, monospace)"
      font-weight="600"
      class="health-ring-text"
    >
      {clampedHealth}
    </text>
  {/if}
</svg>

<style>
  .health-ring {
    display: inline-block;
    vertical-align: middle;
  }

  .health-ring-arc {
    filter: drop-shadow(0 0 4px currentColor);
  }

  .health-ring-text {
    user-select: none;
  }
</style>

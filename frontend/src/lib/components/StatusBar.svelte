<script lang="ts">
  /**
   * StatusBar - Bottom status bar showing organism state.
   * Displays mood (with emoji + color), health %, active threats, current mode, last SSE update.
   * Fixed bottom. Dark glass effect.
   */
  import { health, mood, mode, activeThreatCount, timestamp } from '$lib/stores/organism';
  import { connected, lastUpdate } from '$lib/stores/sse';
  import HealthRing from './HealthRing.svelte';
  import { getMoodColor, getMoodEmoji } from '$lib/utils/colors';
  import { formatDate, capitalizeFirst } from '$lib/utils/format';

  // Reactive state from stores
  let healthVal: number = $state(100);
  let moodVal: string = $state('unknown');
  let modeVal: string = $state('idle');
  let threatCount: number = $state(0);
  let lastUpdateVal: Date | null = $state(null);
  let isConnected: boolean = $state(false);
  let tsVal: string = $state('');

  $effect(() => {
    const unsubs: (() => void)[] = [];
    unsubs.push(health.subscribe((v) => { healthVal = v; }));
    unsubs.push(mood.subscribe((v) => { moodVal = v; }));
    unsubs.push(mode.subscribe((v) => { modeVal = v; }));
    unsubs.push(activeThreatCount.subscribe((v) => { threatCount = v; }));
    unsubs.push(timestamp.subscribe((v) => { tsVal = v; }));
    unsubs.push(lastUpdate.subscribe((v) => { lastUpdateVal = v; }));
    unsubs.push(connected.subscribe((v) => { isConnected = v; }));
    return () => unsubs.forEach((fn) => fn());
  });

  const moodColor = $derived(getMoodColor(moodVal));
  const moodEmoji = $derived(getMoodEmoji(moodVal));
  const lastUpdateStr = $derived(lastUpdateVal ? formatDate(lastUpdateVal.toISOString()) : '---');
  const moodLabel = $derived(capitalizeFirst(moodVal));
</script>

<footer class="status-bar glass">
  <div class="status-bar-inner">
    <!-- Left section: Organism state -->
    <div class="status-section status-organism">
      <div class="status-mood" style="--mood-color: {moodColor};">
        <span class="mood-emoji">{moodEmoji}</span>
        <span class="mood-label">{moodLabel}</span>
      </div>
      <div class="status-divider"></div>
      <div class="status-health">
        <HealthRing health={healthVal} size={24} strokeWidth={3} />
        <span class="health-value">{Math.round(healthVal)}%</span>
      </div>
    </div>

    <!-- Center section: Mode and threats -->
    <div class="status-section status-center">
      <div class="status-mode">
        <span class="status-label">Mode</span>
        <span class="status-value">{capitalizeFirst(modeVal)}</span>
      </div>
      {#if threatCount > 0}
        <div class="status-threats">
          <span class="status-label">Threats</span>
          <span class="status-value threat-count">{threatCount}</span>
        </div>
      {:else}
        <div class="status-threats status-safe">
          <span class="status-label">Status</span>
          <span class="status-value safe-text">All Clear</span>
        </div>
      {/if}
    </div>

    <!-- Right section: Connection info -->
    <div class="status-section status-right">
      <div class="status-connection">
        <span
          class="connection-dot"
          class:connected={isConnected}
          class:disconnected={!isConnected}
        ></span>
        <span class="connection-text">{isConnected ? 'Live' : 'Disconnected'}</span>
      </div>
      {#if lastUpdateVal}
        <div class="status-update">
          <span class="status-label">Updated</span>
          <span class="status-value update-time">{lastUpdateStr}</span>
        </div>
      {/if}
    </div>
  </div>
</footer>

<style>
  .status-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    padding: 8px 20px;
    border-radius: 0;
    border-top: 1px solid var(--glass-border);
    border-left: none;
    border-right: none;
    border-bottom: none;
  }

  .status-bar-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    max-width: 100%;
    gap: 16px;
  }

  .status-section {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .status-divider {
    width: 1px;
    height: 20px;
    background: var(--color-border, #374151);
  }

  /* Organism section */
  .status-mood {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 10px 2px 6px;
    border-radius: 20px;
    background: color-mix(in srgb, var(--mood-color, #9ca3af) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--mood-color, #9ca3af) 25%, transparent);
  }

  .mood-emoji {
    font-size: 1.1rem;
    line-height: 1;
  }

  .mood-label {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--mood-color, var(--color-text-primary));
  }

  .status-health {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .health-value {
    font-size: 0.875rem;
    font-weight: 700;
    font-family: var(--font-mono, monospace);
    color: var(--color-text-primary);
  }

  /* Center section */
  .status-center {
    gap: 16px;
  }

  .status-mode,
  .status-threats {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .status-label {
    font-size: 0.6875rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-tertiary, #9ca3af);
  }

  .status-value {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--color-text-primary, #f3f4f6);
  }

  .threat-count {
    color: var(--color-danger, #ef4444);
  }

  .safe-text {
    color: var(--color-success, #10b981);
  }

  .status-safe .status-value {
    color: var(--color-success, #10b981);
  }

  /* Right section */
  .status-right {
    gap: 12px;
  }

  .status-connection {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .connection-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    transition: background-color 0.3s ease;
  }

  .connection-dot.connected {
    background-color: var(--color-success, #10b981);
    box-shadow: 0 0 6px var(--color-success, #10b981);
  }

  .connection-dot.disconnected {
    background-color: var(--color-danger, #ef4444);
    box-shadow: 0 0 6px var(--color-danger, #ef4444);
    animation: pulse 2s ease-in-out infinite;
  }

  .connection-text {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .status-update {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .update-time {
    font-family: var(--font-mono, monospace);
    font-size: 0.75rem;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* Responsive */
  @media (max-width: 768px) {
    .status-bar {
      padding: 6px 12px;
    }

    .status-center {
      display: none;
    }

    .status-section {
      gap: 8px;
    }
  }
</style>

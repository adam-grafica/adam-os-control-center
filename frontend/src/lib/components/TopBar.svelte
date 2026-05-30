<script lang="ts">
  /**
   * TopBar.svelte — Main header with system indicators.
   */
  import { getHealthColor } from '$lib/utils/colors';
  import { formatBytes, getPercentColor } from '$lib/stores/infra';
  import type { CpuInfo, MemoryInfo, NetworkInfo } from '$lib/stores/infra';

  interface Provider {
    name: string;
    status: 'online' | 'offline' | 'error';
    last_call: string;
  }

  interface Props {
    health: number;
    mode: string;
    status: string;
    cpu: CpuInfo | null;
    memory: MemoryInfo | null;
    network: NetworkInfo | null;
    alerts: number;
    providers: Provider[];
    connected: boolean;
    lastUpdate: Date | null;
  }

  let {
    health = 100,
    mode = 'idle',
    status = 'secure',
    cpu = null,
    memory = null,
    network = null,
    alerts = 0,
    providers = [],
    connected = false,
    lastUpdate = null,
  }: Props = $props();

  function formatLatency(): string {
    if (!lastUpdate) return '--';
    const diff = Date.now() - lastUpdate.getTime();
    if (diff < 1000) return `${diff}ms`;
    if (diff < 60000) return `${Math.floor(diff / 1000)}s`;
    return `${Math.floor(diff / 60000)}m`;
  }

  // Update latency display every second
  let tick = $state(0);
  $effect(() => {
    const interval = setInterval(() => { tick = Date.now(); }, 1000);
    return () => clearInterval(interval);
  });
</script>

<header class="topbar">
  <div class="topbar-left">
    <div class="logo-section">
      <div class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="14" stroke="url(#logo-grad)" stroke-width="2" fill="none" />
          <circle cx="16" cy="16" r="6" fill="url(#logo-grad)" opacity="0.6" />
          <path d="M16 2 L16 8 M16 24 L16 30 M2 16 L8 16 M24 16 L30 16"
                stroke="url(#logo-grad)" stroke-width="1" opacity="0.3" />
          <defs>
            <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#3b82f6" />
              <stop offset="100%" stop-color="#a855f7" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <div class="logo-text">
        <span class="logo-title">ADAM OS</span>
        <span class="logo-sub">Control Center</span>
      </div>
    </div>
  </div>

  <div class="topbar-center">
    <!-- Health Pill -->
    <div class="pill" class:warn={health < 80 && health >= 50} class:critical={health < 50}>
      <span class="pill-icon">❤️</span>
      <span class="pill-value" style="color: {getHealthColor(health)};">{Math.round(health)}%</span>
    </div>

    <!-- Mode Pill -->
    <div class="pill">
      <span class="pill-icon">⚙️</span>
      <span class="pill-label">{mode}</span>
    </div>

    <!-- Status Pill -->
    <div class="pill"
      class:warn={status === 'warning'}
      class:critical={status === 'critical' || status === 'compromised'}
    >
      <span class="pill-icon">🛡️</span>
      <span class="pill-label">{status}</span>
    </div>

    <!-- CPU Bar -->
    {#if cpu}
      <div class="metric-bar" title="CPU: {cpu.percent}%">
        <span class="metric-label">CPU</span>
        <div class="bar-track">
          <div class="bar-fill" style="width: {cpu.percent}%; background: {getPercentColor(cpu.percent)};"></div>
        </div>
        <span class="metric-value font-mono">{cpu.percent.toFixed(1)}%</span>
      </div>
    {/if}

    <!-- RAM Bar -->
    {#if memory}
      <div class="metric-bar" title="RAM: {memory.percent}%">
        <span class="metric-label">RAM</span>
        <div class="bar-track">
          <div class="bar-fill" style="width: {memory.percent}%; background: {getPercentColor(memory.percent)};"></div>
        </div>
        <span class="metric-value font-mono">{memory.percent.toFixed(1)}%</span>
      </div>
    {/if}

    <!-- Network -->
    {#if network}
      <div class="pill net-pill" title="Net I/O">
        <span class="pill-icon">🌐</span>
        <span class="pill-label font-mono">↓{formatBytes(network.bytes_recv)} ↑{formatBytes(network.bytes_sent)}</span>
      </div>
    {/if}

    <!-- Latency -->
    <div class="pill latency-pill" class:slow={lastUpdate && (Date.now() - lastUpdate.getTime()) > 5000}>
      <span class="pill-icon">📡</span>
      <span class="pill-label font-mono">{formatLatency()}</span>
    </div>
  </div>

  <div class="topbar-right">
    <!-- API Providers -->
    <div class="providers-group">
      {#each providers as provider}
        <div
          class="provider-dot"
          title="{provider.name}: {provider.status}"
          class:online={provider.status === 'online'}
          class:offline={provider.status === 'offline' || provider.status === 'error'}
        ></div>
      {/each}
    </div>

    <!-- Alerts Badge -->
    {#if alerts > 0}
      <div class="alerts-badge">
        <span class="alert-icon">⚠️</span>
        <span class="alert-count">{alerts}</span>
      </div>
    {/if}

    <!-- Live Indicator -->
    <div class="live-indicator" class:active={connected}>
      <div class="live-dot"></div>
      <span class="live-text">LIVE</span>
    </div>
  </div>
</header>

<style>
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 16px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    min-height: 48px;
    flex-wrap: nowrap;
  }

  /* ─── Left ─── */
  .topbar-left {
    flex-shrink: 0;
  }

  .logo-section {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .logo-text {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .logo-title {
    font-size: 0.95rem;
    font-weight: 800;
    background: linear-gradient(135deg, #3b82f6, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
  }

  .logo-sub {
    font-size: 0.6rem;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* ─── Center ─── */
  .topbar-center {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    justify-content: center;
    overflow: hidden;
  }

  .pill {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    font-size: 0.75rem;
    white-space: nowrap;
    transition: border-color 0.2s ease;
  }

  .pill.warn {
    border-color: rgba(234,179,8,0.3);
    background: rgba(234,179,8,0.06);
  }

  .pill.critical {
    border-color: rgba(239,68,68,0.3);
    background: rgba(239,68,68,0.06);
  }

  .pill-icon {
    font-size: 0.8rem;
    line-height: 1;
  }

  .pill-value {
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
  }

  .pill-label {
    font-weight: 600;
    color: #94a3b8;
    text-transform: capitalize;
  }

  .net-pill .pill-label {
    font-size: 0.7rem;
  }

  .latency-pill.slow {
    border-color: rgba(234,179,8,0.3);
    background: rgba(234,179,8,0.06);
  }

  /* ─── Metric Bars ─── */
  .metric-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 100px;
  }

  .metric-label {
    font-size: 0.65rem;
    font-weight: 600;
    color: #64748b;
    min-width: 28px;
  }

  .bar-track {
    flex: 1;
    height: 4px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    overflow: hidden;
    min-width: 40px;
  }

  .bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease, background 0.5s ease;
  }

  .metric-value {
    font-size: 0.65rem;
    color: #94a3b8;
    min-width: 36px;
    text-align: right;
  }

  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Right ─── */
  .topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .providers-group {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.05);
  }

  .provider-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #64748b;
    transition: background 0.3s ease;
  }

  .provider-dot.online {
    background: #22c55e;
    box-shadow: 0 0 4px rgba(34,197,94,0.5);
  }

  .provider-dot.offline {
    background: #ef4444;
    box-shadow: 0 0 4px rgba(239,68,68,0.4);
  }

  .alerts-badge {
    display: flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 12px;
  }

  .alert-icon {
    font-size: 0.7rem;
  }

  .alert-count {
    font-size: 0.7rem;
    font-weight: 700;
    color: #ef4444;
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Live Indicator ─── */
  .live-indicator {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.2);
    border-radius: 20px;
  }

  .live-indicator.active {
    background: rgba(34,197,94,0.1);
    border-color: rgba(34,197,94,0.3);
  }

  .live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34,197,94,0.6);
    animation: livePulse 2s ease-in-out infinite;
  }

  .live-indicator.active .live-dot {
    animation: livePulse 1.5s ease-in-out infinite;
  }

  @keyframes livePulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
  }

  .live-text {
    font-size: 0.65rem;
    font-weight: 700;
    color: #22c55e;
    letter-spacing: 0.08em;
  }

  /* ─── Responsive ─── */
  @media (max-width: 1200px) {
    .metric-bar { display: none; }
    .logo-sub { display: none; }
  }

  @media (max-width: 900px) {
    .net-pill { display: none; }
    .latency-pill { display: none; }
    .providers-group { display: none; }
  }

  @media (max-width: 640px) {
    .topbar { padding: 6px 10px; gap: 6px; flex-wrap: wrap; }
    .topbar-center { flex-wrap: wrap; justify-content: flex-start; }
    .alerts-badge { display: none; }
  }
</style>

<script lang="ts">
  /**
   * InfraPanel.svelte — Right rail panel showing server health.
   */
  import { formatBytes, getPercentColor, currentCpu, currentMemory, currentDisk, currentNetwork, currentProcesses, currentUptime } from '$lib/stores/infra';
  import type { CpuInfo, MemoryInfo, DiskInfo, NetworkInfo, ProcessInfo, UptimeInfo } from '$lib/stores/infra';

  let cpu: CpuInfo | null = $state(null);
  let memory: MemoryInfo | null = $state(null);
  let disk: DiskInfo[] = $state([]);
  let network: NetworkInfo | null = $state(null);
  let processes: ProcessInfo[] = $state([]);
  let uptime: UptimeInfo | null = $state(null);

  $effect(() => {
    const unsubs = [
      currentCpu.subscribe((v) => { cpu = v; }),
      currentMemory.subscribe((v) => { memory = v; }),
      currentDisk.subscribe((v) => { disk = v; }),
      currentNetwork.subscribe((v) => { network = v; }),
      currentProcesses.subscribe((v) => { processes = v; }),
      currentUptime.subscribe((v) => { uptime = v; }),
    ];
    return () => unsubs.forEach((fn) => fn());
  });

  let freeingRam = $state(false);
  let freeRamMessage = $state<string | null>(null);

  async function handleFreeRam() {
    if (freeingRam) return;
    freeingRam = true;
    freeRamMessage = null;
    try {
      const res = await fetch('/api/infra/memory/free', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        freeRamMessage = data.message || 'Memory freed successfully';
      } else {
        freeRamMessage = 'Failed to free memory';
      }
    } catch {
      freeRamMessage = 'Request failed';
    } finally {
      freeingRam = false;
    }
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const parts: string[] = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    parts.push(`${mins}m`);
    return parts.join(' ');
  }

  const topProcesses = $derived(
    processes ? [...processes].sort((a, b) => b.cpu_percent - a.cpu_percent).slice(0, 8) : []
  );
</script>

<div class="infra-panel">
  <!-- ─── CPU ─── -->
  <div class="panel-section">
    <div class="section-header">
      <span class="section-icon">⚡</span>
      <span class="section-title">CPU</span>
      {#if cpu}
        <span class="section-status" class:good={cpu.status === 'ok' || cpu.status === 'healthy'} class:warn={cpu.status === 'warning'} class:bad={cpu.status === 'critical'}>
          {cpu.status}
        </span>
      {/if}
    </div>
    {#if cpu}
      <div class="metric-block">
        <div class="metric-bar-large">
          <div class="bar-label-row">
            <span class="bar-label">Usage</span>
            <span class="bar-value font-mono" style="color: {getPercentColor(cpu.percent)};">{cpu.percent.toFixed(1)}%</span>
          </div>
          <div class="bar-track-lg">
            <div class="bar-fill-lg" style="width: {cpu.percent}%; background: {getPercentColor(cpu.percent)};"></div>
          </div>
        </div>
        <div class="metric-details">
          <div class="detail-item">
            <span class="detail-key">Cores</span>
            <span class="detail-val font-mono">{cpu.cores}</span>
          </div>
          <div class="detail-item">
            <span class="detail-key">Load</span>
            <span class="detail-val font-mono">{cpu.load_avg.map((l) => l.toFixed(2)).join(', ')}</span>
          </div>
        </div>
      </div>
    {:else}
      <div class="empty-state">Waiting for CPU data...</div>
    {/if}
  </div>

  <!-- ─── Memory ─── -->
  <div class="panel-section">
    <div class="section-header">
      <span class="section-icon">💾</span>
      <span class="section-title">Memory</span>
      {#if memory}
        <span class="section-status" class:good={memory.status === 'ok' || memory.status === 'healthy'} class:warn={memory.status === 'warning'} class:bad={memory.status === 'critical'}>
          {memory.status}
        </span>
      {/if}
    </div>
    {#if memory}
      <div class="metric-block">
        <div class="metric-bar-large">
          <div class="bar-label-row">
            <span class="bar-label">RAM</span>
            <span class="bar-value font-mono" style="color: {getPercentColor(memory.percent)};">
              {formatBytes(memory.used)} / {formatBytes(memory.total)}
            </span>
          </div>
          <div class="bar-track-lg">
            <div class="bar-fill-lg" style="width: {memory.percent}%; background: {getPercentColor(memory.percent)};"></div>
          </div>
        </div>
        <div class="metric-details">
          <div class="detail-item">
            <span class="detail-key">Available</span>
            <span class="detail-val font-mono">{formatBytes(memory.available)}</span>
          </div>
          <div class="detail-item">
            <span class="detail-key">Free</span>
            <span class="detail-val font-mono">{formatBytes(memory.free)}</span>
          </div>
        </div>
        <button class="action-btn" onclick={handleFreeRam} disabled={freeingRam}>
          {freeingRam ? 'Freeing...' : '🧹 Free RAM'}
        </button>
        {#if freeRamMessage}
          <div class="action-feedback">{freeRamMessage}</div>
        {/if}
      </div>
    {:else}
      <div class="empty-state">Waiting for memory data...</div>
    {/if}
  </div>

  <!-- ─── Disk ─── -->
  <div class="panel-section">
    <div class="section-header">
      <span class="section-icon">💿</span>
      <span class="section-title">Disk</span>
    </div>
    {#if disk.length > 0}
      <div class="metric-block">
        {#each disk as d}
          <div class="disk-item">
            <div class="bar-label-row">
              <span class="bar-label" title="{d.device}">{d.mountpoint}</span>
              <span class="bar-value font-mono" style="color: {getPercentColor(d.percent)};">
                {d.percent.toFixed(1)}%
              </span>
            </div>
            <div class="bar-track-lg">
              <div class="bar-fill-lg" style="width: {d.percent}%; background: {getPercentColor(d.percent)};"></div>
            </div>
            <div class="disk-details">
              <span class="detail-val font-mono">{formatBytes(d.used)} / {formatBytes(d.total)}</span>
              <span class="detail-val font-mono">{formatBytes(d.free)} free</span>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state">Waiting for disk data...</div>
    {/if}
  </div>

  <!-- ─── Network ─── -->
  <div class="panel-section">
    <div class="section-header">
      <span class="section-icon">🌐</span>
      <span class="section-title">Network</span>
      {#if network}
        <span class="section-status" class:good={network.status === 'ok' || network.status === 'healthy'} class:warn={network.status === 'warning'} class:bad={network.status === 'critical'}>
          {network.status}
        </span>
      {/if}
    </div>
    {#if network}
      <div class="metric-block">
        <div class="net-grid">
          <div class="net-item">
            <span class="detail-key">⬇ Received</span>
            <span class="detail-val font-mono">{formatBytes(network.bytes_recv)}</span>
          </div>
          <div class="net-item">
            <span class="detail-key">⬆ Sent</span>
            <span class="detail-val font-mono">{formatBytes(network.bytes_sent)}</span>
          </div>
          <div class="net-item">
            <span class="detail-key">📦 Packets In</span>
            <span class="detail-val font-mono">{network.packets_recv.toLocaleString()}</span>
          </div>
          <div class="net-item">
            <span class="detail-key">📦 Packets Out</span>
            <span class="detail-val font-mono">{network.packets_sent.toLocaleString()}</span>
          </div>
        </div>
      </div>
    {:else}
      <div class="empty-state">Waiting for network data...</div>
    {/if}
  </div>

  <!-- ─── Uptime ─── -->
  {#if uptime}
    <div class="panel-section uptime-section">
      <div class="section-header">
        <span class="section-icon">⏱️</span>
        <span class="section-title">Uptime</span>
        <span class="section-status" class:good={uptime.status === 'ok' || uptime.status === 'healthy'}>{uptime.status}</span>
      </div>
      <div class="metric-block">
        <span class="uptime-value font-mono">{formatUptime(uptime.uptime_seconds)}</span>
      </div>
    </div>
  {/if}

  <!-- ─── Top Processes ─── -->
  <div class="panel-section">
    <div class="section-header">
      <span class="section-icon">📋</span>
      <span class="section-title">Top Processes</span>
    </div>
    {#if topProcesses.length > 0}
      <div class="process-table">
        <div class="process-header">
          <span class="proc-col pid">PID</span>
          <span class="proc-col name">Name</span>
          <span class="proc-col cpu">CPU%</span>
          <span class="proc-col mem">Mem%</span>
          <span class="proc-col status">Status</span>
        </div>
        {#each topProcesses as proc}
          <div class="process-row">
            <span class="proc-col pid font-mono">{proc.pid}</span>
            <span class="proc-col name" title={proc.name}>{proc.name}</span>
            <span class="proc-col cpu font-mono" style="color: {getPercentColor(proc.cpu_percent)};">{proc.cpu_percent.toFixed(1)}</span>
            <span class="proc-col mem font-mono" style="color: {getPercentColor(proc.memory_percent)};">{proc.memory_percent.toFixed(1)}</span>
            <span class="proc-col status"><span class="status-dot" class:running={proc.status === 'running'}></span></span>
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state">No process data</div>
    {/if}
  </div>
</div>

<style>
  .infra-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .panel-section {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 12px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
  }

  .section-icon {
    font-size: 0.85rem;
  }

  .section-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e2e8f0;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .section-status {
    margin-left: auto;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #64748b;
    background: rgba(255,255,255,0.04);
  }

  .section-status.good { color: #22c55e; background: rgba(34,197,94,0.1); }
  .section-status.warn { color: #eab308; background: rgba(234,179,8,0.1); }
  .section-status.bad { color: #ef4444; background: rgba(239,68,68,0.1); }

  .metric-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .metric-bar-large {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .bar-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .bar-label {
    font-size: 0.7rem;
    color: #94a3b8;
    font-weight: 500;
  }

  .bar-value {
    font-size: 0.75rem;
    font-weight: 700;
  }

  .bar-track-lg {
    height: 6px;
    background: rgba(255,255,255,0.05);
    border-radius: 3px;
    overflow: hidden;
  }

  .bar-fill-lg {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease, background 0.5s ease;
  }

  .metric-details {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .detail-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .detail-key {
    font-size: 0.65rem;
    color: #64748b;
    font-weight: 500;
  }

  .detail-val {
    font-size: 0.7rem;
    color: #94a3b8;
  }

  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  .empty-state {
    font-size: 0.7rem;
    color: #475569;
    text-align: center;
    padding: 12px;
    font-style: italic;
  }

  /* ─── Action Button ─── */
  .action-btn {
    padding: 5px 12px;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 6px;
    color: #60a5fa;
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    width: fit-content;
  }

  .action-btn:hover:not(:disabled) {
    background: rgba(59,130,246,0.2);
    border-color: rgba(59,130,246,0.4);
  }

  .action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .action-feedback {
    font-size: 0.65rem;
    color: #22c55e;
    padding: 4px 0;
  }

  /* ─── Disk ─── */
  .disk-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }

  .disk-item:last-child { border-bottom: none; }

  .disk-details {
    display: flex;
    gap: 16px;
  }

  /* ─── Network ─── */
  .net-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .net-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  /* ─── Uptime ─── */
  .uptime-section .uptime-value {
    font-size: 1rem;
    font-weight: 700;
    color: #22c55e;
  }

  /* ─── Processes ─── */
  .process-table {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.65rem;
  }

  .process-header {
    display: flex;
    gap: 4px;
    padding: 4px 6px;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }

  .process-row {
    display: flex;
    gap: 4px;
    padding: 3px 6px;
    border-radius: 4px;
    transition: background 0.15s ease;
  }

  .process-row:hover {
    background: rgba(255,255,255,0.03);
  }

  .proc-col.pid { width: 40px; flex-shrink: 0; }
  .proc-col.name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .proc-col.cpu { width: 40px; text-align: right; flex-shrink: 0; }
  .proc-col.mem { width: 40px; text-align: right; flex-shrink: 0; }
  .proc-col.status { width: 20px; text-align: center; flex-shrink: 0; }

  .status-dot {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #64748b;
  }

  .status-dot.running {
    background: #22c55e;
    box-shadow: 0 0 4px rgba(34,197,94,0.5);
  }
</style>

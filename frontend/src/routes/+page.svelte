<script lang="ts">
  /**
   * Main dashboard page — Master layout for the Control Tower.
   * Layout: TopBar | Left (ControlCenter) + Center (OrganismBody) + Right (InfraPanel + AgentFleet) | Bottom (MissionConsole)
   */
  import TopBar from '$lib/components/TopBar.svelte';
  import ControlCenter from '$lib/components/ControlCenter.svelte';
  import OrganismBody from '$lib/components/OrganismBody.svelte';
  import InfraPanel from '$lib/components/InfraPanel.svelte';
  import AgentFleet from '$lib/components/AgentFleet.svelte';
  import MissionConsole from '$lib/components/MissionConsole.svelte';
  import PipelineView from '$lib/components/PipelineView.svelte';

  import { health, mode, organs, recentEvents, type Organ } from '$lib/stores/organism';
  import type { DashboardEvent } from '$lib/stores/organism';
  import { connected, lastUpdate, errorMessage } from '$lib/stores/sse';
  import { currentCpu, currentMemory, currentNetwork } from '$lib/stores/infra';
  import type { CpuInfo, MemoryInfo, NetworkInfo } from '$lib/stores/infra';
  import { activeAlerts } from '$lib/stores/agents';
  import type { Agent } from '$lib/stores/agents';
  import { agents } from '$lib/stores/agents';
  import { pipelineOverview } from '$lib/stores/pipeline';
  import type { PipelineOverview } from '$lib/stores/pipeline';

  // ─── Reactive State ───
  let healthVal: number = $state(100);
  let modeVal: string = $state('idle');
  let statusVal: string = $state('secure');
  let organList: Organ[] = $state([]);
  let eventList: DashboardEvent[] = $state([]);
  let cpuData: CpuInfo | null = $state(null);
  let memData: MemoryInfo | null = $state(null);
  let netData: NetworkInfo | null = $state(null);
  let alertCount: number = $state(0);
  let agentList: Agent[] = $state([]);
  let isConnected: boolean = $state(false);
  let lastUpdateTime: Date | null = $state(null);
  let providers: Array<{ name: string; status: 'online' | 'offline' | 'error'; last_call: string }> = $state([]);
  let overview: PipelineOverview | null = $state(null);

  $effect(() => {
    const unsubs = [
      health.subscribe((v) => { healthVal = v; }),
      mode.subscribe((v) => { modeVal = v; }),
      organs.subscribe((v) => { organList = v; }),
      recentEvents.subscribe((v) => { eventList = v; }),
      currentCpu.subscribe((v) => { cpuData = v; }),
      currentMemory.subscribe((v) => { memData = v; }),
      currentNetwork.subscribe((v) => { netData = v; }),
      activeAlerts.subscribe((v) => { alertCount = v; }),
      agents.subscribe((v) => { agentList = v; }),
      connected.subscribe((v) => { isConnected = v; }),
      lastUpdate.subscribe((v) => { lastUpdateTime = v; }),
      errorMessage.subscribe((v) => { if (!v) { statusVal = 'secure'; } }),
      pipelineOverview.subscribe((v) => { overview = v; }),
    ];
    return () => unsubs.forEach((fn) => fn());
  });

  // Derive status from health
  $effect(() => {
    if (healthVal < 50) { statusVal = 'critical'; }
    else if (healthVal < 80) { statusVal = 'warning'; }
    else { statusVal = 'secure'; }
  });

  // Derive agent data for OrganismBody orbiting agents
  const orbitingAgents = $derived(
    agentList.map((a) => ({ id: a.id, name: a.name, status: a.status, type: a.type }))
  );

  const eventsForBody = $derived(
    eventList.slice(0, 10).map((e) => ({
      id: e.id,
      type: e.type,
      severity: e.severity,
      timestamp: new Date(e.timestamp).getTime(),
      message: e.preview || e.type,
      organ: e.source,
    }))
  );

  // Left rail collapsible for responsive
  let leftRailVisible = $state(true);

  // Center view mode toggle
  let centerView: 'organism' | 'pipeline' = $state('organism');

  function toggleLeftRail() {
    leftRailVisible = !leftRailVisible;
  }
</script>

<div class="dashboard">
  <!-- ═══ TOP BAR ═══ -->
  <div class="dashboard-topbar">
    <TopBar
      health={healthVal}
      mode={modeVal}
      status={statusVal}
      cpu={cpuData}
      memory={memData}
      network={netData}
      alerts={alertCount}
      providers={providers}
      connected={isConnected}
      lastUpdate={lastUpdateTime}
    />
  </div>

  <!-- ═══ MAIN AREA ═══ -->
  <div class="dashboard-main">
    <!-- Left Rail Toggle (mobile) -->
    <button class="left-toggle" onclick={toggleLeftRail} aria-label="Toggle left panel">
      {leftRailVisible ? '✕' : '☰'}
    </button>

    <!-- Left Rail -->
    <aside class="left-rail" class:hidden={!leftRailVisible}>
      <ControlCenter />
    </aside>

    <!-- Center Stage - Organism Body or Pipeline View -->
    <section class="center-stage">
      <!-- View Tabs -->
      <div class="center-tabs">
        <button
          class="center-tab"
          class:active={centerView === 'organism'}
          onclick={() => { centerView = 'organism'; }}
        >
          <span class="tab-icon">🧬</span>
          <span class="tab-label">Organism</span>
        </button>
        <button
          class="center-tab"
          class:active={centerView === 'pipeline'}
          onclick={() => { centerView = 'pipeline'; }}
        >
          <span class="tab-icon">🏭</span>
          <span class="tab-label">Pipeline</span>
          {#if overview && overview.total_projects > 0}
            <span class="tab-badge">{overview.total_projects}</span>
          {/if}
        </button>
      </div>

      {#if centerView === 'organism'}
        <div class="center-panel">
          <div class="center-header">
            <h2 class="center-title">🧬 Organism Status</h2>
            <div class="center-health-badge">
              <span class="badge-dot" style="background: {healthVal >= 80 ? '#22c55e' : healthVal >= 50 ? '#eab308' : '#ef4444'};"></span>
              <span class="badge-label">Health {Math.round(healthVal)}%</span>
            </div>
          </div>
          <div class="center-body">
            <OrganismBody
              organs={organList}
              events={eventsForBody}
              agents={orbitingAgents}
            />
          </div>
        </div>
      {:else}
        <div class="center-panel pipeline-panel">
          <PipelineView />
        </div>
      {/if}
    </section>

    <!-- Right Rail -->
    <aside class="right-rail">
      <div class="right-panel">
        <InfraPanel />
      </div>
      <div class="right-panel">
        <AgentFleet />
      </div>
    </aside>
  </div>

  <!-- ═══ BOTTOM DOCK ═══ -->
  <div class="dashboard-bottom">
    <div class="bottom-header">
      <span class="console-title">🖥️ Mission Console</span>
      <div class="bottom-meta">
        <span class="connection-status" class:connected={isConnected}>
          <span class="conn-dot"></span>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
        {#if lastUpdateTime}
          <span class="last-update">Last: {lastUpdateTime.toLocaleTimeString()}</span>
        {/if}
      </div>
    </div>
    <div class="console-container">
      <MissionConsole />
    </div>
  </div>
</div>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: #0f1117;
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  /* ═══ TOP BAR ═══ */
  .dashboard-topbar {
    flex-shrink: 0;
    z-index: 50;
  }

  /* ═══ MAIN AREA (Center) ═══ */
  .dashboard-main {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  /* Left Rail Toggle */
  .left-toggle {
    display: none;
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 60;
    width: 32px;
    height: 32px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: #94a3b8;
    font-size: 1rem;
    cursor: pointer;
    align-items: center;
    justify-content: center;
  }

  /* ─── Left Rail ─── */
  .left-rail {
    width: 260px;
    min-width: 260px;
    border-right: 1px solid rgba(255,255,255,0.04);
    overflow-y: auto;
    background: rgba(255,255,255,0.01);
    flex-shrink: 0;
  }

  .left-rail.hidden {
    display: none;
  }

  .left-rail::-webkit-scrollbar {
    width: 4px;
  }

  .left-rail::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.04);
    border-radius: 2px;
  }

  /* ─── Center Stage ─── */
  .center-stage {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  .center-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    margin: 10px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 14px;
    overflow: hidden;
  }

  .center-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    flex-shrink: 0;
  }

  .center-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #e2e8f0;
  }

  .center-health-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
  }

  .badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .badge-label {
    font-size: 0.65rem;
    font-weight: 600;
    color: #94a3b8;
  }

  .center-body {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
    position: relative;
    overflow: hidden;
  }

  /* ─── View Tabs ─── */
  .center-tabs {
    display: flex;
    gap: 2px;
    padding: 0 10px;
    margin-top: 10px;
    background: rgba(255,255,255,0.01);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    flex-shrink: 0;
  }

  .center-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: none;
    background: transparent;
    color: #64748b;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
    position: relative;
  }
  .center-tab:hover {
    color: #94a3b8;
    background: rgba(255,255,255,0.02);
  }
  .center-tab.active {
    color: #e2e8f0;
    border-bottom-color: #3b82f6;
  }
  .tab-icon {
    font-size: 0.85rem;
  }
  .tab-label {
    font-size: 0.7rem;
  }
  .tab-badge {
    font-size: 0.55rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 8px;
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
    margin-left: 2px;
  }

  .center-panel.pipeline-panel {
    margin-top: 0;
    margin-bottom: 0;
    margin-left: 0;
    margin-right: 0;
    border-radius: 0;
    border: none;
    background: transparent;
  }

  /* ─── Right Rail ─── */
  .right-rail {
    width: 340px;
    min-width: 340px;
    border-left: 1px solid rgba(255,255,255,0.04);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    flex-shrink: 0;
  }

  .right-rail::-webkit-scrollbar {
    width: 4px;
  }

  .right-rail::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.04);
    border-radius: 2px;
  }

  .right-panel {
    flex-shrink: 0;
  }

  /* ═══ BOTTOM DOCK ═══ */
  .dashboard-bottom {
    flex-shrink: 0;
    height: 220px;
    display: flex;
    flex-direction: column;
    border-top: 1px solid rgba(255,255,255,0.04);
  }

  .bottom-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px;
    background: rgba(255,255,255,0.015);
    border-bottom: 1px solid rgba(255,255,255,0.03);
    flex-shrink: 0;
  }

  .console-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .bottom-meta {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.6rem;
    font-weight: 600;
    color: #64748b;
  }

  .conn-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #ef4444;
    transition: background 0.3s ease;
  }

  .connection-status.connected .conn-dot {
    background: #22c55e;
    box-shadow: 0 0 5px rgba(34,197,94,0.5);
    animation: livePulse 2s ease-in-out infinite;
  }

  @keyframes livePulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .connection-status.connected {
    color: #22c55e;
  }

  .last-update {
    font-size: 0.6rem;
    color: #475569;
    font-family: 'JetBrains Mono', monospace;
  }

  .console-container {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .console-container :global(.console) {
    height: 100%;
  }

  /* ═══ RESPONSIVE ═══ */
  @media (max-width: 1400px) {
    .left-rail:not(.hidden) {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      z-index: 40;
      background: #0f1117;
      border-right: 1px solid rgba(255,255,255,0.08);
      box-shadow: 4px 0 20px rgba(0,0,0,0.4);
    }

    .left-toggle {
      display: flex;
    }

    .left-rail.hidden {
      display: none;
    }
  }

  @media (max-width: 1024px) {
    .dashboard-main {
      flex-direction: column;
    }

    .left-rail:not(.hidden) {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      width: 280px;
      z-index: 100;
    }

    .right-rail {
      width: 100%;
      min-width: 0;
      border-left: none;
      border-top: 1px solid rgba(255,255,255,0.04);
      max-height: 300px;
    }

    .center-stage {
      min-height: 350px;
    }
  }

  @media (max-width: 640px) {
    .center-header { padding: 8px 12px; }
    .center-title { font-size: 0.75rem; }
    .center-body { padding: 6px; }
    .right-rail { padding: 6px; max-height: 250px; }
    .dashboard-bottom { height: 160px; }
    .bottom-meta { display: none; }
  }
</style>

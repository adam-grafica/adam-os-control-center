<script lang="ts">
  /**
   * OrganismBody.svelte — Digital human silhouette with 7 pulsing organs,
   * energy lines, and orbiting agent cards.
   */
  import { getHealthColor } from '$lib/utils/colors';
  import { capitalizeFirst, formatTime } from '$lib/utils/format';
  import type { Organ } from '$lib/stores/organism';

  interface Props {
    organs: Organ[];
    events: Array<{ id: string; type: string; severity: string; timestamp: number; message: string; organ: string }>;
    agents: Array<{ id: string; name: string; status: string; type: string }>;
  }

  let { organs = [], events = [], agents = [] }: Props = $props();

  // Organ positions on the silhouette (relative %) — functional ADAM OS names
  const organPositions: Record<string, { x: number; y: number }> = {
    autonomic: { x: 50, y: 8 },
    heart: { x: 50, y: 32 },
    immune: { x: 50, y: 38 },
    proprioception: { x: 55, y: 48 },
    reflexes: { x: 45, y: 48 },
    dreams: { x: 50, y: 55 },
    growth: { x: 50, y: 35 },
  };

  // Organ-specific accent colors (from ux-research.md design tokens)
  const organColors: Record<string, string> = {
    heart: '#ff3366',
    autonomic: '#00d4aa',
    immune: '#7c3aed',
    proprioception: '#3b82f6',
    reflexes: '#f59e0b',
    dreams: '#ec4899',
    growth: '#10b981',
  };

  function getOrganEvent(organName: string) {
    return events.find((e) => e.organ === organName);
  }

  function getPulseClass(health: number): string {
    if (health >= 80) return 'pulse-healthy';
    if (health >= 50) return 'pulse-warning';
    return 'pulse-critical';
  }

  // Generate orbiting agents with computed positions
  function getAgentOrbit(agent: any, index: number, total: number) {
    const angle = (index / total) * 360;
    const rad = (angle * Math.PI) / 180;
    const radiusX = 160;
    const radiusY = 220;
    return {
      '--orbit-x': `${Math.cos(rad) * radiusX}px`,
      '--orbit-y': `${Math.sin(rad) * radiusY}px`,
      '--orbit-delay': `${index * 2}s`,
    };
  }

  // Energy lines connecting organs (using ADAM OS functional names)
  const energyLines = [
    { from: 'autonomic', to: 'heart' },
    { from: 'heart', to: 'immune' },
    { from: 'immune', to: 'proprioception' },
    { from: 'heart', to: 'dreams' },
    { from: 'proprioception', to: 'reflexes' },
    { from: 'dreams', to: 'growth' },
  ];
</script>

<div class="organism-container">
  <!-- Background glow effects -->
  <div class="glow-bg"></div>

  <!-- SVG Silhouette -->
  <svg class="silhouette" viewBox="0 0 240 480" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="rgba(59,130,246,0.15)" />
        <stop offset="50%" stop-color="rgba(168,85,247,0.08)" />
        <stop offset="100%" stop-color="rgba(59,130,246,0.12)" />
      </linearGradient>
      <filter id="glow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>

    <!-- Body outline -->
    <!-- Head -->
    <ellipse cx="120" cy="30" rx="32" ry="28" fill="none" stroke="rgba(148,163,184,0.3)" stroke-width="1.5" />
    <!-- Neck -->
    <rect x="110" y="52" width="20" height="18" rx="4" fill="none" stroke="rgba(148,163,184,0.25)" stroke-width="1" />
    <!-- Torso -->
    <path d="M88 70 Q85 160 82 220 Q80 260 90 280 L150 280 Q160 260 158 220 Q155 160 152 70 Z"
          fill="url(#bodyGrad)" stroke="rgba(148,163,184,0.25)" stroke-width="1.5" />
    <!-- Left arm -->
    <path d="M88 80 Q60 120 52 170 Q48 200 55 220"
          fill="none" stroke="rgba(148,163,184,0.2)" stroke-width="1.5" />
    <!-- Right arm -->
    <path d="M152 80 Q180 120 188 170 Q192 200 185 220"
          fill="none" stroke="rgba(148,163,184,0.2)" stroke-width="1.5" />
    <!-- Left leg -->
    <path d="M90 270 Q85 320 80 380 Q78 420 82 450"
          fill="none" stroke="rgba(148,163,184,0.2)" stroke-width="1.5" />
    <!-- Right leg -->
    <path d="M150 270 Q155 320 160 380 Q162 420 158 450"
          fill="none" stroke="rgba(148,163,184,0.2)" stroke-width="1.5" />

    <!-- Energy lines between organs -->
    {#each energyLines as line}
      {@const from = organPositions[line.from]}
      {@const to = organPositions[line.to]}
      <line x1={from.x * 2.4} y1={from.y * 4.8}
            x2={to.x * 2.4} y2={to.y * 4.8}
            stroke="rgba(59,130,246,0.12)" stroke-width="0.8"
            class="energy-line" />
    {/each}
  </svg>

  <!-- Organ nodes positioned over the silhouette -->
  {#each organs as organ}
    {@const pos = organPositions[organ.name.toLowerCase()]}
    {@const organBaseColor = organColors[organ.name.toLowerCase()] ?? getHealthColor(organ.health)}
    {#if pos}
      <div
        class="organ-node {getPulseClass(organ.health)}"
        style="
          left: {pos.x}%;
          top: {pos.y}%;
          --organ-color: {organBaseColor};
          --glow-color: {organBaseColor}33;
        "
        title="{capitalizeFirst(organ.name)} — {Math.round(organ.health)}% — {capitalizeFirst(organ.status)}"
      >
        <div class="organ-dot">
          <div class="organ-inner"></div>
        </div>
        <div class="organ-label">{capitalizeFirst(organ.name)}</div>
        <div class="organ-tooltip">
          <div class="tooltip-name">{capitalizeFirst(organ.name)}</div>
          <div class="tooltip-health" style="color: {organBaseColor};">
            {Math.round(organ.health)}%
          </div>
          <div class="tooltip-status">{capitalizeFirst(organ.status)}</div>
          {#if getOrganEvent(organ.name.toLowerCase())}
            {@const ev = getOrganEvent(organ.name.toLowerCase())!}
            <div class="tooltip-event">{ev.message}</div>
          {/if}
        </div>
      </div>
    {/if}
  {/each}

  <!-- Orbiting agents -->
  {#each agents as agent, i}
    <div
      class="orbit-agent"
      style="
        --orbit-x: {getAgentOrbit(agent, i, agents.length)['--orbit-x']};
        --orbit-y: {getAgentOrbit(agent, i, agents.length)['--orbit-y']};
        --orbit-delay: {getAgentOrbit(agent, i, agents.length)['--orbit-delay']};
      "
    >
      <div
        class="orbit-agent-dot"
        class:running={agent.status === 'running'}
        class:idle={agent.status === 'idle'}
        class:error={agent.status === 'error'}
      ></div>
      <span class="orbit-agent-name">{agent.name}</span>
    </div>
  {/each}

  <!-- Center aura -->
  <div class="center-aura">
    <svg class="pulse-ring" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(59,130,246,0.08)" stroke-width="1" />
      <circle cx="50" cy="50" r="35" fill="none" stroke="rgba(168,85,247,0.06)" stroke-width="0.8" />
    </svg>
  </div>
</div>

<style>
  .organism-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .glow-bg {
    position: absolute;
    width: 300px;
    height: 400px;
    background: radial-gradient(ellipse at center, rgba(59,130,246,0.04) 0%, transparent 70%);
    pointer-events: none;
  }

  .silhouette {
    width: 200px;
    height: auto;
    position: relative;
    z-index: 1;
    filter: drop-shadow(0 0 30px rgba(59,130,246,0.06));
  }

  .energy-line {
    animation: flowEnergy 4s ease-in-out infinite;
    stroke-dasharray: 4 4;
  }

  @keyframes flowEnergy {
    0%, 100% { stroke-dashoffset: 0; opacity: 0.3; }
    50% { stroke-dashoffset: -8; opacity: 0.8; }
  }

  /* ─── Organ Nodes ─── */
  .organ-node {
    position: absolute;
    transform: translate(-50%, -50%);
    z-index: 2;
    cursor: pointer;
  }

  .organ-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--organ-color);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: box-shadow 0.3s ease, transform 0.3s ease;
    margin: 0 auto;
    position: relative;
  }

  .organ-inner {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
  }

  .pulse-healthy .organ-dot {
    box-shadow: 0 0 12px var(--glow-color), 0 0 24px var(--glow-color);
    animation: pulseOrgan 2s ease-in-out infinite;
  }

  .pulse-warning .organ-dot {
    box-shadow: 0 0 14px var(--glow-color), 0 0 28px var(--glow-color);
    animation: pulseOrgan 1.5s ease-in-out infinite;
  }

  .pulse-critical .organ-dot {
    box-shadow: 0 0 18px var(--glow-color), 0 0 36px var(--glow-color);
    animation: pulseOrgan 0.8s ease-in-out infinite;
  }

  @keyframes pulseOrgan {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.3);
      opacity: 0.7;
    }
  }

  .organ-label {
    font-size: 0.6rem;
    font-weight: 500;
    color: rgba(148,163,184,0.7);
    text-align: center;
    margin-top: 4px;
    white-space: nowrap;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  /* ─── Tooltip ─── */
  .organ-tooltip {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15,17,23,0.95);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 12px;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
    z-index: 10;
    min-width: 120px;
  }

  .organ-node:hover .organ-tooltip {
    opacity: 1;
  }

  .tooltip-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 4px;
  }

  .tooltip-health {
    font-size: 1.1rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }

  .tooltip-status {
    font-size: 0.7rem;
    color: #94a3b8;
    margin-bottom: 4px;
  }

  .tooltip-event {
    font-size: 0.65rem;
    color: #3b82f6;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ─── Orbiting Agents ─── */
  .orbit-agent {
    position: absolute;
    left: calc(50% + var(--orbit-x));
    top: calc(50% + var(--orbit-y));
    transform: translate(-50%, -50%);
    display: flex;
    align-items: center;
    gap: 4px;
    animation: orbitFloat 8s ease-in-out infinite;
    animation-delay: var(--orbit-delay);
    z-index: 3;
  }

  .orbit-agent-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34,197,94,0.5);
  }

  .orbit-agent-dot.running {
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34,197,94,0.5);
  }

  .orbit-agent-dot.idle {
    background: #94a3b8;
    box-shadow: 0 0 4px rgba(148,163,184,0.3);
  }

  .orbit-agent-dot.error {
    background: #ef4444;
    box-shadow: 0 0 6px rgba(239,68,68,0.5);
    animation: pulseError 1s ease-in-out infinite;
  }

  .orbit-agent-name {
    font-size: 0.6rem;
    color: rgba(148,163,184,0.6);
    white-space: nowrap;
    max-width: 60px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @keyframes orbitFloat {
    0%, 100% { transform: translate(-50%, -50%) scale(1); }
    50% { transform: translate(-50%, -50%) scale(1.1); }
  }

  @keyframes pulseError {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  /* ─── Center Aura ─── */
  .center-aura {
    position: absolute;
    width: 280px;
    height: 280px;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 0;
  }

  .pulse-ring {
    width: 100%;
    height: 100%;
    animation: ringPulse 4s ease-in-out infinite;
  }

  @keyframes ringPulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.5;
    }
    50% {
      transform: scale(1.05);
      opacity: 0.2;
    }
  }

  @media (max-width: 768px) {
    .silhouette {
      width: 140px;
    }
    .organ-dot {
      width: 14px;
      height: 14px;
    }
    .organ-inner {
      width: 6px;
      height: 6px;
    }
    .organ-label {
      display: none;
    }
    .center-aura {
      width: 200px;
      height: 200px;
    }
  }
</style>

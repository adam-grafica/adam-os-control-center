<script lang="ts">
  /**
   * OrganGraph - SVG interactive organ graph with 7 nodes connected by lines.
   * Each node shows organ name + health ring. Click selects organ.
   */
  import HealthRing from './HealthRing.svelte';
  import { organs, type Organ } from '$lib/stores/organism';
  import { selectedOrgan } from '$lib/stores/ui';
  import { getStatusColor } from '$lib/utils/colors';
  import { capitalizeFirst } from '$lib/utils/format';

  // Node positions in a pseudo-anatomical layout (viewBox 0 0 800 600)
  const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
    heart: { x: 400, y: 220 },
    autonomic: { x: 200, y: 120 },
    immune: { x: 600, y: 120 },
    proprioception: { x: 120, y: 400 },
    reflexes: { x: 680, y: 400 },
    dreams: { x: 400, y: 80 },
    growth: { x: 400, y: 520 }
  };

  // Connections between organs (edges of the graph)
  const CONNECTIONS: Array<[string, string]> = [
    ['heart', 'autonomic'],
    ['heart', 'immune'],
    ['heart', 'dreams'],
    ['heart', 'growth'],
    ['autonomic', 'proprioception'],
    ['autonomic', 'dreams'],
    ['immune', 'reflexes'],
    ['immune', 'dreams'],
    ['proprioception', 'reflexes'],
    ['proprioception', 'growth'],
    ['reflexes', 'growth'],
    ['dreams', 'growth']
  ];

  // Turn Svelte store into reactive local
  let organList: Organ[] = $state([]);
  let selected: string | null = $state(null);

  $effect(() => {
    const unsubOrgans = organs.subscribe((val) => { organList = val; });
    const unsubSelected = selectedOrgan.subscribe((val) => { selected = val; });
    return () => {
      unsubOrgans();
      unsubSelected();
    };
  });

  // Build quick lookup
  const organMap = $derived(() => {
    const map: Record<string, Organ> = {};
    for (const org of organList) {
      map[org.name.toLowerCase()] = org;
    }
    return map;
  });

  function getNodeColor(organName: string): string {
    const org = organMap()[organName.toLowerCase()];
    if (!org) return '#6b7280';
    return getStatusColor(org.status);
  }

  function getNodeOpacity(organName: string): number {
    if (!selected) return 0.8;
    if (selected === organName.toLowerCase()) return 1;
    // Check if connected
    const connected = CONNECTIONS.some(
      ([a, b]) =>
        (a === selected && b === organName) ||
        (a === organName && b === selected)
    );
    return connected ? 0.7 : 0.3;
  }

  function handleNodeClick(organName: string): void {
    const normalized = organName.toLowerCase();
    selectedOrgan.set(selected === normalized ? null : normalized);
  }

  function getNodeLabel(name: string): string {
    return capitalizeFirst(name);
  }
</script>

<svg
  class="organ-graph"
  viewBox="0 0 800 600"
  xmlns="http://www.w3.org/2000/svg"
>
  <!-- Background -->
  <rect width="800" height="600" fill="transparent" />

  <!-- Connection lines -->
  {#each CONNECTIONS as [source, target]}
    {@const src = NODE_POSITIONS[source]}
    {@const tgt = NODE_POSITIONS[target]}
    {@const isActive =
      selected === null ||
      selected === source ||
      selected === target}
    <line
      x1={src.x}
      y1={src.y}
      x2={tgt.x}
      y2={tgt.y}
      stroke={isActive ? 'var(--color-border, #374151)' : '#1f2937'}
      stroke-width={isActive ? 2 : 1}
      stroke-dasharray={isActive ? 'none' : '4 4'}
      class:connection-active={isActive}
      class:connection-inactive={!isActive}
      style="transition: stroke 0.3s ease, stroke-width 0.3s ease;"
    />
  {/each}

  <!-- Organ nodes -->
  {#each Object.entries(NODE_POSITIONS) as [name, pos]}
    {@const org = organMap()[name]}
    {@const nodeColor = getNodeColor(name)}
    {@const nodeOpacity = getNodeOpacity(name)}
    <g
      transform="translate({pos.x}, {pos.y})"
      style="cursor: pointer; opacity: {nodeOpacity};"
      onclick={() => handleNodeClick(name)}
      onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleNodeClick(name); }}
      role="button"
      tabindex="0"
      aria-label="{getNodeLabel(name)} organ"
      class="organ-node"
      class:selected={selected === name}
    >
      <!-- Selection ring -->
      {#if selected === name}
        <circle
          r="48"
          fill="none"
          stroke={nodeColor}
          stroke-width="2"
          opacity="0.4"
          class="pulse-ring"
        />
      {/if}

      <!-- Node background -->
      <circle
        r="40"
        fill="var(--color-bg-secondary, #1f2937)"
        stroke={nodeColor}
        stroke-width="2"
        class="node-bg"
        style="transition: stroke 0.3s ease;"
      />

      <!-- Health ring (small, inside node) -->
      <foreignObject x="-20" y="-20" width="40" height="40">
        <div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">
          {#if org}
            <HealthRing health={org.health} size={40} strokeWidth={4} />
          {/if}
        </div>
      </foreignObject>

      <!-- Organ label -->
      <text
        x="0"
        y="58"
        text-anchor="middle"
        fill="var(--color-text-primary, #f3f4f6)"
        font-size="12"
        font-family="var(--font-sans, sans-serif)"
        font-weight="500"
      >
        {getNodeLabel(name)}
      </text>
    </g>
  {/each}
</svg>

<style>
  .organ-graph {
    width: 100%;
    height: auto;
    max-height: 600px;
    user-select: none;
  }

  .organ-node {
    transition: opacity 0.4s ease;
    outline: none;
  }

  .organ-node:hover .node-bg {
    filter: brightness(1.3);
  }

  .organ-node.selected .node-bg {
    filter: brightness(1.2);
  }

  .connection-active {
    transition: stroke 0.3s ease, stroke-width 0.3s ease;
  }

  .connection-inactive {
    transition: stroke 0.3s ease, stroke-width 0.3s ease, stroke-dasharray 0.3s ease;
  }

  .pulse-ring {
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 0.4;
      r: 48;
    }
    50% {
      opacity: 0.1;
      r: 52;
    }
  }
</style>

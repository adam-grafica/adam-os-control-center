<script lang="ts">
  /**
   * AgentFleet.svelte — Right rail panel showing agent fleet status.
   */
  import { agents, tasks, tasksRunning, axonAgent, regularAgents, activeAlerts } from '$lib/stores/agents';
  import type { Agent, Task } from '$lib/stores/agents';

  let agentList: Agent[] = $state([]);
  let taskList: Task[] = $state([]);
  let runningCount: number = $state(0);
  let axon: Agent | null = $state(null);
  let regulars: Agent[] = $state([]);
  let alerts: number = $state(0);

  $effect(() => {
    const unsubs = [
      agents.subscribe((v) => { agentList = v; }),
      tasks.subscribe((v) => { taskList = v; }),
      tasksRunning.subscribe((v) => { runningCount = v; }),
      axonAgent.subscribe((v) => { axon = v; }),
      regularAgents.subscribe((v) => { regulars = v; }),
      activeAlerts.subscribe((v) => { alerts = v; }),
    ];
    return () => unsubs.forEach((fn) => fn());
  });

  let expandedSubs: Set<string> = $state(new Set());

  function toggleSubs(id: string) {
    if (expandedSubs.has(id)) {
      expandedSubs.delete(id);
    } else {
      expandedSubs.add(id);
    }
    expandedSubs = new Set(expandedSubs); // trigger reactivity
  }

  const recentToolCalls = $derived(
    taskList.filter((t) => t.status === 'running').slice(0, 5)
  );
</script>

<div class="agent-fleet">
  <!-- ─── AXON Card ─── -->
  {#if axon}
    <div class="axon-card">
      <div class="axon-header">
        <div class="axon-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="#a855f7" stroke-width="1.5" fill="none" />
            <circle cx="12" cy="12" r="4" fill="#a855f7" opacity="0.6" />
            <path d="M12 2 L12 6 M12 18 L12 22 M2 12 L6 12 M18 12 L22 12"
                  stroke="#a855f7" stroke-width="0.8" opacity="0.3" />
          </svg>
        </div>
        <div class="axon-info">
          <span class="axon-name">AXON</span>
          <span class="axon-type">Central Orchestrator</span>
        </div>
        <div class="axon-status" class:running={axon.status === 'running'} class:idle={axon.status === 'idle'} class:error={axon.status === 'error'}>
          {axon.status}
        </div>
      </div>
      <div class="axon-metrics">
        <div class="axon-metric">
          <span class="metric-label">Latency</span>
          <span class="metric-val font-mono">{axon.latency}ms</span>
        </div>
        <div class="axon-metric">
          <span class="metric-label">Tasks</span>
          <span class="metric-val font-mono">{runningCount}</span>
        </div>
        <div class="axon-metric">
          <span class="metric-label">Agents</span>
          <span class="metric-val font-mono">{agentList.length}</span>
        </div>
      </div>
      {#if axon.current_task}
        <div class="axon-current">
          <span class="current-label">Current Task:</span>
          <span class="current-val">{axon.current_task}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="axon-card axon-placeholder">
      <div class="axon-header">
        <span class="axon-name">AXON</span>
        <span class="axon-type">Waiting for connection...</span>
      </div>
    </div>
  {/if}

  <!-- ─── Active Agents ─── -->
  <div class="section-label">
    <span>Active Agents</span>
    {#if alerts > 0}
      <span class="alert-count">{alerts}</span>
    {/if}
  </div>

  <div class="agents-list">
    {#each regulars as agent}
      <div class="agent-card">
        <div class="agent-header">
          <div class="agent-dot" class:running={agent.status === 'running'} class:idle={agent.status === 'idle'} class:error={agent.status === 'error'}></div>
          <div class="agent-info">
            <span class="agent-name">{agent.name}</span>
            <span class="agent-type">{agent.type}</span>
          </div>
          <span class="agent-latency font-mono">{agent.latency}ms</span>
        </div>
        <div class="agent-details">
          {#if agent.current_task}
            <div class="agent-detail-row">
              <span class="detail-key">Task:</span>
              <span class="detail-val">{agent.current_task}</span>
            </div>
          {/if}
          {#if agent.current_tool}
            <div class="agent-detail-row">
              <span class="detail-key">Tool:</span>
              <span class="detail-val">{agent.current_tool}</span>
            </div>
          {/if}
        </div>

        <!-- Sub-agents toggle -->
        {#if agent.sub_agents && agent.sub_agents.length > 0}
          <button class="sub-toggle" onclick={() => toggleSubs(agent.id)}>
            {expandedSubs.has(agent.id) ? '▼' : '▶'} {agent.sub_agents.length} sub-agents
          </button>
          {#if expandedSubs.has(agent.id)}
            <div class="sub-agents">
              {#each agent.sub_agents as sub}
                <div class="sub-agent-row">
                  <div class="sub-dot" class:running={sub.status === 'running'} class:idle={sub.status === 'idle'}></div>
                  <span class="sub-name">{sub.name}</span>
                  <span class="sub-status">{sub.status}</span>
                  {#if sub.current_tool}
                    <span class="sub-tool">{sub.current_tool}</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </div>
    {:else}
      <div class="empty-state">No agents registered</div>
    {/each}
  </div>

  <!-- ─── Recent Tool Calls ─── -->
  {#if recentToolCalls.length > 0}
    <div class="section-label">Recent Tasks</div>
    <div class="tool-calls">
      {#each recentToolCalls as task}
        <div class="tool-call-row">
          <span class="task-status" class:running={task.status === 'running'} class:completed={task.status === 'completed'}></span>
          <span class="task-name">{task.title}</span>
          <span class="task-assignee">{task.assigned_to || '—'}</span>
        </div>
      {/each}
    </div>
  {/if}

  <!-- ─── Agent Tools Summary ─── -->
  {#if agentList.length > 0}
    <div class="section-label">Agent Tools</div>
    <div class="tools-summary">
      {#each agentList as agent}
        {#if agent.tools && agent.tools.length > 0}
          {#each agent.tools as tool}
            <div class="tool-chip" class:active={tool.status === 'active'} class:error={tool.status === 'error'}>
              <span class="tool-dot"></span>
              <span class="tool-name">{tool.name}</span>
            </div>
          {/each}
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .agent-fleet {
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-size: 0.75rem;
  }

  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Section Label ─── */
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #e2e8f0;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 4px 0;
  }

  .alert-count {
    font-size: 0.65rem;
    font-weight: 700;
    color: #ef4444;
    background: rgba(239,68,68,0.1);
    padding: 1px 6px;
    border-radius: 8px;
  }

  /* ─── AXON Card ─── */
  .axon-card {
    background: rgba(168,85,247,0.06);
    border: 1px solid rgba(168,85,247,0.2);
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .axon-placeholder {
    background: rgba(148,163,184,0.04);
    border-color: rgba(148,163,184,0.1);
  }

  .axon-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .axon-icon {
    flex-shrink: 0;
  }

  .axon-info {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .axon-name {
    font-size: 0.95rem;
    font-weight: 800;
    color: #a855f7;
    letter-spacing: -0.02em;
  }

  .axon-type {
    font-size: 0.6rem;
    color: #64748b;
    text-transform: uppercase;
  }

  .axon-status {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 8px;
    letter-spacing: 0.04em;
  }

  .axon-status.running { color: #22c55e; background: rgba(34,197,94,0.15); }
  .axon-status.idle { color: #94a3b8; background: rgba(148,163,184,0.15); }
  .axon-status.error { color: #ef4444; background: rgba(239,68,68,0.15); animation: pulseStatus 1.5s ease-in-out infinite; }

  @keyframes pulseStatus {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  .axon-metrics {
    display: flex;
    gap: 16px;
  }

  .axon-metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .axon-metric .metric-label {
    font-size: 0.6rem;
    color: #64748b;
    text-transform: uppercase;
  }

  .axon-metric .metric-val {
    font-size: 0.85rem;
    font-weight: 700;
    color: #e2e8f0;
  }

  .axon-current {
    display: flex;
    gap: 4px;
    font-size: 0.65rem;
  }

  .current-label {
    color: #64748b;
  }

  .current-val {
    color: #94a3b8;
  }

  /* ─── Agent Cards ─── */
  .agents-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .agent-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .agent-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .agent-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    background: #64748b;
  }

  .agent-dot.running { background: #22c55e; box-shadow: 0 0 5px rgba(34,197,94,0.5); }
  .agent-dot.idle { background: #94a3b8; }
  .agent-dot.error { background: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,0.5); animation: pulseError 1.5s ease infinite; }

  @keyframes pulseError {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .agent-info {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .agent-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .agent-type {
    font-size: 0.6rem;
    color: #64748b;
    text-transform: capitalize;
  }

  .agent-latency {
    font-size: 0.65rem;
    color: #94a3b8;
    flex-shrink: 0;
  }

  .agent-details {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .agent-detail-row {
    display: flex;
    gap: 4px;
    font-size: 0.65rem;
  }

  .agent-detail-row .detail-key { color: #64748b; }
  .agent-detail-row .detail-val { color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* Sub-agents */
  .sub-toggle {
    background: none;
    border: none;
    color: #64748b;
    font-size: 0.65rem;
    cursor: pointer;
    padding: 2px 0;
    text-align: left;
    transition: color 0.15s ease;
  }

  .sub-toggle:hover { color: #94a3b8; }

  .sub-agents {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding-left: 16px;
    border-left: 1px solid rgba(255,255,255,0.04);
  }

  .sub-agent-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.65rem;
  }

  .sub-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #64748b;
  }

  .sub-dot.running { background: #22c55e; }
  .sub-dot.idle { background: #94a3b8; }

  .sub-name {
    font-weight: 600;
    color: #94a3b8;
  }

  .sub-status {
    color: #64748b;
    text-transform: capitalize;
  }

  .sub-tool {
    color: #3b82f6;
    margin-left: auto;
  }

  .empty-state {
    font-size: 0.7rem;
    color: #475569;
    text-align: center;
    padding: 16px;
    font-style: italic;
    background: rgba(255,255,255,0.01);
    border-radius: 8px;
    border: 1px dashed rgba(255,255,255,0.04);
  }

  /* ─── Tool Calls ─── */
  .tool-calls {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .tool-call-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    background: rgba(255,255,255,0.02);
    border-radius: 6px;
    font-size: 0.65rem;
  }

  .task-status {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #64748b;
    flex-shrink: 0;
  }

  .task-status.running { background: #3b82f6; }
  .task-status.completed { background: #22c55e; }

  .task-name {
    flex: 1;
    color: #94a3b8;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .task-assignee {
    color: #64748b;
    font-size: 0.6rem;
  }

  /* ─── Tools Summary ─── */
  .tools-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .tool-chip {
    display: flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    font-size: 0.6rem;
  }

  .tool-chip.active { border-color: rgba(59,130,246,0.2); }
  .tool-chip.error { border-color: rgba(239,68,68,0.2); }

  .tool-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #64748b;
  }

  .tool-chip.active .tool-dot { background: #3b82f6; }
  .tool-chip.error .tool-dot { background: #ef4444; }

  .tool-name {
    color: #94a3b8;
  }
</style>

<script lang="ts">
  /**
   * PipelineView — Visual Pipeline de Manufactura
   *
   * Muestra las 7 fases del pipeline MIDI SOFT como nodos conectados
   * con glassmorphism, animaciones de flujo, y actualizaciones en vivo.
   */
  import { onMount } from 'svelte';
  import {
    pipelineData,
    pipelineProjects,
    pipelineOverview,
    fetchPipelineData,
    getPhaseDef,
    getAllPhaseDefs,
    phaseColor,
    projectProgress,
    type PipelineProject,
    type PipelinePhase,
    type PendingTask,
    type PipelineOverview,
  } from '$lib/stores/pipeline';

  // ─── Reactive State ───

  let projects: PipelineProject[] = $state([]);
  let overview: PipelineOverview | null = $state(null);
  let selectedProjectId: string | null = $state(null);
  let expandedProjectId: string | null = $state(null);
  let expandedPhaseId: number | null = $state(null);
  let viewMode: 'pipeline' | 'list' | 'detail' = $state('pipeline');

  $effect(() => {
    const unsub1 = pipelineProjects.subscribe((v) => { projects = v; });
    const unsub2 = pipelineOverview.subscribe((v) => { overview = v; });
    return () => { unsub1(); unsub2(); };
  });

  // If there are projects, select the first one by default
  $effect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      selectedProjectId = projects[0].project_id;
    }
  });

  const selectedProject = $derived(
    projects.find(p => p.project_id === selectedProjectId) ?? null
  );

  const phaseDefs = $derived(getAllPhaseDefs());

  // ─── Helpers ───

  function selectProject(id: string) {
    selectedProjectId = id;
    expandedPhaseId = null;
    viewMode = 'detail';
  }

  function toggleExpandProject(id: string) {
    expandedProjectId = expandedProjectId === id ? null : id;
  }

  function togglePhaseDetail(phaseId: number) {
    expandedPhaseId = expandedPhaseId === phaseId ? null : phaseId;
  }

  function goBack() {
    viewMode = 'pipeline';
    selectedProjectId = null;
  }

  function formatDate(iso: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('es-MX', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function getPhaseStatus(project: PipelineProject, phaseId: number): 'completed' | 'in_progress' | 'pending' {
    if (!project?.phases) return 'pending';
    const found = project.phases.find(p => p.phase_id === phaseId);
    if (found) return found.status as 'completed' | 'in_progress' | 'pending';
    return phaseId < project.current_phase ? 'completed' : 'pending';
  }

  function getPhaseDeliverables(project: PipelineProject, phaseId: number) {
    return project.phases.find(p => p.phase_id === phaseId)?.deliverables ?? [];
  }

  function getPhaseSignatories(project: PipelineProject, phaseId: number) {
    return project.phases.find(p => p.phase_id === phaseId)?.signatories ?? [];
  }

  function getTaskProgress(project: PipelineProject): string {
    const total = project.pending_tasks?.length ?? 0;
    const done = project.pending_tasks?.filter(t => t.status === 'completed').length ?? 0;
    if (total === 0) return 'No tasks';
    return `${done}/${total} tasks`;
  }

  function getProjectPhaseById(project: PipelineProject, phaseId: number): PipelinePhase | null {
    return project.phases.find(p => p.phase_id === phaseId) ?? null;
  }

  // ─── Initial Load ───

  onMount(() => {
    fetchPipelineData();
  });
</script>

<div class="pipeline-shell">
  <!-- ═══ HEADER ═══ -->
  <div class="pipeline-header">
    <div class="header-left">
      {#if viewMode === 'detail'}
        <button class="back-btn" onclick={goBack}>← Back</button>
      {/if}
      <h2 class="pipeline-title">
        {#if viewMode === 'pipeline'}
          🏭 Pipeline de Manufactura
        {:else if viewMode === 'detail' && selectedProject}
          🚧 {selectedProject.name}
        {:else}
          📋 Pipeline Overview
        {/if}
      </h2>
    </div>
    <div class="header-right">
      {#if overview}
        <div class="pipeline-stats">
          <span class="stat-badge">
            <span class="stat-num">{overview.total_projects}</span>
            <span class="stat-label">Projects</span>
          </span>
        </div>
      {/if}
      <div class="view-tabs">
        <button
          class="view-tab"
          class:active={viewMode === 'pipeline'}
          onclick={() => { viewMode = 'pipeline'; selectedProjectId = null; }}
        >Visual</button>
        <button
          class="view-tab"
          class:active={viewMode === 'list'}
          onclick={() => { viewMode = 'list'; selectedProjectId = null; expandedProjectId = null; }}
        >List</button>
      </div>
    </div>
  </div>

  <!-- ═══ PIPELINE VISUAL VIEW ═══ -->
  {#if viewMode === 'pipeline'}
    <div class="pipeline-visual">
      <!-- Phase Flow -->
      <div class="phase-flow">
        <div class="phase-track">
          {#each phaseDefs as phase, idx}
            <div class="phase-node-wrapper">
              <!-- Connector line (before node, except first) -->
              {#if idx > 0}
                <div class="phase-connector">
                  <div class="connector-line" class:connector-active={projects.some(p => p.current_phase >= phase.id)}></div>
                  <div class="connector-arrow" class:arrow-active={projects.some(p => p.current_phase >= phase.id)}>▶</div>
                </div>
              {/if}

              <!-- Phase Node -->
              <div
                class="phase-node glass"
                class:phase-active={projects.some(p => p.current_phase === phase.id)}
                class:phase-completed={projects.every(p => p.current_phase > phase.id)}
                style="--phase-color: {phaseColor(projects.some(p => p.current_phase === phase.id) ? 'in_progress' : projects.every(p => p.current_phase > phase.id) ? 'completed' : 'pending')};"
                onclick={() => {
                  if (projects.length > 0) {
                    selectedProjectId = projects[0].project_id;
                    expandedPhaseId = phase.id;
                    viewMode = 'detail';
                  }
                }}
              >
                <div class="phase-icon">{phase.icon}</div>
                <div class="phase-number">Phase {phase.id}</div>
                <div class="phase-name">{phase.name}</div>
                <div class="phase-dept">{phase.dept}</div>
                {#if projects.some(p => p.current_phase === phase.id)}
                  <div class="phase-active-badge">{projects.filter(p => p.current_phase === phase.id).length} active</div>
                {:else if projects.every(p => p.current_phase > phase.id)}
                  <div class="phase-done-badge">✓ Done</div>
                {:else}
                  <div class="phase-pending-badge">Pending</div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Project Cards -->
      <div class="project-cards-section">
        <h3 class="section-title">Active Projects</h3>
        {#if projects.length === 0}
          <div class="empty-state">
            <span class="empty-icon">📦</span>
            <span class="empty-text">No projects in pipeline yet</span>
          </div>
        {:else}
          <div class="project-cards">
            {#each projects as project}
              <div
                class="project-card glass"
                class:card-selected={selectedProjectId === project.project_id}
                onclick={() => selectProject(project.project_id)}
              >
                <div class="card-header">
                  <span class="card-team-badge" class:midisoft={project.team === 'midisoft'} class:adamgrafica={project.team === 'adamgrafica'}>
                    {project.team === 'midisoft' ? '🎵 MIDI' : '🎨 AG'}
                  </span>
                  <span class="card-status-dot" style="background: {phaseColor('in_progress')};"></span>
                </div>
                <div class="card-name">{project.name}</div>
                <div class="card-phase">
                  <span class="card-phase-icon">{getPhaseDef(project.current_phase).icon}</span>
                  <span class="card-phase-text">{project.phase_name}</span>
                </div>
                <div class="card-dept">{project.active_department}</div>
                <div class="card-progress-bar">
                  <div class="progress-track">
                    <div class="progress-fill" style="width: {projectProgress(project)}%;"></div>
                  </div>
                  <span class="progress-text">{projectProgress(project)}%</span>
                </div>
                <div class="card-progress-text">{project.agent_progress}</div>
                <div class="card-tasks">📋 {getTaskProgress(project)}</div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

  <!-- ═══ LIST VIEW ═══ -->
  {:else if viewMode === 'list'}
    <div class="pipeline-list">
      {#if projects.length === 0}
        <div class="empty-state">
          <span class="empty-icon">📦</span>
          <span class="empty-text">No projects in pipeline</span>
        </div>
      {:else}
        <div class="list-table">
          <div class="list-header">
            <span class="list-col-id">ID</span>
            <span class="list-col-name">Project</span>
            <span class="list-col-team">Team</span>
            <span class="list-col-phase">Phase</span>
            <span class="list-col-dept">Department</span>
            <span class="list-col-progress">Progress</span>
            <span class="list-col-tasks">Tasks</span>
          </div>
          {#each projects as project}
            <div
              class="list-row"
              class:list-row-selected={selectedProjectId === project.project_id}
              onclick={() => selectProject(project.project_id)}
            >
              <span class="list-col-id mono">{project.project_id}</span>
              <span class="list-col-name">{project.name}</span>
              <span class="list-col-team">
                <span class="team-tag" class:midisoft={project.team === 'midisoft'} class:adamgrafica={project.team === 'adamgrafica'}>
                  {project.team}
                </span>
              </span>
              <span class="list-col-phase">
                <span class="phase-tag" style="--phase-tag-color: {phaseColor('in_progress')};">
                  {getPhaseDef(project.current_phase).icon} {project.phase_name}
                </span>
              </span>
              <span class="list-col-dept">{project.active_department}</span>
              <span class="list-col-progress">
                <div class="mini-progress">
                  <div class="mini-track">
                    <div class="mini-fill" style="width: {projectProgress(project)}%;"></div>
                  </div>
                  <span class="mini-text">{projectProgress(project)}%</span>
                </div>
              </span>
              <span class="list-col-tasks">{getTaskProgress(project)}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  <!-- ═══ DETAIL VIEW ═══ -->
  {:else if viewMode === 'detail' && selectedProject}
    <div class="pipeline-detail">
      <!-- Project Overview -->
      <div class="detail-overview glass">
        <div class="overview-top">
          <div class="overview-title-section">
            <span class="overview-team-badge" class:midisoft={selectedProject.team === 'midisoft'} class:adamgrafica={selectedProject.team === 'adamgrafica'}>
              {selectedProject.team === 'midisoft' ? '🎵 MIDI SOFT' : '🎨 AdamGráfica'}
            </span>
            <h3 class="overview-name">{selectedProject.name}</h3>
          </div>
          <div class="overview-stats">
            <div class="overview-stat">
              <span class="stat-value">{selectedProject.current_phase}/7</span>
              <span class="stat-desc">Phase</span>
            </div>
            <div class="overview-stat">
              <span class="stat-value">{projectProgress(selectedProject)}%</span>
              <span class="stat-desc">Complete</span>
            </div>
            <div class="overview-stat">
              <span class="stat-value">{selectedProject.pending_tasks?.length ?? 0}</span>
              <span class="stat-desc">Tasks</span>
            </div>
          </div>
        </div>
        <div class="overview-progress-bar">
          <div class="overview-progress-track">
            {#each phaseDefs as phase, idx}
              <div
                class="overview-phase-segment"
                class:segment-completed={getPhaseStatus(selectedProject, phase.id) === 'completed'}
                class:segment-active={getPhaseStatus(selectedProject, phase.id) === 'in_progress'}
                style="width: {100 / 7}%; left: {idx * (100 / 7)}%;"
                title="{phase.name}"
              >
                <div class="segment-label">{phase.icon}</div>
              </div>
            {/each}
          </div>
        </div>
        <div class="overview-agent-info">
          <span class="agent-label">🤖 Agent Progress:</span>
          <span class="agent-value">{selectedProject.agent_progress}</span>
        </div>
      </div>

      <!-- Current Phase Highlight -->
      {#if selectedProject.phases.length > 0}
        <div class="detail-phases">
          {#each phaseDefs as phaseDef}
            {@const phaseStatus = getPhaseStatus(selectedProject, phaseDef.id)}
            {@const phaseData = getProjectPhaseById(selectedProject, phaseDef.id)}
            <div
              class="phase-detail-card glass"
              class:phase-detail-active={phaseStatus === 'in_progress'}
              class:phase-detail-completed={phaseStatus === 'completed'}
              style="--phase-card-color: {phaseColor(phaseStatus)};"
            >
              <div class="phase-detail-header" onclick={() => togglePhaseDetail(phaseDef.id)}>
                <div class="phase-detail-left">
                  <span class="phase-detail-icon">{phaseDef.icon}</span>
                  <div class="phase-detail-info">
                    <span class="phase-detail-name">Phase {phaseDef.id}: {phaseDef.name}</span>
                    <span class="phase-detail-dept">{phaseDef.dept}</span>
                  </div>
                </div>
                <div class="phase-detail-right">
                  <span class="phase-status-badge" class:status-completed={phaseStatus === 'completed'} class:status-active={phaseStatus === 'in_progress'} class:status-pending={phaseStatus === 'pending'}>
                    {phaseStatus === 'completed' ? '✓ Complete' : phaseStatus === 'in_progress' ? '● Active' : '○ Pending'}
                  </span>
                  {#if expandedPhaseId === phaseDef.id}
                    <span class="expand-arrow expanded">▼</span>
                  {:else}
                    <span class="expand-arrow">▶</span>
                  {/if}
                </div>
              </div>

              {#if expandedPhaseId === phaseDef.id}
                <div class="phase-detail-body">
                  <p class="phase-description">{phaseDef.desc}</p>

                  {#if phaseData?.deliverables && phaseData.deliverables.length > 0}
                    <div class="detail-section">
                      <h4 class="detail-section-title">📦 Deliverables</h4>
                      <div class="deliverable-list">
                        {#each phaseData.deliverables as del}
                          <div class="deliverable-item">
                            <span class="del-icon">📄</span>
                            <span class="del-title">{del.title}</span>
                            {#if del.url}
                              <a href={del.url} class="del-url" target="_blank">🔗</a>
                            {/if}
                            <span class="del-date">{formatDate(del.added_at)}</span>
                          </div>
                        {/each}
                      </div>
                    </div>
                  {:else if phaseStatus === 'completed'}
                    <div class="detail-section">
                      <p class="no-data">No deliverables recorded for this phase.</p>
                    </div>
                  {/if}

                  {#if phaseData?.signatories && phaseData.signatories.length > 0}
                    <div class="detail-section">
                      <h4 class="detail-section-title">✍️ Signatories</h4>
                      <div class="signatory-list">
                        {#each phaseData.signatories as sig}
                          <span class="signatory-tag">{sig}</span>
                        {/each}
                      </div>
                    </div>
                  {/if}

                  {#if phaseData?.started_at}
                    <div class="detail-section">
                      <h4 class="detail-section-title">⏱ Timeline</h4>
                      <div class="timeline-info">
                        <span>Started: {formatDate(phaseData.started_at)}</span>
                        {#if phaseData.completed_at}
                          <span>Completed: {formatDate(phaseData.completed_at)}</span>
                        {/if}
                      </div>
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

      <!-- Pending Tasks -->
      {#if selectedProject.pending_tasks && selectedProject.pending_tasks.length > 0}
        <div class="detail-tasks glass">
          <h3 class="detail-section-title">📋 Pending Tasks</h3>
          <div class="tasks-list">
            {#each selectedProject.pending_tasks as task}
              <div class="task-item" class:task-done={task.status === 'completed'}>
                <span class="task-check">{task.status === 'completed' ? '✅' : '⬜'}</span>
                <span class="task-title">{task.title}</span>
                <span class="task-dept">{task.department}</span>
                {#if task.completed_at}
                  <span class="task-date">{formatDate(task.completed_at)}</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  /* ═══ SHELL ═══ */
  .pipeline-shell {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    background: transparent;
    color: #e2e8f0;
    font-family: var(--font-sans, 'Inter', sans-serif);
  }

  /* ═══ HEADER ═══ */
  .pipeline-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    flex-shrink: 0;
    gap: 12px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .back-btn {
    padding: 4px 12px;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px;
    background: rgba(255,255,255,0.03);
    color: #94a3b8;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .back-btn:hover {
    background: rgba(255,255,255,0.06);
    color: #e2e8f0;
  }

  .pipeline-title {
    font-size: 0.9rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .pipeline-stats {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .stat-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.15);
    border-radius: 12px;
    font-size: 0.7rem;
  }
  .stat-num {
    font-weight: 700;
    color: #3b82f6;
  }
  .stat-label {
    color: #64748b;
  }

  .view-tabs {
    display: flex;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    overflow: hidden;
  }
  .view-tab {
    padding: 4px 12px;
    border: none;
    background: transparent;
    color: #64748b;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .view-tab.active {
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
  }
  .view-tab:hover {
    color: #94a3b8;
  }

  /* ═══ PIPELINE VISUAL ═══ */
  .pipeline-visual {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .pipeline-visual::-webkit-scrollbar {
    width: 4px;
  }
  .pipeline-visual::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.04);
    border-radius: 2px;
  }

  /* ─── Phase Flow ─── */
  .phase-flow {
    overflow-x: auto;
    padding: 8px 0;
  }
  .phase-flow::-webkit-scrollbar { height: 3px; }
  .phase-flow::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 2px; }

  .phase-track {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    min-width: max-content;
    padding: 0 12px;
  }

  .phase-node-wrapper {
    display: flex;
    align-items: center;
  }

  /* ─── Connectors ─── */
  .phase-connector {
    display: flex;
    align-items: center;
    width: 48px;
    position: relative;
  }

  .connector-line {
    flex: 1;
    height: 2px;
    background: rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
    transition: background 0.3s ease;
  }
  .connector-line.connector-active {
    background: linear-gradient(90deg, rgba(59,130,246,0.3), rgba(59,130,246,0.1));
  }
  .connector-line.connector-active::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, #3b82f6, transparent);
    animation: flowDash 1.5s linear infinite;
  }

  .connector-arrow {
    font-size: 0.4rem;
    color: rgba(255,255,255,0.1);
    margin-left: 2px;
    transition: color 0.3s ease;
  }
  .connector-arrow.arrow-active {
    color: #3b82f6;
    animation: arrowPulse 1.5s ease-in-out infinite;
  }

  @keyframes flowDash {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
  @keyframes arrowPulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }

  /* ─── Phase Nodes ─── */
  .phase-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 10px 14px;
    min-width: 100px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    text-align: center;
  }
  .phase-node:hover {
    transform: translateY(-2px);
    border-color: rgba(255,255,255,0.12);
  }

  .glass {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
  }

  .phase-node.phase-active {
    border-color: rgba(59,130,246,0.3);
    box-shadow: 0 0 20px rgba(59,130,246,0.15), inset 0 0 20px rgba(59,130,246,0.03);
    animation: activeGlow 2s ease-in-out infinite;
  }
  .phase-node.phase-completed {
    border-color: rgba(34,197,94,0.15);
  }

  @keyframes activeGlow {
    0%, 100% { box-shadow: 0 0 15px rgba(59,130,246,0.1), inset 0 0 15px rgba(59,130,246,0.02); }
    50% { box-shadow: 0 0 25px rgba(59,130,246,0.2), inset 0 0 25px rgba(59,130,246,0.04); }
  }

  .phase-icon {
    font-size: 1.5rem;
  }
  .phase-number {
    font-size: 0.6rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .phase-name {
    font-size: 0.7rem;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.2;
  }
  .phase-dept {
    font-size: 0.6rem;
    color: #64748b;
  }

  .phase-active-badge, .phase-done-badge, .phase-pending-badge {
    font-size: 0.55rem;
    font-weight: 600;
    padding: 1px 8px;
    border-radius: 8px;
    margin-top: 3px;
  }
  .phase-active-badge {
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
    animation: pulse 2s ease-in-out infinite;
  }
  .phase-done-badge {
    background: rgba(34,197,94,0.12);
    color: #4ade80;
  }
  .phase-pending-badge {
    background: rgba(71,85,105,0.12);
    color: #64748b;
  }

  /* ─── Phase Description ─── */
  .phase-description {
    font-size: 0.75rem;
    color: #94a3b8;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    margin-bottom: 8px;
  }

  /* ─── Project Cards Section ─── */
  .project-cards-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #cbd5e1;
    margin: 0;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 32px;
    color: #475569;
  }
  .empty-icon {
    font-size: 2rem;
  }
  .empty-text {
    font-size: 0.8rem;
  }

  .project-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
  }

  .project-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.25s ease;
    border-radius: 10px;
  }
  .project-card:hover {
    border-color: rgba(255,255,255,0.1);
    transform: translateY(-1px);
  }
  .project-card.card-selected {
    border-color: rgba(59,130,246,0.25);
    background: rgba(59,130,246,0.04);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-team-badge {
    font-size: 0.55rem;
    font-weight: 700;
    padding: 1px 8px;
    border-radius: 6px;
    letter-spacing: 0.04em;
  }
  .card-team-badge.midisoft {
    background: rgba(59,130,246,0.1);
    color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.15);
  }
  .card-team-badge.adamgrafica {
    background: rgba(168,85,247,0.1);
    color: #a78bfa;
    border: 1px solid rgba(168,85,247,0.15);
  }

  .card-status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .card-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .card-phase {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.7rem;
    color: #94a3b8;
  }
  .card-phase-icon {
    font-size: 0.85rem;
  }

  .card-dept {
    font-size: 0.6rem;
    color: #64748b;
  }

  .card-progress-bar {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .progress-track {
    flex: 1;
    height: 3px;
    background: rgba(255,255,255,0.05);
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    border-radius: 2px;
    transition: width 0.5s ease;
  }
  .progress-text {
    font-size: 0.6rem;
    font-weight: 600;
    color: #64748b;
    min-width: 28px;
    text-align: right;
  }

  .card-progress-text {
    font-size: 0.65rem;
    color: #64748b;
  }
  .card-tasks {
    font-size: 0.65rem;
    color: #94a3b8;
  }

  /* ═══ LIST VIEW ═══ */
  .pipeline-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .list-table {
    display: flex;
    flex-direction: column;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.04);
  }

  .list-header {
    display: flex;
    align-items: center;
    padding: 8px 14px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.6rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .list-header > span, .list-row > span {
    flex: 1;
    padding: 0 4px;
  }

  .list-col-id { flex: 0.5 !important; }
  .list-col-name { flex: 1.5 !important; }
  .list-col-team { flex: 0.6 !important; }
  .list-col-phase { flex: 1.2 !important; }
  .list-col-dept { flex: 1 !important; }
  .list-col-progress { flex: 0.8 !important; }
  .list-col-tasks { flex: 0.6 !important; }

  .mono {
    font-family: var(--font-mono, monospace);
    font-size: 0.65rem;
    color: #64748b;
  }

  .list-row {
    display: flex;
    align-items: center;
    padding: 8px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.02);
    font-size: 0.7rem;
    color: #cbd5e1;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .list-row:last-child {
    border-bottom: none;
  }
  .list-row:hover {
    background: rgba(255,255,255,0.02);
  }
  .list-row.list-row-selected {
    background: rgba(59,130,246,0.04);
  }

  .team-tag {
    font-size: 0.55rem;
    font-weight: 600;
    padding: 1px 8px;
    border-radius: 6px;
  }
  .team-tag.midisoft {
    background: rgba(59,130,246,0.1);
    color: #60a5fa;
  }
  .team-tag.adamgrafica {
    background: rgba(168,85,247,0.1);
    color: #a78bfa;
  }

  .phase-tag {
    font-size: 0.65rem;
    padding: 1px 8px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.06);
  }

  .mini-progress {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .mini-track {
    width: 50px;
    height: 3px;
    background: rgba(255,255,255,0.05);
    border-radius: 2px;
    overflow: hidden;
  }
  .mini-fill {
    height: 100%;
    background: #3b82f6;
    border-radius: 2px;
    transition: width 0.5s ease;
  }
  .mini-text {
    font-size: 0.6rem;
    color: #64748b;
  }

  /* ═══ DETAIL VIEW ═══ */
  .pipeline-detail {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* Overview Card */
  .detail-overview {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .overview-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .overview-title-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .overview-team-badge {
    font-size: 0.55rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 6px;
    letter-spacing: 0.04em;
    width: fit-content;
  }
  .overview-team-badge.midisoft {
    background: rgba(59,130,246,0.1);
    color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.15);
  }
  .overview-team-badge.adamgrafica {
    background: rgba(168,85,247,0.1);
    color: #a78bfa;
    border: 1px solid rgba(168,85,247,0.15);
  }

  .overview-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0;
  }

  .overview-stats {
    display: flex;
    gap: 16px;
  }
  .overview-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .stat-value {
    font-size: 1.2rem;
    font-weight: 700;
    color: #e2e8f0;
  }
  .stat-desc {
    font-size: 0.55rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .overview-progress-bar {
    padding: 4px 0;
  }
  .overview-progress-track {
    display: flex;
    height: 24px;
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
  }
  .overview-phase-segment {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    position: relative;
    background: rgba(255,255,255,0.02);
  }
  .overview-phase-segment.segment-completed {
    background: rgba(34,197,94,0.12);
  }
  .overview-phase-segment.segment-active {
    background: rgba(59,130,246,0.15);
    animation: segmentPulse 2s ease-in-out infinite;
  }

  @keyframes segmentPulse {
    0%, 100% { background: rgba(59,130,246,0.12); }
    50% { background: rgba(59,130,246,0.2); }
  }

  .segment-label {
    font-size: 0.7rem;
  }

  .overview-agent-info {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
  }
  .agent-label {
    color: #94a3b8;
  }
  .agent-value {
    color: #60a5fa;
    font-weight: 500;
  }

  /* ─── Phase Detail Cards ─── */
  .detail-phases {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .phase-detail-card {
    border-radius: 10px;
    overflow: hidden;
    transition: all 0.25s ease;
  }
  .phase-detail-card.phase-detail-active {
    border-color: rgba(59,130,246,0.2);
    box-shadow: 0 0 12px rgba(59,130,246,0.08);
  }
  .phase-detail-card.phase-detail-completed {
    border-color: rgba(34,197,94,0.08);
  }

  .phase-detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .phase-detail-header:hover {
    background: rgba(255,255,255,0.015);
  }

  .phase-detail-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .phase-detail-icon {
    font-size: 1.2rem;
  }
  .phase-detail-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .phase-detail-name {
    font-size: 0.75rem;
    font-weight: 600;
    color: #e2e8f0;
  }
  .phase-detail-dept {
    font-size: 0.6rem;
    color: #64748b;
  }

  .phase-detail-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .phase-status-badge {
    font-size: 0.55rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 8px;
  }
  .status-completed {
    background: rgba(34,197,94,0.1);
    color: #4ade80;
  }
  .status-active {
    background: rgba(59,130,246,0.1);
    color: #60a5fa;
  }
  .status-pending {
    background: rgba(71,85,105,0.1);
    color: #64748b;
  }

  .expand-arrow {
    font-size: 0.6rem;
    color: #64748b;
    transition: transform 0.2s ease;
  }
  .expand-arrow.expanded {
    transform: rotate(180deg);
  }

  .phase-detail-body {
    padding: 0 14px 12px;
    border-top: 1px solid rgba(255,255,255,0.03);
    animation: slideDown 0.2s ease;
  }

  @keyframes slideDown {
    from { opacity: 0; max-height: 0; }
    to { opacity: 1; max-height: 500px; }
  }

  .detail-section {
    margin-top: 8px;
  }
  .detail-section-title {
    font-size: 0.7rem;
    font-weight: 700;
    color: #94a3b8;
    margin: 0 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .no-data {
    font-size: 0.7rem;
    color: #475569;
    font-style: italic;
  }

  .deliverable-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .deliverable-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: rgba(255,255,255,0.02);
    border-radius: 6px;
    font-size: 0.7rem;
  }
  .del-icon {
    font-size: 0.75rem;
  }
  .del-title {
    flex: 1;
    color: #cbd5e1;
  }
  .del-url {
    font-size: 0.7rem;
    text-decoration: none;
  }
  .del-date {
    font-size: 0.55rem;
    color: #475569;
  }

  .signatory-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .signatory-tag {
    font-size: 0.6rem;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(139,92,246,0.08);
    color: #a78bfa;
    border: 1px solid rgba(139,92,246,0.1);
  }

  .timeline-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.7rem;
    color: #94a3b8;
  }

  /* ─── Pending Tasks ─── */
  .detail-tasks {
    padding: 14px;
  }
  .tasks-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .task-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.7rem;
    transition: all 0.2s ease;
  }
  .task-item:hover {
    background: rgba(255,255,255,0.02);
  }
  .task-item.task-done {
    opacity: 0.5;
  }
  .task-check {
    font-size: 0.8rem;
  }
  .task-title {
    flex: 1;
    color: #cbd5e1;
  }
  .task-dept {
    font-size: 0.55rem;
    color: #64748b;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(255,255,255,0.03);
  }
  .task-date {
    font-size: 0.55rem;
    color: #475569;
  }

  /* ═══ RESPONSIVE ═══ */
  @media (max-width: 1200px) {
    .project-cards {
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
  }

  @media (max-width: 900px) {
    .pipeline-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    .header-right {
      width: 100%;
      justify-content: space-between;
    }
    .phase-track {
      justify-content: flex-start;
    }
    .project-cards {
      grid-template-columns: 1fr 1fr;
    }
    .overview-top {
      flex-direction: column;
    }
  }

  @media (max-width: 640px) {
    .project-cards {
      grid-template-columns: 1fr;
    }
    .list-header, .list-row {
      font-size: 0.6rem;
      padding: 6px 10px;
    }
    .pipeline-visual, .pipeline-list, .pipeline-detail {
      padding: 10px;
    }
    .phase-node {
      min-width: 80px;
      padding: 8px 10px;
    }
    .phase-connector {
      width: 24px;
    }
  }

  /* Global pulse animation */
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>

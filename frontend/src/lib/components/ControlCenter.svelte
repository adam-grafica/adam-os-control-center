<script lang="ts">
  /**
   * ControlCenter.svelte — Left rail navigation with tabs/sidebar.
   */
  type Tab = 'kanban' | 'files' | 'config' | 'providers' | 'emergency';

  let activeTab: Tab = $state('kanban');
  let showingConfirm = $state<string | null>(null);

  // ─── Tab Config ───
  const tabs: Array<{ id: Tab; label: string; icon: string }> = [
    { id: 'kanban', label: 'Kanban', icon: '📋' },
    { id: 'files', label: 'Files', icon: '📁' },
    { id: 'config', label: 'Config', icon: '⚙️' },
    { id: 'providers', label: 'APIs', icon: '🔌' },
    { id: 'emergency', label: 'Emergency', icon: '🆘' },
  ];

  // ─── Kanban State ───
  const kanbanCols = ['backlog', 'ready', 'running', 'blocked', 'review', 'done'] as const;
  type KanbanStatus = typeof kanbanCols[number];

  interface KanbanTask {
    id: string;
    title: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    assignee: string;
    status: KanbanStatus;
  }

  let kanbanTasks = $state<KanbanTask[]>([
    { id: 't1', title: 'Initialize ADAM OS', priority: 'high', assignee: 'AXON', status: 'running' },
    { id: 't2', title: 'Configure API providers', priority: 'medium', assignee: 'agent-1', status: 'backlog' },
    { id: 't3', title: 'Run system diagnostics', priority: 'high', assignee: 'agent-2', status: 'ready' },
    { id: 't4', title: 'Process data batch #42', priority: 'low', assignee: 'agent-3', status: 'done' },
    { id: 't5', title: 'Security audit', priority: 'critical', assignee: 'AXON', status: 'review' },
  ]);

  let showNewTask = $state(false);
  let newTaskTitle = $state('');
  let newTaskPriority: KanbanTask['priority'] = $state('medium');
  let newTaskAssignee = $state('');

  function createTask() {
    if (!newTaskTitle.trim()) return;
    kanbanTasks = [...kanbanTasks, {
      id: `t-${Date.now()}`,
      title: newTaskTitle.trim(),
      priority: newTaskPriority,
      assignee: newTaskAssignee || 'unassigned',
      status: 'backlog' as KanbanStatus,
    }];
    newTaskTitle = '';
    newTaskAssignee = '';
    showNewTask = false;
  }

  function moveTask(taskId: string, direction: -1 | 1) {
    kanbanTasks = kanbanTasks.map((t) => {
      if (t.id !== taskId) return t;
      const idx = kanbanCols.indexOf(t.status);
      const newIdx = Math.max(0, Math.min(kanbanCols.length - 1, idx + direction));
      return { ...t, status: kanbanCols[newIdx] };
    });
  }

  function getPriorityColor(p: string): string {
    switch (p) {
      case 'critical': return '#ef4444';
      case 'high': return '#eab308';
      case 'medium': return '#3b82f6';
      case 'low': return '#64748b';
      default: return '#94a3b8';
    }
  }

  function getTasksByCol(col: KanbanStatus) {
    return kanbanTasks.filter((t) => t.status === col);
  }

  // ─── File Tree State ───
  interface FileNode {
    name: string;
    type: 'file' | 'folder';
    children?: FileNode[];
    expanded?: boolean;
  }

  let fileTree = $state<FileNode[]>([
    {
      name: 'src', type: 'folder', expanded: true, children: [
        { name: 'lib', type: 'folder', expanded: true, children: [
          { name: 'stores', type: 'folder', children: [
            { name: 'sse.ts', type: 'file' },
            { name: 'infra.ts', type: 'file' },
            { name: 'agents.ts', type: 'file' },
          ]},
          { name: 'components', type: 'folder', children: [
            { name: 'TopBar.svelte', type: 'file' },
            { name: 'OrganismBody.svelte', type: 'file' },
          ]},
        ]},
        { name: 'routes', type: 'folder', children: [
          { name: '+page.svelte', type: 'file' },
          { name: '+layout.svelte', type: 'file' },
        ]},
      ],
    },
    { name: 'package.json', type: 'file' },
    { name: 'static', type: 'folder', children: [
      { name: 'favicon.svg', type: 'file' },
    ]},
  ]);

  let previewFile = $state<string | null>(null);

  function toggleFolder(node: FileNode) {
    if (node.type === 'folder') {
      node.expanded = !node.expanded;
      fileTree = [...fileTree];
    } else {
      previewFile = node.name;
    }
  }

  function renderTree(nodes: FileNode[], depth: number = 0): Array<{ node: FileNode; depth: number; visible: boolean }> {
    const result: Array<{ node: FileNode; depth: number; visible: boolean }> = [];
    for (const node of nodes) {
      result.push({ node, depth, visible: true });
      if (node.type === 'folder' && node.expanded && node.children) {
        result.push(...renderTree(node.children, depth + 1));
      }
    }
    return result;
  }

  // ─── Config State ───
  let refreshInterval = $state(2000);
  let ramWarningThreshold = $state(75);
  let ramCriticalThreshold = $state(90);
  let darkModeEnabled = $state(true);
  let configSaved = $state(false);

  async function saveConfig() {
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          refresh_interval: refreshInterval,
          ram_warning_threshold: ramWarningThreshold,
          ram_critical_threshold: ramCriticalThreshold,
          dark_mode: darkModeEnabled,
        }),
      });
      configSaved = true;
      setTimeout(() => { configSaved = false; }, 3000);
    } catch {
      console.error('Failed to save config');
    }
  }

  // ─── API Providers State ───
  interface ApiProvider {
    name: string;
    status: 'online' | 'offline' | 'error';
    last_call: string;
    tokens_used: number;
    enabled: boolean;
  }

  let apiProviders = $state<ApiProvider[]>([
    { name: 'OpenAI', status: 'online', last_call: '2s ago', tokens_used: 1250000, enabled: true },
    { name: 'Anthropic', status: 'online', last_call: '5s ago', tokens_used: 890000, enabled: true },
    { name: 'Groq', status: 'offline', last_call: '1m ago', tokens_used: 450000, enabled: true },
    { name: 'Mistral', status: 'online', last_call: '12s ago', tokens_used: 320000, enabled: false },
  ]);

  function toggleProvider(name: string) {
    apiProviders = apiProviders.map((p) =>
      p.name === name ? { ...p, enabled: !p.enabled } : p
    );
  }

  // ─── Emergency Actions ───
  function confirmAction(action: string) {
    showingConfirm = action;
  }

  function executeAction() {
    if (!showingConfirm) return;
    switch (showingConfirm) {
      case 'restart':
        fetch('/api/control/restart', { method: 'POST' }).catch(() => {});
        break;
      case 'safemode':
        fetch('/api/control/safe-mode', { method: 'POST' }).catch(() => {});
        break;
      case 'cache':
        fetch('/api/control/clear-cache', { method: 'POST' }).catch(() => {});
        break;
    }
    showingConfirm = null;
  }
</script>

<div class="control-center">
  <!-- Tab Navigation -->
  <div class="tab-nav">
    {#each tabs as tab}
      <button
        class="tab-btn"
        class:active={activeTab === tab.id}
        onclick={() => { activeTab = tab.id; }}
        title={tab.label}
      >
        <span class="tab-icon">{tab.icon}</span>
        <span class="tab-label">{tab.label}</span>
      </button>
    {/each}
  </div>

  <!-- Tab Content -->
  <div class="tab-content">
    {#if activeTab === 'kanban'}
      <!-- ═══ KANBAN BOARD ═══ -->
      <div class="kanban-board">
        <div class="kanban-header">
          <h3 class="tab-title">📋 Kanban Board</h3>
          <button class="small-btn" onclick={() => { showNewTask = !showNewTask; }}>
            {showNewTask ? '✕' : '+ New Task'}
          </button>
        </div>

        {#if showNewTask}
          <div class="new-task-form">
            <input type="text" class="nt-input" placeholder="Task title..." bind:value={newTaskTitle} />
            <div class="nt-row">
              <select class="nt-select" bind:value={newTaskPriority}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <input type="text" class="nt-input" placeholder="Assignee" bind:value={newTaskAssignee} />
              <button class="small-btn primary" onclick={createTask}>Create</button>
            </div>
          </div>
        {/if}

        <div class="kanban-columns">
          {#each kanbanCols as col}
            <div class="kanban-col">
              <div class="col-header">
                <span class="col-name">{col}</span>
                <span class="col-count">{getTasksByCol(col).length}</span>
              </div>
              <div class="col-cards">
                {#each getTasksByCol(col) as task}
                  <div class="kanban-card" style="border-left-color: {getPriorityColor(task.priority)};">
                    <div class="card-header">
                      <span class="card-priority" style="color: {getPriorityColor(task.priority)};">
                        {task.priority}
                      </span>
                      <span class="card-assignee">@{task.assignee}</span>
                    </div>
                    <div class="card-title">{task.title}</div>
                    <div class="card-actions">
                      <button class="card-btn" onclick={() => moveTask(task.id, -1)} disabled={kanbanCols.indexOf(col) === 0}>‹</button>
                      <button class="card-btn" onclick={() => moveTask(task.id, 1)} disabled={kanbanCols.indexOf(col) === kanbanCols.length - 1}>›</button>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>

    {:else if activeTab === 'files'}
      <!-- ═══ FILE TREE ═══ -->
      <div class="file-panel">
        <h3 class="tab-title">📁 File Tree</h3>
        <div class="file-tree">
          {#each renderTree(fileTree) as { node, depth }}
            <div
              class="file-node"
              style="padding-left: {8 + depth * 14}px;"
              onclick={() => toggleFolder(node)}
              role="treeitem"
              aria-selected={false}
              tabindex="0"
              onkeydown={(e) => { if (e.key === 'Enter') toggleFolder(node); }}
            >
              <span class="node-icon">
                {node.type === 'folder' ? (node.expanded ? '📂' : '📁') : '📄'}
              </span>
              <span class="node-name">{node.name}</span>
            </div>
          {/each}
        </div>

        {#if previewFile}
          <div class="file-preview">
            <div class="preview-header">
              <span>Preview: {previewFile}</span>
              <button class="small-btn" onclick={() => { previewFile = null; }}>✕</button>
            </div>
            <div class="preview-body">
              <span class="preview-placeholder">Quick preview of {previewFile}</span>
            </div>
          </div>
        {/if}
      </div>

    {:else if activeTab === 'config'}
      <!-- ═══ CONFIG ═══ -->
      <div class="config-panel">
        <h3 class="tab-title">⚙️ Configuration</h3>

        <div class="config-group">
          <div class="config-label" id="refresh-label">
            <span>Refresh Interval: <strong class="font-mono">{refreshInterval}ms</strong></span>
          </div>
          <input type="range" min="500" max="10000" step="500" bind:value={refreshInterval} class="config-slider" aria-labelledby="refresh-label" />
        </div>

        <div class="config-group">
          <div class="config-label" id="warn-label">
            <span>RAM Warning Threshold: <strong class="font-mono">{ramWarningThreshold}%</strong></span>
          </div>
          <input type="range" min="50" max="95" step="5" bind:value={ramWarningThreshold} class="config-slider" aria-labelledby="warn-label" />
        </div>

        <div class="config-group">
          <div class="config-label" id="crit-label">
            <span>RAM Critical Threshold: <strong class="font-mono">{ramCriticalThreshold}%</strong></span>
          </div>
          <input type="range" min="60" max="99" step="5" bind:value={ramCriticalThreshold} class="config-slider" aria-labelledby="crit-label" />
        </div>

        <div class="config-group toggle-group">
          <div class="config-label" id="dark-label">
            <span>Dark Mode</span>
          </div>
          <button
            class="toggle-btn"
            class:active={darkModeEnabled}
            onclick={() => { darkModeEnabled = !darkModeEnabled; }}
          >
            {darkModeEnabled ? 'ON' : 'OFF'}
          </button>
        </div>

        <button class="save-btn" onclick={saveConfig}>
          {configSaved ? '✓ Saved!' : '💾 Save Config'}
        </button>
      </div>

    {:else if activeTab === 'providers'}
      <!-- ═══ API PROVIDERS ═══ -->
      <div class="providers-panel">
        <h3 class="tab-title">🔌 API Providers</h3>
        <div class="provider-list">
          {#each apiProviders as provider}
            <div class="provider-card">
              <div class="provider-info">
                <div class="provider-dot" class:online={provider.status === 'online'} class:offline={provider.status !== 'online'}></div>
                <div class="provider-details">
                  <span class="provider-name">{provider.name}</span>
                  <span class="provider-meta">
                    Last: {provider.last_call} · {(provider.tokens_used / 1000000).toFixed(1)}M tokens
                  </span>
                </div>
              </div>
              <button
                class="enable-btn"
                class:enabled={provider.enabled}
                class:disabled={!provider.enabled}
                onclick={() => toggleProvider(provider.name)}
              >
                {provider.enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          {/each}
        </div>
      </div>

    {:else if activeTab === 'emergency'}
      <!-- ═══ EMERGENCY ═══ -->
      <div class="emergency-panel">
        <h3 class="tab-title">🆘 Emergency Controls</h3>
        <div class="emergency-actions">
          <button class="emg-btn danger" onclick={() => confirmAction('restart')}>
            🔄 Restart System
          </button>
          <button class="emg-btn warning" onclick={() => confirmAction('safemode')}>
            🛡️ Enter Safe Mode
          </button>
          <button class="emg-btn" onclick={() => confirmAction('cache')}>
            🗑️ Clear All Cache
          </button>
        </div>

        {#if showingConfirm}
          <div class="confirm-dialog">
            <div class="confirm-text">
              Are you sure you want to <strong>"{showingConfirm}"</strong>?
            </div>
            <div class="confirm-actions">
              <button class="confirm-btn yes" onclick={executeAction}>Yes, execute</button>
              <button class="confirm-btn no" onclick={() => { showingConfirm = null; }}>Cancel</button>
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .control-center {
    display: flex;
    flex-direction: column;
    height: 100%;
    font-size: 0.75rem;
  }

  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Tab Navigation ─── */
  .tab-nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    flex-shrink: 0;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #64748b;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
    width: 100%;
  }

  .tab-btn:hover {
    background: rgba(255,255,255,0.04);
    color: #94a3b8;
  }

  .tab-btn.active {
    background: rgba(59,130,246,0.08);
    color: #60a5fa;
    font-weight: 600;
  }

  .tab-icon {
    font-size: 0.9rem;
    width: 20px;
    text-align: center;
  }

  .tab-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  /* ─── Tab Content ─── */
  .tab-content {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
  }

  .tab-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 10px;
  }

  .small-btn {
    padding: 3px 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    color: #94a3b8;
    font-size: 0.65rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .small-btn:hover {
    background: rgba(255,255,255,0.07);
    color: #e2e8f0;
  }

  .small-btn.primary {
    background: rgba(59,130,246,0.15);
    border-color: rgba(59,130,246,0.3);
    color: #60a5fa;
  }

  .small-btn.primary:hover {
    background: rgba(59,130,246,0.25);
  }

  /* ═══ KANBAN ═══ */
  .kanban-board {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .kanban-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .kanban-header .tab-title {
    margin-bottom: 0;
  }

  .new-task-form {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px;
  }

  .nt-input {
    padding: 4px 8px;
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.7rem;
    font-family: inherit;
    outline: none;
  }

  .nt-input:focus { border-color: rgba(59,130,246,0.3); }

  .nt-row {
    display: flex;
    gap: 4px;
  }

  .nt-select {
    padding: 3px 6px;
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 4px;
    color: #94a3b8;
    font-size: 0.65rem;
    outline: none;
  }

  .kanban-columns {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .kanban-col {
    background: rgba(255,255,255,0.01);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 8px;
  }

  .col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .col-name {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    color: #64748b;
    letter-spacing: 0.04em;
  }

  .col-count {
    font-size: 0.6rem;
    font-weight: 700;
    color: #475569;
    font-family: 'JetBrains Mono', monospace;
  }

  .col-cards {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .kanban-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
    border-left: 3px solid #64748b;
    border-radius: 6px;
    padding: 6px 8px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 3px;
  }

  .card-priority {
    font-size: 0.55rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .card-assignee {
    font-size: 0.55rem;
    color: #475569;
  }

  .card-title {
    font-size: 0.7rem;
    color: #e2e8f0;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .card-actions {
    display: flex;
    gap: 2px;
  }

  .card-btn {
    padding: 1px 6px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 3px;
    color: #64748b;
    font-size: 0.65rem;
    cursor: pointer;
  }

  .card-btn:disabled {
    opacity: 0.2;
    cursor: not-allowed;
  }

  .card-btn:hover:not(:disabled) {
    background: rgba(255,255,255,0.06);
    color: #e2e8f0;
  }

  /* ═══ FILE TREE ═══ */
  .file-tree {
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin-bottom: 8px;
  }

  .file-node {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.1s ease;
  }

  .file-node:hover {
    background: rgba(255,255,255,0.03);
  }

  .node-icon {
    font-size: 0.75rem;
    flex-shrink: 0;
  }

  .node-name {
    font-size: 0.7rem;
    color: #94a3b8;
  }

  .file-preview {
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px;
    overflow: hidden;
  }

  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    background: rgba(255,255,255,0.03);
    font-size: 0.65rem;
    color: #64748b;
  }

  .preview-body {
    padding: 12px 8px;
    text-align: center;
  }

  .preview-placeholder {
    font-size: 0.65rem;
    color: #475569;
    font-style: italic;
  }

  /* ═══ CONFIG ═══ */
  .config-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .config-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .config-label {
    font-size: 0.7rem;
    color: #94a3b8;
  }

  .config-slider {
    width: 100%;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    outline: none;
  }

  .config-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #3b82f6;
    cursor: pointer;
    box-shadow: 0 0 6px rgba(59,130,246,0.3);
  }

  .toggle-group {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .toggle-btn {
    padding: 4px 16px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.03);
    color: #64748b;
    font-size: 0.65rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn.active {
    background: rgba(59,130,246,0.15);
    border-color: rgba(59,130,246,0.3);
    color: #60a5fa;
  }

  .save-btn {
    padding: 6px 16px;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 8px;
    color: #60a5fa;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .save-btn:hover {
    background: rgba(59,130,246,0.2);
    border-color: rgba(59,130,246,0.4);
  }

  /* ═══ API PROVIDERS ═══ */
  .provider-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .provider-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 8px;
  }

  .provider-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .provider-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #64748b;
    flex-shrink: 0;
  }

  .provider-dot.online { background: #22c55e; box-shadow: 0 0 4px rgba(34,197,94,0.5); }
  .provider-dot.offline { background: #ef4444; box-shadow: 0 0 4px rgba(239,68,68,0.4); }

  .provider-details {
    display: flex;
    flex-direction: column;
  }

  .provider-name {
    font-size: 0.75rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .provider-meta {
    font-size: 0.6rem;
    color: #64748b;
  }

  .enable-btn {
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 0.6rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    border: 1px solid transparent;
  }

  .enable-btn.enabled {
    background: rgba(34,197,94,0.1);
    border-color: rgba(34,197,94,0.2);
    color: #22c55e;
  }

  .enable-btn.disabled {
    background: rgba(239,68,68,0.1);
    border-color: rgba(239,68,68,0.2);
    color: #ef4444;
  }

  /* ═══ EMERGENCY ═══ */
  .emergency-actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .emg-btn {
    padding: 10px 16px;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    color: #e2e8f0;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
  }

  .emg-btn:hover {
    background: rgba(255,255,255,0.06);
  }

  .emg-btn.danger {
    border-color: rgba(239,68,68,0.3);
    background: rgba(239,68,68,0.06);
    color: #ef4444;
  }

  .emg-btn.danger:hover {
    background: rgba(239,68,68,0.12);
  }

  .emg-btn.warning {
    border-color: rgba(234,179,8,0.3);
    background: rgba(234,179,8,0.06);
    color: #eab308;
  }

  .emg-btn.warning:hover {
    background: rgba(234,179,8,0.12);
  }

  .confirm-dialog {
    margin-top: 12px;
    padding: 12px;
    background: rgba(239,68,68,0.06);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 8px;
  }

  .confirm-text {
    font-size: 0.75rem;
    color: #e2e8f0;
    margin-bottom: 8px;
  }

  .confirm-actions {
    display: flex;
    gap: 6px;
  }

  .confirm-btn {
    padding: 5px 14px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.06);
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
  }

  .confirm-btn.yes {
    background: rgba(239,68,68,0.15);
    border-color: rgba(239,68,68,0.3);
    color: #ef4444;
  }

  .confirm-btn.no {
    background: rgba(255,255,255,0.04);
    color: #94a3b8;
  }
</style>

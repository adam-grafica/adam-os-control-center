<script lang="ts">
  /**
   * MissionConsole.svelte — Bottom dock terminal with live logs.
   */
  import { logs, logFilter, filteredLogs, setFilter, addLog, clearLogs, resetFilter, toggleLogLevel, type LogEntry, type LogLevel } from '$lib/stores/console';

  let allLogs: LogEntry[] = $state([]);
  let displayLogs: LogEntry[] = $state([]);
  let currentFilter = $state({ level: ['info', 'warn', 'error', 'debug'] as LogLevel[], source: '', search: '' });

  $effect(() => {
    const unsubs = [
      logs.subscribe((v) => { allLogs = v; }),
      filteredLogs.subscribe((v) => { displayLogs = v; }),
      logFilter.subscribe((v) => { currentFilter = v; }),
    ];
    return () => unsubs.forEach((fn) => fn());
  });

  let paused = $state(false);
  let logContainer: HTMLDivElement | undefined = $state();
  let pinIds = $state(new Set<string>());
  let searchText = $state('');

  // Auto-scroll when new logs arrive
  $effect(() => {
    if (!paused && displayLogs.length > 0 && logContainer) {
      // Use microtask to ensure DOM is updated
      queueMicrotask(() => {
        if (logContainer) {
          logContainer.scrollTop = logContainer.scrollHeight;
        }
      });
    }
  });

  function togglePause() {
    paused = !paused;
  }

  function togglePin(id: string) {
    if (pinIds.has(id)) {
      pinIds.delete(id);
    } else {
      pinIds.add(id);
    }
    pinIds = new Set(pinIds);
  }

  function handleSearch(e: Event) {
    const target = e.target as HTMLInputElement;
    searchText = target.value;
    setFilter({ search: searchText });
  }

  function handleSourceFilter(e: Event) {
    const target = e.target as HTMLSelectElement;
    setFilter({ source: target.value });
  }

  function exportLogs() {
    const text = displayLogs.map((l) =>
      `[${new Date(l.ts).toISOString()}] [${l.level.toUpperCase()}] [${l.source}] ${l.message}`
    ).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `adam-os-logs-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Get available sources for filter
  let availableSources = $state<string[]>([]);
  $effect(() => {
    const sources = new Set<string>();
    allLogs.forEach((l) => sources.add(l.source));
    availableSources = Array.from(sources).sort();
  });

  function formatLogTime(ts: string): string {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) +
      '.' + String(d.getMilliseconds()).padStart(3, '0');
  }

  function getLevelColor(level: LogLevel): string {
    switch (level) {
      case 'info': return '#3b82f6';
      case 'warn': return '#eab308';
      case 'error': return '#ef4444';
      case 'debug': return '#64748b';
      default: return '#94a3b8';
    }
  }
</script>

<div class="console">
  <div class="console-toolbar">
    <div class="toolbar-left">
      <span class="console-title">⚡ Mission Console</span>
      <span class="log-count font-mono">{displayLogs.length} logs</span>
    </div>

    <div class="toolbar-center">
      <!-- Level filters -->
      <div class="level-filters">
        {#each ['info', 'warn', 'error', 'debug'] as level}
          <button
            class="level-btn"
            class:active={currentFilter.level.includes(level as LogLevel)}
            style="--level-color: {getLevelColor(level as LogLevel)};"
            onclick={() => toggleLogLevel(level as LogLevel)}
          >
            {level}
          </button>
        {/each}
      </div>

      <!-- Source filter -->
      <select class="source-select" onchange={handleSourceFilter} value={currentFilter.source}>
        <option value="">All Sources</option>
        {#each availableSources as source}
          <option value={source}>{source}</option>
        {/each}
      </select>

      <!-- Search -->
      <input
        type="text"
        class="search-input"
        placeholder="Search logs..."
        value={searchText}
        oninput={handleSearch}
      />
    </div>

    <div class="toolbar-right">
      <button class="toolbar-btn" onclick={togglePause} class:active={paused}>
        {paused ? '▶ Resume' : '⏸ Pause'}
      </button>
      <button class="toolbar-btn" onclick={clearLogs}>🗑 Clear</button>
      <button class="toolbar-btn" onclick={exportLogs}>📥 Export</button>
    </div>
  </div>

  <div class="console-logs" bind:this={logContainer}>
    {#if displayLogs.length === 0}
      <div class="console-empty">
        <span class="empty-prompt">Waiting for log data...</span>
      </div>
    {:else}
      {#each displayLogs as log (log.id)}
        <div
          class="log-entry"
          class:pinned={pinIds.has(log.id)}
          style="--log-level-color: {getLevelColor(log.level)};"
        >
          <span class="log-pin" onclick={() => togglePin(log.id)} onkeydown={(e) => { if (e.key === 'Enter') togglePin(log.id); }} role="button" tabindex="0">
            {pinIds.has(log.id) ? '📌' : '·'}
          </span>
          <span class="log-time font-mono">{formatLogTime(log.ts)}</span>
          <span class="log-level" style="color: {getLevelColor(log.level)};">
            [{log.level.toUpperCase()}]
          </span>
          <span class="log-source">{log.source}</span>
          <span class="log-type">{log.type}</span>
          <span class="log-message">{log.message}</span>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .console {
    display: flex;
    flex-direction: column;
    background: rgba(0,0,0,0.3);
    border-top: 1px solid rgba(255,255,255,0.06);
    border-radius: 0;
    height: 100%;
  }

  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Toolbar ─── */
  .console-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    flex-wrap: wrap;
    flex-shrink: 0;
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .console-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #e2e8f0;
  }

  .log-count {
    font-size: 0.65rem;
    color: #64748b;
  }

  .toolbar-center {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    justify-content: center;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .toolbar-btn {
    padding: 3px 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    color: #94a3b8;
    font-size: 0.65rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
  }

  .toolbar-btn:hover {
    background: rgba(255,255,255,0.06);
    color: #e2e8f0;
  }

  .toolbar-btn.active {
    background: rgba(59,130,246,0.1);
    border-color: rgba(59,130,246,0.2);
    color: #60a5fa;
  }

  /* ─── Level Filters ─── */
  .level-filters {
    display: flex;
    gap: 2px;
  }

  .level-btn {
    padding: 2px 8px;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 4px;
    color: #64748b;
    font-size: 0.6rem;
    font-weight: 600;
    cursor: pointer;
    text-transform: uppercase;
    transition: all 0.15s ease;
  }

  .level-btn.active {
    background: rgba(255,255,255,0.04);
    border-color: var(--level-color, rgba(255,255,255,0.1));
    color: var(--level-color, #e2e8f0);
  }

  /* ─── Source / Search ─── */
  .source-select {
    padding: 2px 6px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 4px;
    color: #94a3b8;
    font-size: 0.6rem;
    max-width: 100px;
    outline: none;
  }

  .source-select:focus {
    border-color: rgba(59,130,246,0.3);
  }

  .search-input {
    padding: 2px 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    width: 120px;
    outline: none;
  }

  .search-input::placeholder {
    color: #475569;
  }

  .search-input:focus {
    border-color: rgba(59,130,246,0.3);
  }

  /* ─── Log Area ─── */
  .console-logs {
    flex: 1;
    overflow-y: auto;
    padding: 4px 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    line-height: 1.6;
    background: rgba(0,0,0,0.2);
  }

  .console-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 60px;
  }

  .empty-prompt {
    color: #475569;
    font-style: italic;
    font-size: 0.7rem;
  }

  /* ─── Log Entry ─── */
  .log-entry {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    padding: 1px 4px;
    border-radius: 2px;
    cursor: default;
    transition: background 0.15s ease;
    border-left: 2px solid transparent;
  }

  .log-entry:hover {
    background: rgba(255,255,255,0.03);
  }

  .log-entry.pinned {
    background: rgba(59,130,246,0.05);
    border-left-color: #3b82f6;
  }

  .log-pin {
    cursor: pointer;
    color: #475569;
    flex-shrink: 0;
    width: 10px;
    text-align: center;
    font-size: 0.6rem;
    user-select: none;
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .log-entry:hover .log-pin {
    opacity: 1;
  }

  .log-pin:hover {
    color: #3b82f6;
  }

  .log-time {
    color: #475569;
    flex-shrink: 0;
    white-space: nowrap;
    min-width: 100px;
  }

  .log-level {
    flex-shrink: 0;
    font-weight: 700;
    min-width: 40px;
  }

  .log-source {
    color: #64748b;
    flex-shrink: 0;
    min-width: 60px;
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .log-type {
    color: #475569;
    flex-shrink: 0;
    min-width: 40px;
    font-size: 0.6rem;
  }

  .log-message {
    color: #e2e8f0;
    flex: 1;
    word-break: break-all;
  }

  /* Scrollbar */
  .console-logs::-webkit-scrollbar {
    width: 4px;
  }

  .console-logs::-webkit-scrollbar-track {
    background: rgba(0,0,0,0.1);
  }

  .console-logs::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
  }

  @media (max-width: 768px) {
    .toolbar-center {
      order: 3;
      width: 100%;
      justify-content: flex-start;
    }
    .search-input { width: 80px; }
    .log-source, .log-type { display: none; }
  }
</style>

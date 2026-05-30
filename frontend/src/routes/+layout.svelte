<script lang="ts">
  /**
   * Root layout - Connects SSE on mount, initializes stores.
   * Shows connection state and renders page content.
   */
  import '../app.css';
  import { onMount } from 'svelte';
  import { connectSSE, fetchAgentsData, fetchConsoleLogs } from '$lib/stores/sse';
  import { connected, errorMessage } from '$lib/stores/sse';

  let { children }: { children?: import('svelte').Snippet } = $props();

  let isConnected: boolean = $state(false);
  let error: string | null = $state(null);

  $effect(() => {
    const unsubConnected = connected.subscribe((v) => { isConnected = v; });
    const unsubError = errorMessage.subscribe((v) => { error = v; });
    return () => {
      unsubConnected();
      unsubError();
    };
  });

  onMount(() => {
    // Auto-connect to SSE master stream
    connectSSE('/api/stream/master');

    // Fetch initial data
    fetchAgentsData();
    fetchConsoleLogs();
  });
</script>

<div class="app-shell">
  <!-- Connection error banner -->
  {#if error && !isConnected}
    <div class="error-banner">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{error}</span>
    </div>
  {/if}

  <!-- Loading overlay on initial connect -->
  {#if !isConnected && !error}
    <div class="loading-overlay">
      <div class="loading-content">
        <div class="loading-spinner"></div>
        <span class="loading-text">Connecting to ADAM OS...</span>
      </div>
    </div>
  {/if}

  <!-- Render page content (will be the dashboard layout) -->
  {#if children}
    {@render children()}
  {/if}
</div>

<style>
  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #0f1117;
  }

  /* Error banner */
  .error-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    background: rgba(239,68,68,0.08);
    border-bottom: 1px solid rgba(239,68,68,0.2);
    color: #ef4444;
    font-size: 0.8rem;
    font-weight: 500;
    animation: slideIn 0.3s ease forwards;
    z-index: 100;
  }

  .error-icon { font-size: 1rem; }
  .error-text { flex: 1; }

  /* Loading overlay */
  .loading-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0f1117;
    z-index: 999;
  }

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .loading-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(255,255,255,0.06);
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .loading-text {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>

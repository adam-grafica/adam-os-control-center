import { writable, type Writable } from 'svelte/store';
import { organism } from './organism';
import type { DashboardSnapshot } from './organism';
import { addInfraSnapshot } from './infra';
import type { InfraSnapshot } from './infra';
import { updateAgentsFromApi } from './agents';
import { addLog } from './console';
import type { LogLevel } from './console';
import { updatePipelineFromSSE } from './pipeline';

// ─── Combined Update Types ──────────────────────────────────────────────

export interface CombinedUpdate {
  ts: number;
  organism: DashboardSnapshot | null;
  infra: InfraSnapshot | null;
  pipeline: any;
}

// ─── Stores ─────────────────────────────────────────────────────────────

export const connected: Writable<boolean> = writable<boolean>(false);
export const lastUpdate: Writable<Date | null> = writable<Date | null>(null);
export const errorMessage: Writable<string | null> = writable<string | null>(null);

// ─── Internals ──────────────────────────────────────────────────────────

let eventSource: EventSource | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let currentUrl: string = '';
let isDisconnecting: boolean = false;
let reconnectDelay: number = 1000; // starts at 1s, exponential backoff to 30s

function scheduleReconnect(url: string): void {
  if (isDisconnecting) return;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  errorMessage.set(`Connection lost. Reconnecting in ${reconnectDelay / 1000}s...`);
  reconnectTimer = setTimeout(() => {
    if (!isDisconnecting) {
      connectSSE(url);
    }
  }, reconnectDelay);
  // Exponential backoff, capped at 30s
  reconnectDelay = Math.min(reconnectDelay * 2, 30000);
}

function resetReconnectDelay(): void {
  reconnectDelay = 1000;
}

function handleOpen(): void {
  connected.set(true);
  errorMessage.set(null);
  resetReconnectDelay();
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function parseCombinedUpdate(data: any): void {
  if (!data) return;

  // Update organism store
  if (data.organism) {
    organism.set(data.organism as DashboardSnapshot);
  }

  // Update infra store
  if (data.infra) {
    addInfraSnapshot(data.infra as InfraSnapshot);
  }

  lastUpdate.set(new Date());
  errorMessage.set(null);
}

function handleMessage(event: MessageEvent): void {
  try {
    const data = JSON.parse(event.data);
    parseCombinedUpdate(data);
  } catch (err) {
    console.error('[SSE] Failed to parse event data:', err);
  }
}

function handleCombinedUpdate(event: MessageEvent): void {
  try {
    const data = JSON.parse(event.data);
    parseCombinedUpdate(data);

    // If the data has agent/task/console info, update those too
    if (data.agents) {
      updateAgentsFromApi(data.agents);
    }
    if (data.console && Array.isArray(data.console)) {
      data.console.forEach((entry: any) => {
        addLog({
          ts: entry.ts || new Date().toISOString(),
          level: (entry.level || 'info') as LogLevel,
          source: entry.source || 'system',
          type: entry.type || 'log',
          message: entry.message || '',
        });
      });
    }

    // Parse pipeline data from SSE
    if (data.pipeline) {
      updatePipelineFromSSE(data);
    }
  } catch (err) {
    console.error('[SSE] Failed to parse combined_update:', err);
  }
}

function handleHeartbeat(event: MessageEvent): void {
  try {
    const data = JSON.parse(event.data);
    lastUpdate.set(new Date(data.ts ? data.ts * 1000 : Date.now()));
    errorMessage.set(null);
  } catch {
    lastUpdate.set(new Date());
    errorMessage.set(null);
  }
}

function handleError(): void {
  connected.set(false);
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  if (currentUrl && !isDisconnecting) {
    scheduleReconnect(currentUrl);
  }
}

// ─── Public API ─────────────────────────────────────────────────────────

export function connectSSE(url: string = '/api/stream/master'): void {
  if (eventSource) {
    disconnectSSE();
  }

  isDisconnecting = false;
  currentUrl = url;

  try {
    eventSource = new EventSource(url);

    eventSource.onopen = handleOpen;
    eventSource.onerror = handleError;

    // Handle named events
    eventSource.addEventListener('combined_update', handleCombinedUpdate);
    eventSource.addEventListener('heartbeat', handleHeartbeat);

    // Fallback for unnamed messages
    eventSource.onmessage = handleMessage;

    connected.set(false);
  } catch (err) {
    errorMessage.set(`Failed to connect: ${err}`);
    scheduleReconnect(url);
  }
}

export function disconnectSSE(): void {
  isDisconnecting = true;
  currentUrl = '';

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (eventSource) {
    eventSource.removeEventListener('combined_update', handleCombinedUpdate);
    eventSource.removeEventListener('heartbeat', handleHeartbeat);
    eventSource.onopen = null;
    eventSource.onmessage = null;
    eventSource.onerror = null;
    eventSource.close();
    eventSource = null;
  }

  connected.set(false);
  errorMessage.set(null);
}

/**
 * Manually fetch agent/task/tool data from REST endpoints.
 */
export async function fetchAgentsData(): Promise<void> {
  try {
    const res = await fetch('/api/agents/status');
    if (res.ok) {
      const data = await res.json();
      updateAgentsFromApi(data);
    }
  } catch (err) {
    console.error('[SSE] Failed to fetch agents data:', err);
  }
}

/**
 * Manually fetch console logs from REST endpoint.
 */
export async function fetchConsoleLogs(): Promise<void> {
  try {
    const res = await fetch('/api/console/logs');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        data.forEach((entry: any) => {
          addLog({
            ts: entry.ts || new Date().toISOString(),
            level: (entry.level || 'info') as LogLevel,
            source: entry.source || 'system',
            type: entry.type || 'log',
            message: entry.message || '',
          });
        });
      }
    }
  } catch (err) {
    console.error('[SSE] Failed to fetch console logs:', err);
  }
}

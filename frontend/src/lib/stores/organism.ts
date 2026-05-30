import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ─── Types ──────────────────────────────────────────────────────────────

export interface Organ {
  name: string;
  health: number;           // 0-100
  status: string;           // 'healthy' | 'degraded' | 'critical' | 'offline'
  last_activity: string;    // ISO datetime
  metrics: Record<string, number>;
}

export interface Threat {
  id: string;
  type: string;
  severity: string;         // 'low' | 'medium' | 'high' | 'critical'
  message: string;
  source: string;
  timestamp: string;
  resolved: boolean;
}

export interface DashboardEvent {
  id: string;
  timestamp: string;
  source: string;
  type: string;
  severity: string;
  payload: Record<string, unknown>;
  preview: string;
}

export interface DashboardSnapshot {
  timestamp: string;
  organism_health: number;
  organism_mood: string;
  current_mode: string;
  active_threats: number;
  organs: Organ[];
  recent_events: DashboardEvent[];
  active_threats_list: Threat[];
}

// ─── Stores ─────────────────────────────────────────────────────────────

export const organism: Writable<DashboardSnapshot | null> = writable<DashboardSnapshot | null>(null);

export const health: Readable<number> = derived(
  organism,
  ($organism) => $organism?.organism_health ?? 100
);

export const mood: Readable<string> = derived(
  organism,
  ($organism) => $organism?.organism_mood ?? 'unknown'
);

export const mode: Readable<string> = derived(
  organism,
  ($organism) => $organism?.current_mode ?? 'idle'
);

export const activeThreatCount: Readable<number> = derived(
  organism,
  ($organism) => $organism?.active_threats ?? 0
);

export const organs: Readable<Organ[]> = derived(
  organism,
  ($organism) => $organism?.organs ?? []
);

export const recentEvents: Readable<DashboardEvent[]> = derived(
  organism,
  ($organism) => $organism?.recent_events ?? []
);

export const activeThreatsList: Readable<Threat[]> = derived(
  organism,
  ($organism) => $organism?.active_threats_list ?? []
);

export const timestamp: Readable<string> = derived(
  organism,
  ($organism) => $organism?.timestamp ?? ''
);

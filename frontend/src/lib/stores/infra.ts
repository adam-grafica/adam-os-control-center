import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ─── Types ──────────────────────────────────────────────────────────────

export interface CpuInfo {
  percent: number;
  cores: number;
  load_avg: number[];
  status: string;
}

export interface MemoryInfo {
  total: number;
  available: number;
  used: number;
  free: number;
  percent: number;
  status: string;
}

export interface DiskInfo {
  device: string;
  mountpoint: string;
  total: number;
  used: number;
  free: number;
  percent: number;
}

export interface NetworkInfo {
  bytes_sent: number;
  bytes_recv: number;
  packets_sent: number;
  packets_recv: number;
  status: string;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
  status: string;
}

export interface UptimeInfo {
  uptime_seconds: number;
  status: string;
}

export interface InfraSnapshot {
  ts: number;
  cpu: CpuInfo;
  memory: MemoryInfo;
  disk: DiskInfo[];
  network: NetworkInfo;
  uptime: UptimeInfo;
  processes: ProcessInfo[];
}

export type SnapshotsMap = Map<number, InfraSnapshot>;

// ─── Helpers ────────────────────────────────────────────────────────────

const MAX_SNAPSHOTS = 60;

// ─── Stores ─────────────────────────────────────────────────────────────

export const infraData: Writable<SnapshotsMap> = writable<SnapshotsMap>(new Map());

export const currentCpu: Readable<CpuInfo | null> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return null;
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.cpu ?? null;
  }
);

export const currentMemory: Readable<MemoryInfo | null> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return null;
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.memory ?? null;
  }
);

export const currentDisk: Readable<DiskInfo[]> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return [];
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.disk ?? [];
  }
);

export const currentNetwork: Readable<NetworkInfo | null> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return null;
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.network ?? null;
  }
);

export const currentProcesses: Readable<ProcessInfo[]> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return [];
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.processes ?? [];
  }
);

export const currentUptime: Readable<UptimeInfo | null> = derived(
  infraData,
  ($map) => {
    if ($map.size === 0) return null;
    const keys = Array.from($map.keys()).sort((a, b) => b - a);
    return $map.get(keys[0])?.uptime ?? null;
  }
);

// ─── Functions ──────────────────────────────────────────────────────────

export function addInfraSnapshot(snapshot: InfraSnapshot): void {
  infraData.update((map) => {
    const updated = new Map(map);
    updated.set(snapshot.ts, snapshot);

    // Keep only the latest MAX_SNAPSHOTS entries
    if (updated.size > MAX_SNAPSHOTS) {
      const keys = Array.from(updated.keys()).sort((a, b) => a - b);
      const toDelete = keys.length - MAX_SNAPSHOTS;
      for (let i = 0; i < toDelete; i++) {
        updated.delete(keys[i]);
      }
    }

    return updated;
  });
}

/** Humanize bytes to GB/MB/KB */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = parseFloat((bytes / Math.pow(k, i)).toFixed(decimals));
  return `${val} ${sizes[i]}`;
}

/** Get health color for a percentage value */
export function getPercentColor(pct: number): string {
  if (pct >= 90) return '#ef4444';     // red
  if (pct >= 75) return '#eab308';     // yellow
  if (pct >= 50) return '#f59e0b';     // amber
  return '#22c55e';                     // green
}

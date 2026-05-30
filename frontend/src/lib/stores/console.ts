import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ─── Types ──────────────────────────────────────────────────────────────

export type LogLevel = 'info' | 'warn' | 'error' | 'debug';

export interface LogEntry {
  id: string;
  ts: string;           // ISO timestamp
  level: LogLevel;
  source: string;       // component/module name
  type: string;         // event type / category
  message: string;
}

export interface LogFilter {
  level: LogLevel[];
  source: string;
  search: string;
}

// ─── Defaults ───────────────────────────────────────────────────────────

const MAX_LOGS = 1000;

const defaultFilter: LogFilter = {
  level: ['info', 'warn', 'error', 'debug'] as LogLevel[],
  source: '',
  search: '',
};

// ─── Stores ─────────────────────────────────────────────────────────────

export const logs: Writable<LogEntry[]> = writable<LogEntry[]>([]);
export const logFilter: Writable<LogFilter> = writable<LogFilter>({ ...defaultFilter });

// ─── Derived Stores ─────────────────────────────────────────────────────

export const filteredLogs: Readable<LogEntry[]> = derived(
  [logs, logFilter],
  ([$logs, $filter]) => {
    return $logs.filter((entry) => {
      // Filter by level
      if ($filter.level.length > 0 && !$filter.level.includes(entry.level)) {
        return false;
      }
      // Filter by source
      if ($filter.source && entry.source.toLowerCase() !== $filter.source.toLowerCase()) {
        return false;
      }
      // Filter by search text
      if ($filter.search) {
        const q = $filter.search.toLowerCase();
        if (
          !entry.message.toLowerCase().includes(q) &&
          !entry.source.toLowerCase().includes(q) &&
          !entry.type.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }
);

// ─── Functions ──────────────────────────────────────────────────────────

let idCounter = 0;

export function addLog(entry: Omit<LogEntry, 'id'>): void {
  const newEntry: LogEntry = {
    ...entry,
    id: `log-${Date.now()}-${idCounter++}`,
  };

  logs.update((current) => {
    const updated = [...current, newEntry];
    if (updated.length > MAX_LOGS) {
      return updated.slice(updated.length - MAX_LOGS);
    }
    return updated;
  });
}

export function setFilter(partial: Partial<LogFilter>): void {
  logFilter.update((current) => ({
    ...current,
    ...partial,
  }));
}

export function clearLogs(): void {
  logs.set([]);
}

export function toggleLogLevel(level: LogLevel): void {
  logFilter.update((current) => {
    const idx = current.level.indexOf(level);
    if (idx >= 0) {
      // Don't allow removing all levels
      if (current.level.length <= 1) return current;
      return { ...current, level: current.level.filter((l) => l !== level) };
    }
    return { ...current, level: [...current.level, level] };
  });
}

export function resetFilter(): void {
  logFilter.set({ ...defaultFilter });
}

/** Get all available sources from current logs */
export function getAvailableSources(logsList: LogEntry[]): string[] {
  const sources = new Set<string>();
  logsList.forEach((l) => sources.add(l.source));
  return Array.from(sources).sort();
}

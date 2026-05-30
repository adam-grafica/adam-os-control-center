import { writable, type Writable } from 'svelte/store';

// ─── UI State Stores ────────────────────────────────────────────────────

export const selectedOrgan: Writable<string | null> = writable<string | null>(null);
export const showTimeline: Writable<boolean> = writable<boolean>(true);
export const showThreats: Writable<boolean> = writable<boolean>(true);
export const showEvents: Writable<boolean> = writable<boolean>(true);
export const darkMode: Writable<boolean> = writable<boolean>(true);

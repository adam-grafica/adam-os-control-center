import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ─── Types ──────────────────────────────────────────────────────────────

export interface Tool {
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'error';
  last_called: string | null;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'blocked';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
}

export interface Agent {
  id: string;
  name: string;
  type: 'AXON' | 'agent' | 'sub-agent';
  status: 'running' | 'idle' | 'error' | 'paused';
  current_task: string | null;
  current_tool: string | null;
  latency: number;
  last_seen: string;
  parent_id: string | null;
  sub_agents: Agent[];
  tools: Tool[];
}

// ─── Stores ─────────────────────────────────────────────────────────────

export const agents: Writable<Agent[]> = writable<Agent[]>([]);
export const tasks: Writable<Task[]> = writable<Task[]>([]);
export const tools: Writable<Tool[]> = writable<Tool[]>([]);

// ─── Derived Stores ─────────────────────────────────────────────────────

export const activeAgents: Readable<Agent[]> = derived(
  agents,
  ($agents) => $agents.filter((a) => a.status === 'running' || a.status === 'idle')
);

export const tasksRunning: Readable<number> = derived(
  tasks,
  ($tasks) => $tasks.filter((t) => t.status === 'running').length
);

export const activeAlerts: Readable<number> = derived(
  [agents, tasks],
  ([$agents, $tasks]) => {
    const errAgents = $agents.filter((a) => a.status === 'error').length;
    const failedTasks = $tasks.filter((t) => t.status === 'failed').length;
    return errAgents + failedTasks;
  }
);

export const axonAgent: Readable<Agent | null> = derived(
  agents,
  ($agents) => $agents.find((a) => a.type === 'AXON') ?? null
);

export const regularAgents: Readable<Agent[]> = derived(
  agents,
  ($agents) => $agents.filter((a) => a.type !== 'AXON' && a.parent_id === null)
);

// ─── Helper Functions ───────────────────────────────────────────────────

export function updateAgentsFromApi(data: { agents: Agent[]; tasks: Task[]; tools: Tool[] }): void {
  if (data.agents) agents.set(data.agents);
  if (data.tasks) tasks.set(data.tasks);
  if (data.tools) tools.set(data.tools);
}

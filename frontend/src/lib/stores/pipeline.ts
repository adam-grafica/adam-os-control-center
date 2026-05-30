import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ─── Types ──────────────────────────────────────────────────────────────

export interface PipelinePhase {
  phase_id: number;
  name: string;
  department: string;
  status: 'completed' | 'in_progress' | 'pending';
  started_at: string;
  completed_at?: string;
  deliverables: { title: string; url?: string; added_at: string }[];
  signatories: string[];
}

export interface PendingTask {
  id: string;
  title: string;
  department: string;
  status: string;
  completed_at?: string;
}

export interface PipelineProject {
  project_id: string;
  name: string;
  team: string;
  current_phase: number;
  phase_name: string;
  active_department: string;
  agent_progress: string;
  phases: PipelinePhase[];
  pending_tasks: PendingTask[];
  created_at: string;
  updated_at: string;
}

export interface PhaseDetail {
  phase_id: number;
  name: string;
  department: string;
  icon: string;
  active_projects: number;
  description: string;
}

export interface PipelineOverview {
  total_projects: number;
  projects_by_phase: Record<number, number>;
  phase_details: PhaseDetail[];
  updated_at: string;
}

export interface PipelineData {
  projects: PipelineProject[];
  overview: PipelineOverview;
}

// ─── Stores ─────────────────────────────────────────────────────────────

export const pipelineData: Writable<PipelineData | null> = writable<PipelineData | null>(null);

export const pipelineProjects: Readable<PipelineProject[]> = derived(
  pipelineData,
  ($data) => $data?.projects ?? []
);

export const pipelineOverview: Readable<PipelineOverview | null> = derived(
  pipelineData,
  ($data) => $data?.overview ?? null
);

export const pipelineTotalProjects: Readable<number> = derived(
  pipelineData,
  ($data) => $data?.overview?.total_projects ?? 0
);

export const pipelineLastUpdate: Readable<string> = derived(
  pipelineData,
  ($data) => $data?.overview?.updated_at ?? ''
);

// ─── Helpers ────────────────────────────────────────────────────────────

const PHASE_DEFS = [
  { id: 0, name: 'Intake & Brief', dept: 'Product', icon: '📋', desc: 'Definición del proyecto y alcance inicial' },
  { id: 1, name: 'Deep Research', dept: 'Product + UX/UI', icon: '🔍', desc: 'Investigación profunda del dominio' },
  { id: 2, name: 'Arquitectura', dept: 'Engineering', icon: '🏗️', desc: 'Arquitectura y coordinación de módulos' },
  { id: 3, name: 'Consenso', dept: 'All Departments', icon: '🤝', desc: 'Consenso de ingeniería y sign-off' },
  { id: 4, name: 'Ejecución', dept: 'Engineering + QA', icon: '⚡', desc: 'Implementación en paralelo' },
  { id: 5, name: 'QA & Integración', dept: 'QA/Quality', icon: '✅', desc: 'Tests, revisión y validación' },
  { id: 6, name: 'Deploy & Sign-off', dept: 'Delivery', icon: '🚀', desc: 'Deploy final y cierre' },
];

export function getPhaseDef(phaseId: number) {
  return PHASE_DEFS[phaseId] ?? PHASE_DEFS[0];
}

export function getAllPhaseDefs() {
  return PHASE_DEFS;
}

/**
 * Returns a CSS color for a phase based on its status.
 */
export function phaseColor(status: string): string {
  switch (status) {
    case 'completed': return '#22c55e';
    case 'in_progress': return '#3b82f6';
    case 'pending': return '#475569';
    default: return '#475569';
  }
}

/**
 * Returns a numeric progress (0-100) for a project.
 */
export function projectProgress(project: PipelineProject): number {
  if (!project?.phases?.length) return 0;
  const completed = project.phases.filter(p => p.status === 'completed').length;
  return Math.round((completed / 7) * 100);
}

// ─── API helpers ────────────────────────────────────────────────────────

export async function fetchPipelineData(): Promise<void> {
  try {
    const [projectsRes, overviewRes] = await Promise.all([
      fetch('/api/pipeline'),
      fetch('/api/pipeline/overview'),
    ]);

    if (!projectsRes.ok || !overviewRes.ok) {
      console.error('[Pipeline] Failed to fetch pipeline data');
      return;
    }

    const projects: PipelineProject[] = await projectsRes.json();
    const overview: PipelineOverview = await overviewRes.json();

    pipelineData.set({ projects, overview });
  } catch (err) {
    console.error('[Pipeline] Error fetching pipeline data:', err);
  }
}

/**
 * Parse pipeline data from SSE combined_update event.
 */
export function updatePipelineFromSSE(data: any): void {
  if (!data?.pipeline) return;
  const pd = data.pipeline;
  pipelineData.set({
    projects: pd.projects ?? [],
    overview: pd.overview ?? null,
  });
}

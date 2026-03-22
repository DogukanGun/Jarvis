export interface PipelineEvent {
  timestamp: string;
  type: string;
  phase?: string;
  problem_id?: string;
  error?: string;
  result?: string;
  content?: string;
  topic?: string;
  [key: string]: unknown;
}

export interface PhaseStatus {
  [phase: string]: 'pending' | 'running' | 'done' | 'error' | 'healing' | 'healed';
}

export interface ProblemState {
  phases: PhaseStatus;
}

export interface PipelineMetrics {
  total_cost: number;
  total_tokens: number;
  total_duration_ms: number;
}

export interface PipelineState {
  status: 'idle' | 'running' | 'complete';
  topic: string;
  start_time: string | null;
  problems: Record<string, ProblemState>;
  metrics: PipelineMetrics;
  healer_invocations: number;
}

export interface Lesson {
  timestamp: string;
  phase: string;
  error: string;
  fix: string;
  files_modified: string[];
}

export const PHASES = ['gather', 'evaluate', 'decompose', 'research', 'plan', 'code', 'test', 'compare', 'write', 'pdf'] as const;
export type Phase = typeof PHASES[number];

export const PHASE_STATUS_COLORS: Record<string, string> = {
  pending: '#4b5563',
  running: '#3b82f6',
  done: '#22c55e',
  error: '#ef4444',
  healing: '#f59e0b',
  healed: '#a855f7',
};

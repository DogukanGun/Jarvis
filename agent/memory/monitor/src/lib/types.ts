export interface MemoryEvent {
  timestamp: string;
  type: string;
  graph?: string;
  node?: string;
  episode_id?: string;
  user_id?: string;
  duration_ms?: number;
  error?: string;
  [key: string]: unknown;
}

export interface GraphStatus {
  runs: number;
  errors: number;
  last_run: string | null;
  active_node: string | null;
}

export interface MemoryMetrics {
  total_episodes: number;
  total_promotions: number;
  total_rejections: number;
  total_reflections: number;
  total_searches: number;
  avg_write_latency_ms: number;
  avg_search_latency_ms: number;
  dedup_hit_count: number;
  dedup_total_count: number;
  secrets_redacted: number;
}

export interface ServiceStatus {
  status: 'running' | 'stopped';
  queue_depth?: number;
  jobs_completed?: number;
  pending?: number;
  last_reflection?: string | null;
  next_reflection?: string | null;
}

export interface StorageStatus {
  sqlite: { episode_count: number; db_size_bytes: number };
  long_term: { healthy: boolean; backend: string };
}

export interface MemoryState {
  status: 'idle' | 'active' | 'error';
  graphs: Record<string, GraphStatus>;
  metrics: MemoryMetrics;
  services: Record<string, ServiceStatus>;
  storage: StorageStatus;
}

export const GRAPH_NAMES = ['main_graph', 'memory_write_graph', 'reflection_graph', 'user_approval_graph'] as const;
export type GraphName = typeof GRAPH_NAMES[number];

export const NODE_STATUS_COLORS: Record<string, string> = {
  idle: '#4b5563',
  running: '#3b82f6',
  done: '#22c55e',
  error: '#ef4444',
};

export const EVENT_TYPE_COLORS: Record<string, string> = {
  graph_run_start: '#3b82f6',
  graph_run_end: '#22c55e',
  graph_run_error: '#ef4444',
  node_start: '#60a5fa',
  node_end: '#86efac',
  node_error: '#fca5a5',
  episode_inserted: '#a78bfa',
  episode_reinforced: '#c084fc',
  episode_deduplicated: '#f59e0b',
  promotion_proposed: '#fbbf24',
  promotion_approved: '#22c55e',
  promotion_rejected: '#ef4444',
  search_executed: '#06b6d4',
  secret_redacted: '#f97316',
  reflection_start: '#8b5cf6',
  reflection_end: '#a78bfa',
  service_status_change: '#64748b',
  write_completed: '#10b981',
};

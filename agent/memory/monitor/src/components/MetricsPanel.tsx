'use client';
import type { MemoryState } from '../lib/types';

interface Props {
  state: MemoryState;
}

function MetricCard({ label, value, unit, color }: { label: string; value: number | string; unit?: string; color?: string }) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-2xl font-mono font-bold ${color || 'text-slate-100'}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && <span className="text-sm text-slate-500 ml-1">{unit}</span>}
      </div>
    </div>
  );
}

export default function MetricsPanel({ state }: Props) {
  const m = state.metrics;
  const dedupRate = m.dedup_total_count > 0
    ? Math.round((m.dedup_hit_count / m.dedup_total_count) * 100)
    : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
      <MetricCard label="Episodes" value={m.total_episodes} color="text-purple-400" />
      <MetricCard label="Promotions" value={m.total_promotions} color="text-green-400" />
      <MetricCard label="Rejections" value={m.total_rejections} color="text-red-400" />
      <MetricCard label="Searches" value={m.total_searches} color="text-cyan-400" />
      <MetricCard label="Dedup Rate" value={`${dedupRate}%`} color="text-amber-400" />
      <MetricCard label="Secrets" value={m.secrets_redacted} color="text-orange-400" />
      <MetricCard label="Avg Write" value={m.avg_write_latency_ms} unit="ms" />
      <MetricCard label="Avg Search" value={m.avg_search_latency_ms} unit="ms" />
      <MetricCard label="Reflections" value={m.total_reflections} color="text-violet-400" />

      {/* Graph run counts */}
      {Object.entries(state.graphs).map(([name, g]) => (
        <MetricCard
          key={name}
          label={name.replace('_graph', '').replace('_', ' ')}
          value={`${g.runs}/${g.errors}`}
          color={g.errors > 0 ? 'text-red-400' : 'text-slate-300'}
        />
      ))}
    </div>
  );
}

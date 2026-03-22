'use client';

import { useMemo, useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { PipelineEvent, PipelineState } from '../lib/types';
import { PHASES, PHASE_STATUS_COLORS } from '../lib/types';

const API = 'http://localhost:8585';

interface MetricsPanelProps {
  state: PipelineState;
  events: PipelineEvent[];
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const secs = ms / 1000;
  if (secs < 60) return `${secs.toFixed(1)}s`;
  const mins = Math.floor(secs / 60);
  const remaining = Math.floor(secs % 60);
  return `${mins}m ${remaining}s`;
}

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}

function MetricCard({ label, value, sub, accent = 'text-slate-100' }: MetricCardProps) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/30 rounded-lg px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{label}</div>
      <div className={`text-lg font-semibold font-mono ${accent}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-600 mt-0.5">{sub}</div>}
    </div>
  );
}

interface MetricsReport {
  total?: { cost_usd?: number; duration_ms?: number; tokens?: number; turns?: number };
  phases?: { phase: string; problem_id?: string; cost_usd?: number; duration_ms?: number }[];
}

export default function MetricsPanel({ state, events }: MetricsPanelProps) {
  const problemCount = Object.keys(state.problems).length;
  const [report, setReport] = useState<MetricsReport>({});

  // Poll metrics report file every 10 seconds
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${API}/api/metrics`);
        if (res.ok) {
          const data = await res.json();
          if (data.total) setReport(data);
        }
      } catch { /* ignore */ }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  // Compute live elapsed time
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!state.start_time) return;
    const start = new Date(state.start_time).getTime();
    const tick = () => setElapsed(Date.now() - start);
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [state.start_time]);

  // Use report data if available, else use state metrics
  const totalCost = report.total?.cost_usd ?? state.metrics.total_cost;
  const totalDuration = state.status === 'running' ? elapsed : (report.total?.duration_ms ?? state.metrics.total_duration_ms);
  const totalTurns = report.total?.turns ?? 0;

  // Build cost-per-phase from report
  const phaseCosts = useMemo(() => {
    const costs: Record<string, number> = {};
    PHASES.forEach((p) => (costs[p] = 0));

    if (report.phases) {
      for (const step of report.phases) {
        if (step.phase && costs[step.phase] !== undefined && step.cost_usd) {
          costs[step.phase] += step.cost_usd;
        }
      }
    }

    return PHASES.map((phase) => ({
      phase: phase.charAt(0).toUpperCase() + phase.slice(1),
      cost: parseFloat(costs[phase].toFixed(4)),
      phaseKey: phase,
    }));
  }, [report]);

  const hasCostData = phaseCosts.some((p) => p.cost > 0);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden h-full">
      <div className="px-4 py-2.5 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-300">Metrics</h2>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-2 px-3 py-3">
        <MetricCard
          label="Total Cost"
          value={`$${totalCost.toFixed(4)}`}
          accent="text-green-400"
        />
        <MetricCard
          label="Duration"
          value={formatDuration(totalDuration)}
          sub={state.status === 'running' ? 'live' : undefined}
          accent="text-blue-400"
        />
        <MetricCard
          label="Healer Calls"
          value={String(state.healer_invocations)}
          sub={state.healer_invocations > 0 ? 'self-healing active' : 'none yet'}
          accent="text-amber-400"
        />
        <MetricCard
          label="Problems"
          value={String(problemCount)}
          sub={totalTurns > 0 ? `${totalTurns} turns` : (problemCount > 0 ? 'being processed' : 'none')}
          accent="text-purple-400"
        />
      </div>

      {/* Bar chart */}
      <div className="flex-1 px-3 pb-3">
        <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2 px-1">
          Cost by Phase
        </div>
        {hasCostData ? (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={phaseCosts} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
              <XAxis
                dataKey="phase"
                tick={{ fill: '#64748b', fontSize: 9 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={false}
                angle={-35}
                textAnchor="end"
                height={40}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 9 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={false}
                width={40}
                tickFormatter={(v: number) => `$${v}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: '#e2e8f0',
                }}
                formatter={(value) => [`$${Number(value).toFixed(4)}`, 'Cost']}
              />
              <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                {phaseCosts.map((entry) => {
                  const problems = state.problems;
                  let status = 'pending';
                  for (const probId of Object.keys(problems)) {
                    const s = problems[probId]?.phases?.[entry.phaseKey];
                    if (s === 'done' || s === 'healed') { status = 'done'; break; }
                    if (s === 'running') status = 'running';
                    if (s === 'error') status = 'error';
                  }
                  return (
                    <Cell
                      key={entry.phaseKey}
                      fill={entry.cost > 0 ? (PHASE_STATUS_COLORS[status] || '#3b82f6') : '#1e293b'}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[160px] text-sm text-slate-600">
            {state.status === 'running' ? 'Collecting cost data...' : 'No cost data yet'}
          </div>
        )}
      </div>
    </div>
  );
}

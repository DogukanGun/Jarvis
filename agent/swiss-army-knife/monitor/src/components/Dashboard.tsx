'use client';
import type { JobStatus, ToolEvent, ToolMetadata } from '../lib/types';
import { JOB_STATUS_COLORS, CATEGORY_LABELS } from '../lib/constants';

interface DashboardProps {
  jobs: JobStatus[];
  events: ToolEvent[];
  tools: ToolMetadata[];
  onViewOutput: (jobId: string) => void;
}

export default function Dashboard({ jobs, events, tools, onViewOutput }: DashboardProps) {
  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'pending' || j.status === 'waiting_confirmation');
  const completedJobs = jobs.filter((j) => j.status === 'completed');
  const failedJobs = jobs.filter((j) => j.status === 'failed');
  const recentEvents = events.slice(-20).reverse();

  // Category breakdown
  const catCounts: Record<string, number> = {};
  for (const t of tools) {
    catCounts[t.category] = (catCounts[t.category] || 0) + 1;
  }

  return (
    <div className="space-y-4">
      {/* Metrics */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Tools" value={tools.length} color="text-slate-100" />
        <MetricCard label="Active Jobs" value={activeJobs.length} color="text-blue-400" />
        <MetricCard label="Completed" value={completedJobs.length} color="text-green-400" />
        <MetricCard label="Failed" value={failedJobs.length} color="text-red-400" />
      </div>

      {/* Category breakdown */}
      <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-300 mb-3">Tool Categories</h3>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(catCounts).map(([cat, count]) => (
            <div key={cat} className="bg-slate-800/50 rounded-lg p-2 text-center">
              <p className="text-lg font-mono font-bold text-slate-200">{count}</p>
              <p className="text-[10px] text-slate-500 uppercase">{CATEGORY_LABELS[cat as keyof typeof CATEGORY_LABELS] || cat}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Active Jobs */}
        <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-300 mb-3">Active Jobs</h3>
          {activeJobs.length === 0 ? (
            <p className="text-xs text-slate-600">No active jobs</p>
          ) : (
            <div className="space-y-2">
              {activeJobs.map((job) => {
                const sc = JOB_STATUS_COLORS[job.status] || JOB_STATUS_COLORS.pending;
                return (
                  <button
                    key={job.job_id}
                    onClick={() => onViewOutput(job.job_id)}
                    className="w-full flex items-center gap-2 bg-slate-800/50 rounded-lg p-2 text-left hover:bg-slate-800 transition-colors"
                  >
                    <span className={`text-[9px] px-1.5 py-0.5 rounded ${sc.bg} ${sc.text}`}>{job.status}</span>
                    <span className="text-xs text-slate-300 truncate flex-1">{job.tool_name || 'graph'}</span>
                    <span className="text-[10px] text-slate-600 font-mono">{job.job_id.slice(0, 8)}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Events */}
        <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-300 mb-3">Recent Events</h3>
          {recentEvents.length === 0 ? (
            <p className="text-xs text-slate-600">No events yet</p>
          ) : (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {recentEvents.map((evt, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-slate-800/50">
                  <span className="text-[10px] text-slate-600 font-mono w-16 shrink-0">
                    {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                  </span>
                  <span className="text-slate-400">{evt.type}</span>
                  {evt.tool_name && <span className="text-slate-600">({evt.tool_name})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-3">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-mono font-bold ${color} mt-1`}>{value}</p>
    </div>
  );
}

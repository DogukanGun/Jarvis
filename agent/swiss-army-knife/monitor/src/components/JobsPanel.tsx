'use client';
import { useState } from 'react';
import type { JobStatus } from '../lib/types';
import { JOB_STATUS_COLORS } from '../lib/constants';
import { confirmJob } from '../lib/api';

interface JobsPanelProps {
  jobs: JobStatus[];
  onViewOutput: (jobId: string) => void;
}

const FILTERS = ['all', 'pending', 'running', 'waiting_confirmation', 'completed', 'failed'] as const;

export default function JobsPanel({ jobs, onViewOutput }: JobsPanelProps) {
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all' ? jobs : jobs.filter((j) => j.status === filter);
  const sorted = [...filtered].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());

  const handleConfirm = async (jobId: string, confirmed: boolean) => {
    try {
      await confirmJob(jobId, confirmed);
    } catch { /* */ }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-1.5 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2.5 py-1 text-[10px] rounded transition-colors ${
              filter === f ? 'bg-red-500/20 text-red-400' : 'text-slate-500 hover:text-slate-300 bg-slate-800/50'
            }`}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {sorted.length === 0 ? (
        <p className="text-xs text-slate-600">No jobs found</p>
      ) : (
        <div className="space-y-2">
          {sorted.map((job) => {
            const sc = JOB_STATUS_COLORS[job.status] || JOB_STATUS_COLORS.pending;
            return (
              <div key={job.job_id} className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[9px] px-1.5 py-0.5 rounded ${sc.bg} ${sc.text}`}>{job.status.replace('_', ' ')}</span>
                  <span className="text-xs text-slate-300 font-medium">{job.tool_name || 'graph'}</span>
                  <span className="text-[10px] text-slate-600 font-mono ml-auto">{job.job_id.slice(0, 8)}...</span>
                </div>
                <p className="text-[10px] text-slate-600">{new Date(job.started_at).toLocaleString()}</p>
                {job.error && <p className="text-[10px] text-red-400 mt-1">{job.error}</p>}
                <div className="flex gap-2 mt-2">
                  {(job.status === 'running' || job.status === 'pending') && (
                    <button onClick={() => onViewOutput(job.job_id)} className="text-[10px] text-blue-400 hover:underline">View Output</button>
                  )}
                  {job.status === 'waiting_confirmation' && (
                    <>
                      <button onClick={() => handleConfirm(job.job_id, true)} className="text-[10px] px-2 py-0.5 bg-green-600 text-white rounded hover:bg-green-500">Confirm</button>
                      <button onClick={() => handleConfirm(job.job_id, false)} className="text-[10px] px-2 py-0.5 bg-red-600 text-white rounded hover:bg-red-500">Deny</button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

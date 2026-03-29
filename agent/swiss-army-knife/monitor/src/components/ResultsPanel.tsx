'use client';
import { useState } from 'react';
import type { JobStatus } from '../lib/types';
import FindingsBadge from './FindingsBadge';

interface ResultsPanelProps {
  jobs: JobStatus[];
}

export default function ResultsPanel({ jobs }: ResultsPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const completed = jobs
    .filter((j) => j.status === 'completed' && j.result)
    .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());

  if (completed.length === 0) {
    return <p className="text-xs text-slate-600">No completed results yet</p>;
  }

  return (
    <div className="space-y-2">
      {completed.map((job) => {
        const result = job.result || {};
        const findings = (result.findings || []) as Array<{ severity: string; description: string }>;
        const toolsUsed = (result.tools_used || []) as string[];
        const report = result.report as Record<string, unknown> | undefined;
        const isExpanded = expandedId === job.job_id;

        return (
          <div key={job.job_id} className="bg-slate-900/50 border border-slate-700/50 rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedId(isExpanded ? null : job.job_id)}
              className="w-full p-3 flex items-center gap-2 text-left hover:bg-slate-800/30 transition-colors"
            >
              <span className="text-xs text-slate-300 font-medium">{job.tool_name || 'graph'}</span>
              {findings.length > 0 && (
                <span className="text-[10px] text-slate-500">{findings.length} findings</span>
              )}
              {toolsUsed.length > 0 && (
                <span className="text-[10px] text-slate-600">[{toolsUsed.join(', ')}]</span>
              )}
              <span className="text-[10px] text-slate-600 font-mono ml-auto">{new Date(job.started_at).toLocaleString()}</span>
              <span className="text-slate-600">{isExpanded ? '\u25B2' : '\u25BC'}</span>
            </button>
            {isExpanded && (
              <div className="border-t border-slate-800 p-3 space-y-3">
                {findings.length > 0 && (
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase mb-1">Findings</p>
                    <div className="space-y-1">
                      {findings.map((f, i) => (
                        <div key={i} className="flex items-start gap-1.5">
                          <FindingsBadge severity={f.severity} />
                          <span className="text-xs text-slate-400">{f.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {report?.summary != null && (
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase mb-1">Report</p>
                    <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto bg-slate-800/50 rounded-lg p-2">
                      {typeof report.summary === 'string' ? report.summary : JSON.stringify(report.summary, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import type { PipelineState } from '../lib/types';

interface StatusBarProps {
  state: PipelineState;
  connected: boolean;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export default function StatusBar({ state, connected }: StatusBarProps) {
  const [elapsed, setElapsed] = useState<number>(0);

  useEffect(() => {
    if (state.status !== 'running' || !state.start_time) {
      if (state.status === 'complete') {
        setElapsed(state.metrics.total_duration_ms);
      }
      return;
    }

    const startMs = new Date(state.start_time).getTime();

    const tick = () => {
      setElapsed(Date.now() - startMs);
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [state.status, state.start_time, state.metrics.total_duration_ms]);

  const statusConfig = {
    idle: { label: 'Idle', bg: 'bg-slate-600', text: 'text-slate-200', pulse: false },
    running: { label: 'Running', bg: 'bg-blue-600', text: 'text-blue-100', pulse: true },
    complete: { label: 'Complete', bg: 'bg-green-600', text: 'text-green-100', pulse: false },
  };

  const cfg = statusConfig[state.status];
  const problemCount = Object.keys(state.problems).length;

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-slate-900 border-b border-slate-700/50">
      {/* Left section */}
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-slate-100 tracking-tight">
          Pipeline Monitor
        </h1>

        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}
        >
          {cfg.pulse && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-300 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-200" />
            </span>
          )}
          {cfg.label}
        </span>

        {state.topic && (
          <span className="text-sm text-slate-400 max-w-md truncate" title={state.topic}>
            {state.topic}
          </span>
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-6 text-sm">
        {state.status !== 'idle' && (
          <>
            <div className="flex items-center gap-1.5 text-slate-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-mono">{formatElapsed(elapsed)}</span>
            </div>

            <div className="flex items-center gap-1.5 text-slate-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
              <span className="font-mono">${state.metrics.total_cost.toFixed(4)}</span>
            </div>

            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="text-xs">Tokens:</span>
              <span className="font-mono">{state.metrics.total_tokens.toLocaleString()}</span>
            </div>

            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="text-xs">Problems:</span>
              <span className="font-mono">{problemCount}</span>
            </div>
          </>
        )}

        {/* Connection indicator */}
        <div className="flex items-center gap-1.5" title={connected ? 'Connected' : 'Disconnected'}>
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full transition-colors duration-300 ${
              connected ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'
            }`}
          />
          <span className="text-xs text-slate-500">{connected ? 'Live' : 'Offline'}</span>
        </div>
      </div>
    </header>
  );
}

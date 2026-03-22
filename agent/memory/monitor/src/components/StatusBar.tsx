'use client';
import type { MemoryState } from '../lib/types';

interface Props {
  state: MemoryState;
  connected: boolean;
  eventCount: number;
}

export default function StatusBar({ state, connected, eventCount }: Props) {
  const activeGraphs = Object.entries(state.graphs).filter(
    ([, g]) => g.active_node !== null
  );

  const statusColor = {
    idle: 'bg-slate-500',
    active: 'bg-blue-500 animate-pulse-dot',
    error: 'bg-red-500',
  }[state.status];

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-slate-900 border-b border-slate-800">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm font-mono text-slate-400">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
          <span className="text-sm font-mono capitalize">{state.status}</span>
        </div>

        {activeGraphs.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Active:</span>
            {activeGraphs.map(([name, g]) => (
              <span key={name} className="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
                {name.replace('_graph', '')}:{g.active_node}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-xs text-slate-500 font-mono">
          <span>Events: {eventCount}</span>
          <span>Episodes: {state.metrics.total_episodes}</span>
          <span>Promotions: {state.metrics.total_promotions}</span>
        </div>

        <div className="flex items-center gap-2">
          {Object.entries(state.services).map(([name, svc]) => (
            <div
              key={name}
              className={`w-2 h-2 rounded-full ${svc.status === 'running' ? 'bg-green-500' : 'bg-slate-600'}`}
              title={`${name}: ${svc.status}`}
            />
          ))}
        </div>

        <a
          href="http://localhost:3000"
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          Thinker Monitor &rarr;
        </a>
      </div>
    </div>
  );
}

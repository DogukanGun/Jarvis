'use client';
import type { MemoryState } from '../lib/types';

interface Props {
  state: MemoryState;
}

interface ServiceData {
  status: string;
  queue_depth?: number;
  jobs_completed?: number;
  pending?: number;
  next_reflection?: string | null;
  last_reflection?: string | null;
}

function ServiceCard({ name, service }: { name: string; service: ServiceData }) {
  const status = service.status;
  const isRunning = status === 'running';

  return (
    <div className={`
      bg-slate-800/50 rounded-lg p-4 border
      ${isRunning ? 'border-green-500/30' : 'border-slate-700/50'}
    `}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-mono font-medium capitalize">
          {name.replace('_', ' ')}
        </span>
        <div className={`
          flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase
          ${isRunning ? 'bg-green-500/20 text-green-400' : 'bg-slate-700/50 text-slate-500'}
        `}>
          <div className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-green-400' : 'bg-slate-600'}`} />
          {status}
        </div>
      </div>

      <div className="space-y-1.5 text-xs font-mono text-slate-400">
        {service.queue_depth !== undefined && (
          <div className="flex justify-between">
            <span className="text-slate-500">Queue depth</span>
            <span>{service.queue_depth}</span>
          </div>
        )}
        {service.jobs_completed !== undefined && (
          <div className="flex justify-between">
            <span className="text-slate-500">Jobs done</span>
            <span>{service.jobs_completed}</span>
          </div>
        )}
        {service.pending !== undefined && (
          <div className="flex justify-between">
            <span className="text-slate-500">Pending</span>
            <span>{service.pending}</span>
          </div>
        )}
        {service.next_reflection && (
          <div className="flex justify-between">
            <span className="text-slate-500">Next run</span>
            <span>{new Date(service.next_reflection).toLocaleTimeString()}</span>
          </div>
        )}
        {service.last_reflection && (
          <div className="flex justify-between">
            <span className="text-slate-500">Last run</span>
            <span>{new Date(service.last_reflection).toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function StorageCard({ state }: { state: MemoryState }) {
  const sqlite = state.storage.sqlite;
  const lt = state.storage.long_term;

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
      <div className="text-sm font-mono font-medium mb-3">Storage</div>
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-500 font-mono">SQLite</span>
            <span className="text-slate-400 font-mono">{sqlite.episode_count} episodes</span>
          </div>
          <div className="text-[10px] text-slate-600 font-mono">
            {(sqlite.db_size_bytes / 1024).toFixed(1)} KB
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-mono">Long-term ({lt.backend})</span>
            <div className={`flex items-center gap-1 ${lt.healthy ? 'text-green-400' : 'text-red-400'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${lt.healthy ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-[10px] font-mono">{lt.healthy ? 'Healthy' : 'Down'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ServicePanel({ state }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      {Object.entries(state.services).map(([name, svc]) => (
        <ServiceCard key={name} name={name} service={svc as ServiceData} />
      ))}
      <StorageCard state={state} />
    </div>
  );
}

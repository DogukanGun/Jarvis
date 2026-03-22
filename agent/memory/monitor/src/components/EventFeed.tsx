'use client';
import { useState, useRef, useEffect } from 'react';
import type { MemoryEvent } from '../lib/types';
import { EVENT_TYPE_COLORS } from '../lib/types';

interface Props {
  events: MemoryEvent[];
}

export default function EventFeed({ events }: Props) {
  const [filter, setFilter] = useState('');
  const [graphFilter, setGraphFilter] = useState<string>('all');
  const bottomRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events.length, autoScroll]);

  const filtered = events.filter((e) => {
    if (graphFilter !== 'all' && e.graph !== graphFilter) return false;
    if (filter && !JSON.stringify(e).toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  // Show last 200 events
  const display = filtered.slice(-200);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 p-3 border-b border-slate-700/50">
        <input
          type="text"
          placeholder="Filter events..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm font-mono text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500"
        />
        <select
          value={graphFilter}
          onChange={(e) => setGraphFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm font-mono text-slate-300 focus:outline-none"
        >
          <option value="all">All graphs</option>
          <option value="main_graph">main</option>
          <option value="memory_write_graph">memory_write</option>
          <option value="reflection_graph">reflection</option>
          <option value="user_approval_graph">approval</option>
        </select>
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={`text-xs px-2 py-1 rounded ${autoScroll ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-700 text-slate-500'}`}
        >
          {autoScroll ? 'Auto' : 'Manual'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 font-mono text-xs">
        {display.map((event, i) => {
          const color = EVENT_TYPE_COLORS[event.type] || '#64748b';
          const ts = event.timestamp?.split('T')[1]?.split('.')[0] || '';

          return (
            <div
              key={`${event.timestamp}-${i}`}
              className="flex items-start gap-2 px-2 py-1 rounded hover:bg-slate-800/50 animate-slide-in"
            >
              <span className="text-slate-600 shrink-0">{ts}</span>
              <span
                className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"
                style={{ backgroundColor: `${color}20`, color }}
              >
                {event.type}
              </span>
              {event.graph && (
                <span className="text-slate-500 shrink-0">{event.graph.replace('_graph', '')}</span>
              )}
              {event.node && (
                <span className="text-slate-400">{event.node}</span>
              )}
              {event.episode_id && (
                <span className="text-purple-400 truncate">{event.episode_id.slice(0, 8)}...</span>
              )}
              {event.duration_ms !== undefined && (
                <span className="text-emerald-400">{event.duration_ms}ms</span>
              )}
              {event.error && (
                <span className="text-red-400 truncate">{event.error}</span>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div className="px-3 py-1.5 border-t border-slate-700/50 text-xs text-slate-600 font-mono">
        {filtered.length} events ({events.length} total)
      </div>
    </div>
  );
}

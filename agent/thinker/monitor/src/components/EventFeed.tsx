'use client';

import { useEffect, useRef, useState } from 'react';
import type { PipelineEvent } from '../lib/types';

interface EventFeedProps {
  events: PipelineEvent[];
}

type FilterTab = 'all' | 'phases' | 'agents' | 'healer';

const EVENT_TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  phase_start: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'START' },
  phase_end: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'END' },
  phase_error: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'ERROR' },
  agent_message: { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'AGENT' },
  healer_start: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'HEAL+' },
  healer_end: { bg: 'bg-amber-500/20', text: 'text-amber-300', label: 'HEAL-' },
  pipeline_start: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', label: 'PIPE+' },
  pipeline_end: { bg: 'bg-cyan-500/20', text: 'text-cyan-300', label: 'PIPE-' },
};

const FILTER_MAP: Record<FilterTab, string[]> = {
  all: [],
  phases: ['phase_start', 'phase_end', 'phase_error'],
  agents: ['agent_message'],
  healer: ['healer_start', 'healer_end'],
};

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '--:--:--';
  }
}

export default function EventFeed({ events }: EventFeedProps) {
  const [filter, setFilter] = useState<FilterTab>('all');
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  const filtered = filter === 'all'
    ? events
    : events.filter((e) => FILTER_MAP[filter].includes(e.type));

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filtered.length]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 60;
  };

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'phases', label: 'Phases' },
    { key: 'agents', label: 'Agents' },
    { key: 'healer', label: 'Healer' },
  ];

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden h-full">
      {/* Header with filter tabs */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-300">Event Feed</h2>
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                filter === tab.key
                  ? 'bg-slate-700 text-slate-200'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto max-h-[400px] px-3 py-2 space-y-1"
      >
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-sm text-slate-600">
            {events.length === 0 ? 'Waiting for events...' : 'No matching events'}
          </div>
        ) : (
          filtered.map((event, index) => {
            const style = EVENT_TYPE_STYLES[event.type] || {
              bg: 'bg-slate-500/20',
              text: 'text-slate-400',
              label: event.type.toUpperCase(),
            };
            const evtAny = event as Record<string, unknown>;
            const phase = (evtAny.phase as string) || undefined;
            const problemId = (evtAny.problem_id as string) || undefined;
            const message = ((evtAny.content || evtAny.error || evtAny.result || '') as string);

            return (
              <div
                key={`${event.timestamp}-${index}`}
                className="flex items-start gap-2 py-1.5 px-2 rounded-lg hover:bg-slate-800/50 transition-colors group"
              >
                {/* Timestamp */}
                <span className="text-[11px] font-mono text-slate-600 whitespace-nowrap pt-0.5 min-w-[60px]">
                  {formatTime(event.timestamp)}
                </span>

                {/* Type badge */}
                <span
                  className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide ${style.bg} ${style.text} min-w-[44px] justify-center`}
                >
                  {style.label}
                </span>

                {/* Phase */}
                {phase && (
                  <span className="text-[11px] text-slate-500 font-mono whitespace-nowrap pt-0.5">
                    {phase}
                  </span>
                )}

                {/* Problem ID */}
                {problemId && (
                  <span className="text-[11px] text-slate-600 font-mono whitespace-nowrap pt-0.5">
                    #{problemId}
                  </span>
                )}

                {/* Message */}
                {message && (
                  <span className="text-xs text-slate-400 font-mono truncate pt-0.5 flex-1" title={message}>
                    {message}
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-1.5 border-t border-slate-700/50 flex items-center justify-between">
        <span className="text-[10px] text-slate-600">
          {filtered.length} event{filtered.length !== 1 ? 's' : ''}
        </span>
        {!autoScrollRef.current && (
          <button
            onClick={() => {
              autoScrollRef.current = true;
              if (scrollRef.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
              }
            }}
            className="text-[10px] text-blue-500 hover:text-blue-400 transition-colors"
          >
            Scroll to bottom
          </button>
        )}
      </div>
    </div>
  );
}

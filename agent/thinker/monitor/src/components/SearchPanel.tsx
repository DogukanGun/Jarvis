'use client';
import { useState } from 'react';

const API = 'http://localhost:8585';

interface EventResult {
  type: string;
  timestamp: string;
  phase?: string;
  problem_id?: string;
  [key: string]: unknown;
}

interface OutputMatch {
  problem_id: string;
  file: string;
  matches: { line: number; text: string }[];
}

export default function SearchPanel() {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<'events' | 'outputs'>('events');
  const [eventResults, setEventResults] = useState<EventResult[]>([]);
  const [outputResults, setOutputResults] = useState<OutputMatch[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      if (tab === 'events') {
        const res = await fetch(`${API}/api/search/events?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setEventResults(data.results || []);
      } else {
        const res = await fetch(`${API}/api/search/outputs?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setOutputResults(data.results || []);
      }
    } catch { /* ignore */ }
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
        <span className="text-purple-400">&#128269;</span> Search
      </h3>

      {/* Search bar */}
      <div className="flex gap-2 mb-3">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search events, agent messages, outputs..."
          className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
        <button
          onClick={search}
          disabled={loading}
          className="px-4 py-1.5 bg-blue-500/20 border border-blue-500/50 text-blue-300 text-sm rounded-lg hover:bg-blue-500/30 disabled:opacity-50"
        >
          {loading ? '...' : 'Search'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-3">
        {(['events', 'outputs'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1 text-xs rounded-lg ${
              tab === t ? 'bg-slate-700 text-slate-200' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t === 'events' ? 'Agent Messages' : 'Output Files'}
          </button>
        ))}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {tab === 'events' && eventResults.map((evt, i) => (
          <div key={i} className="p-2 bg-slate-800/30 border border-slate-700/30 rounded-lg">
            <div className="flex gap-2 items-center mb-1">
              <span className="text-[10px] text-slate-500">{evt.timestamp?.slice(11, 19)}</span>
              <span className="px-1.5 py-0.5 text-[10px] rounded bg-slate-700/50 text-slate-400">{evt.type}</span>
              {evt.phase && <span className="text-[10px] text-blue-400">{evt.phase as string}</span>}
              {evt.problem_id && <span className="text-[10px] text-slate-500">{evt.problem_id as string}</span>}
            </div>
            <p className="text-xs text-slate-400 font-mono truncate">
              {JSON.stringify(evt).slice(0, 200)}
            </p>
          </div>
        ))}

        {tab === 'outputs' && outputResults.map((res, i) => (
          <div key={i} className="p-2 bg-slate-800/30 border border-slate-700/30 rounded-lg">
            <div className="flex gap-2 items-center mb-1">
              <span className="text-xs text-blue-400">{res.problem_id}</span>
              <span className="text-xs text-slate-400">{res.file}</span>
            </div>
            {res.matches.map((m, j) => (
              <p key={j} className="text-xs text-slate-500 font-mono ml-2">
                <span className="text-slate-600">L{m.line}:</span> {m.text}
              </p>
            ))}
          </div>
        ))}

        {tab === 'events' && eventResults.length === 0 && query && !loading && (
          <p className="text-xs text-slate-500 text-center py-4">No matching events</p>
        )}
        {tab === 'outputs' && outputResults.length === 0 && query && !loading && (
          <p className="text-xs text-slate-500 text-center py-4">No matching outputs</p>
        )}
      </div>
    </div>
  );
}

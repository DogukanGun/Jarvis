'use client';

import { useEffect, useState, useCallback } from 'react';
import type { Lesson } from '../lib/types';

const API_BASE = 'http://localhost:8585';

interface HealerLogProps {
  healerInvocations: number; // used as a trigger to refetch
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '--:--:--';
  }
}

export default function HealerLog({ healerInvocations }: HealerLogProps) {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLessons = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/lessons`);
      if (res.ok) {
        const data = await res.json();
        setLessons(Array.isArray(data) ? data : data.lessons || []);
      } else {
        setError('Failed to fetch lessons');
      }
    } catch {
      setError('Server unreachable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLessons();
  }, [fetchLessons, healerInvocations]);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-300">Healer Log</h2>
        <button
          onClick={fetchLessons}
          className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
          title="Refresh"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[400px] px-3 py-2 space-y-2">
        {loading && lessons.length === 0 && (
          <div className="flex items-center justify-center h-32 text-sm text-slate-600">
            Loading lessons...
          </div>
        )}

        {error && lessons.length === 0 && (
          <div className="flex items-center justify-center h-32 text-sm text-slate-600">
            {error}
          </div>
        )}

        {!loading && !error && lessons.length === 0 && (
          <div className="flex items-center justify-center h-32 text-sm text-slate-600">
            No healer activity yet
          </div>
        )}

        {lessons.map((lesson, i) => (
          <div
            key={`${lesson.timestamp}-${i}`}
            className="relative pl-4 border-l-2 border-amber-500/30 py-2"
          >
            {/* Timeline dot */}
            <div className="absolute left-[-5px] top-3 w-2 h-2 rounded-full bg-amber-500" />

            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-mono text-slate-600">
                {formatTime(lesson.timestamp)}
              </span>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-400">
                {lesson.phase}
              </span>
            </div>

            {/* Error */}
            <div className="mb-1">
              <span className="text-[10px] uppercase tracking-wider text-red-500 mr-1.5">Error:</span>
              <span className="text-xs text-slate-400 font-mono">{lesson.error}</span>
            </div>

            {/* Fix */}
            <div className="mb-1">
              <span className="text-[10px] uppercase tracking-wider text-green-500 mr-1.5">Fix:</span>
              <span className="text-xs text-slate-400 font-mono">{lesson.fix}</span>
            </div>

            {/* Files modified */}
            {lesson.files_modified && lesson.files_modified.length > 0 && (
              <div className="flex items-start gap-1.5 mt-1">
                <span className="text-[10px] uppercase tracking-wider text-slate-600 whitespace-nowrap">Files:</span>
                <div className="flex flex-wrap gap-1">
                  {lesson.files_modified.map((file, j) => (
                    <span
                      key={j}
                      className="inline-block px-1.5 py-0.5 bg-slate-800 rounded text-[10px] text-slate-500 font-mono"
                    >
                      {file}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-1.5 border-t border-slate-700/50">
        <span className="text-[10px] text-slate-600">
          {lessons.length} lesson{lessons.length !== 1 ? 's' : ''} learned
        </span>
      </div>
    </div>
  );
}

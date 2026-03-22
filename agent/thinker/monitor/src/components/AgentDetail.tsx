'use client';

import { useMemo, useRef, useEffect } from 'react';
import type { PipelineEvent } from '../lib/types';

interface AgentDetailProps {
  selectedPhase: string | null;
  selectedProblem: string | null;
  events: PipelineEvent[];
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '--:--:--';
  }
}

export default function AgentDetail({ selectedPhase, selectedProblem, events }: AgentDetailProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const agentMessages = useMemo(() => {
    return events.filter((e) => {
      if (e.type !== 'agent_message') return false;
      if (selectedPhase && e.phase !== selectedPhase) return false;
      if (selectedProblem && e.problem_id !== selectedProblem) return false;
      return true;
    });
  }, [events, selectedPhase, selectedProblem]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentMessages.length]);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-300">Agent Messages</h2>
        <div className="flex items-center gap-2">
          {selectedPhase && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-400">
              {selectedPhase}
            </span>
          )}
          {selectedProblem && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-700 text-slate-400">
              #{selectedProblem}
            </span>
          )}
          {!selectedPhase && !selectedProblem && (
            <span className="text-[10px] text-slate-600">All agents</span>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto max-h-[400px] px-3 py-2 space-y-2"
      >
        {agentMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-sm text-slate-600 gap-1">
            <span>No agent messages</span>
            {!selectedPhase && (
              <span className="text-[10px]">Messages appear when agents communicate during phases</span>
            )}
          </div>
        ) : (
          agentMessages.map((msg, index) => {
            const content = ((msg.content || msg.error || '') as string);
            const source = (msg.source as string) || 'agent';

            return (
              <div key={`${msg.timestamp}-${index}`} className="py-1.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-slate-600">
                    {formatTime(msg.timestamp)}
                  </span>
                  <span className="text-[10px] text-cyan-500 font-medium">{source}</span>
                </div>
                <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-words bg-slate-800/50 rounded-lg px-3 py-2 leading-relaxed">
                  {content}
                </pre>
              </div>
            );
          })
        )}
      </div>

      <div className="px-4 py-1.5 border-t border-slate-700/50">
        <span className="text-[10px] text-slate-600">
          {agentMessages.length} message{agentMessages.length !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  );
}

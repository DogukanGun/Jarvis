'use client';
import { useState } from 'react';
import type { Message, Finding } from '../lib/types';

const INTENT_COLORS: Record<string, string> = {
  chat: 'bg-slate-700/50 text-slate-300',
  research: 'bg-purple-500/20 text-purple-400',
  web_fetch: 'bg-cyan-500/20 text-cyan-400',
  security: 'bg-red-500/20 text-red-400',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'border-red-500/50 bg-red-500/10 text-red-300',
  high: 'border-orange-500/50 bg-orange-500/10 text-orange-300',
  medium: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-300',
  low: 'border-blue-500/50 bg-blue-500/10 text-blue-300',
  info: 'border-slate-600/50 bg-slate-700/30 text-slate-300',
};

function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);
  const severity = finding.severity || 'info';
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;

  return (
    <div className={`border rounded-lg p-2.5 ${colors}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-center justify-between gap-2"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] uppercase font-medium opacity-70 shrink-0">
            {severity}
          </span>
          <span className="text-xs truncate">{finding.description}</span>
        </div>
        <span className="text-[10px] opacity-50 shrink-0">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && finding.details && (
        <pre className="mt-2 text-[11px] leading-relaxed opacity-80 overflow-x-auto max-h-60 whitespace-pre-wrap break-words bg-black/20 rounded p-2">
          {finding.details.raw_output as string ||
            finding.details.raw as string ||
            JSON.stringify(finding.details, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  const hasFindings = msg.findings && msg.findings.length > 0;
  const [showFindings, setShowFindings] = useState(false);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[75%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`
            rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
            ${isUser
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-slate-800 text-slate-200 border border-slate-700/50 rounded-bl-md'}
          `}
        >
          {msg.content}
        </div>

        {/* Metadata badges */}
        {!isUser && (msg.intent || msg.tools_used?.length) && (
          <div className="flex items-center gap-2 mt-1.5 px-1 flex-wrap">
            {msg.intent && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${INTENT_COLORS[msg.intent] || INTENT_COLORS.chat}`}>
                {msg.intent}
              </span>
            )}
            {msg.tools_used?.map((tool) => (
              <span key={tool} className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                {tool}
              </span>
            ))}
            {msg.duration_ms !== undefined && (
              <span className="text-[10px] text-slate-600">{msg.duration_ms}ms</span>
            )}
            {hasFindings && (
              <button
                onClick={() => setShowFindings(!showFindings)}
                className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
              >
                {showFindings ? 'Hide' : 'Show'} {msg.findings!.length} finding{msg.findings!.length !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        )}

        {/* Findings panel */}
        {!isUser && showFindings && hasFindings && (
          <div className="mt-2 space-y-1.5 px-1">
            {msg.findings!.map((f, i) => (
              <FindingCard key={i} finding={f} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

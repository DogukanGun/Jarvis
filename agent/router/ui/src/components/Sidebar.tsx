'use client';
import { useState, useEffect } from 'react';
import type { AgentStatus } from '../lib/types';

const API_BASE = process.env.NEXT_PUBLIC_ROUTER_URL || 'http://localhost:8888';

const MONITOR_LINKS = [
  { name: 'Thinker Monitor', url: 'http://localhost:3000', color: 'text-blue-400' },
  { name: 'Memory Monitor', url: 'http://localhost:3001', color: 'text-purple-400' },
];

export default function Sidebar() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/agents/status`);
        if (res.ok) {
          const data = await res.json();
          setAgents(data.agents || []);
        }
      } catch { /* router not running */ }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="w-56 bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-800">
        <h1 className="text-lg font-bold text-slate-100">Jarvis</h1>
        <p className="text-[10px] text-slate-500 mt-0.5">AI Assistant</p>
      </div>

      {/* Agent Status */}
      <div className="px-4 py-4 flex-1">
        <h2 className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Agents</h2>
        <div className="space-y-2">
          {agents.map((agent) => (
            <div key={agent.name} className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${agent.healthy ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-xs text-slate-400 capitalize">{agent.name.replace('_', ' ')}</span>
            </div>
          ))}
          {agents.length === 0 && (
            <p className="text-xs text-slate-600">Router offline</p>
          )}
        </div>
      </div>

      {/* Monitor Links */}
      <div className="px-4 py-4 border-t border-slate-800">
        <h2 className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Monitors</h2>
        <div className="space-y-2">
          {MONITOR_LINKS.map((link) => (
            <a
              key={link.name}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`block text-xs ${link.color} hover:underline`}
            >
              {link.name} &rarr;
            </a>
          ))}
        </div>
      </div>
    </aside>
  );
}

'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useSSE } from '../hooks/useSSE';
import StatusBar from '../components/StatusBar';
import MetricsPanel from '../components/MetricsPanel';
import EventFeed from '../components/EventFeed';
import HealerLog from '../components/HealerLog';
import AgentDetail from '../components/AgentDetail';
import OutputBrowser from '../components/OutputBrowser';
import SearchPanel from '../components/SearchPanel';
import ControlPanel from '../components/ControlPanel';

const PipelineGraph = dynamic(() => import('../components/PipelineGraph'), {
  ssr: false,
  loading: () => (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl h-[260px] flex items-center justify-center text-sm text-slate-600">
      Loading graph...
    </div>
  ),
});

type BottomTab = 'events' | 'healer' | 'agent' | 'outputs' | 'search';

export default function DashboardPage() {
  const { events, state, connected } = useSSE();
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [selectedProblem, setSelectedProblem] = useState<string | null>(null);
  const [bottomTab, setBottomTab] = useState<BottomTab>('events');

  const tabs: { key: BottomTab; label: string }[] = [
    { key: 'events', label: 'Event Feed' },
    { key: 'agent', label: 'Agent Detail' },
    { key: 'healer', label: 'Healer Log' },
    { key: 'outputs', label: 'Outputs' },
    { key: 'search', label: 'Search' },
  ];

  return (
    <div className="flex flex-col h-screen bg-slate-950">
      {/* Top: Status Bar */}
      <StatusBar state={state} connected={connected} />

      {/* Main content */}
      <main className="flex-1 overflow-auto p-4 space-y-4">
        {/* Control Panel */}
        <ControlPanel state={state} />

        {/* Middle row: Pipeline Graph + Metrics */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <PipelineGraph state={state} />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <MetricsPanel state={state} events={events} />
          </div>
        </div>

        {/* Bottom section: Tabbed panels */}
        <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl overflow-hidden" style={{ minHeight: '340px' }}>
          {/* Tab bar */}
          <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-700/50 bg-slate-800/30">
            {tabs.map(t => (
              <button
                key={t.key}
                onClick={() => setBottomTab(t.key)}
                className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                  bottomTab === t.key
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/50'
                }`}
              >
                {t.label}
              </button>
            ))}

            {/* Phase/Problem selectors for Agent Detail tab */}
            {bottomTab === 'agent' && (
              <div className="flex items-center gap-2 ml-auto">
                <select
                  value={selectedPhase || ''}
                  onChange={(e) => setSelectedPhase(e.target.value || null)}
                  className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Phases</option>
                  {['gather', 'evaluate', 'decompose', 'research', 'plan', 'code', 'test', 'compare', 'write', 'pdf'].map(
                    (p) => (
                      <option key={p} value={p}>
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                      </option>
                    ),
                  )}
                </select>
                <select
                  value={selectedProblem || ''}
                  onChange={(e) => setSelectedProblem(e.target.value || null)}
                  className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Problems</option>
                  {Object.keys(state.problems).map((pid) => (
                    <option key={pid} value={pid}>
                      #{pid}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Tab content */}
          <div className="p-4" style={{ height: '280px', overflow: 'auto' }}>
            {bottomTab === 'events' && <EventFeed events={events} />}
            {bottomTab === 'agent' && (
              <AgentDetail selectedPhase={selectedPhase} selectedProblem={selectedProblem} events={events} />
            )}
            {bottomTab === 'healer' && <HealerLog healerInvocations={state.healer_invocations} />}
            {bottomTab === 'outputs' && <OutputBrowser />}
            {bottomTab === 'search' && <SearchPanel />}
          </div>
        </div>
      </main>
    </div>
  );
}

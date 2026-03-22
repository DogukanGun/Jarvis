'use client';
import { useSSE } from '../hooks/useSSE';
import StatusBar from '../components/StatusBar';
import MetricsPanel from '../components/MetricsPanel';
import GraphView from '../components/GraphView';
import EventFeed from '../components/EventFeed';
import ServicePanel from '../components/ServicePanel';

export default function Home() {
  const { events, state, connected } = useSSE();

  return (
    <div className="flex flex-col h-screen">
      {/* Status Bar */}
      <StatusBar state={state} connected={connected} eventCount={events.length} />

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[1600px] mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-slate-100 font-mono">Memory Monitor</h1>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Jarvis Episodic Memory System
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className={`
                  px-3 py-1.5 rounded-lg text-xs font-mono
                  ${state.storage.long_term.healthy
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'}
                `}>
                  {state.storage.long_term.backend}: {state.storage.long_term.healthy ? 'Connected' : 'Offline'}
                </div>
              </div>
            </div>

            {/* Metrics */}
            <section>
              <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Metrics</h2>
              <MetricsPanel state={state} />
            </section>

            {/* Graph Visualization */}
            <section>
              <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Graph Pipeline</h2>
              <GraphView state={state} />
            </section>

            {/* Services & Storage */}
            <section>
              <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Services & Storage</h2>
              <ServicePanel state={state} />
            </section>

            {/* Event Feed */}
            <section className="h-[400px] bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
              <div className="px-4 py-2 border-b border-slate-800">
                <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider">Event Feed</h2>
              </div>
              <div className="h-[calc(100%-36px)]">
                <EventFeed events={events} />
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

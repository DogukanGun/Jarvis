'use client';
import { useState } from 'react';
import type { MemoryState } from '../lib/types';
import { GRAPH_NAMES, NODE_STATUS_COLORS } from '../lib/types';

interface Props {
  state: MemoryState;
}

// Define the nodes for each graph
const GRAPH_NODES: Record<string, { id: string; label: string }[]> = {
  main_graph: [
    { id: 'preprocess_input', label: 'Preprocess' },
    { id: 'mem0_router', label: 'Mem0 Router' },
    { id: 'load_mem0', label: 'Load Mem0' },
    { id: 'use_mem0_state', label: 'Use State' },
    { id: 'retrieve_episodes', label: 'Retrieve' },
    { id: 'compose_context', label: 'Compose' },
    { id: 'llm_step', label: 'LLM Step' },
    { id: 'return_output', label: 'Return' },
    { id: 'enqueue_write', label: 'Enqueue Write' },
  ],
  memory_write_graph: [
    { id: 'build_episode_candidates', label: 'Build Candidates' },
    { id: 'gate_action', label: 'Gate Action' },
    { id: 'redact_secrets', label: 'Redact Secrets' },
    { id: 'fingerprint', label: 'Fingerprint' },
    { id: 'dedupe_lookup', label: 'Dedupe Lookup' },
    { id: 'insert_episode', label: 'Insert' },
    { id: 'reinforce_episode', label: 'Reinforce' },
    { id: 'embed_episode', label: 'Embed' },
    { id: 'promote_check', label: 'Promote Check' },
    { id: 'create_promotion', label: 'Create Proposal' },
    { id: 'noop', label: 'Skip' },
  ],
  reflection_graph: [
    { id: 'load_recent_episodes', label: 'Load Episodes' },
    { id: 'extract_patterns', label: 'Extract Patterns' },
    { id: 'resolve_conflicts', label: 'Resolve' },
    { id: 'create_proposals', label: 'Create Proposals' },
  ],
  user_approval_graph: [
    { id: 'await_approval', label: 'Await Approval' },
    { id: 'apply_patch', label: 'Apply Patch' },
    { id: 'record_decision', label: 'Record Decision' },
  ],
};

function NodeBox({ label, isActive, status }: { label: string; isActive: boolean; status: string }) {
  const color = isActive ? NODE_STATUS_COLORS.running : NODE_STATUS_COLORS[status] || NODE_STATUS_COLORS.idle;

  return (
    <div
      className={`
        px-3 py-2 rounded-lg border text-xs font-mono text-center
        transition-all duration-300 min-w-[100px]
        ${isActive ? 'border-blue-400 bg-blue-500/20 shadow-lg shadow-blue-500/10 scale-105' : 'border-slate-700 bg-slate-800/50'}
      `}
      style={{ borderColor: isActive ? color : undefined }}
    >
      {isActive && (
        <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-dot mx-auto mb-1" />
      )}
      <span style={{ color: isActive ? color : '#cbd5e1' }}>{label}</span>
    </div>
  );
}

export default function GraphView({ state }: Props) {
  const [activeTab, setActiveTab] = useState<string>('memory_write_graph');

  const graphState = state.graphs[activeTab];
  const nodes = GRAPH_NODES[activeTab] || [];

  return (
    <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-slate-800">
        {GRAPH_NAMES.map((name) => {
          const g = state.graphs[name];
          const isActive = g?.active_node !== null;
          return (
            <button
              key={name}
              onClick={() => setActiveTab(name)}
              className={`
                flex items-center gap-2 px-4 py-2.5 text-xs font-mono transition-colors
                ${activeTab === name ? 'bg-slate-800 text-slate-100 border-b-2 border-blue-500' : 'text-slate-500 hover:text-slate-300'}
              `}
            >
              {isActive && <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-dot" />}
              {name.replace('_graph', '').replace('_', ' ')}
              <span className="text-slate-600">({g?.runs || 0})</span>
            </button>
          );
        })}
      </div>

      {/* Graph visualization */}
      <div className="p-6">
        <div className="flex flex-wrap items-center justify-center gap-2">
          {nodes.map((node, i) => (
            <div key={node.id} className="flex items-center gap-2">
              <NodeBox
                label={node.label}
                isActive={graphState?.active_node === node.id}
                status="idle"
              />
              {i < nodes.length - 1 && (
                <svg width="20" height="12" className="shrink-0 text-slate-600">
                  <line x1="0" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth="1.5" />
                  <polygon points="14,2 20,6 14,10" fill="currentColor" />
                </svg>
              )}
            </div>
          ))}
        </div>

        {/* Graph stats */}
        <div className="flex justify-center gap-6 mt-4 text-xs text-slate-500 font-mono">
          <span>Runs: {graphState?.runs || 0}</span>
          <span>Errors: {graphState?.errors || 0}</span>
          <span>Last: {graphState?.last_run ? new Date(graphState.last_run).toLocaleTimeString() : 'never'}</span>
        </div>
      </div>
    </div>
  );
}

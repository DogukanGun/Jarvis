'use client';

import { useRef, useEffect, useMemo } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { PHASES, PHASE_STATUS_COLORS } from '../lib/types';
import type { PipelineState } from '../lib/types';

interface PipelineGraphProps {
  state: PipelineState;
}

type StatusPriority = 'error' | 'healing' | 'running' | 'healed' | 'pending' | 'done';

const STATUS_PRIORITY: StatusPriority[] = ['error', 'healing', 'running', 'healed', 'pending', 'done'];

function worstStatus(statuses: string[]): string {
  for (const s of STATUS_PRIORITY) {
    if (statuses.includes(s)) return s;
  }
  return 'pending';
}

export default function PipelineGraph({ state }: PipelineGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);

  // Build the graph once
  const graph = useMemo(() => {
    const g = new Graph();

    PHASES.forEach((phase, i) => {
      const x = (i / (PHASES.length - 1)) * 10 - 5;
      const y = Math.sin(i * 0.4) * 0.5;
      g.addNode(phase, {
        label: phase.charAt(0).toUpperCase() + phase.slice(1),
        x,
        y,
        size: 14,
        color: PHASE_STATUS_COLORS.pending,
      });
    });

    for (let i = 0; i < PHASES.length - 1; i++) {
      g.addEdge(PHASES[i], PHASES[i + 1], {
        size: 2,
        color: '#334155',
        type: 'arrow',
      });
    }

    return g;
  }, []);

  // Initialize sigma
  useEffect(() => {
    if (!containerRef.current || sigmaRef.current) return;

    graphRef.current = graph;

    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      labelColor: { color: '#e2e8f0' },
      labelFont: 'Inter, system-ui, sans-serif',
      labelSize: 12,
      labelWeight: '500',
      defaultEdgeType: 'arrow',
      defaultEdgeColor: '#334155',
      stagePadding: 60,
      allowInvalidContainer: true,
      enableEdgeEvents: false,
    });

    // Disable camera movement for a fixed layout
    renderer.getCamera().disable();

    sigmaRef.current = renderer;

    return () => {
      renderer.kill();
      sigmaRef.current = null;
    };
  }, [graph]);

  // Update node colors when state changes
  useEffect(() => {
    if (!graphRef.current) return;
    const g = graphRef.current;
    const problems = state.problems;

    PHASES.forEach((phase) => {
      const statuses: string[] = [];
      for (const probId of Object.keys(problems)) {
        const phaseStatus = problems[probId]?.phases?.[phase];
        if (phaseStatus) {
          statuses.push(phaseStatus);
        }
      }

      const resolved = statuses.length > 0 ? worstStatus(statuses) : 'pending';
      const color = PHASE_STATUS_COLORS[resolved] || PHASE_STATUS_COLORS.pending;

      g.setNodeAttribute(phase, 'color', color);

      // Animate running nodes with larger size
      if (resolved === 'running') {
        g.setNodeAttribute(phase, 'size', 18);
      } else if (resolved === 'error') {
        g.setNodeAttribute(phase, 'size', 16);
      } else {
        g.setNodeAttribute(phase, 'size', 14);
      }
    });

    // Update edge colors based on completed phases
    for (let i = 0; i < PHASES.length - 1; i++) {
      const sourcePhase = PHASES[i];
      const sourceStatuses: string[] = [];
      for (const probId of Object.keys(problems)) {
        const s = problems[probId]?.phases?.[sourcePhase];
        if (s) sourceStatuses.push(s);
      }
      const sourceResolved = sourceStatuses.length > 0 ? worstStatus(sourceStatuses) : 'pending';

      const edgeKey = g.edge(PHASES[i], PHASES[i + 1]);
      if (edgeKey) {
        if (sourceResolved === 'done' || sourceResolved === 'healed') {
          g.setEdgeAttribute(edgeKey, 'color', '#22c55e50');
        } else if (sourceResolved === 'running') {
          g.setEdgeAttribute(edgeKey, 'color', '#3b82f650');
        } else {
          g.setEdgeAttribute(edgeKey, 'color', '#334155');
        }
      }
    }

    sigmaRef.current?.refresh();
  }, [state, graph]);

  return (
    <div className="relative bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden">
      <div className="absolute top-3 left-4 z-10">
        <h2 className="text-sm font-semibold text-slate-300">Pipeline Phases</h2>
      </div>

      <div ref={containerRef} className="w-full h-[260px]" />

      {/* Legend */}
      <div className="absolute bottom-3 left-4 flex gap-3 z-10">
        {Object.entries(PHASE_STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[10px] text-slate-400 capitalize">{status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

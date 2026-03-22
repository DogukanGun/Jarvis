'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { MemoryEvent, MemoryState } from '../lib/types';

const API_BASE = 'http://localhost:8686';

const DEFAULT_STATE: MemoryState = {
  status: 'idle',
  graphs: {
    main_graph: { runs: 0, errors: 0, last_run: null, active_node: null },
    memory_write_graph: { runs: 0, errors: 0, last_run: null, active_node: null },
    reflection_graph: { runs: 0, errors: 0, last_run: null, active_node: null },
    user_approval_graph: { runs: 0, errors: 0, last_run: null, active_node: null },
  },
  metrics: {
    total_episodes: 0,
    total_promotions: 0,
    total_rejections: 0,
    total_reflections: 0,
    total_searches: 0,
    avg_write_latency_ms: 0,
    avg_search_latency_ms: 0,
    dedup_hit_count: 0,
    dedup_total_count: 0,
    secrets_redacted: 0,
  },
  services: {
    memory_worker: { status: 'stopped', queue_depth: 0, jobs_completed: 0 },
    approval_consumer: { status: 'stopped', pending: 0 },
    reflection_scheduler: { status: 'stopped', last_reflection: null, next_reflection: null },
  },
  storage: {
    sqlite: { episode_count: 0, db_size_bytes: 0 },
    long_term: { healthy: false, backend: 'unknown' },
  },
};

export function useSSE() {
  const [events, setEvents] = useState<MemoryEvent[]>([]);
  const [state, setState] = useState<MemoryState>(DEFAULT_STATE);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const stateRes = await fetch(`${API_BASE}/api/state`);
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setState(stateData || DEFAULT_STATE);
      }
      const eventsRes = await fetch(`${API_BASE}/api/events/history`);
      if (eventsRes.ok) {
        const eventsData = await eventsRes.json();
        if (Array.isArray(eventsData)) {
          setEvents(eventsData);
        }
      }
    } catch {
      /* server not running yet */
    }
  }, []);

  useEffect(() => {
    fetchState();

    const connect = () => {
      const es = new EventSource(`${API_BASE}/api/events`);
      esRef.current = es;

      es.onopen = () => setConnected(true);

      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          if (parsed.type) {
            setEvents((prev) => [...prev, parsed as MemoryEvent]);
          }
        } catch {
          /* ignore */
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };
    };

    connect();

    const interval = setInterval(fetchState, 5000);

    return () => {
      esRef.current?.close();
      clearInterval(interval);
    };
  }, [fetchState]);

  return { events, state, connected };
}

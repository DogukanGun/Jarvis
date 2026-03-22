'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { PipelineEvent, PipelineState } from '../lib/types';

const API_BASE = 'http://localhost:8585';

const DEFAULT_STATE: PipelineState = {
  status: 'idle',
  topic: '',
  start_time: null,
  problems: {},
  metrics: { total_cost: 0, total_tokens: 0, total_duration_ms: 0 },
  healer_invocations: 0,
};

export function useSSE() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [state, setState] = useState<PipelineState>(DEFAULT_STATE);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const fetchState = useCallback(async () => {
    try {
      // /api/state returns the state object directly
      const stateRes = await fetch(`${API_BASE}/api/state`);
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setState(stateData || DEFAULT_STATE);
      }
      // /api/events/history returns the events array
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

      // Server sends unnamed SSE messages (data: {...})
      // Use onmessage to catch them
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          // It's an event object with a "type" field
          if (parsed.type) {
            setEvents((prev) => [...prev, parsed as PipelineEvent]);
          }
        } catch {
          /* ignore parse errors or keep-alive comments */
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };
    };

    connect();

    // Also poll state every 5 seconds for reliability
    const interval = setInterval(fetchState, 5000);

    return () => {
      esRef.current?.close();
      clearInterval(interval);
    };
  }, [fetchState]);

  return { events, state, connected };
}

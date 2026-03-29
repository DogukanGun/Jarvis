'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { ToolEvent } from '../lib/types';

const API_BASE = 'http://localhost:8787';

export function useSSE() {
  const [events, setEvents] = useState<ToolEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/events/history`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setEvents(data);
      }
    } catch { /* server not running */ }
  }, []);

  useEffect(() => {
    fetchHistory();

    const connect = () => {
      const es = new EventSource(`${API_BASE}/api/events`);
      esRef.current = es;
      es.onopen = () => setConnected(true);
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          if (parsed.type) {
            setEvents((prev) => [...prev, parsed as ToolEvent]);
          }
        } catch { /* ignore */ }
      };
      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };
    };

    connect();
    const interval = setInterval(fetchHistory, 5000);
    return () => {
      esRef.current?.close();
      clearInterval(interval);
    };
  }, [fetchHistory]);

  return { events, connected };
}

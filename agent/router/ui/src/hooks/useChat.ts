'use client';
import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message, ChatApiResponse, Finding } from '../lib/types';

const API_BASE = process.env.NEXT_PUBLIC_ROUTER_URL || 'http://localhost:8888';
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws/chat';

export function useChat(userId: string = 'default') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingResolveRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'status') {
            setStatus(data.content);
          } else if (data.type === 'agent_event') {
            // Real-time events forwarded from sub-agents via Kafka
            const eventType: string = data.event_type || '';
            if (eventType === 'task.started') {
              setStatus(`Agent ${data.sender || ''} started ${data.target_agent || 'task'}...`);
            } else if (eventType === 'task.completed') {
              if (data.response) {
                // Rich result from swiss-knife — add as a real assistant message
                const resultMsg: Message = {
                  id: `agent-${Date.now()}`,
                  role: 'assistant',
                  content: data.response,
                  timestamp: new Date().toISOString(),
                  intent: 'security',
                  tools_used: data.tools_used || [],
                  findings: (data.findings || []) as Finding[],
                  report: data.report as Record<string, unknown> | undefined,
                };
                setMessages((prev) => [...prev, resultMsg]);
                setStatus(null);
              } else {
                setStatus(`Agent ${data.sender || ''} completed task.`);
              }
            } else if (eventType === 'task.failed') {
              // Show error as a persistent message bubble
              const errMsg: Message = {
                id: `agent-err-${Date.now()}`,
                role: 'assistant',
                content: `Security task failed: ${data.error || 'unknown error'}`,
                timestamp: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, errMsg]);
              setStatus(null);
            } else if (eventType === 'result.security_scan') {
              setStatus('Security scan results received.');
            }
          } else if (data.type === 'response') {
            const assistantMsg: Message = {
              id: `asst-${Date.now()}`,
              role: 'assistant',
              content: data.content,
              timestamp: new Date().toISOString(),
              intent: data.intent,
              tools_used: data.tools_used,
              findings: data.findings as Finding[] | undefined,
              report: data.report as Record<string, unknown> | undefined,
              duration_ms: data.duration_ms,
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setLoading(false);
            setStatus(null);
            pendingResolveRef.current?.();
          } else if (data.type === 'error') {
            const errorMsg: Message = {
              id: `err-${Date.now()}`,
              role: 'assistant',
              content: `Error: ${data.content}`,
              timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMsg]);
            setLoading(false);
            setStatus(null);
            pendingResolveRef.current?.();
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        // Reconnect after 2 seconds
        setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStatus('Sending...');

    const ws = wsRef.current;

    // If WebSocket is connected, use it
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ user_id: userId, message: text }));
      return;
    }

    // Fallback to HTTP if WebSocket is not connected
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, message: text }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data: ChatApiResponse = await res.json();

      const assistantMsg: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        intent: data.intent,
        tools_used: data.tools_used,
        findings: data.findings,
        report: data.report,
        duration_ms: data.metadata?.duration_ms as number | undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Connection error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setStatus(null);
    }
  }, [userId]);

  return { messages, loading, status, sendMessage };
}

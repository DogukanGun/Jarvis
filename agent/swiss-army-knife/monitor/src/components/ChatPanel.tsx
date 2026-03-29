'use client';
import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../lib/types';
import { executeSync } from '../lib/api';
import FindingsBadge from './FindingsBadge';

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await executeSync({ user_id: 'monitor-chat', message: userMsg.content });
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.response,
        timestamp: new Date().toISOString(),
        response: res,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      const errMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 pb-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-slate-600">Send a security-related message to get started</p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
              msg.role === 'user'
                ? 'bg-red-600/20 border border-red-500/30 text-slate-200'
                : 'bg-slate-800/80 border border-slate-700/50 text-slate-300'
            }`}>
              <pre className="text-xs whitespace-pre-wrap font-sans">{msg.content}</pre>
              {msg.response?.tools_used && msg.response.tools_used.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-700/50">
                  <p className="text-[10px] text-slate-500 mb-1">Tools used:</p>
                  <div className="flex flex-wrap gap-1">
                    {msg.response.tools_used.map((t) => (
                      <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">{t}</span>
                    ))}
                  </div>
                </div>
              )}
              {msg.response?.findings && msg.response.findings.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-700/50">
                  <p className="text-[10px] text-slate-500 mb-1">Findings ({msg.response.findings.length}):</p>
                  <div className="space-y-1">
                    {msg.response.findings.slice(0, 5).map((f, i) => (
                      <div key={i} className="flex items-start gap-1.5">
                        <FindingsBadge severity={f.severity} />
                        <span className="text-[10px] text-slate-400">{f.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-xl px-4 py-2.5">
              <span className="text-xs text-slate-500 animate-pulse">Analyzing...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-slate-800 pt-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Describe the security task..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:border-red-500 focus:outline-none"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs rounded-lg transition-colors disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

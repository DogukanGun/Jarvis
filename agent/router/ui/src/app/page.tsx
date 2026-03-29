'use client';
import { useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import Sidebar from '../components/Sidebar';

export default function Home() {
  const { messages, loading, status, sendMessage } = useChat('default');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  return (
    <div className="flex h-screen">
      <Sidebar />

      <main className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto py-6 px-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-20">
                <h2 className="text-2xl font-bold text-slate-300 mb-2">Jarvis</h2>
                <p className="text-sm text-slate-500 mb-8">Your AI assistant with research, web browsing, and security tools</p>
                <div className="flex justify-center gap-3 flex-wrap">
                  {[
                    { label: 'Chat', example: 'Hello, what can you do?' },
                    { label: 'Research', example: 'Research LLM efficiency techniques' },
                    { label: 'Web', example: 'Fetch https://example.com' },
                    { label: 'Security', example: 'Scan the local network for open ports' },
                  ].map((item) => (
                    <button
                      key={item.label}
                      onClick={() => sendMessage(item.example)}
                      className="
                        px-4 py-3 rounded-xl bg-slate-800 border border-slate-700/50
                        text-xs text-slate-400 hover:text-slate-200 hover:border-slate-600
                        transition-colors text-left max-w-[180px]
                      "
                    >
                      <span className="block text-slate-500 text-[10px] uppercase mb-1">{item.label}</span>
                      {item.example}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}

            {loading && (
              <div className="flex justify-start animate-fade-in">
                <div className="bg-slate-800 border border-slate-700/50 rounded-2xl rounded-bl-md px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    {status && <span className="text-xs text-slate-500">{status}</span>}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput onSend={sendMessage} loading={loading} />
      </main>
    </div>
  );
}

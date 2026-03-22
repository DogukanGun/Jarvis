'use client';
import type { Message } from '../lib/types';

const INTENT_COLORS: Record<string, string> = {
  chat: 'bg-slate-700/50 text-slate-300',
  research: 'bg-purple-500/20 text-purple-400',
  web_fetch: 'bg-cyan-500/20 text-cyan-400',
  security: 'bg-red-500/20 text-red-400',
};

export default function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[75%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`
            rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
            ${isUser
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-slate-800 text-slate-200 border border-slate-700/50 rounded-bl-md'}
          `}
        >
          {msg.content}
        </div>

        {/* Metadata badges */}
        {!isUser && (msg.intent || msg.tools_used?.length) && (
          <div className="flex items-center gap-2 mt-1.5 px-1">
            {msg.intent && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${INTENT_COLORS[msg.intent] || INTENT_COLORS.chat}`}>
                {msg.intent}
              </span>
            )}
            {msg.tools_used?.map((tool) => (
              <span key={tool} className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                {tool}
              </span>
            ))}
            {msg.duration_ms !== undefined && (
              <span className="text-[10px] text-slate-600">{msg.duration_ms}ms</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

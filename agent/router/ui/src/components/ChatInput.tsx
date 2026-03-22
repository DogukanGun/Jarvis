'use client';
import { useState, useRef, useEffect } from 'react';

interface Props {
  onSend: (text: string) => void;
  loading: boolean;
}

export default function ChatInput({ onSend, loading }: Props) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [loading]);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-3 p-4 border-t border-slate-800 bg-slate-900/80">
      <textarea
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={loading ? 'Thinking...' : 'Message Jarvis...'}
        disabled={loading}
        rows={1}
        className="
          flex-1 resize-none bg-slate-800 border border-slate-700 rounded-xl
          px-4 py-3 text-sm text-slate-200 placeholder-slate-500
          focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30
          disabled:opacity-50
        "
      />
      <button
        onClick={handleSubmit}
        disabled={loading || !text.trim()}
        className="
          px-5 py-3 rounded-xl text-sm font-medium
          bg-blue-600 text-white hover:bg-blue-500
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {loading ? (
          <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          'Send'
        )}
      </button>
    </div>
  );
}

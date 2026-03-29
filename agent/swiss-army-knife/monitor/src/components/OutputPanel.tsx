'use client';
import { useEffect, useRef, useState } from 'react';
import { useJobOutput } from '../hooks/useJobOutput';
import { sendSessionCommand } from '../lib/api';

interface OutputPanelProps {
  jobId: string | null;
  onClose: () => void;
}

export default function OutputPanel({ jobId, onClose }: OutputPanelProps) {
  const { output } = useJobOutput(jobId);
  const [command, setCommand] = useState('');
  const outputRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const handleCommand = async () => {
    if (!command.trim() || !jobId) return;
    try {
      await sendSessionCommand(jobId, command);
      setCommand('');
    } catch { /* */ }
  };

  return (
    <div className="h-64 border-t border-slate-800 bg-slate-950 flex flex-col shrink-0">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Terminal Output</span>
          {jobId && <span className="text-[10px] text-slate-600 font-mono">{jobId.slice(0, 8)}</span>}
        </div>
        <button onClick={onClose} className="text-slate-600 hover:text-slate-400 text-xs">Close</button>
      </div>
      <pre ref={outputRef} className="flex-1 overflow-y-auto px-3 py-2 text-[11px] text-green-400 font-mono whitespace-pre-wrap">
        {output || (jobId ? 'Waiting for output...' : 'No job selected')}
      </pre>
      {jobId && (
        <div className="flex items-center border-t border-slate-800 px-3 py-1.5">
          <span className="text-green-500 text-xs mr-2 font-mono">&gt;</span>
          <input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCommand()}
            placeholder="Send command..."
            className="flex-1 bg-transparent text-xs text-green-300 placeholder:text-slate-700 focus:outline-none font-mono"
          />
        </div>
      )}
    </div>
  );
}

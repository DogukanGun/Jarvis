'use client';

interface StatusBarProps {
  connected: boolean;
  activeJobCount: number;
}

export default function StatusBar({ connected, activeJobCount }: StatusBarProps) {
  return (
    <header className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-bold text-slate-100">Swiss Army Knife</h1>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">Security Monitor</span>
      </div>
      <div className="flex items-center gap-4">
        {activeJobCount > 0 && (
          <span className="text-xs text-blue-400 font-mono">{activeJobCount} active</span>
        )}
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]' : 'bg-red-400'}`} />
          <span className="text-[10px] text-slate-500">{connected ? 'Live' : 'Offline'}</span>
        </div>
      </div>
    </header>
  );
}

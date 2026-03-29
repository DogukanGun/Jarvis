'use client';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/40',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/40',
  info: 'bg-slate-500/20 text-slate-400 border-slate-500/40',
};

export default function FindingsBadge({ severity }: { severity: string }) {
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-mono uppercase ${colors}`}>
      {severity}
    </span>
  );
}

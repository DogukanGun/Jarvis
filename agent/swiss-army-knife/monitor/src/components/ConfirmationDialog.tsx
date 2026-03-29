'use client';
import type { AuthLevel } from '../lib/types';
import { AUTH_LEVEL_COLORS } from '../lib/constants';

interface ConfirmationDialogProps {
  toolName: string;
  authLevel: AuthLevel;
  params: Record<string, unknown>;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmationDialog({ toolName, authLevel, params, onConfirm, onCancel }: ConfirmationDialogProps) {
  const colors = AUTH_LEVEL_COLORS[authLevel];
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-sm font-bold text-slate-100 mb-2">Confirm Execution</h3>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-slate-400">{toolName}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded border ${colors.bg} ${colors.text} ${colors.border}`}>
            {authLevel.toUpperCase()} RISK
          </span>
        </div>
        <p className="text-xs text-amber-400 mb-3">This tool has elevated privileges. Please confirm you want to proceed.</p>
        {Object.keys(params).length > 0 && (
          <div className="bg-slate-800 rounded-lg p-3 mb-4 max-h-32 overflow-y-auto">
            <p className="text-[10px] text-slate-500 mb-1">Parameters:</p>
            {Object.entries(params).map(([k, v]) => (
              <p key={k} className="text-xs text-slate-400 font-mono">{k}: {JSON.stringify(v)}</p>
            ))}
          </div>
        )}
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition-colors">Cancel</button>
          <button onClick={onConfirm} className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded transition-colors">Confirm</button>
        </div>
      </div>
    </div>
  );
}

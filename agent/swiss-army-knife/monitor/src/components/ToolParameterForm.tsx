'use client';
import { useState } from 'react';
import type { ToolParameter } from '../lib/types';

interface ToolParameterFormProps {
  parameters: ToolParameter[];
  onExecute: (params: Record<string, unknown>) => void;
  onExecuteAsync: (params: Record<string, unknown>) => void;
  executing: boolean;
  isLongRunning: boolean;
}

export default function ToolParameterForm({ parameters, onExecute, onExecuteAsync, executing, isLongRunning }: ToolParameterFormProps) {
  const [values, setValues] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    for (const p of parameters) {
      if (p.default !== undefined && p.default !== null) initial[p.name] = p.default;
    }
    return initial;
  });

  const setValue = (name: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const getParams = () => {
    const params: Record<string, unknown> = {};
    for (const p of parameters) {
      const v = values[p.name];
      if (v !== undefined && v !== '' && v !== null) {
        params[p.name] = p.type === 'integer' ? Number(v) : p.type === 'boolean' ? Boolean(v) : v;
      }
    }
    return params;
  };

  if (parameters.length === 0) {
    return (
      <div>
        <p className="text-xs text-slate-600 mb-3">No parameters required</p>
        <button onClick={() => onExecute({})} disabled={executing} className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded transition-colors disabled:opacity-50">
          {executing ? 'Executing...' : 'Execute'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {parameters.map((p) => (
        <div key={p.name}>
          <label className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            {p.name}
            {p.required && <span className="text-red-400">*</span>}
            <span className="text-[10px] text-slate-600">({p.type})</span>
          </label>
          {p.type === 'boolean' ? (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!values[p.name]}
                onChange={(e) => setValue(p.name, e.target.checked)}
                className="rounded border-slate-700 bg-slate-800"
              />
              <span className="text-xs text-slate-500">{p.description}</span>
            </label>
          ) : p.choices ? (
            <select
              value={String(values[p.name] || '')}
              onChange={(e) => setValue(p.name, e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-red-500 focus:outline-none"
            >
              <option value="">Select...</option>
              {p.choices.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          ) : (
            <input
              type={p.type === 'integer' ? 'number' : 'text'}
              value={String(values[p.name] ?? '')}
              onChange={(e) => setValue(p.name, e.target.value)}
              placeholder={p.description}
              className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-red-500 focus:outline-none"
            />
          )}
        </div>
      ))}
      <div className="flex gap-2 pt-2">
        <button onClick={() => onExecute(getParams())} disabled={executing} className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded transition-colors disabled:opacity-50">
          {executing ? 'Executing...' : 'Execute'}
        </button>
        {isLongRunning && (
          <button onClick={() => onExecuteAsync(getParams())} disabled={executing} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded transition-colors disabled:opacity-50">
            Execute Async
          </button>
        )}
      </div>
    </div>
  );
}

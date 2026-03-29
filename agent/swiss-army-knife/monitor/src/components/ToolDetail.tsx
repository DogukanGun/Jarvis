'use client';
import { useState } from 'react';
import type { ToolMetadata } from '../lib/types';
import { AUTH_LEVEL_COLORS } from '../lib/constants';
import { executeSync, executeAsync } from '../lib/api';
import ToolParameterForm from './ToolParameterForm';
import ConfirmationDialog from './ConfirmationDialog';

interface ToolDetailProps {
  tool: ToolMetadata | null;
  onJobStarted: (jobId: string) => void;
}

export default function ToolDetail({ tool, onJobStarted }: ToolDetailProps) {
  const [result, setResult] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(false);
  const [pendingParams, setPendingParams] = useState<Record<string, unknown>>({});

  if (!tool) {
    return <div className="flex items-center justify-center h-full text-slate-600 text-sm">Select a tool from the sidebar</div>;
  }

  const colors = AUTH_LEVEL_COLORS[tool.auth_level];
  const needsConfirm = tool.auth_level === 'high' || tool.auth_level === 'critical';

  const handleExecute = async (params: Record<string, unknown>) => {
    if (needsConfirm) {
      setPendingParams(params);
      setConfirmDialog(true);
      return;
    }
    await doExecute(params, false);
  };

  const handleExecuteAsync = async (params: Record<string, unknown>) => {
    if (needsConfirm) {
      setPendingParams(params);
      setConfirmDialog(true);
      return;
    }
    await doExecute(params, true);
  };

  const doExecute = async (params: Record<string, unknown>, isAsync: boolean) => {
    setExecuting(true);
    setResult(null);
    try {
      const message = `Execute ${tool.name} with parameters: ${JSON.stringify(params)}`;
      const req = { user_id: 'monitor', message, target_tools: [tool.name], parameters: params };

      if (isAsync || tool.is_long_running) {
        const res = await executeAsync(req);
        onJobStarted(res.job_id);
        setResult(`Async job started: ${res.job_id}`);
      } else {
        const res = await executeSync(req);
        setResult(res.response || JSON.stringify(res.report, null, 2));
      }
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleConfirm = () => {
    setConfirmDialog(false);
    doExecute(pendingParams, tool.is_long_running || false);
  };

  return (
    <div className="space-y-4 max-w-3xl">
      {/* Header */}
      <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-lg font-bold text-slate-100">{tool.display_name}</h2>
          <span className={`text-[10px] px-2 py-0.5 rounded border ${colors.bg} ${colors.text} ${colors.border}`}>
            {tool.auth_level.toUpperCase()}
          </span>
          {tool.is_long_running && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/40">
              LONG-RUNNING
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400 mb-3">{tool.description}</p>
        <div className="flex flex-wrap gap-1.5">
          {tool.capabilities.map((cap) => (
            <span key={cap} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              {cap}
            </span>
          ))}
        </div>
      </div>

      {/* Parameter Form */}
      <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-300 mb-3">Parameters</h3>
        <ToolParameterForm
          parameters={tool.parameters}
          onExecute={handleExecute}
          onExecuteAsync={handleExecuteAsync}
          executing={executing}
          isLongRunning={tool.is_long_running || false}
        />
      </div>

      {/* Result */}
      {result && (
        <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-300 mb-2">Result</h3>
          <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">{result}</pre>
        </div>
      )}

      {confirmDialog && (
        <ConfirmationDialog
          toolName={tool.display_name}
          authLevel={tool.auth_level}
          params={pendingParams}
          onConfirm={handleConfirm}
          onCancel={() => setConfirmDialog(false)}
        />
      )}
    </div>
  );
}

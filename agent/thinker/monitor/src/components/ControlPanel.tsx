'use client';
import { useState, useEffect } from 'react';
import type { PipelineState } from '../lib/types';

const API = 'http://localhost:8585';

interface Props {
  state: PipelineState;
}

export default function ControlPanel({ state }: Props) {
  const [topic, setTopic] = useState('');
  const [agent, setAgent] = useState('claude');
  const [maxProblems, setMaxProblems] = useState('3');
  const [maxAccepted, setMaxAccepted] = useState('3');
  const [maxResearch, setMaxResearch] = useState('3');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API}/api/pipeline/status`);
        const data = await res.json();
        setPipelineRunning(data.running);
      } catch { /* server not up */ }
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  const startPipeline = async () => {
    if (!topic.trim()) {
      setMessage('Please enter a research topic');
      return;
    }
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`${API}/api/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          agent,
          max_problems: maxProblems ? parseInt(maxProblems) : null,
          max_accepted: maxAccepted ? parseInt(maxAccepted) : null,
          max_research: maxResearch ? parseInt(maxResearch) : null,
        }),
      });
      const data = await res.json();
      if (data.error) {
        setMessage(data.error);
      } else {
        setMessage(`Pipeline started (PID: ${data.pid})`);
        setPipelineRunning(true);
      }
    } catch (e) {
      setMessage(`Failed to start: ${e}`);
    }
    setLoading(false);
  };

  const stopPipeline = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/pipeline/stop`, { method: 'POST' });
      const data = await res.json();
      setMessage(`Pipeline ${data.status}`);
      setPipelineRunning(false);
    } catch (e) {
      setMessage(`Failed to stop: ${e}`);
    }
    setLoading(false);
  };

  return (
    <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
        <span className="text-green-400">&#9654;</span> Pipeline Control
        {pipelineRunning && (
          <span className="ml-auto flex items-center gap-1.5 text-xs">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-green-400">Running</span>
          </span>
        )}
      </h3>

      {/* Topic input */}
      <div className="mb-3">
        <label className="text-xs text-slate-500 block mb-1">Research Topic</label>
        <input
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. Agent orchestration; How to let agents work together..."
          className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          disabled={pipelineRunning}
        />
      </div>

      {/* Config row */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Agent</label>
          <select
            value={agent}
            onChange={e => setAgent(e.target.value)}
            disabled={pipelineRunning}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none"
          >
            <option value="claude">Claude</option>
            <option value="qwen">Qwen</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Max Problems</label>
          <input
            value={maxProblems}
            onChange={e => setMaxProblems(e.target.value)}
            type="number"
            min="1"
            disabled={pipelineRunning}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Max Accepted</label>
          <input
            value={maxAccepted}
            onChange={e => setMaxAccepted(e.target.value)}
            type="number"
            min="1"
            disabled={pipelineRunning}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Max Research</label>
          <input
            value={maxResearch}
            onChange={e => setMaxResearch(e.target.value)}
            type="number"
            min="1"
            disabled={pipelineRunning}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none"
          />
        </div>
      </div>

      {/* Buttons */}
      <div className="flex gap-2 items-center">
        {!pipelineRunning ? (
          <button
            onClick={startPipeline}
            disabled={loading}
            className="px-4 py-2 bg-green-500/20 border border-green-500/50 text-green-300 text-sm rounded-lg hover:bg-green-500/30 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Starting...' : 'Start Research'}
          </button>
        ) : (
          <button
            onClick={stopPipeline}
            disabled={loading}
            className="px-4 py-2 bg-red-500/20 border border-red-500/50 text-red-300 text-sm rounded-lg hover:bg-red-500/30 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Stopping...' : 'Stop Pipeline'}
          </button>
        )}
        {message && (
          <span className="text-xs text-slate-400">{message}</span>
        )}
      </div>
    </div>
  );
}

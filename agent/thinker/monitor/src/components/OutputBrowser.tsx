'use client';
import { useState, useEffect } from 'react';

const API = 'http://localhost:8585';

interface Run {
  problem_id: string;
  files: string[];
  has_pdf: boolean;
  has_paper: boolean;
  subdirs: string[];
}

interface FileEntry {
  name: string;
  size?: number;
  type: 'file' | 'dir';
  ext?: string;
}

export default function OutputBrowser() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [viewingFile, setViewingFile] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/runs`).then(r => r.json()).then(d => setRuns(d.runs || [])).catch(() => {});
  }, []);

  const selectRun = async (problemId: string) => {
    setSelectedRun(problemId);
    setFileContent(null);
    setViewingFile(null);
    try {
      const res = await fetch(`${API}/api/outputs/${problemId}`);
      const data = await res.json();
      setFiles(data.files || []);
    } catch { setFiles([]); }
  };

  const viewFile = async (problemId: string, filePath: string, ext: string) => {
    if (['.pdf', '.png', '.jpg'].includes(ext)) {
      window.open(`${API}/api/outputs/${problemId}/${filePath}`, '_blank');
      return;
    }
    try {
      const res = await fetch(`${API}/api/outputs/${problemId}/${filePath}`);
      const data = await res.json();
      setViewingFile(filePath);
      setFileContent(typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2));
    } catch { setFileContent('Failed to load file'); }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
        <span className="text-blue-400">&#128193;</span> Output Browser
      </h3>

      {/* Run selector */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {runs.map(run => (
          <button
            key={run.problem_id}
            onClick={() => selectRun(run.problem_id)}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              selectedRun === run.problem_id
                ? 'bg-blue-500/20 border-blue-500/50 text-blue-300'
                : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-slate-200'
            }`}
          >
            {run.problem_id}
            {run.has_pdf && <span className="ml-1 text-green-400" title="PDF available">&#9679;</span>}
          </button>
        ))}
        {runs.length === 0 && <p className="text-xs text-slate-500">No output runs found</p>}
      </div>

      {/* File list + content */}
      <div className="flex-1 flex gap-3 min-h-0 overflow-hidden">
        {selectedRun && (
          <div className="w-56 flex-shrink-0 overflow-y-auto border border-slate-700/50 rounded-lg bg-slate-800/30 p-2">
            {files.filter(f => f.type === 'file').map(f => (
              <button
                key={f.name}
                onClick={() => viewFile(selectedRun, f.name, f.ext || '')}
                className={`w-full text-left px-2 py-1 text-xs rounded hover:bg-slate-700/50 flex justify-between items-center ${
                  viewingFile === f.name ? 'bg-slate-700/50 text-blue-300' : 'text-slate-400'
                }`}
              >
                <span className="truncate">{f.name}</span>
                <span className="text-slate-600 ml-1 flex-shrink-0">{formatSize(f.size)}</span>
              </button>
            ))}
          </div>
        )}

        {fileContent !== null && (
          <div className="flex-1 overflow-auto border border-slate-700/50 rounded-lg bg-slate-900/50 p-3">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400">{viewingFile}</span>
              <button
                onClick={() => { setFileContent(null); setViewingFile(null); }}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Close
              </button>
            </div>
            <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-words">
              {fileContent}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

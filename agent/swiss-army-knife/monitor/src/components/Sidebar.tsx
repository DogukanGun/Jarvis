'use client';
import type { ToolMetadata, ToolCategory } from '../lib/types';
import { AUTH_LEVEL_COLORS, CATEGORY_LABELS } from '../lib/constants';

interface SidebarProps {
  tools: ToolMetadata[];
  loading: boolean;
  selectedTool: ToolMetadata | null;
  onSelectTool: (tool: ToolMetadata) => void;
}

const CATEGORY_ORDER: ToolCategory[] = [
  'wifi', 'network', 'exploitation', 'post_exploitation', 'password', 'monitoring', 'ctf',
];

export default function Sidebar({ tools, loading, selectedTool, onSelectTool }: SidebarProps) {
  const grouped = CATEGORY_ORDER.reduce((acc, cat) => {
    acc[cat] = tools.filter((t) => t.category === cat);
    return acc;
  }, {} as Record<ToolCategory, ToolMetadata[]>);

  return (
    <aside className="w-56 bg-slate-900 border-r border-slate-800 flex flex-col overflow-y-auto shrink-0">
      <div className="px-3 py-3 border-b border-slate-800">
        <p className="text-[10px] text-slate-500 uppercase tracking-wider">Tools ({tools.length})</p>
      </div>
      {loading ? (
        <p className="text-xs text-slate-600 p-3">Loading...</p>
      ) : (
        <div className="py-1">
          {CATEGORY_ORDER.map((cat) => {
            const catTools = grouped[cat];
            if (!catTools || catTools.length === 0) return null;
            return (
              <div key={cat} className="mb-1">
                <p className="text-[9px] text-slate-600 uppercase tracking-wider px-3 py-1.5 font-semibold">
                  {CATEGORY_LABELS[cat]}
                </p>
                {catTools.map((tool) => {
                  const colors = AUTH_LEVEL_COLORS[tool.auth_level];
                  const isSelected = selectedTool?.name === tool.name;
                  return (
                    <button
                      key={tool.name}
                      onClick={() => onSelectTool(tool)}
                      className={`w-full text-left px-3 py-1.5 flex items-center gap-2 text-xs transition-colors ${
                        isSelected
                          ? 'bg-slate-800 text-slate-100'
                          : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                      }`}
                    >
                      <span className="truncate flex-1">{tool.display_name}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded ${colors.bg} ${colors.text} ${colors.border} border`}>
                        {tool.auth_level.toUpperCase()}
                      </span>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}

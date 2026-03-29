'use client';
import type { MainTab } from '../lib/types';

interface TabBarProps {
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
}

const TABS: { key: MainTab; label: string }[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'tool-detail', label: 'Tool' },
  { key: 'chat', label: 'Chat' },
  { key: 'jobs', label: 'Jobs' },
  { key: 'results', label: 'Results' },
];

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="h-10 bg-slate-900/50 border-b border-slate-800 flex items-center px-2 gap-1 shrink-0">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          className={`px-3 py-1.5 text-xs rounded transition-colors ${
            activeTab === tab.key
              ? 'bg-red-500/20 text-red-400 font-medium'
              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

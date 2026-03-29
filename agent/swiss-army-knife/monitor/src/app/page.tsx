'use client';
import { useState } from 'react';
import type { ToolMetadata, MainTab } from '../lib/types';
import { useSSE } from '../hooks/useSSE';
import { useTools } from '../hooks/useTools';
import { useJobs } from '../hooks/useJobs';
import StatusBar from '../components/StatusBar';
import Sidebar from '../components/Sidebar';
import TabBar from '../components/TabBar';
import Dashboard from '../components/Dashboard';
import ToolDetail from '../components/ToolDetail';
import ChatPanel from '../components/ChatPanel';
import JobsPanel from '../components/JobsPanel';
import ResultsPanel from '../components/ResultsPanel';
import OutputPanel from '../components/OutputPanel';

export default function Home() {
  const { events, connected } = useSSE();
  const { tools, loading } = useTools();
  const { jobs } = useJobs();
  const [selectedTool, setSelectedTool] = useState<ToolMetadata | null>(null);
  const [activeTab, setActiveTab] = useState<MainTab>('dashboard');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [outputExpanded, setOutputExpanded] = useState(false);

  const handleSelectTool = (tool: ToolMetadata) => {
    setSelectedTool(tool);
    setActiveTab('tool-detail');
  };

  const handleViewOutput = (jobId: string) => {
    setActiveJobId(jobId);
    setOutputExpanded(true);
  };

  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'pending');

  return (
    <div className="h-screen flex flex-col">
      <StatusBar connected={connected} activeJobCount={activeJobs.length} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          tools={tools}
          loading={loading}
          selectedTool={selectedTool}
          onSelectTool={handleSelectTool}
        />
        <div className="flex-1 flex flex-col overflow-hidden">
          <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
          <div className="flex-1 overflow-auto p-4">
            {activeTab === 'dashboard' && (
              <Dashboard jobs={jobs} events={events} tools={tools} onViewOutput={handleViewOutput} />
            )}
            {activeTab === 'tool-detail' && (
              <ToolDetail tool={selectedTool} onJobStarted={handleViewOutput} />
            )}
            {activeTab === 'chat' && <ChatPanel />}
            {activeTab === 'jobs' && (
              <JobsPanel jobs={jobs} onViewOutput={handleViewOutput} />
            )}
            {activeTab === 'results' && <ResultsPanel jobs={jobs} />}
          </div>
          {outputExpanded && (
            <OutputPanel
              jobId={activeJobId}
              onClose={() => setOutputExpanded(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

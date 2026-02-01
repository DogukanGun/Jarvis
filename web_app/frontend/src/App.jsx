import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import ChatInterface from './components/ChatInterface';
import EventTimeline from './components/EventTimeline';
import ApprovalPanel from './components/ApprovalPanel';
import StatusDashboard from './components/StatusDashboard';

function App() {
  const [events, setEvents] = useState([]);
  const [systemStatus, setSystemStatus] = useState('disconnected');
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [eventStream, setEventStream] = useState(null);

  // Connect to event stream
  useEffect(() => {
    const connectEventStream = () => {
      const eventSource = new EventSource('/api/events/stream');

      eventSource.onopen = () => {
        console.log('Connected to event stream');
        setSystemStatus('connected');
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Event received:', data);

          setEvents((prev) => [data, ...prev].slice(0, 100)); // Keep last 100 events

          // Check for approval requests
          if (data.type === 'approval.requested') {
            setPendingApprovals((prev) => [...prev, data.payload]);
          }

          // Remove approval when granted/denied
          if (
            data.type === 'approval.granted' ||
            data.type === 'approval.denied'
          ) {
            setPendingApprovals((prev) =>
              prev.filter((a) => a.approval_id !== data.payload.approval_id)
            );
          }
        } catch (err) {
          console.error('Error parsing event:', err);
        }
      };

      eventSource.onerror = () => {
        console.error('Event stream error');
        setSystemStatus('disconnected');
        eventSource.close();

        // Reconnect after 3 seconds
        setTimeout(connectEventStream, 3000);
      };

      setEventStream(eventSource);

      return () => {
        eventSource.close();
      };
    };

    connectEventStream();
  }, []);

  // Check system health periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await axios.get('/api/health', { timeout: 5000 });
        setSystemStatus('healthy');
      } catch (err) {
        if (systemStatus === 'connected') {
          setSystemStatus('warning');
        }
      }
    };

    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [systemStatus]);

  const handleMessage = async (message, imageData) => {
    try {
      setActiveTab('timeline');
      await axios.post('/api/message', { message, imageData });
    } catch (err) {
      console.error('Error sending message:', err);
      alert(`Error sending message: ${err.message}`);
    }
  };

  const handleApprovalDecision = async (approvalId, decision, reason) => {
    try {
      await axios.post(`/api/approval/${approvalId}/${decision}`, { reason });
      setPendingApprovals((prev) =>
        prev.filter((a) => a.approval_id !== approvalId)
      );
    } catch (err) {
      console.error('Error publishing approval:', err);
      alert(`Error: ${err.message}`);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div>
            <h1>🤖 Jarvis Group Layer Tester</h1>
            <p>Real-time testing interface for multi-agent orchestration</p>
          </div>
          <div className="status-indicator">
            <div className={`status-dot ${systemStatus}`}></div>
            <span>{systemStatus}</span>
          </div>
        </div>
      </header>

      <div className="app-container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat ({events.length})
          </button>
          <button
            className={`tab ${activeTab === 'timeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('timeline')}
          >
            📊 Events ({events.length})
          </button>
          <button
            className={`tab ${activeTab === 'approvals' ? 'active' : ''}`}
            onClick={() => setActiveTab('approvals')}
          >
            ✅ Approvals ({pendingApprovals.length})
          </button>
          <button
            className={`tab ${activeTab === 'status' ? 'active' : ''}`}
            onClick={() => setActiveTab('status')}
          >
            📈 Status
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'chat' && <ChatInterface onSendMessage={handleMessage} />}

          {activeTab === 'timeline' && <EventTimeline events={events} />}

          {activeTab === 'approvals' && (
            <ApprovalPanel
              approvals={pendingApprovals}
              onDecision={handleApprovalDecision}
            />
          )}

          {activeTab === 'status' && <StatusDashboard events={events} />}
        </div>
      </div>

      <footer className="app-footer">
        <p>Jarvis Group Communication Layer v1.0.0</p>
        <p>Status: {systemStatus}</p>
      </footer>
    </div>
  );
}

export default App;

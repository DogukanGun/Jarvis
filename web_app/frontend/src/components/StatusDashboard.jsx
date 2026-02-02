import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './StatusDashboard.css';

function StatusDashboard({ events }) {
  const [orchestratorStatus, setOrchestratorStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get('/api/orchestrator/status');
        setOrchestratorStatus(response.data);
      } catch (err) {
        console.error('Error fetching orchestrator status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Calculate event statistics
  const stats = {
    total: events.length,
    chat: events.filter((e) => e.type === 'chat.message').length,
    proposals: events.filter((e) => e.type.startsWith('proposal.')).length,
    approvals: events.filter((e) => e.type.startsWith('approval.')).length,
    tasks: events.filter((e) => e.type.startsWith('task.')).length,
    results: events.filter((e) => e.type.startsWith('result.')).length,
    errors: events.filter((e) => e.type === 'error').length,
  };

  const getEventTypeBreakdown = () => {
    const breakdown = {};
    events.forEach((e) => {
      breakdown[e.type] = (breakdown[e.type] || 0) + 1;
    });
    return Object.entries(breakdown)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
  };

  return (
    <div className="status-dashboard">
      <div className="status-grid">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-label">Total Events</div>
            <div className="stat-value">{stats.total}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-content">
            <div className="stat-label">Messages</div>
            <div className="stat-value">{stats.chat}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">💡</div>
          <div className="stat-content">
            <div className="stat-label">Proposals</div>
            <div className="stat-value">{stats.proposals}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">❓</div>
          <div className="stat-content">
            <div className="stat-label">Approvals</div>
            <div className="stat-value">{stats.approvals}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📋</div>
          <div className="stat-content">
            <div className="stat-label">Tasks</div>
            <div className="stat-value">{stats.tasks}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📤</div>
          <div className="stat-content">
            <div className="stat-label">Results</div>
            <div className="stat-value">{stats.results}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-content">
            <div className="stat-label">Errors</div>
            <div className="stat-value" style={{ color: stats.errors > 0 ? '#f44336' : '#999' }}>
              {stats.errors}
            </div>
          </div>
        </div>
      </div>

      <div className="status-sections">
        <div className="status-section">
          <h3>🔧 Orchestrator Status</h3>
          {loading ? (
            <p className="loading">Loading orchestrator status...</p>
          ) : orchestratorStatus ? (
            <div className="orchestrator-info">
              <div className="info-item">
                <label>Status:</label>
                <span className={`badge ${orchestratorStatus.enabled ? 'enabled' : 'disabled'}`}>
                  {orchestratorStatus.enabled ? '✅ Enabled' : '❌ Disabled'}
                </span>
              </div>
              <div className="info-item">
                <label>Group ID:</label>
                <code>{orchestratorStatus.group_id}</code>
              </div>
              <div className="info-item">
                <label>Messages Processed:</label>
                <span>{orchestratorStatus.messages || 0}</span>
              </div>
              <div className="info-item">
                <label>Consumer Lag:</label>
                <span>{orchestratorStatus.lag || 0}</span>
              </div>
              <div className="info-item">
                <label>Topics:</label>
                <div className="topics-list">
                  {orchestratorStatus.topics &&
                    orchestratorStatus.topics.map((topic) => (
                      <code key={topic}>{topic}</code>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="error">Failed to load orchestrator status</p>
          )}
        </div>

        <div className="status-section">
          <h3>📈 Event Type Breakdown</h3>
          <div className="breakdown-list">
            {getEventTypeBreakdown().map(([type, count]) => (
              <div key={type} className="breakdown-item">
                <span className="type-label">{type}</span>
                <div className="type-bar-container">
                  <div
                    className="type-bar"
                    style={{
                      width: `${(count / stats.total) * 100}%`,
                    }}
                  ></div>
                </div>
                <span className="type-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="status-info-box">
        <h4>💡 Tips</h4>
        <ul>
          <li>Monitor the event count to track workflow progress</li>
          <li>Check orchestrator status for connection details</li>
          <li>Event breakdown shows distribution of processed events</li>
          <li>High error count may indicate a problem - check the Events tab</li>
          <li>Refresh the status dashboard every 5 seconds</li>
        </ul>
      </div>
    </div>
  );
}

export default StatusDashboard;

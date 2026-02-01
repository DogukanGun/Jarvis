import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import './EventTimeline.css';

function EventTimeline({ events }) {
  const getEventIcon = (type) => {
    const icons = {
      'chat.message': '💬',
      'proposal.created': '💡',
      'approval.requested': '❓',
      'approval.granted': '✅',
      'approval.denied': '❌',
      'task.created': '📋',
      'task.started': '▶️',
      'task.progress': '⏳',
      'task.completed': '✨',
      'task.failed': '⚠️',
      'result.generated': '📤',
      'result.image_analysis': '🖼️',
      'result.code_diff': '💻',
      'result.plan': '📊',
      'result.web_extraction': '🌐',
      'result.summary': '📋',
      'error': '🔴',
      'heartbeat': '💓',
      'connection.established': '🔗',
    };
    return icons[type] || '📌';
  };

  const getEventColor = (type) => {
    if (type.startsWith('approval')) return '#ff9800';
    if (type.startsWith('task')) return '#2196f3';
    if (type.startsWith('result')) return '#4caf50';
    if (type.startsWith('error')) return '#f44336';
    if (type.startsWith('proposal')) return '#9c27b0';
    return '#667eea';
  };

  const formatPayload = (payload) => {
    if (!payload) return 'No payload';
    if (typeof payload === 'string') return payload;
    if (payload.text) return payload.text;
    if (payload.title) return payload.title;
    if (payload.description) return payload.description;
    return JSON.stringify(payload).substring(0, 100) + '...';
  };

  return (
    <div className="event-timeline">
      {events.length === 0 ? (
        <div className="no-events">
          <p>📭 No events yet</p>
          <p>Send a message in the Chat tab to get started!</p>
        </div>
      ) : (
        <div className="events-list">
          {events.map((event, idx) => (
            <div key={idx} className="event-item">
              <div
                className="event-marker"
                style={{ borderColor: getEventColor(event.type) }}
              >
                <span>{getEventIcon(event.type)}</span>
              </div>

              <div className="event-content">
                <div className="event-header">
                  <h4 className="event-type" style={{ color: getEventColor(event.type) }}>
                    {event.type}
                  </h4>
                  <span className="event-time">
                    {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                  </span>
                </div>

                <div className="event-body">
                  <p className="event-description">{formatPayload(event.payload)}</p>

                  {event.sender && (
                    <div className="event-meta">
                      <span className="event-sender">
                        From: <strong>{event.sender.agent || event.sender.id}</strong>
                      </span>
                      <span className="event-role">{event.sender.role}</span>
                    </div>
                  )}

                  {event.thread_id && (
                    <div className="event-thread">
                      Thread: <code>{event.thread_id.substring(0, 12)}...</code>
                    </div>
                  )}
                </div>

                <details className="event-details">
                  <summary>View Full JSON</summary>
                  <pre>{JSON.stringify(event, null, 2)}</pre>
                </details>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default EventTimeline;

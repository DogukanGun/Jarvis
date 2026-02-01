import React, { useState } from 'react';
import './ApprovalPanel.css';

function ApprovalPanel({ approvals, onDecision }) {
  const [expandedId, setExpandedId] = useState(null);
  const [reasons, setReasons] = useState({});

  const handleApprove = async (approvalId) => {
    await onDecision(approvalId, 'grant', reasons[approvalId] || 'Approved');
  };

  const handleDeny = async (approvalId) => {
    await onDecision(approvalId, 'deny', reasons[approvalId] || 'Denied');
  };

  return (
    <div className="approval-panel">
      {approvals.length === 0 ? (
        <div className="no-approvals">
          <p>✅ No pending approvals</p>
          <p>All requests have been handled!</p>
        </div>
      ) : (
        <div className="approvals-list">
          <div className="approvals-header">
            <h3>Pending Approvals ({approvals.length})</h3>
            <p>Review and approve/deny pending requests</p>
          </div>

          {approvals.map((approval) => (
            <div
              key={approval.approval_id}
              className={`approval-card ${expandedId === approval.approval_id ? 'expanded' : ''}`}
            >
              <div
                className="approval-title"
                onClick={() =>
                  setExpandedId(
                    expandedId === approval.approval_id ? null : approval.approval_id
                  )
                }
              >
                <div className="approval-icon">❓</div>
                <div className="approval-info">
                  <h4>
                    {approval.proposal_id ? 'Proposal Approval' : 'Task Approval'}
                  </h4>
                  <p className="approval-time">
                    ID: {approval.approval_id.substring(0, 12)}...
                  </p>
                </div>
                <div className="approval-toggle">
                  {expandedId === approval.approval_id ? '▼' : '▶'}
                </div>
              </div>

              {expandedId === approval.approval_id && (
                <div className="approval-details">
                  <div className="approval-content">
                    <div className="field">
                      <label>Description:</label>
                      <p>{approval.text || 'No description provided'}</p>
                    </div>

                    {approval.proposal_id && (
                      <div className="field">
                        <label>Proposal ID:</label>
                        <code>{approval.proposal_id}</code>
                      </div>
                    )}

                    {approval.task_id && (
                      <div className="field">
                        <label>Task ID:</label>
                        <code>{approval.task_id}</code>
                      </div>
                    )}

                    <div className="field">
                      <label>Reason (optional):</label>
                      <textarea
                        placeholder="Enter your reason for approval/denial..."
                        value={reasons[approval.approval_id] || ''}
                        onChange={(e) =>
                          setReasons({
                            ...reasons,
                            [approval.approval_id]: e.target.value,
                          })
                        }
                        className="reason-input"
                      />
                    </div>
                  </div>

                  <div className="approval-actions">
                    <button
                      className="btn-approve"
                      onClick={() => handleApprove(approval.approval_id)}
                    >
                      ✅ Approve
                    </button>
                    <button
                      className="btn-deny"
                      onClick={() => handleDeny(approval.approval_id)}
                    >
                      ❌ Deny
                    </button>
                  </div>

                  <details className="approval-json">
                    <summary>View Full JSON</summary>
                    <pre>{JSON.stringify(approval, null, 2)}</pre>
                  </details>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="approval-info-box">
        <h4>About Approvals</h4>
        <ul>
          <li>Review pending approval requests from the orchestrator</li>
          <li>Approvals are required for sensitive operations</li>
          <li>Provide a reason for your decision (optional)</li>
          <li>Click "Approve" to proceed with the action</li>
          <li>Click "Deny" to reject the proposal</li>
          <li>Approvals expire after 24 hours by default</li>
        </ul>
      </div>
    </div>
  );
}

export default ApprovalPanel;

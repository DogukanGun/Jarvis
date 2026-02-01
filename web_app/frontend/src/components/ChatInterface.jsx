import React, { useState } from 'react';
import './ChatInterface.css';

function ChatInterface({ onSendMessage }) {
  const [message, setMessage] = useState('');
  const [imageData, setImageData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImageData(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();

    if (!message.trim()) {
      alert('Please enter a message');
      return;
    }

    setLoading(true);
    try {
      await onSendMessage(message, imageData);
      setMessage('');
      setImageData(null);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const examplePrompts = [
    '🔧 Write a Python function to sort an array',
    '🖼️ Analyze this screenshot for me',
    '🌐 Get the latest Bitcoin price',
    '💻 Create a REST API for a todo app',
    '📊 Analyze the performance metrics',
  ];

  return (
    <div className="chat-interface">
      <div className="chat-examples">
        <h3>Quick Start Examples:</h3>
        <div className="examples-grid">
          {examplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              className="example-btn"
              onClick={() => setMessage(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSend} className="message-form">
        <div className="image-preview">
          {imageData && (
            <div className="preview-box">
              <img src={imageData} alt="preview" />
              <button
                type="button"
                className="remove-image"
                onClick={() => setImageData(null)}
              >
                ✕
              </button>
            </div>
          )}
        </div>

        <div className="input-area">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter your message here... (e.g., 'Write Python code to reverse a list')"
            className="message-input"
            rows="4"
            disabled={loading}
          />

          <div className="form-controls">
            <label className="file-input-label">
              📷 Upload Image
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                disabled={loading}
                style={{ display: 'none' }}
              />
            </label>

            <button
              type="submit"
              className="send-btn"
              disabled={loading || !message.trim()}
            >
              {loading ? 'Sending...' : '📤 Send Message'}
            </button>
          </div>
        </div>
      </form>

      <div className="chat-info">
        <h4>How it works:</h4>
        <ol>
          <li>Type a message describing what you want</li>
          <li>Optionally upload an image for analysis</li>
          <li>Click "Send Message"</li>
          <li>The orchestrator will process your request</li>
          <li>If approval is needed, go to the Approvals tab</li>
          <li>View results in the Events timeline</li>
        </ol>
      </div>
    </div>
  );
}

export default ChatInterface;

# Jarvis Group Communication Layer - Web Testing Interface

A modern web application for testing and interacting with the Jarvis Group Communication Layer in real-time.

## Features

✨ **Real-time Event Streaming**: Watch events as they happen using Server-Sent Events (SSE)

💬 **Chat Interface**: Send messages to the orchestrator with optional image uploads

📊 **Event Timeline**: View detailed event logs with full JSON payloads

✅ **Approval Management**: Review and approve/deny pending approvals with reasoning

📈 **Status Dashboard**: Monitor orchestrator health and event statistics

🚀 **Production Ready**: Full Docker support for easy deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web App (React Frontend)                   │
│  - Chat Interface                                           │
│  - Event Timeline                                           │
│  - Approval Panel                                           │
│  - Status Dashboard                                         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/SSE
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend Server (Express.js + Node.js)             │
│  - REST API (/api/message, /api/approval, etc.)            │
│  - SSE Streaming (/api/events/stream)                      │
│  - Kafka Consumer (subscribes to events)                   │
│  - Kafka Producer (publishes approvals)                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Kafka
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Jarvis Group Communication Layer                     │
│  - Orchestrator                                             │
│  - Agents                                                   │
│  - Kafka Topics                                             │
│  - Router                                                   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 16+ and npm
- Docker & Docker Compose (for containerized deployment)
- Jarvis Group Layer running (router, agents, Kafka)

### Local Development

#### 1. Install Dependencies

```bash
# Backend
cd backend
npm install

# Frontend
cd ../frontend
npm install
```

#### 2. Configure Environment

Create `.env` file in backend directory:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
PORT=5000
ROUTER_URL=http://localhost:8080
KAFKA_BROKERS=localhost:9092
GROUP_ID=jarvis-main
```

#### 3. Start Services

Open three terminal windows:

```bash
# Terminal 1: Backend
cd backend
npm run dev

# Terminal 2: Frontend
cd frontend
npm start

# Terminal 3: Make sure Jarvis agent services are running
cd ../agent
go run ./router &
python general/run_kafka_consumer.py &
```

#### 4. Access Application

Open browser: http://localhost:3000

### Docker Deployment

#### 1. Build Images

```bash
docker-compose build
```

#### 2. Start Stack

```bash
docker-compose up
```

#### 3. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Usage Guide

### 💬 Chat Tab

1. **Enter Message**: Type a message describing what you want
   - Examples:
     - "Write a Python function to sort an array"
     - "Analyze this screenshot"
     - "Get the latest Bitcoin price"

2. **Upload Image** (Optional):
   - Click "📷 Upload Image"
   - Select an image file
   - Image will be included with your message

3. **Send Message**:
   - Click "📤 Send Message"
   - Status shows "Sending..."
   - Wait for response

### 📊 Events Tab

- View all events in chronological order
- Each event shows:
  - Type (with icon)
  - Timestamp (relative)
  - Sender and role
  - Event description
  - Full JSON details (click "View Full JSON")

- Event types:
  - 💬 Chat messages
  - 💡 Proposals
  - ❓ Approvals
  - 📋 Tasks
  - 📤 Results
  - ⚠️ Errors

### ✅ Approvals Tab

1. **Review Request**:
   - Click on an approval to expand
   - Read the proposal description
   - Review proposal/task IDs

2. **Provide Reasoning** (Optional):
   - Enter your reason in the textarea
   - Examples:
     - "Looks good, go ahead"
     - "Need to adjust parameters"

3. **Make Decision**:
   - Click "✅ Approve" to approve
   - Click "❌ Deny" to reject

4. **View Details**:
   - Click "View Full JSON" for complete data

### 📈 Status Tab

- **Event Statistics**: See counts of each event type
- **Orchestrator Status**:
  - Enabled/Disabled status
  - Group ID
  - Messages processed
  - Consumer lag
  - Topic names
- **Event Breakdown**: Visual breakdown of event distribution

## API Endpoints

### Backend Routes

```
POST   /api/message                      - Send message to router
GET    /api/orchestrator/status          - Get orchestrator status
GET    /api/health                       - Health check
GET    /api/events/stream                - SSE stream of events
POST   /api/approval/:id/:decision       - Grant/deny approval
GET    /api/config                       - Get configuration
```

### Example Usage

#### Send Message
```bash
curl -X POST http://localhost:5000/api/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Write Python code to reverse a list"}'
```

#### Get Status
```bash
curl http://localhost:5000/api/orchestrator/status
```

#### Approve Request
```bash
curl -X POST http://localhost:5000/api/approval/{approvalId}/grant \
  -H "Content-Type: application/json" \
  -d '{"reason": "Approved"}'
```

## Configuration

### Backend Environment Variables

```env
# Server
PORT=5000                              # HTTP port

# Router Connection
ROUTER_URL=http://localhost:8080       # Jarvis router URL

# Kafka
KAFKA_BROKERS=localhost:9092           # Kafka brokers (comma-separated)

# Group
GROUP_ID=jarvis-main                   # Group identifier
```

### Frontend Configuration

Backend URL is auto-detected from proxy in `package.json`:

```json
"proxy": "http://localhost:5000"
```

For production, update to point to your backend server.

## Development

### Backend

- Framework: Express.js
- Real-time: Server-Sent Events (SSE)
- Messaging: Kafka Consumer
- Package Manager: npm

**Directory Structure:**
```
backend/
├── server.js          # Main Express server
├── package.json       # Dependencies
├── .env.example       # Environment template
└── Dockerfile         # Container definition
```

### Frontend

- Framework: React 18
- Styling: CSS3
- HTTP Client: Axios
- Date: date-fns
- Package Manager: npm

**Directory Structure:**
```
frontend/
├── src/
│   ├── App.jsx                              # Main app component
│   ├── App.css                              # Main styles
│   ├── index.jsx                            # Entry point
│   └── components/
│       ├── ChatInterface.jsx                # Chat component
│       ├── EventTimeline.jsx                # Events display
│       ├── ApprovalPanel.jsx                # Approval management
│       └── StatusDashboard.jsx              # Status monitoring
├── public/
│   └── index.html                           # HTML template
└── package.json                             # Dependencies
```

## Troubleshooting

### "Cannot connect to backend"

```
Error: Network Error
```

**Solution:**
- Verify backend is running: `http://localhost:5000/api/health`
- Check ROUTER_URL in backend/.env
- Verify Jarvis services are running

### "Cannot connect to Kafka"

```
Error: Failed to connect to broker
```

**Solution:**
- Check Kafka is running: `docker ps | grep kafka`
- Verify KAFKA_BROKERS in backend/.env
- Check Kafka broker logs

### "No events appearing"

```
Events tab is empty
```

**Solution:**
- Check if orchestrator is running
- Send a message via Chat tab
- Check backend logs for errors
- Verify EVENT_STREAM connection in browser DevTools (Network → EventSource)

### "Frontend won't load"

```
Blank screen or React errors
```

**Solution:**
- Check frontend is running: `npm start` output
- Clear browser cache: Ctrl+Shift+Delete
- Check browser console for JavaScript errors
- Verify Node version >= 16: `node --version`

## Performance Tips

1. **Event Stream**: Limited to last 100 events in memory
2. **Refresh Rate**: Status updates every 5 seconds
3. **Browser**: Use modern browser (Chrome, Firefox, Safari)
4. **Network**: For production, use CDN or proxy

## Deployment

### Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### Manual Deployment

#### Backend

```bash
cd backend
npm install --production
PORT=5000 ROUTER_URL=http://production-router:8080 npm start
```

#### Frontend (Build)

```bash
cd frontend
npm install
npm run build
# Serve dist/ directory with web server
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Security Notes

- ⚠️ This is a testing interface, not production-hardened
- No authentication implemented
- Messages not encrypted in transit
- For production:
  - Add authentication (JWT, OAuth)
  - Use HTTPS/WSS
  - Add rate limiting
  - Add CORS configuration
  - Use secure Kafka setup

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit pull request

## License

MIT

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs: `docker-compose logs backend`
3. Check browser DevTools (F12)
4. Open issue with:
   - Error message
   - Steps to reproduce
   - Environment info (OS, browser, Node version)

---

**Version**: 1.0.0
**Last Updated**: 2026-01-31
**Status**: Ready for Testing ✅

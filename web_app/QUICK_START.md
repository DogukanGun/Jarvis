# Quick Start Guide - Jarvis Group Layer Web Tester

Get the web testing interface up and running in 5 minutes!

## Prerequisites

✅ **Required:**
- Node.js 16+ (`node --version`)
- npm 8+ (`npm --version`)
- Jarvis Group Layer running (router, agents, Kafka)

✅ **Optional:**
- Docker & Docker Compose (for containerized setup)

## Method 1: Manual Setup (Fastest)

### Step 1: Setup Backend (2 minutes)

```bash
# Navigate to backend
cd web_app/backend

# Copy environment template
cp .env.example .env

# Install dependencies
npm install

# Start backend
npm run dev
```

✅ You should see:
```
[timestamp] Web app backend started on port 5000
[timestamp] Router URL: http://localhost:8080
[timestamp] Kafka Brokers: localhost:9092
```

### Step 2: Setup Frontend (1 minute)

Open a new terminal:

```bash
# Navigate to frontend
cd web_app/frontend

# Install dependencies
npm install

# Start frontend
npm start
```

✅ Browser should open automatically at http://localhost:3000

### Step 3: Start Using (2 minutes)

1. **Chat Tab**: Type a message like "Write Python code to reverse a list"
2. **Click Send**: Watch the events appear in the Events tab
3. **Approvals Tab**: If approval is needed, click to approve/deny
4. **Status Tab**: Monitor real-time statistics

## Method 2: Docker Compose (1 command)

### Prerequisites
- Docker (https://docker.com)
- Docker Compose

### Start

```bash
# Navigate to web_app
cd web_app

# Start all services
docker-compose up
```

✅ Access at: http://localhost:3000

### Stop

```bash
# Stop all services
docker-compose down
```

## Verify Setup

### Check Backend
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "router": {...},
  "timestamp": "2026-01-31T..."
}
```

### Check Frontend
Open browser: http://localhost:3000

Should see the Jarvis interface with 4 tabs:
- 💬 Chat
- 📊 Events
- ✅ Approvals
- 📈 Status

## Usage Examples

### Example 1: Code Generation

1. **Chat Tab**:
   - Message: "Write a Python function to calculate factorial"
   - Click "Send Message"

2. **Events Tab**:
   - Watch events appear in real-time
   - See proposals, approvals, tasks, results

3. **Approvals Tab** (if needed):
   - Review the proposal
   - Click "✅ Approve" to proceed
   - Or "❌ Deny" to reject

### Example 2: Image Analysis

1. **Chat Tab**:
   - Click "📷 Upload Image"
   - Select an image file
   - Message: "Analyze this screenshot"
   - Click "Send Message"

2. **Events Tab**:
   - Monitor task execution
   - View analysis result when complete

### Example 3: Monitor Status

1. **Status Tab**:
   - See event counts by type
   - Check orchestrator status
   - View event distribution chart

## Troubleshooting

### "Cannot connect to backend"

**Problem**: Frontend shows connection error

**Solution**:
```bash
# Check backend is running
curl http://localhost:5000/api/health

# If not running, start it
cd web_app/backend
npm run dev
```

### "Cannot connect to Kafka"

**Problem**: No events appearing

**Solution**:
```bash
# Verify Kafka is running in agent directory
cd agent
# Make sure Kafka is started with docker-compose or your Kafka setup
docker ps | grep kafka

# Check KAFKA_BROKERS in backend/.env
cat web_app/backend/.env | grep KAFKA_BROKERS
```

### "Module not found"

**Problem**: npm errors about missing modules

**Solution**:
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### "Port already in use"

**Problem**: "EADDRINUSE: address already in use :::3000"

**Solution**:
```bash
# Find process using port 3000
lsof -i :3000

# Kill it (replace PID with actual process ID)
kill -9 <PID>

# Or use different port
PORT=3001 npm start
```

## Configuration

### Backend .env

Edit `web_app/backend/.env`:

```env
PORT=5000                              # Backend server port
ROUTER_URL=http://localhost:8080       # Jarvis router address
KAFKA_BROKERS=localhost:9092           # Kafka brokers
GROUP_ID=jarvis-main                   # Group identifier
```

### Frontend Configuration

Edit `web_app/frontend/package.json`:

```json
"proxy": "http://localhost:5000"       # Backend URL
```

## Development Tips

### Hot Reload

Both frontend and backend support hot reload:

```bash
# Backend (nodemon enabled)
cd backend
npm run dev

# Frontend (React hot reload)
cd frontend
npm start
```

### Debug Backend

```bash
# Enable Node debugging
node --inspect-brk server.js

# Open Chrome DevTools: chrome://inspect
```

### Debug Frontend

1. Open browser DevTools (F12)
2. Check Console for errors
3. Check Network tab for API calls
4. Check Application → Local Storage

## Next Steps

### 1. **Explore the Interface**
   - Send different types of messages
   - Upload images
   - Approve/deny requests
   - Monitor events

### 2. **Read Documentation**
   - Check `README.md` for detailed docs
   - Read `STRUCTURE.md` for architecture
   - Review API endpoints

### 3. **Test Different Workflows**
   - Code generation (Qwen)
   - Image analysis (Visual)
   - Web extraction (Web Fetcher)
   - Approval workflows

### 4. **Monitor Logs**

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
npm start  # Check console output
```

### 5. **Deploy to Production**

See `README.md` deployment section for:
- Building for production
- Securing credentials
- Scaling considerations
- Monitoring setup

## Common Commands

```bash
# Start everything
cd web_app
docker-compose up

# Start backend only
cd web_app/backend
npm run dev

# Start frontend only
cd web_app/frontend
npm start

# Rebuild Docker images
docker-compose build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop everything
docker-compose down

# Clean up
docker-compose down -v
rm -rf node_modules
npm cache clean --force
```

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads at http://localhost:3000
- [ ] Can send message from Chat tab
- [ ] Events appear in Events tab
- [ ] Status dashboard shows event counts
- [ ] Can expand event details
- [ ] Orchestrator status shows in Status tab
- [ ] No console errors in browser DevTools

## Performance Tips

1. **Clear Event History**: Events are limited to 100 (auto-cleared)
2. **Close Unused Tabs**: Reduces browser memory usage
3. **Refresh Browser**: If experiencing slowness (Ctrl+Shift+R)
4. **Check Network**: Ensure fast connection for SSE

## Getting Help

**Check These Resources:**

1. **README.md**: Full documentation
2. **STRUCTURE.md**: Architecture overview
3. **Browser Console**: Error messages (F12)
4. **Backend Logs**: `docker-compose logs backend`
5. **Verify Setup**: Run all verification checks above

**Common Issues:**

| Issue | Solution |
|-------|----------|
| "Cannot connect" | Check backend is running on port 5000 |
| "No events" | Verify Kafka is running and connected |
| "Port in use" | Kill process with `lsof -i :PORT` |
| "Module not found" | Run `npm install` again |
| "Blank page" | Check browser console (F12), clear cache |

## Success Indicators

✅ **Backend Running**
```
Web app backend started on port 5000
```

✅ **Frontend Running**
```
Compiled successfully!
You can now view jarvis-group-layer-frontend in the browser.
```

✅ **Connected to Events**
```
Console shows event objects being received
```

✅ **Full Integration**
```
Send message → see events → approve → complete workflow
```

---

## What's Next?

1. **Send Your First Message**: Try "Write Python code to sort an array"
2. **Monitor the Flow**: Watch events appear in real-time
3. **Approve Requests**: Test the approval workflow
4. **Check Status**: View statistics in the Status tab
5. **Explore Components**: Click "View Full JSON" to see details

## Quick Reference

| Component | Port | URL |
|-----------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 5000 | http://localhost:5000 |
| Kafka | 9092 | localhost:9092 |
| Router | 8080 | http://localhost:8080 |

---

**Version**: 1.0.0
**Last Updated**: 2026-01-31
**Status**: Ready to Test ✅

**Estimated Setup Time**: 5 minutes
**Difficulty**: ⭐ Easy

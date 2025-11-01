# 🎤 Voice Assistant Setup Guide

## Quick Start Instructions

### Step 1: Start the Backend (WebSocket Server)

Open a terminal and run:

```bash
cd backend
source venv/bin/activate
python websocket_demo.py
```

You should see:
```
🎤 Demo Voice Assistant WebSocket Server
========================================
This is a demo server for testing the React frontend.
It simulates voice assistant behavior without requiring AWS or audio dependencies.

INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
```

The backend will be running on:
- **WebSocket**: `ws://localhost:8000/ws/{client_id}`
- **Health Check**: `http://localhost:8000/health`
- **Status API**: `http://localhost:8000/status`

### Step 2: Start the Frontend (React App)

Open a **new terminal** (keep the backend running) and run:

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v7.1.12  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Step 3: Open the App

Open your browser and go to: **http://localhost:5173/**

## What You'll See

### 🎨 Frontend Interface
- **Header**: "Agentic Voice Assistant"
- **Left Panel**: Conversation display with message history
- **Right Panel**: 
  - Voice indicator with animations
  - Live transcription display
  - System status panel
  - Control buttons

### 🔄 Real-time Demo Features

The demo automatically shows:

1. **Connection Status**: 
   - 🔴 Disconnected → 🟡 Connecting → 🟢 Connected

2. **Voice State Animations** (every 10 seconds):
   - **Listening** (with wave animations)
   - **Processing** (with spinner)
   - 🔊 **Speaking** (with sound bars)
   - ⏸️ **Ready** (idle state)

3. **Live Transcription**: Shows simulated speech-to-text

4. **Agent Status Updates**: 
   - "Demo Ready"
   - "Routing to Knowledge Agent"
   - "Processing query"

5. **Demo Messages**: Periodic assistant responses

6. **System Metrics**: Simulated performance data

### 🎛️ Interactive Controls

- **Refresh Status**: Get current system status
- **Request Escalation**: Trigger escalation alert (shows warning banner)
- **Connect/Disconnect**: Manual connection control

## Testing the WebSocket Connection

### Manual Testing
1. Open browser developer tools (F12)
2. Go to Console tab
3. Watch for WebSocket connection logs
4. Try the control buttons to see real-time updates

### Health Check
Visit: http://localhost:8000/health

Should return:
```json
{
  "status": "healthy",
  "connections": 1,
  "demo_mode": true
}
```

### Status API
Visit: http://localhost:8000/status

Should return system status with performance metrics.

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Kill any process using port 8000
lsof -ti:8000 | xargs kill -9
```

**Python virtual environment issues:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_websocket.txt
```

**Missing dependencies:**
```bash
cd backend
source venv/bin/activate
pip install fastapi uvicorn websockets python-dotenv
```

### Frontend Issues

**Port 5173 already in use:**
```bash
# The frontend will automatically try the next available port
# Or specify a different port:
npm run dev -- --port 3000
```

**Node modules issues:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**WebSocket connection fails:**
- Make sure backend is running on port 8000
- Check browser console for connection errors
- Verify CORS settings allow localhost:5173

## Architecture Overview

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│   React App     │ ←──────────────→ │   FastAPI        │
│   (Frontend)    │   ws://localhost │   (Backend)      │
│   Port: 5173    │      :8000       │   Port: 8000     │
└─────────────────┘                  └──────────────────┘
```

### WebSocket Message Flow

**Frontend → Backend:**
- `ping`: Connection health check
- `request_status`: Get current status
- `manual_escalation`: Request escalation

**Backend → Frontend:**
- `connection_established`: Initial connection
- `system_status`: Status updates
- `voice_state_update`: Voice processing states
- `new_message`: New conversation messages
- `escalation_alert`: Escalation notifications

## Next Steps

Once you have the demo running:

1. **Explore the UI**: Try all the buttons and watch the animations
2. **Monitor WebSocket**: Use browser dev tools to see real-time messages
3. **Test Escalation**: Click "Request Escalation" to see alert system
4. **Multiple Tabs**: Open multiple browser tabs to test multi-client support

## Full Voice Assistant

To run the complete voice assistant with AWS integration:

1. Set up AWS credentials in `backend/.env`
2. Install full requirements: `pip install -r requirements.txt`
3. Run: `python main_with_websocket.py`

The demo version shows all the UI functionality without requiring AWS setup!

---

**🎉 Enjoy testing your real-time voice assistant interface!**
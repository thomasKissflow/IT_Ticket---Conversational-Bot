# Agentic Voice Assistant

A conversational AI system that processes voice input through multiple specialized agents to provide intelligent responses about support tickets and knowledge base information.

## Setup Instructions

### Prerequisites

1. **macOS System Requirements**
   - macOS 10.15 or later
   - Python 3.9 or later
   - Node.js 18 or later

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

3. **Install additional dependencies** (if needed)
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials**
   
   Option A - AWS SSO (Recommended):
   ```bash
   aws sso login
   ```
   
   Option B - Environment variables:
   ```bash
   # Edit .env file and add:
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_SESSION_TOKEN=your_session_token  # If using SSO
   ```
### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies** (already done during setup)
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## Development

### Running the Application

1. **Start backend** (in backend directory):
   ```bash
   source venv/bin/activate
   python main_with_websocket.py
   ```

2. **Start frontend** (in frontend directory):
   ```bash
   npm run dev
   ```

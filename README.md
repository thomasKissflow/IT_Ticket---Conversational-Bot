# Agentic Voice Assistant

A conversational AI system that processes voice input through multiple specialized agents to provide intelligent responses about support tickets and knowledge base information.

## Project Structure

```
├── backend/                 # Python backend
│   ├── agents/             # Agent implementations
│   ├── services/           # Service layer
│   ├── models/             # Data models
│   ├── utils/              # Utility functions
│   ├── venv/               # Python virtual environment
│   ├── requirements.txt    # Python dependencies
│   ├── main.py            # Main application entry point
│   ├── test_audio.py      # Audio system test
│   ├── test_aws.py        # AWS configuration test
│   └── .env               # Environment configuration
├── frontend/               # React frontend
│   ├── src/               # React source code
│   ├── package.json       # Node.js dependencies
│   └── ...                # Vite/React files
├── product-documentation.pdf  # Knowledge base document
├── support-tickets.csv        # Ticket data
└── README.md              # This file
```

## Setup Instructions

### Prerequisites

1. **macOS System Requirements**
   - macOS 10.15 or later
   - Python 3.9 or later
   - Node.js 18 or later
   - Homebrew (recommended for PortAudio)

2. **Install PortAudio** (Required for audio processing)
   ```bash
   brew install portaudio
   ```

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

5. **Test audio system**
   ```bash
   python test_audio.py
   ```

6. **Test AWS configuration**
   ```bash
   python test_aws.py
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

### macOS Audio Permissions

If audio tests fail, ensure microphone permissions are granted:

1. Open **System Preferences** > **Security & Privacy** > **Privacy**
2. Select **Microphone** from the left panel
3. Ensure your terminal or IDE has microphone access enabled
4. Restart your terminal/IDE after granting permissions

## Development

### Running the Application

1. **Start backend** (in backend directory):
   ```bash
   source venv/bin/activate
   python main.py
   ```

2. **Start frontend** (in frontend directory):
   ```bash
   npm run dev
   ```

### Testing

- **Audio System**: `python backend/test_audio.py`
- **AWS Configuration**: `python backend/test_aws.py`

## Next Steps

This completes the project structure setup. The next tasks will implement:

1. Voice processing components (speech-to-text, text-to-speech)
2. Agent system with STRAND SDK
3. Database setup and data processing
4. WebSocket communication
5. Frontend interface

## Dependencies Installed

### Backend (Python)
- boto3, chromadb, sounddevice, numpy
- fastapi, uvicorn, websockets
- python-dotenv, python-multipart

### Frontend (React/TypeScript)
- React 18 with TypeScript
- Vite build tool
- WebSocket libraries (ws, socket.io-client)

## Notes

- **STRAND SDK**: Not available in PyPI - will need alternative implementation or manual installation
- **PortAudio**: Required for sounddevice - install via Homebrew
- **AWS Region**: Configured for us-east-1
- **Audio Format**: 16kHz, mono, for optimal AWS Transcribe compatibility
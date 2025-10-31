
import ConversationDisplay from './components/ConversationDisplay'
import VoiceIndicator from './components/VoiceIndicator'
import TranscriptionDisplay from './components/TranscriptionDisplay'
import SystemStatus from './components/SystemStatus'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

function App() {
  const {
    messages,
    conversationState,
    connectionStatus,
    systemStatus,
    escalationAlert,
    connect,
    disconnect,
    requestStatus,
    requestManualEscalation,
    isConnected
  } = useWebSocket();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Voice Assistant</h1>
        <p>Intelligent support with voice interaction</p>
      </header>

      <main className="app-main">
        <div className="conversation-section">
          <ConversationDisplay messages={messages} />
        </div>

        <div className="controls-section">
          <VoiceIndicator 
            isListening={conversationState.isListening}
            isProcessing={conversationState.isProcessing}
            isPlaying={conversationState.isPlaying}
          />
          
          <TranscriptionDisplay 
            currentTranscript={conversationState.currentTranscript}
            isListening={conversationState.isListening}
          />
          
          <SystemStatus 
            agentStatus={systemStatus.agentStatus}
            escalationAlert={escalationAlert}
            connectionStatus={connectionStatus}
          />
          
          <div className="control-buttons">
            <button 
              onClick={requestStatus}
              disabled={!isConnected}
              className="control-button"
            >
              Refresh Status
            </button>
            <button 
              onClick={requestManualEscalation}
              disabled={!isConnected}
              className="control-button escalation-button"
            >
              Request Escalation
            </button>
            <button 
              onClick={isConnected ? disconnect : connect}
              className={`control-button ${isConnected ? 'disconnect' : 'connect'}`}
            >
              {isConnected ? 'Disconnect' : 'Connect'}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App

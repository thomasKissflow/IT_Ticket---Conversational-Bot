
import ConversationDisplay from './components/ConversationDisplay'
import VoiceIndicator from './components/VoiceIndicator'
import TranscriptionDisplay from './components/TranscriptionDisplay'
import SystemStatus from './components/SystemStatus'
import { useWebSocket } from './hooks/useWebSocket'

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
    clearMessages,
    isConnected
  } = useWebSocket();

  return (
    <div className="h-screen bg-gray-900 text-white flex relative">
      {/* Main Content Area - Split Layout */}
      <main className="flex-1 flex h-full">
        {/* Left Side - Conversation Display (70%) */}
        <div className="w-[70%] p-6 border-r border-gray-800 flex flex-col h-full">
          <ConversationDisplay messages={messages} onClearMessages={clearMessages} />
        </div>

        {/* Right Side - App Info and Orb (30%) */}
        <div className="w-[30%] flex flex-col items-center justify-center p-8 space-y-12">
          {/* App Title and Description */}
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Superops IT Voice Assistant
            </h1>
            {/* <p className="text-gray-400 text-lg leading-relaxed">
              Intelligent support with voice interaction
            </p> */}
          </div>

          {/* Central Glowing Orb */}
          <div className="relative">
            {/* Main Orb */}
            <div className={`
              w-40 h-40 rounded-full border-2 
              flex items-center justify-center relative
              ${isConnected 
                ? 'border-blue-500/30 animate-pulse bg-blue-500/20 shadow-[0_0_60px_rgba(59,130,246,0.6)]' 
                : 'border-gray-500/30 bg-gray-500/10 shadow-[0_0_25px_rgba(107,114,128,0.4)]'
              }
              transition-all duration-300 ease-in-out
            `}>
              {/* Inner Orb */}
              <div className={`
                w-24 h-24 rounded-full 
                ${isConnected 
                  ? 'bg-gradient-to-br from-blue-400 to-blue-600 animate-ping shadow-[0_0_40px_rgba(59,130,246,0.9)]' 
                  : 'bg-gradient-to-br from-gray-400 to-gray-600 shadow-[0_0_20px_rgba(107,114,128,0.6)]'
                }
                transition-all duration-300
              `} />
              
              {/* Pulse Rings for Active State */}
              {isConnected && (
                <>
                  <div className="absolute inset-0 rounded-full border-2 border-blue-400/50 animate-ping" />
                  <div className="absolute inset-0 rounded-full border border-blue-300/30 animate-pulse" style={{animationDelay: '0.5s'}} />
                </>
              )}
            </div>
          </div>

          {/* Voice Indicator (Hidden but keeping for functionality) */}
          <div className="hidden">
            <VoiceIndicator 
              isListening={conversationState.isListening}
              isProcessing={conversationState.isProcessing}
              isPlaying={conversationState.isPlaying}
            />
          </div>
        </div>
      </main>

      {/* Bottom Right Overlay */}
      <div className="fixed bottom-6 right-6 flex flex-col space-y-3">
        {/* Connection Status Indicator */}
        <div className={`
          px-3 py-2 rounded-full text-xs font-medium backdrop-blur-md
          ${isConnected 
            ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
            : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }
        `}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>

        {/* Connect/Disconnect Button */}
        <button 
          onClick={isConnected ? disconnect : connect}
          className={`
            px-6 py-3 rounded-full font-medium backdrop-blur-md border transition-all duration-200
            ${isConnected 
              ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border-red-500/30 hover:border-red-500/50' 
              : 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border-blue-500/30 hover:border-blue-500/50'
            }
            hover:scale-105 active:scale-95
          `}
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>

        {/* System Status (Collapsible) */}
        {/* <div className="backdrop-blur-md bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 max-w-xs">
          <SystemStatus 
            agentStatus={systemStatus.agentStatus}
            escalationAlert={escalationAlert}
            connectionStatus={connectionStatus}
          />
        </div> */}

        {/* Additional Controls (Hidden by default, can be toggled) */}
        <div className="flex flex-col space-y-2 opacity-50 hover:opacity-100 transition-opacity">
          {/* <button 
            onClick={requestStatus}
            disabled={!isConnected}
            className="px-4 py-2 text-xs rounded-full bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Refresh
          </button> */}
          {/* <button 
            onClick={requestManualEscalation}
            disabled={!isConnected}
            className="px-4 py-2 text-xs rounded-full bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 border border-yellow-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Escalate
          </button> */}
        </div>
      </div>
    </div>
  )
}

export default App

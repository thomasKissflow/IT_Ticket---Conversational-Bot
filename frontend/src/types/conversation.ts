export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  confidence?: number;
}

export interface ConversationState {
  isListening: boolean;
  isProcessing: boolean;
  isPlaying: boolean;
  currentTranscript: string;
  agentStatus: string;
  escalationAlert?: {
    message: string;
    timestamp: Date;
  };
}

export interface VoiceIndicatorProps {
  isListening: boolean;
  isProcessing: boolean;
  isPlaying: boolean;
}
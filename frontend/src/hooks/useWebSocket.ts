import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService } from '../services/websocketService';
import type { WebSocketCallbacks } from '../services/websocketService';
import type { Message, ConversationState } from '../types/conversation';

interface UseWebSocketReturn {
  messages: Message[];
  conversationState: ConversationState;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  systemStatus: {
    agentStatus: string;
    sessionId?: string;
    performanceMetrics?: any;
  };
  escalationAlert?: {
    message: string;
    timestamp: Date;
  };
  connect: () => Promise<void>;
  disconnect: () => void;
  requestStatus: () => void;
  requestManualEscalation: () => void;
  clearMessages: () => void;
  isConnected: boolean;
}

export const useWebSocket = (url: string = 'ws://localhost:8000'): UseWebSocketReturn => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: 'Connecting to voice assistant...',
      timestamp: new Date()
    }
  ]);

  const [conversationState, setConversationState] = useState<ConversationState>({
    isListening: false,
    isProcessing: false,
    isPlaying: false,
    currentTranscript: '',
    agentStatus: 'Connecting...'
  });

  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');
  
  const [systemStatus, setSystemStatus] = useState({
    agentStatus: 'Connecting...',
    sessionId: undefined,
    performanceMetrics: {}
  });

  const [escalationAlert, setEscalationAlert] = useState<{
    message: string;
    timestamp: Date;
  } | undefined>();

  const [isConnected, setIsConnected] = useState(false);
  
  // Use refs to avoid stale closures in callbacks
  const messagesRef = useRef(messages);
  const conversationStateRef = useRef(conversationState);

  // Update refs when state changes
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    conversationStateRef.current = conversationState;
  }, [conversationState]);

  const addMessage = useCallback((newMessage: Message) => {
    setMessages(prev => {
      // Avoid duplicates
      const exists = prev.some(msg => msg.id === newMessage.id);
      if (exists) return prev;
      return [...prev, newMessage];
    });
  }, []);

  const updateSystemMessage = useCallback((content: string) => {
    const systemMessage: Message = {
      id: `system_${Date.now()}`,
      type: 'system',
      content,
      timestamp: new Date()
    };
    addMessage(systemMessage);
  }, [addMessage]);

  const callbacks: WebSocketCallbacks = {
    onConnect: () => {
      console.log('WebSocket connected');
      setConnectionStatus('connected');
      setIsConnected(true);
      updateSystemMessage('Connected to voice assistant');
    },

    onDisconnect: () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('disconnected');
      setIsConnected(false);
      updateSystemMessage('Disconnected from voice assistant');
      setConversationState(prev => ({
        ...prev,
        agentStatus: 'Disconnected'
      }));
    },

    onError: (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
      setIsConnected(false);
      updateSystemMessage('Connection error occurred');
    },

    onConnectionEstablished: (data) => {
      console.log('Connection established:', data);
      updateSystemMessage('Voice assistant ready');
    },

    onSystemStatus: (data) => {
      console.log('System status update:', data);
      
      setSystemStatus({
        agentStatus: data.agent_status || 'Ready',
        sessionId: data.session_id,
        performanceMetrics: data.performance_metrics || {}
      });

      setConversationState(prev => ({
        ...prev,
        agentStatus: data.agent_status || 'Ready'
      }));

      // Update connection status based on system status
      if (data.connection_status) {
        setConnectionStatus(data.connection_status === 'connected' ? 'connected' : 'disconnected');
      }
    },

    onNewMessage: (data) => {
      console.log('New message:', data);
      
      const newMessage: Message = {
        id: data.id || `msg_${Date.now()}`,
        type: data.type,
        content: data.content,
        timestamp: new Date(data.timestamp),
        confidence: data.confidence
      };
      
      addMessage(newMessage);
    },

    onVoiceStateUpdate: (data) => {
      console.log('Voice state update:', data);
      
      setConversationState(prev => ({
        ...prev,
        isListening: data.is_listening || false,
        isProcessing: data.is_processing || false,
        isPlaying: data.is_playing || false,
        currentTranscript: data.current_transcript || ''
      }));
    },

    onEscalationAlert: (data) => {
      console.log('Escalation alert:', data);
      
      setEscalationAlert({
        message: data.message,
        timestamp: new Date(data.timestamp)
      });

      // Also add as a system message
      updateSystemMessage(`⚠️ Escalation: ${data.message}`);
    },

    onAgentRouting: (data) => {
      console.log('Agent routing update:', data);
      
      setConversationState(prev => ({
        ...prev,
        agentStatus: `${data.agent_name}: ${data.status}`
      }));
    },

    onConversationHistory: (data) => {
      console.log('Conversation history:', data);
      
      if (data.messages && Array.isArray(data.messages)) {
        const historyMessages: Message[] = data.messages.map((msg: any) => ({
          id: msg.id || `hist_${Date.now()}_${Math.random()}`,
          type: msg.type,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          confidence: msg.confidence
        }));
        
        setMessages(prev => {
          // Replace system messages with history
          const nonSystemMessages = prev.filter(msg => msg.type === 'system');
          return [...nonSystemMessages, ...historyMessages];
        });
      }
    }
  };

  const connect = useCallback(async () => {
    try {
      setConnectionStatus('connecting');
      updateSystemMessage('Connecting to voice assistant...');
      await websocketService.connect(url, callbacks);
    } catch (error) {
      console.error('Failed to connect:', error);
      setConnectionStatus('disconnected');
      updateSystemMessage('Failed to connect to voice assistant');
    }
  }, [url, updateSystemMessage]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setConnectionStatus('disconnected');
    setIsConnected(false);
  }, []);

  const requestStatus = useCallback(() => {
    websocketService.requestStatus();
  }, []);

  const requestManualEscalation = useCallback(() => {
    websocketService.requestManualEscalation();
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    
    // Set up periodic ping to keep connection alive
    const pingInterval = setInterval(() => {
      if (websocketService.isConnected()) {
        websocketService.ping();
      }
    }, 30000); // Ping every 30 seconds

    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect]);

  // Clear escalation alert after 10 seconds
  useEffect(() => {
    if (escalationAlert) {
      const timer = setTimeout(() => {
        setEscalationAlert(undefined);
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [escalationAlert]);

  return {
    messages,
    conversationState: {
      ...conversationState,
      escalationAlert
    },
    connectionStatus,
    systemStatus,
    escalationAlert,
    connect,
    disconnect,
    requestStatus,
    requestManualEscalation,
    clearMessages,
    isConnected
  };
};
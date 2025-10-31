// WebSocket service using native WebSocket API

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp: string;
}

export interface WebSocketCallbacks {
  onConnectionEstablished?: (data: any) => void;
  onSystemStatus?: (data: any) => void;
  onNewMessage?: (data: any) => void;
  onVoiceStateUpdate?: (data: any) => void;
  onEscalationAlert?: (data: any) => void;
  onAgentRouting?: (data: any) => void;
  onConversationHistory?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private clientId: string;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;

  constructor() {
    this.clientId = this.generateClientId();
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  connect(url: string = 'ws://localhost:8000', callbacks: WebSocketCallbacks = {}): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
        return;
      }

      this.isConnecting = true;
      this.callbacks = callbacks;

      const wsUrl = `${url}/ws/${this.clientId}`;
      console.log(`Connecting to WebSocket: ${wsUrl}`);

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.callbacks.onConnect?.();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.isConnecting = false;
          this.callbacks.onDisconnect?.();
          
          // Attempt to reconnect if not a clean close
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(url, callbacks);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnecting = false;
          this.callbacks.onError?.(error);
          reject(error);
        };

      } catch (error) {
        this.isConnecting = false;
        console.error('Failed to create WebSocket connection:', error);
        reject(error);
      }
    });
  }

  private scheduleReconnect(url: string, callbacks: WebSocketCallbacks) {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect(url, callbacks).catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  private handleMessage(message: WebSocketMessage) {
    console.log('Received WebSocket message:', message.type, message.data);

    switch (message.type) {
      case 'connection_established':
        this.callbacks.onConnectionEstablished?.(message.data);
        break;
      
      case 'system_status':
        this.callbacks.onSystemStatus?.(message.data);
        break;
      
      case 'new_message':
        this.callbacks.onNewMessage?.(message.data);
        break;
      
      case 'voice_state_update':
        this.callbacks.onVoiceStateUpdate?.(message.data);
        break;
      
      case 'escalation_alert':
        this.callbacks.onEscalationAlert?.(message.data);
        break;
      
      case 'agent_routing':
        this.callbacks.onAgentRouting?.(message.data);
        break;
      
      case 'conversation_history':
        this.callbacks.onConversationHistory?.(message.data);
        break;
      
      case 'pong':
        // Handle ping/pong for connection health
        break;
      
      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  sendMessage(type: string, data?: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString()
      };
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', type);
    }
  }

  requestStatus() {
    this.sendMessage('request_status');
  }

  requestManualEscalation() {
    this.sendMessage('manual_escalation');
  }

  ping() {
    this.sendMessage('ping');
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
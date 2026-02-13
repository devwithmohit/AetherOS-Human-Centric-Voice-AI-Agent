import { useAppStore } from '@store/appStore';

export type WebSocketMessageType =
  | 'connection'
  | 'transcription'
  | 'response'
  | 'status'
  | 'tool_call'
  | 'tool_result'
  | 'audio_chunk'
  | 'error'
  | 'ping'
  | 'pong';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data?: any;
  text?: string;
  audioUrl?: string;
  status?: string;
  tool?: string;
  result?: string;
  error?: string;
  timestamp?: string;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private isIntentionallyClosed = false;
  private pingInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Map<WebSocketMessageType, Set<(data: any) => void>> = new Map();

  constructor() {
    this.initializeHandlers();
  }

  private initializeHandlers() {
    // Initialize handler sets for each message type
    const types: WebSocketMessageType[] = [
      'connection',
      'transcription',
      'response',
      'status',
      'tool_call',
      'tool_result',
      'audio_chunk',
      'error',
      'ping',
      'pong',
    ];

    types.forEach((type) => {
      this.messageHandlers.set(type, new Set());
    });
  }

  connect(url?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = url || this.getWebSocketUrl();

      console.log('Connecting to WebSocket:', wsUrl);

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('✅ WebSocket connected');
          this.reconnectAttempts = 0;
          this.isIntentionallyClosed = false;
          useAppStore.getState().setConnected(true);

          // Start heartbeat
          this.startHeartbeat();

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          useAppStore.getState().setConnected(false);
        };

        this.ws.onclose = (event) => {
          console.log(`🔌 WebSocket closed (code: ${event.code}, reason: ${event.reason || 'none'})`);
          useAppStore.getState().setConnected(false);

          // Stop heartbeat
          this.stopHeartbeat();

          // Only reconnect if closure was unexpected and not a deliberate disconnect
          if (!this.isIntentionallyClosed && event.code !== 1000) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }

  private getWebSocketUrl(): string {
    const apiUrl = useAppStore.getState().settings.apiGatewayUrl;
    // Convert http:// to ws:// and https:// to wss://
    return apiUrl.replace(/^http/, 'ws') + '/ws';
  }

  private handleMessage(data: string) {
    try {
      const message: WebSocketMessage = JSON.parse(data);

      // Handle ping/pong
      if (message.type === 'ping') {
        this.send({ type: 'pong' });
        return;
      }

      // Route to handlers
      const handlers = this.messageHandlers.get(message.type);
      if (handlers) {
        handlers.forEach((handler) => handler(message.data || message));
      }

      // Built-in handlers for common messages
      this.handleBuiltInMessages(message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleBuiltInMessages(message: WebSocketMessage) {
    const store = useAppStore.getState();

    switch (message.type) {
      case 'connection':
        console.log('🔗 Connection established:', message);
        break;

      case 'transcription':
        if (message.text) {
          store.addMessage({
            role: 'user',
            content: message.text,
          });
        }
        break;

      case 'response':
        store.setTyping(false);
        if (message.text) {
          store.addMessage({
            role: 'assistant',
            content: message.text,
            audioUrl: message.audioUrl,
            isMarkdown: true,
          });
        }

        // Handle client-side execution instructions
        if (message.execute && message.execute.url) {
          console.log('🚀 Executing command on client:', message.execute);

          // Use Electron shell to open URL in default browser
          if (window.electron && window.electron.shell) {
            window.electron.shell.openExternal(message.execute.url).then(() => {
              console.log('✅ URL opened:', message.execute.url);
            }).catch((error: any) => {
              console.error('❌ Failed to open URL:', error);
            });
          } else {
            // Fallback to window.open if Electron API not available
            window.open(message.execute.url, '_blank');
          }
        }
        break;

      case 'status':
        if (message.status === 'processing') {
          store.setStatus('processing');
          store.setTyping(true);
        } else if (message.status === 'speaking') {
          store.setStatus('speaking');
        } else if (message.status === 'complete') {
          store.setStatus('idle');
          store.setTyping(false);
        }
        break;

      case 'tool_call':
        store.setTyping(false);
        store.addMessage({
          role: 'system',
          content: `Executing tool: ${message.tool}`,
          toolStatus: {
            tool: message.tool || 'unknown',
            status: 'running',
          },
        });
        break;

      case 'tool_result':
        store.addMessage({
          role: 'system',
          content: `Tool completed: ${message.tool}`,
          toolStatus: {
            tool: message.tool || 'unknown',
            status: 'complete',
            result: message.result,
          },
        });
        break;

      case 'error':
        store.setStatus('idle');
        store.setTyping(false);
        store.addMessage({
          role: 'system',
          content: `Error: ${message.error || 'Unknown error'}`,
        });
        break;

      default:
        break;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`❌ Max reconnection attempts (${this.maxReconnectAttempts}) reached. Giving up.`);
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 3); // Exponential backoff (max 3x)

    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch((error) => {
        console.error('❌ Reconnection failed:', error);
      });
    }, delay);
  }

  private startHeartbeat() {
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(message: WebSocketMessage | any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('📤 Sending WebSocket message:', message);
      this.ws.send(JSON.stringify(message));

      // If sending a user message, set typing indicator
      if (message.type === 'message' && message.text) {
        useAppStore.getState().setTyping(true);
      }
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send message:', message);
    }
  }

  sendAudioChunk(audioData: ArrayBuffer | Blob) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // Send binary data directly
      this.ws.send(audioData);
    } else {
      console.warn('WebSocket not connected, cannot send audio');
    }
  }

  on(type: WebSocketMessageType, handler: (data: any) => void) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.add(handler);
    }
  }

  off(type: WebSocketMessageType, handler: (data: any) => void) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  disconnect() {
    this.isIntentionallyClosed = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }

    useAppStore.getState().setConnected(false);
    console.log('🔌 WebSocket disconnected');
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();

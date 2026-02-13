import { useAppStore } from '@store/appStore';

export type WebSocketMessageType =
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
  private maxReconnectAttempts = 10;
  private reconnectDelay = 5000;
  private isIntentionallyClosed = false;
  private messageHandlers: Map<WebSocketMessageType, Set<(data: any) => void>> = new Map();

  constructor() {
    this.initializeHandlers();
  }

  private initializeHandlers() {
    // Initialize handler sets for each message type
    const types: WebSocketMessageType[] = [
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
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.isIntentionallyClosed = false;
          useAppStore.getState().setConnected(true);
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          useAppStore.getState().setConnected(false);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          useAppStore.getState().setConnected(false);

          if (!this.isIntentionallyClosed) {
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
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Reconnecting (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, this.reconnectDelay);
  }

  send(message: WebSocketMessage | any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
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

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    useAppStore.getState().setConnected(false);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();

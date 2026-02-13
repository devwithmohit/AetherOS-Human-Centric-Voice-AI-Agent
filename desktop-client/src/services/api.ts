import axios, { AxiosInstance, AxiosError } from 'axios';
import { useAppStore } from '@store/appStore';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = useAppStore.getState().settings.apiGatewayUrl;
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Update base URL from settings
        const currentUrl = useAppStore.getState().settings.apiGatewayUrl;
        if (currentUrl !== this.baseURL) {
          this.baseURL = currentUrl;
          config.baseURL = currentUrl;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version?: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Speech-to-Text
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string; confidence?: number }> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const response = await this.client.post('/api/stt/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  // Text-to-Speech
  async synthesizeSpeech(text: string, voice?: string): Promise<{ audioUrl: string }> {
    const response = await this.client.post('/api/tts/synthesize', {
      text,
      voice: voice || useAppStore.getState().settings.voice,
    });

    return response.data;
  }

  // Chat completion
  async sendMessage(message: string, conversationId?: string): Promise<{
    response: string;
    audioUrl?: string;
    conversationId: string;
    toolCalls?: any[];
  }> {
    const response = await this.client.post('/api/chat/message', {
      message,
      conversationId,
      model: useAppStore.getState().settings.llmModel,
      mode: useAppStore.getState().settings.llmMode,
    });

    return response.data;
  }

  // Memory API
  async getMemories(userId?: string): Promise<any[]> {
    const response = await this.client.get('/api/memory/list', {
      params: { userId },
    });

    return response.data.memories || [];
  }

  async deleteMemory(memoryId: string): Promise<void> {
    await this.client.delete(`/api/memory/${memoryId}`);
  }

  async updateMemory(memoryId: string, content: string): Promise<void> {
    await this.client.put(`/api/memory/${memoryId}`, { content });
  }

  async clearMemories(userId?: string): Promise<void> {
    await this.client.post('/api/memory/clear', { userId });
  }

  async getRecentContext(limit: number = 10): Promise<any[]> {
    const response = await this.client.get('/api/memory/recent', {
      params: { limit },
    });

    return response.data.context || [];
  }

  // Settings sync
  async syncSettings(settings: any): Promise<void> {
    await this.client.post('/api/settings/sync', settings);
  }

  async getSettings(): Promise<any> {
    const response = await this.client.get('/api/settings');
    return response.data;
  }

  // Tool execution
  async executeToolCall(toolName: string, parameters: any): Promise<any> {
    const response = await this.client.post('/api/tools/execute', {
      tool: toolName,
      parameters,
    });

    return response.data;
  }

  // Analytics (if enabled)
  async sendAnalytics(event: string, data: any): Promise<void> {
    const { shareAnalytics } = useAppStore.getState().settings;

    if (!shareAnalytics) {
      return;
    }

    try {
      await this.client.post('/api/analytics/event', {
        event,
        data,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      // Silently fail analytics
      console.warn('Analytics failed:', error);
    }
  }
}

export const apiClient = new ApiClient();

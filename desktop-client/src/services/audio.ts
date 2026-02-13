/**
 * Audio encoding/decoding utilities for desktop client
 */

export class AudioService {
  private audioContext: AudioContext | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }

  /**
   * Convert AudioBuffer to WAV format
   */
  audioBufferToWav(buffer: AudioBuffer): Blob {
    const numberOfChannels = buffer.numberOfChannels;
    const length = buffer.length * numberOfChannels * 2;
    const sampleRate = buffer.sampleRate;

    const arrayBuffer = new ArrayBuffer(44 + length);
    const view = new DataView(arrayBuffer);

    // WAV header
    this.writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + length, true);
    this.writeString(view, 8, 'WAVE');
    this.writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // PCM format
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    this.writeString(view, 36, 'data');
    view.setUint32(40, length, true);

    // Write audio data
    const offset = 44;
    const channels: Float32Array[] = [];

    for (let i = 0; i < numberOfChannels; i++) {
      channels.push(buffer.getChannelData(i));
    }

    let index = offset;
    for (let i = 0; i < buffer.length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, channels[channel][i]));
        view.setInt16(index, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
        index += 2;
      }
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' });
  }

  private writeString(view: DataView, offset: number, string: string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  /**
   * Decode audio file to AudioBuffer
   */
  async decodeAudioFile(file: File | Blob): Promise<AudioBuffer> {
    if (!this.audioContext) {
      throw new Error('AudioContext not available');
    }

    const arrayBuffer = await file.arrayBuffer();
    return await this.audioContext.decodeAudioData(arrayBuffer);
  }

  /**
   * Convert Blob to base64
   */
  async blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        resolve(result.split(',')[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  /**
   * Convert base64 to Blob
   */
  base64ToBlob(base64: string, mimeType: string = 'audio/wav'): Blob {
    const byteString = atob(base64);
    const arrayBuffer = new ArrayBuffer(byteString.length);
    const uint8Array = new Uint8Array(arrayBuffer);

    for (let i = 0; i < byteString.length; i++) {
      uint8Array[i] = byteString.charCodeAt(i);
    }

    return new Blob([arrayBuffer], { type: mimeType });
  }

  /**
   * Resample audio to target sample rate
   */
  async resampleAudio(buffer: AudioBuffer, targetSampleRate: number): Promise<AudioBuffer> {
    if (!this.audioContext) {
      throw new Error('AudioContext not available');
    }

    if (buffer.sampleRate === targetSampleRate) {
      return buffer;
    }

    const offlineContext = new OfflineAudioContext(
      buffer.numberOfChannels,
      buffer.duration * targetSampleRate,
      targetSampleRate
    );

    const source = offlineContext.createBufferSource();
    source.buffer = buffer;
    source.connect(offlineContext.destination);
    source.start(0);

    return await offlineContext.startRendering();
  }

  /**
   * Calculate audio level (RMS)
   */
  calculateAudioLevel(buffer: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) {
      sum += buffer[i] * buffer[i];
    }
    const rms = Math.sqrt(sum / buffer.length);
    return Math.min(100, Math.floor(rms * 100 * 10)); // Scale to 0-100
  }

  /**
   * Normalize audio buffer
   */
  normalizeBuffer(buffer: AudioBuffer): AudioBuffer {
    if (!this.audioContext) {
      throw new Error('AudioContext not available');
    }

    const normalized = this.audioContext.createBuffer(
      buffer.numberOfChannels,
      buffer.length,
      buffer.sampleRate
    );

    for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
      const inputData = buffer.getChannelData(channel);
      const outputData = normalized.getChannelData(channel);

      // Find max absolute value
      let max = 0;
      for (let i = 0; i < inputData.length; i++) {
        const abs = Math.abs(inputData[i]);
        if (abs > max) max = abs;
      }

      // Normalize
      const scale = max > 0 ? 1 / max : 1;
      for (let i = 0; i < inputData.length; i++) {
        outputData[i] = inputData[i] * scale;
      }
    }

    return normalized;
  }

  /**
   * Create audio element from URL
   */
  createAudioElement(url: string): HTMLAudioElement {
    const audio = new Audio(url);
    audio.preload = 'auto';
    return audio;
  }

  /**
   * Play audio from URL or Blob
   */
  async playAudio(source: string | Blob, volume: number = 1.0): Promise<void> {
    const url = typeof source === 'string' ? source : URL.createObjectURL(source);
    const audio = this.createAudioElement(url);
    audio.volume = volume;

    return new Promise((resolve, reject) => {
      audio.onended = () => {
        if (typeof source !== 'string') {
          URL.revokeObjectURL(url);
        }
        resolve();
      };

      audio.onerror = (error) => {
        if (typeof source !== 'string') {
          URL.revokeObjectURL(url);
        }
        reject(error);
      };

      audio.play().catch(reject);
    });
  }

  /**
   * Get audio duration without playing
   */
  async getAudioDuration(file: File | Blob): Promise<number> {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const audio = new Audio(url);

      audio.onloadedmetadata = () => {
        URL.revokeObjectURL(url);
        resolve(audio.duration);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Failed to load audio metadata'));
      };
    });
  }

  /**
   * Cleanup
   */
  cleanup() {
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }
  }
}

export const audioService = new AudioService();

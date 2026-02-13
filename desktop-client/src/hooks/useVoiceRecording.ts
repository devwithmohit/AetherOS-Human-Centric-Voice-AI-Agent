import { useState, useRef, useCallback } from 'react';
import { useAppStore } from '@store/appStore';
import { apiClient } from '@services/api';
import { wsService } from '@services/websocket';

export const useVoiceRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number>();

  const setStatus = useAppStore((state) => state.setStatus);
  const setMicLevel = useAppStore((state) => state.setMicLevel);
  const addMessage = useAppStore((state) => state.addMessage);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      // Setup Web Audio API for visualization
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Setup MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        // Send audio to backend for transcription
        try {
          setStatus('processing');

          const result = await apiClient.transcribeAudio(audioBlob);

          if (result.text) {
            addMessage({
              role: 'user',
              content: result.text,
            });

            // Send text to backend via WebSocket for response
            wsService.send({
              type: 'message',
              text: result.text,
            });
          }
        } catch (error) {
          console.error('Failed to transcribe audio:', error);
          addMessage({
            role: 'system',
            content: 'Failed to process voice input. Please try again.',
          });
          setStatus('idle');
        }

        // Cleanup
        stream.getTracks().forEach((track) => track.stop());
        if (audioContextRef.current) {
          audioContextRef.current.close();
          audioContextRef.current = null;
        }
        audioChunksRef.current = [];
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus('listening');

      // Start audio level monitoring
      const updateAudioLevel = () => {
        if (!analyserRef.current) return;

        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        // Calculate average volume
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const level = Math.min((average / 128) * 100, 100);

        setMicLevel(level);

        if (isRecording) {
          animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
        }
      };

      updateAudioLevel();
    } catch (error) {
      console.error('Failed to start recording:', error);
      addMessage({
        role: 'system',
        content: 'Microphone access denied or unavailable.',
      });
      setStatus('idle');
    }
  }, [isRecording, setStatus, setMicLevel, addMessage]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      setMicLevel(0);
    }
  }, [isRecording, setMicLevel]);

  return {
    isRecording,
    startRecording,
    stopRecording,
  };
};

import { useState, useRef, useCallback } from 'react';
import { useAppStore } from '@store/appStore';
import { apiClient } from '@services/api';
import { wsService } from '@services/websocket';

// Voice Activity Detection (VAD) settings
const SILENCE_THRESHOLD = 10; // Audio level below this is considered silence
const SILENCE_DURATION = 2000; // 2 seconds of silence triggers auto-stop
const MIN_RECORDING_DURATION = 500; // Minimum 500ms recording

export const useVoiceRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number>();

  // VAD state
  const silenceStartRef = useRef<number | null>(null);
  const recordingStartRef = useRef<number>(0);
  const autoStopTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
          console.log('🎤 Sending audio for transcription...');

          const result = await apiClient.transcribeAudio(audioBlob);
          console.log('📝 Transcription result:', result);

          const transcribedText = result.text || result.transcript;

          if (transcribedText) {
            console.log('✅ Transcribed text:', transcribedText);

            addMessage({
              role: 'user',
              content: transcribedText,
            });

            // Send text to backend via WebSocket for response
            console.log('📤 Sending to WebSocket:', { type: 'message', text: transcribedText });
            wsService.send({
              type: 'message',
              text: transcribedText,
            });
          } else {
            console.warn('⚠️ No transcribed text received:', result);
          }

          // Return to idle state after processing
          setStatus('idle');
        } catch (error) {
          console.error('❌ Failed to transcribe audio:', error);
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
        silenceStartRef.current = null;
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus('listening');
      recordingStartRef.current = Date.now();
      silenceStartRef.current = null;

      // Start audio level monitoring with VAD
      const updateAudioLevel = () => {
        if (!analyserRef.current) return;

        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        // Calculate average volume
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const level = Math.min((average / 128) * 100, 100);

        setMicLevel(level);

        // Voice Activity Detection (VAD)
        const recordingDuration = Date.now() - recordingStartRef.current;

        if (level < SILENCE_THRESHOLD) {
          // Silence detected
          if (silenceStartRef.current === null) {
            silenceStartRef.current = Date.now();
          } else {
            const silenceDuration = Date.now() - silenceStartRef.current;

            // Auto-stop if silence exceeds threshold AND minimum recording duration met
            if (silenceDuration >= SILENCE_DURATION && recordingDuration >= MIN_RECORDING_DURATION) {
              console.log('Auto-stopping due to silence');
              stopRecording();
              return;
            }
          }
        } else {
          // Voice detected, reset silence timer
          silenceStartRef.current = null;
        }

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
      console.log('Stopping recording...');
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      if (autoStopTimeoutRef.current) {
        clearTimeout(autoStopTimeoutRef.current);
        autoStopTimeoutRef.current = null;
      }

      setMicLevel(0);
      silenceStartRef.current = null;
    }
  }, [isRecording, setMicLevel]);

  return {
    isRecording,
    startRecording,
    stopRecording,
  };
};

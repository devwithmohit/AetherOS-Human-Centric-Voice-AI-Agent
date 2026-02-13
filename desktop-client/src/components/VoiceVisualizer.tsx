import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface VoiceVisualizerProps {
  isRecording: boolean;
  audioLevel: number; // 0-100
  onWakeWordDetected?: () => void;
}

export const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({
  isRecording,
  audioLevel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const barsRef = useRef<number[]>(new Array(32).fill(0));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const barCount = 32;
    const barWidth = canvas.width / barCount;
    const centerY = canvas.height / 2;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (isRecording) {
        // Update bars with smooth animation
        barsRef.current = barsRef.current.map((bar, i) => {
          const target = audioLevel * (0.5 + Math.random() * 0.5);
          return bar + (target - bar) * 0.2;
        });
      } else {
        // Fade to idle state
        barsRef.current = barsRef.current.map((bar) => bar * 0.9);
      }

      // Draw bars
      barsRef.current.forEach((height, i) => {
        const x = i * barWidth;
        const normalizedHeight = (height / 100) * centerY * 0.8;

        // Gradient for active state
        const gradient = ctx.createLinearGradient(x, centerY - normalizedHeight, x, centerY + normalizedHeight);

        if (isRecording) {
          gradient.addColorStop(0, '#0ea5e9'); // primary-500
          gradient.addColorStop(0.5, '#d946ef'); // accent-500
          gradient.addColorStop(1, '#0ea5e9');
        } else {
          gradient.addColorStop(0, '#64748b'); // gray
          gradient.addColorStop(1, '#475569');
        }

        ctx.fillStyle = gradient;

        // Draw mirrored bars
        ctx.fillRect(x + 2, centerY - normalizedHeight, barWidth - 4, normalizedHeight * 2);
      });

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isRecording, audioLevel]);

  return (
    <motion.div
      className="relative w-full h-32 bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl overflow-hidden shadow-2xl"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Glow effect when recording */}
      {isRecording && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-primary-500/20 to-accent-500/20"
          animate={{
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      {/* Canvas for waveform */}
      <canvas
        ref={canvasRef}
        width={800}
        height={128}
        className="absolute inset-0 w-full h-full"
      />

      {/* Status indicator */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        {isRecording && (
          <>
            <motion.div
              className="w-2 h-2 rounded-full bg-red-500"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span className="text-xs text-slate-300 font-medium">Listening</span>
          </>
        )}
      </div>

      {/* Audio level indicator */}
      {isRecording && (
        <div className="absolute bottom-4 left-4 right-4">
          <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary-500 to-accent-500"
              style={{ width: `${audioLevel}%` }}
              transition={{ duration: 0.1 }}
            />
          </div>
        </div>
      )}
    </motion.div>
  );
};

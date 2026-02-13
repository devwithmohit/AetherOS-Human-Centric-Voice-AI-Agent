import React from 'react';
import { motion } from 'framer-motion';
import { useAppStore, AppStatus } from '@store/appStore';

export const StatusIndicator: React.FC = () => {
  const status = useAppStore((state) => state.status);
  const isConnected = useAppStore((state) => state.isConnected);

  return (
    <div className="flex items-center justify-between px-6 py-4 bg-slate-800 rounded-xl shadow-lg">
      <div className="flex items-center gap-4">
        {/* Visual state indicator */}
        <div className="relative w-12 h-12 flex items-center justify-center">
          {status === 'idle' && <IdleOrb />}
          {status === 'listening' && <ListeningWaveform />}
          {status === 'processing' && <ProcessingSpinner />}
          {status === 'speaking' && <SpeakingSoundWaves />}
        </div>

        {/* Status label */}
        <div className="flex flex-col">
          <span className={`font-semibold ${
            status === 'idle' ? 'text-slate-400' :
            status === 'listening' ? 'text-blue-500' :
            status === 'processing' ? 'text-orange-500' :
            'text-green-500'
          }`}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
          <span className="text-xs text-slate-500">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Connection indicator */}
      <motion.div
        className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-green-500' : 'bg-red-500'
        }`}
        animate={
          isConnected ? { opacity: [1, 0.3, 1] } : {}
        }
        transition={{ duration: 2, repeat: Infinity }}
      />
    </div>
  );
};

// Idle: Gray pulsing orb
const IdleOrb: React.FC = () => {
  return (
    <motion.div
      className="w-8 h-8 rounded-full bg-slate-500"
      animate={{
        scale: [1, 1.2, 1],
        opacity: [0.5, 0.8, 0.5],
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    />
  );
};

// Listening: Blue animated waveform
const ListeningWaveform: React.FC = () => {
  return (
    <div className="flex items-center justify-center gap-1 h-8">
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          className="w-1 bg-blue-500 rounded-full"
          animate={{
            height: ['16px', '32px', '16px'],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            delay: i * 0.1,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
};

// Processing: Orange spinning loader
const ProcessingSpinner: React.FC = () => {
  return (
    <motion.div
      className="relative w-8 h-8"
      animate={{ rotate: 360 }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'linear',
      }}
    >
      <div className="absolute inset-0 border-4 border-orange-500/30 rounded-full" />
      <div className="absolute inset-0 border-4 border-transparent border-t-orange-500 rounded-full" />
    </motion.div>
  );
};

// Speaking: Green sound waves
const SpeakingSoundWaves: React.FC = () => {
  return (
    <div className="relative w-8 h-8 flex items-center justify-center">
      {/* Center circle */}
      <div className="absolute w-3 h-3 rounded-full bg-green-500" />

      {/* Expanding sound waves */}
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 border-2 border-green-500 rounded-full"
          initial={{ scale: 0, opacity: 0.8 }}
          animate={{
            scale: [0, 2],
            opacity: [0.8, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: i * 0.6,
            ease: 'easeOut',
          }}
        />
      ))}
    </div>
  );
};

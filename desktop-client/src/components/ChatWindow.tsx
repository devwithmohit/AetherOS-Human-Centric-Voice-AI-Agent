import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAppStore } from '@store/appStore';
import { wsService } from '@services/websocket';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  toolStatus?: {
    tool: string;
    status: 'running' | 'complete' | 'error';
    result?: string;
  };
  isMarkdown?: boolean;
}

interface ChatWindowProps {
  onUserInput?: (text: string) => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ onUserInput }) => {
  const messages = useAppStore((state) => state.messages);
  const isTyping = useAppStore((state) => state.isTyping);
  const inputMode = useAppStore((state) => state.inputMode);
  const setInputMode = useAppStore((state) => state.setInputMode);
  const addMessage = useAppStore((state) => state.addMessage);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [textInput, setTextInput] = useState('');

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSendText = () => {
    if (textInput.trim()) {
      addMessage({
        role: 'user',
        content: textInput.trim(),
      });

      // Send to backend via WebSocket
      wsService.send({
        type: 'message',
        text: textInput.trim(),
      });

      if (onUserInput) {
        onUserInput(textInput.trim());
      }

      setTextInput('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-slate-800 to-slate-700 border-b border-slate-600">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <div>
            <h2 className="text-white font-semibold">Aether</h2>
            <p className="text-xs text-slate-400">Voice Assistant</p>
          </div>
        </div>
        <div className="flex gap-2">
          {/* Voice/Text toggle */}
          <div className="flex items-center bg-slate-700 rounded-lg p-1">
            <button
              className={`px-3 py-1 text-xs rounded transition-colors ${
                inputMode === 'voice'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
              onClick={() => setInputMode('voice')}
              title="Voice mode"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>
            <button
              className={`px-3 py-1 text-xs rounded transition-colors ${
                inputMode === 'text'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
              onClick={() => setInputMode('text')}
              title="Text mode"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          </div>

          <button
            className="p-2 hover:bg-slate-600 rounded-lg transition-colors"
            title="Clear conversation"
            onClick={() => useAppStore.getState().clearMessages()}
          >
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-800"
      >
        <AnimatePresence initial={false}>
          {messages.length === 0 ? (
            <motion.div
              className="flex flex-col items-center justify-center h-full text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="w-20 h-20 mb-4 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
                <svg className="w-10 h-10 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-300 mb-2">
                Start a conversation
              </h3>
              <p className="text-sm text-slate-500 max-w-sm">
                {inputMode === 'voice' ? (
                  <>
                    Press <kbd>Ctrl + `</kbd> or say{' '}
                    <span className="text-primary-400 font-medium">"Hey Jarvis"</span> to begin
                  </>
                ) : (
                  <>Type your message below or switch to voice mode</>
                )}
              </p>
            </motion.div>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}

              {/* Typing indicator */}
              {isTyping && <TypingIndicator />}
            </>
          )}
        </AnimatePresence>
      </div>

      {/* Input area - shown only in text mode */}
      {inputMode === 'text' && (
        <div className="px-6 py-4 bg-slate-800 border-t border-slate-700">
          <div className="flex gap-3">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            />
            <button
              onClick={handleSendText}
              disabled={!textInput.trim()}
              className="px-4 py-2 bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all"
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* Voice mode hint */}
      {inputMode === 'voice' && (
        <div className="px-6 py-3 bg-slate-800 border-t border-slate-700">
          <p className="text-xs text-slate-500 text-center">
            Voice-controlled interface • Press <kbd>Ctrl + `</kbd> to toggle listening
          </p>
        </div>
      )}
    </div>
  );
};

const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  // System messages (tool status, etc.)
  if (isSystem) {
    return (
      <motion.div
        className="flex justify-center"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
      >
        <div className="px-4 py-2 bg-slate-700/50 text-slate-400 text-xs rounded-lg border border-slate-600">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <div className={`flex gap-3 max-w-[70%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div
          className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
            isUser
              ? 'bg-gradient-to-br from-slate-600 to-slate-700'
              : 'bg-gradient-to-br from-primary-500 to-accent-500'
          }`}
        >
          <span className="text-white text-sm font-semibold">
            {isUser ? 'U' : 'A'}
          </span>
        </div>

        {/* Message content */}
        <div className="flex flex-col gap-1">
          <div
            className={`px-4 py-3 rounded-2xl ${
              isUser
                ? 'bg-gradient-to-br from-primary-600 to-primary-700 text-white'
                : 'bg-slate-800 text-slate-100'
            }`}
          >
            {/* Tool execution status */}
            {message.toolStatus && (
              <div className="mb-2 flex items-center gap-2 text-xs opacity-80">
                {message.toolStatus.status === 'running' && (
                  <>
                    <motion.div
                      className="w-2 h-2 rounded-full bg-yellow-400"
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                    <span>Running {message.toolStatus.tool}...</span>
                  </>
                )}
                {message.toolStatus.status === 'complete' && (
                  <>
                    <svg className="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Completed {message.toolStatus.tool}</span>
                  </>
                )}
                {message.toolStatus.status === 'error' && (
                  <>
                    <svg className="w-3 h-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span>Error in {message.toolStatus.tool}</span>
                  </>
                )}
              </div>
            )}

            {/* Message content with markdown support */}
            {message.isMarkdown ? (
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            )}

            {/* Audio playback button */}
            {message.audioUrl && (
              <button
                className="mt-2 flex items-center gap-2 text-xs opacity-70 hover:opacity-100 transition-opacity"
                onClick={() => {
                  const audio = new Audio(message.audioUrl);
                  audio.play();
                }}
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Play audio
              </button>
            )}
          </div>

          {/* Timestamp */}
          <span
            className={`text-xs text-slate-500 px-2 ${isUser ? 'text-right' : 'text-left'}`}
          >
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

const TypingIndicator: React.FC = () => {
  return (
    <motion.div
      className="flex justify-start"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <div className="flex gap-3 max-w-[70%]">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center bg-gradient-to-br from-primary-500 to-accent-500">
          <span className="text-white text-sm font-semibold">A</span>
        </div>

        {/* Typing animation */}
        <div className="px-4 py-3 bg-slate-800 rounded-2xl">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 rounded-full bg-slate-500"
                animate={{ y: [0, -8, 0] }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

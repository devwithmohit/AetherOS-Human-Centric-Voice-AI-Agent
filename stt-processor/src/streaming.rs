/// Streaming STT processor module
///
/// Handles real-time speech-to-text with chunked processing and context accumulation.

use crate::audio_preprocessor::{AudioFormat, AudioPreprocessor, AudioSample, PreprocessorError};
use crate::whisper_wrapper::{TranscriptionResult, WhisperError, WhisperProcessor};
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};
use thiserror::Error;
use tokio::sync::{mpsc, RwLock};
use tracing::{debug, info, trace, warn};

/// Chunk size in milliseconds (500ms windows)
pub const CHUNK_DURATION_MS: u64 = 500;

/// Overlap between chunks in milliseconds (50ms for context continuity)
pub const CHUNK_OVERLAP_MS: u64 = 50;

/// Maximum context buffer size in seconds
pub const MAX_CONTEXT_DURATION_SECS: u64 = 30;

#[derive(Error, Debug)]
pub enum StreamingError {
    #[error("Preprocessing error: {0}")]
    PreprocessingError(#[from] PreprocessorError),

    #[error("Whisper error: {0}")]
    WhisperError(#[from] WhisperError),

    #[error("Stream closed")]
    StreamClosed,

    #[error("Buffer overflow: too much audio queued")]
    BufferOverflow,

    #[error("Timeout waiting for audio")]
    Timeout,

    #[error("Invalid chunk size: {0}")]
    InvalidChunkSize(usize),
}

/// Streaming transcription event
#[derive(Debug, Clone)]
pub enum StreamingEvent {
    /// Partial transcription result (may change as more context arrives)
    Partial {
        text: String,
        confidence: f32,
        timestamp_ms: u64,
    },

    /// Final transcription result (stable, won't change)
    Final {
        text: String,
        confidence: f32,
        start_ms: u64,
        end_ms: u64,
    },

    /// End of speech detected
    EndOfSpeech,

    /// Error occurred
    Error {
        message: String,
    },
}

/// Streaming configuration
#[derive(Debug, Clone)]
pub struct StreamingConfig {
    /// Chunk duration in milliseconds
    pub chunk_duration_ms: u64,

    /// Overlap between chunks in milliseconds
    pub overlap_ms: u64,

    /// Maximum buffered audio duration
    pub max_buffer_duration_secs: u64,

    /// Minimum confidence threshold for partial results
    pub min_partial_confidence: f32,

    /// Enable partial results
    pub enable_partial_results: bool,

    /// Maximum queue size before backpressure
    pub max_queue_size: usize,
}

impl Default for StreamingConfig {
    fn default() -> Self {
        Self {
            chunk_duration_ms: CHUNK_DURATION_MS,
            overlap_ms: CHUNK_OVERLAP_MS,
            max_buffer_duration_secs: MAX_CONTEXT_DURATION_SECS,
            min_partial_confidence: 0.5,
            enable_partial_results: true,
            max_queue_size: 100,
        }
    }
}

/// Streaming STT processor state
struct StreamingState {
    audio_buffer: VecDeque<AudioSample>,
    last_transcription: String,
    total_samples_processed: usize,
    chunks_processed: usize,
    is_active: bool,
}

impl StreamingState {
    fn new() -> Self {
        Self {
            audio_buffer: VecDeque::new(),
            last_transcription: String::new(),
            total_samples_processed: 0,
            chunks_processed: 0,
            is_active: false,
        }
    }
}

/// Streaming STT processor
pub struct StreamingSTT {
    whisper: Arc<WhisperProcessor>,
    preprocessor: AudioPreprocessor,
    config: StreamingConfig,
    state: Arc<RwLock<StreamingState>>,
}

impl StreamingSTT {
    /// Create a new streaming STT processor
    pub fn new(
        whisper: Arc<WhisperProcessor>,
        input_format: AudioFormat,
        config: StreamingConfig,
    ) -> Result<Self, StreamingError> {
        let preprocessor = AudioPreprocessor::new(input_format)?;

        info!("Initializing streaming STT");
        info!("Chunk duration: {}ms, overlap: {}ms", config.chunk_duration_ms, config.overlap_ms);

        Ok(Self {
            whisper,
            preprocessor,
            config,
            state: Arc::new(RwLock::new(StreamingState::new())),
        })
    }

    /// Start streaming transcription
    pub async fn start(&self) -> Result<(), StreamingError> {
        let mut state = self.state.write().await;
        state.is_active = true;
        state.audio_buffer.clear();
        state.last_transcription.clear();
        state.total_samples_processed = 0;
        state.chunks_processed = 0;

        info!("Streaming STT started");
        Ok(())
    }

    /// Stop streaming transcription
    pub async fn stop(&self) -> Result<(), StreamingError> {
        let mut state = self.state.write().await;
        state.is_active = false;

        info!("Streaming STT stopped");
        Ok(())
    }

    /// Process audio chunk
    pub async fn process_chunk(&self, audio: &[AudioSample]) -> Result<Option<StreamingEvent>, StreamingError> {
        let mut state = self.state.write().await;

        if !state.is_active {
            return Ok(None);
        }

        if audio.is_empty() {
            return Ok(None);
        }

        trace!("Processing chunk: {} samples", audio.len());

        // Preprocess audio
        let processed = self.preprocessor.process(audio)?;

        // Add to buffer
        state.audio_buffer.extend(processed.iter());
        state.total_samples_processed += processed.len();

        // Check buffer size limit
        let max_samples = (self.config.max_buffer_duration_secs * 16000) as usize;
        if state.audio_buffer.len() > max_samples {
            warn!("Buffer overflow, dropping oldest samples");
            let to_drop = state.audio_buffer.len() - max_samples;
            state.audio_buffer.drain(0..to_drop);
        }

        // Check if we have enough for a chunk
        let chunk_samples = (self.config.chunk_duration_ms * 16) as usize; // 16kHz * ms / 1000

        if state.audio_buffer.len() >= chunk_samples {
            let chunk: Vec<AudioSample> = state.audio_buffer.iter().take(chunk_samples).copied().collect();

            // Remove processed samples (minus overlap)
            let overlap_samples = (self.config.overlap_ms * 16) as usize;
            let to_remove = chunk_samples.saturating_sub(overlap_samples);
            state.audio_buffer.drain(0..to_remove);

            state.chunks_processed += 1;

            // Release lock before transcription (can take time)
            drop(state);

            // Transcribe chunk
            let result = self.whisper.transcribe(&chunk)?;

            // Determine event type
            let event = if self.config.enable_partial_results {
                StreamingEvent::Partial {
                    text: result.text.clone(),
                    confidence: result.confidence,
                    timestamp_ms: (chunk_samples * 1000 / 16000) as u64,
                }
            } else {
                StreamingEvent::Final {
                    text: result.text.clone(),
                    confidence: result.confidence,
                    start_ms: 0,
                    end_ms: (chunk_samples * 1000 / 16000) as u64,
                }
            };

            // Update state
            let mut state = self.state.write().await;
            state.last_transcription = result.text;

            debug!(
                "Chunk {} transcribed: {} chars, confidence: {:.2}",
                state.chunks_processed,
                state.last_transcription.len(),
                result.confidence
            );

            Ok(Some(event))
        } else {
            Ok(None)
        }
    }

    /// Process audio stream (async iterator)
    pub async fn process_stream(
        &self,
        mut audio_rx: mpsc::Receiver<Vec<AudioSample>>,
    ) -> mpsc::Receiver<StreamingEvent> {
        let (tx, rx) = mpsc::channel(self.config.max_queue_size);

        let self_clone = Self {
            whisper: self.whisper.clone(),
            preprocessor: AudioPreprocessor::new(self.preprocessor.input_format()).unwrap(),
            config: self.config.clone(),
            state: self.state.clone(),
        };

        tokio::spawn(async move {
            while let Some(audio) = audio_rx.recv().await {
                match self_clone.process_chunk(&audio).await {
                    Ok(Some(event)) => {
                        if tx.send(event).await.is_err() {
                            warn!("Event receiver dropped");
                            break;
                        }
                    }
                    Ok(None) => {
                        // Not enough audio yet
                    }
                    Err(e) => {
                        let _ = tx.send(StreamingEvent::Error {
                            message: e.to_string(),
                        }).await;
                        break;
                    }
                }
            }

            // Stream ended
            let _ = tx.send(StreamingEvent::EndOfSpeech).await;
        });

        rx
    }

    /// Get current statistics
    pub async fn stats(&self) -> StreamingStats {
        let state = self.state.read().await;

        StreamingStats {
            total_samples_processed: state.total_samples_processed,
            chunks_processed: state.chunks_processed,
            buffer_size: state.audio_buffer.len(),
            is_active: state.is_active,
            last_transcription_length: state.last_transcription.len(),
        }
    }

    /// Get last transcription
    pub async fn last_transcription(&self) -> String {
        let state = self.state.read().await;
        state.last_transcription.clone()
    }

    /// Clear buffer
    pub async fn clear_buffer(&self) {
        let mut state = self.state.write().await;
        state.audio_buffer.clear();
        debug!("Buffer cleared");
    }
}

/// Streaming statistics
#[derive(Debug, Clone)]
pub struct StreamingStats {
    pub total_samples_processed: usize,
    pub chunks_processed: usize,
    pub buffer_size: usize,
    pub is_active: bool,
    pub last_transcription_length: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_config_default() {
        let config = StreamingConfig::default();
        assert_eq!(config.chunk_duration_ms, 500);
        assert_eq!(config.overlap_ms, 50);
        assert!(config.enable_partial_results);
    }

    #[test]
    fn test_chunk_size_calculation() {
        let chunk_duration_ms = 500;
        let sample_rate = 16000;

        let chunk_samples = (chunk_duration_ms * sample_rate / 1000) as usize;
        assert_eq!(chunk_samples, 8000); // 500ms at 16kHz
    }

    #[test]
    fn test_overlap_calculation() {
        let overlap_ms = 50;
        let sample_rate = 16000;

        let overlap_samples = (overlap_ms * sample_rate / 1000) as usize;
        assert_eq!(overlap_samples, 800); // 50ms at 16kHz
    }

    #[tokio::test]
    async fn test_streaming_state_initialization() {
        let state = StreamingState::new();
        assert!(!state.is_active);
        assert_eq!(state.chunks_processed, 0);
        assert_eq!(state.total_samples_processed, 0);
        assert!(state.audio_buffer.is_empty());
    }
}

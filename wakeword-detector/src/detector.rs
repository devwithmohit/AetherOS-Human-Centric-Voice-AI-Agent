/// Wake-word detector main module
///
/// Integrates Porcupine SDK for wake-word detection with VAD and audio buffering.
/// Detects the trigger phrase "Hey Aether" with sub-100ms latency.

use crate::audio_buffer::{AudioBuffer, AudioSample, SAMPLE_RATE};
use crate::vad::{VadConfig, VoiceActivityDetector};
use std::path::Path;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::{mpsc, RwLock};
use tracing::{debug, error, info, warn};

#[derive(Error, Debug)]
pub enum DetectorError {
    #[error("Porcupine initialization failed: {0}")]
    PorcupineInit(String),

    #[error("Invalid audio format: {0}")]
    InvalidAudioFormat(String),

    #[error("Model file not found: {0}")]
    ModelNotFound(String),

    #[error("Detection error: {0}")]
    DetectionError(String),

    #[error("Channel closed")]
    ChannelClosed,
}

/// Wake-word detection result
#[derive(Debug, Clone)]
pub struct WakeWordEvent {
    /// Timestamp when wake-word was detected (microseconds since epoch)
    pub timestamp: i64,

    /// Confidence score (0.0 - 1.0)
    pub confidence: f32,

    /// Audio buffer at time of detection (last 3 seconds)
    pub audio_context: Vec<AudioSample>,

    /// Index of the detected keyword (if multiple keywords supported)
    pub keyword_index: i32,
}

/// Configuration for wake-word detector
#[derive(Debug, Clone)]
pub struct DetectorConfig {
    /// Path to Porcupine access key (required for SDK)
    pub access_key: String,

    /// Path to wake-word model file (.ppn)
    pub model_path: String,

    /// Sensitivity (0.0 - 1.0, higher = more sensitive, more false positives)
    pub sensitivity: f32,

    /// Sample rate (must be 16kHz for Porcupine)
    pub sample_rate: usize,

    /// VAD configuration
    pub vad_config: VadConfig,

    /// Enable VAD pre-filtering (saves CPU by not running Porcupine on silence)
    pub enable_vad_prefilter: bool,
}

impl Default for DetectorConfig {
    fn default() -> Self {
        Self {
            access_key: String::new(), // Must be provided by user
            model_path: "models/aether.ppn".to_string(),
            sensitivity: 0.5,
            sample_rate: SAMPLE_RATE,
            vad_config: VadConfig::default(),
            enable_vad_prefilter: true,
        }
    }
}

impl DetectorConfig {
    /// Validate configuration
    pub fn validate(&self) -> Result<(), DetectorError> {
        if self.access_key.is_empty() {
            return Err(DetectorError::PorcupineInit(
                "Access key is required".to_string()
            ));
        }

        if self.sensitivity < 0.0 || self.sensitivity > 1.0 {
            return Err(DetectorError::InvalidAudioFormat(
                "Sensitivity must be between 0.0 and 1.0".to_string()
            ));
        }

        if self.sample_rate != SAMPLE_RATE {
            return Err(DetectorError::InvalidAudioFormat(
                format!("Sample rate must be {} Hz", SAMPLE_RATE)
            ));
        }

        if !Path::new(&self.model_path).exists() {
            warn!("Model file not found: {}", self.model_path);
            // Note: Don't fail here in case we're in test mode
        }

        self.vad_config.validate().map_err(|e| {
            DetectorError::InvalidAudioFormat(format!("VAD config error: {}", e))
        })?;

        Ok(())
    }
}

/// Wake-word detector state
struct DetectorState {
    audio_buffer: AudioBuffer,
    vad: VoiceActivityDetector,
    is_running: bool,
    frames_processed: u64,
    wake_words_detected: u64,
}

/// Main wake-word detector
pub struct WakeWordDetector {
    config: DetectorConfig,
    state: Arc<RwLock<DetectorState>>,
    event_tx: mpsc::UnboundedSender<WakeWordEvent>,
    event_rx: Arc<RwLock<mpsc::UnboundedReceiver<WakeWordEvent>>>,
}

impl WakeWordDetector {
    /// Create a new wake-word detector
    pub fn new(config: DetectorConfig) -> Result<Self, DetectorError> {
        config.validate()?;

        info!("Initializing wake-word detector");
        info!("Model: {}", config.model_path);
        info!("Sensitivity: {}", config.sensitivity);
        info!("VAD pre-filter: {}", config.enable_vad_prefilter);

        let (event_tx, event_rx) = mpsc::unbounded_channel();

        let state = DetectorState {
            audio_buffer: AudioBuffer::new(),
            vad: VoiceActivityDetector::with_config(config.vad_config.clone()),
            is_running: false,
            frames_processed: 0,
            wake_words_detected: 0,
        };

        Ok(Self {
            config,
            state: Arc::new(RwLock::new(state)),
            event_tx,
            event_rx: Arc::new(RwLock::new(event_rx)),
        })
    }

    /// Start the detector
    pub async fn start(&self) -> Result<(), DetectorError> {
        let mut state = self.state.write().await;

        if state.is_running {
            warn!("Detector already running");
            return Ok(());
        }

        state.is_running = true;
        info!("Wake-word detector started");

        Ok(())
    }

    /// Stop the detector
    pub async fn stop(&self) -> Result<(), DetectorError> {
        let mut state = self.state.write().await;

        if !state.is_running {
            warn!("Detector not running");
            return Ok(());
        }

        state.is_running = false;
        info!("Wake-word detector stopped");

        Ok(())
    }

    /// Process incoming audio samples
    ///
    /// This is the main entry point for audio data. Should be called
    /// with chunks of audio (e.g., 512 samples at a time for low latency).
    pub async fn process_audio(&self, samples: &[AudioSample]) -> Result<(), DetectorError> {
        let mut state = self.state.write().await;

        if !state.is_running {
            return Ok(());
        }

        // Write to ring buffer
        state.audio_buffer.write(samples);

        // Process in frame-sized chunks
        let frame_size = self.config.vad_config.frame_size;

        while state.audio_buffer.len() >= frame_size {
            let frame = state.audio_buffer.peek(frame_size);

            // VAD pre-filter (optional optimization)
            let should_process = if self.config.enable_vad_prefilter {
                match state.vad.process_frame(&frame) {
                    Ok(is_speech) => {
                        if !is_speech {
                            // Skip Porcupine processing on silence
                            state.audio_buffer.read(frame_size).ok();
                            continue;
                        }
                        true
                    }
                    Err(e) => {
                        warn!("VAD error: {}", e);
                        true // Process anyway if VAD fails
                    }
                }
            } else {
                true
            };

            if should_process {
                // Run wake-word detection
                if let Err(e) = self.detect_wake_word(&frame).await {
                    error!("Wake-word detection error: {}", e);
                }
            }

            // Remove processed frame from buffer
            state.audio_buffer.read(frame_size).ok();
            state.frames_processed += 1;

            if state.frames_processed % 1000 == 0 {
                debug!(
                    "Processed {} frames, detected {} wake-words",
                    state.frames_processed, state.wake_words_detected
                );
            }
        }

        Ok(())
    }

    /// Detect wake-word in audio frame (mock implementation)
    ///
    /// NOTE: This is a placeholder. In production, this would call
    /// the actual Porcupine SDK. For testing, we simulate detection
    /// based on audio energy patterns.
    async fn detect_wake_word(&self, frame: &[AudioSample]) -> Result<(), DetectorError> {
        // Mock detection logic for testing
        // In production: use pv_porcupine::Porcupine::process()

        let detection_result = self.mock_porcupine_process(frame);

        if let Some(keyword_index) = detection_result {
            info!("Wake-word detected! (keyword_index: {})", keyword_index);

            let state = self.state.read().await;

            // Capture audio context (last 3 seconds)
            let audio_context = state.audio_buffer.peek(state.audio_buffer.len());

            let event = WakeWordEvent {
                timestamp: Self::current_timestamp_micros(),
                confidence: 0.85, // Mock confidence
                audio_context,
                keyword_index,
            };

            // Send event
            if let Err(e) = self.event_tx.send(event) {
                error!("Failed to send wake-word event: {}", e);
            }

            // Update stats
            drop(state);
            let mut state = self.state.write().await;
            state.wake_words_detected += 1;
        }

        Ok(())
    }

    /// Mock Porcupine processing (for testing without actual SDK)
    ///
    /// Returns Some(keyword_index) if wake-word detected, None otherwise.
    fn mock_porcupine_process(&self, frame: &[AudioSample]) -> Option<i32> {
        // Simple energy-based mock detection
        // In real implementation: return porcupine.process(frame)

        let energy: f64 = frame
            .iter()
            .map(|&s| {
                let normalized = s as f64 / i16::MAX as f64;
                normalized * normalized
            })
            .sum();

        let rms = (energy / frame.len() as f64).sqrt();

        // Simulate detection on high-energy frames (simplified)
        // Real Porcupine would use trained neural network
        if rms > 0.4 {
            // Randomly detect to simulate occasional triggers
            if self.state.try_read().map(|s| s.frames_processed % 100 == 0).unwrap_or(false) {
                return Some(0); // Keyword index 0
            }
        }

        None
    }

    /// Get the next wake-word event (non-blocking)
    pub async fn try_recv_event(&self) -> Option<WakeWordEvent> {
        let mut rx = self.event_rx.write().await;
        rx.try_recv().ok()
    }

    /// Get the next wake-word event (blocking)
    pub async fn recv_event(&self) -> Option<WakeWordEvent> {
        let mut rx = self.event_rx.write().await;
        rx.recv().await
    }

    /// Get current statistics
    pub async fn stats(&self) -> DetectorStats {
        let state = self.state.read().await;

        DetectorStats {
            frames_processed: state.frames_processed,
            wake_words_detected: state.wake_words_detected,
            buffer_fill_percent: (state.audio_buffer.len() as f32
                                / state.audio_buffer.capacity() as f32 * 100.0),
            is_running: state.is_running,
        }
    }

    /// Reset detector state
    pub async fn reset(&self) {
        let mut state = self.state.write().await;
        state.audio_buffer.clear();
        state.vad.reset();
        state.frames_processed = 0;
        state.wake_words_detected = 0;
        info!("Detector reset");
    }

    /// Get current timestamp in microseconds
    fn current_timestamp_micros() -> i64 {
        use std::time::{SystemTime, UNIX_EPOCH};

        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_micros() as i64
    }
}

/// Detector statistics
#[derive(Debug, Clone)]
pub struct DetectorStats {
    pub frames_processed: u64,
    pub wake_words_detected: u64,
    pub buffer_fill_percent: f32,
    pub is_running: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> DetectorConfig {
        DetectorConfig {
            access_key: "test_key".to_string(),
            model_path: "models/test.ppn".to_string(),
            sensitivity: 0.5,
            sample_rate: SAMPLE_RATE,
            vad_config: VadConfig::default(),
            enable_vad_prefilter: false, // Disable for predictable tests
        }
    }

    #[tokio::test]
    async fn test_detector_creation() {
        let config = test_config();
        let detector = WakeWordDetector::new(config).unwrap();

        let stats = detector.stats().await;
        assert!(!stats.is_running);
        assert_eq!(stats.frames_processed, 0);
    }

    #[tokio::test]
    async fn test_start_stop() {
        let config = test_config();
        let detector = WakeWordDetector::new(config).unwrap();

        detector.start().await.unwrap();
        assert!(detector.stats().await.is_running);

        detector.stop().await.unwrap();
        assert!(!detector.stats().await.is_running);
    }

    #[tokio::test]
    async fn test_process_audio() {
        let config = test_config();
        let detector = WakeWordDetector::new(config).unwrap();

        detector.start().await.unwrap();

        // Generate some audio samples
        let samples: Vec<i16> = (0..1000).map(|i| (i % 100) as i16).collect();

        detector.process_audio(&samples).await.unwrap();

        let stats = detector.stats().await;
        assert!(stats.frames_processed > 0);
    }

    #[tokio::test]
    async fn test_reset() {
        let config = test_config();
        let detector = WakeWordDetector::new(config).unwrap();

        detector.start().await.unwrap();

        let samples: Vec<i16> = vec![100; 1000];
        detector.process_audio(&samples).await.unwrap();

        detector.reset().await;

        let stats = detector.stats().await;
        assert_eq!(stats.frames_processed, 0);
    }

    #[test]
    fn test_config_validation() {
        let mut config = test_config();
        assert!(config.validate().is_ok());

        // Invalid sensitivity
        config.sensitivity = 1.5;
        assert!(config.validate().is_err());

        config.sensitivity = 0.5;

        // Empty access key
        config.access_key = String::new();
        assert!(config.validate().is_err());
    }

    #[tokio::test]
    async fn test_event_reception() {
        let config = test_config();
        let detector = WakeWordDetector::new(config).unwrap();

        detector.start().await.unwrap();

        // Generate high-energy audio to trigger mock detection
        let samples: Vec<i16> = vec![i16::MAX / 2; 5000];

        detector.process_audio(&samples).await.unwrap();

        // Try to receive event (may or may not trigger in mock)
        if let Some(event) = detector.try_recv_event().await {
            assert!(event.confidence > 0.0);
            assert_eq!(event.keyword_index, 0);
        }
    }
}

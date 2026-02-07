/// Whisper wrapper module
///
/// Provides safe Rust bindings to whisper.cpp for speech-to-text transcription.
/// Uses a mock implementation when the `whisper` feature is not enabled.

use crate::audio_preprocessor::{AudioSample, WHISPER_SAMPLE_RATE};
use parking_lot::Mutex;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use thiserror::Error;
use tracing::{debug, info, warn};

#[cfg(feature = "whisper")]
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

#[derive(Error, Debug)]
pub enum WhisperError {
    #[error("Model loading failed: {0}")]
    ModelLoadError(String),
    
    #[error("Transcription failed: {0}")]
    TranscriptionError(String),
    
    #[error("Invalid audio format: {0}")]
    InvalidAudioFormat(String),
    
    #[error("Model file not found: {0}")]
    ModelNotFound(PathBuf),
    
    #[error("Initialization failed: {0}")]
    InitializationError(String),
}

/// Whisper transcription result
#[derive(Debug, Clone)]
pub struct TranscriptionResult {
    /// Transcribed text
    pub text: String,
    
    /// Confidence score (0.0 - 1.0)
    pub confidence: f32,
    
    /// Processing time in milliseconds
    pub processing_time_ms: u64,
    
    /// Language detected (ISO 639-1 code)
    pub language: String,
    
    /// Individual segments with timestamps
    pub segments: Vec<TranscriptionSegment>,
}

/// Individual transcription segment
#[derive(Debug, Clone)]
pub struct TranscriptionSegment {
    /// Start time in milliseconds
    pub start_ms: i64,
    
    /// End time in milliseconds
    pub end_ms: i64,
    
    /// Segment text
    pub text: String,
    
    /// Segment confidence
    pub confidence: f32,
}

/// Whisper model configuration
#[derive(Debug, Clone)]
pub struct WhisperConfig {
    /// Path to Whisper model file (.bin)
    pub model_path: PathBuf,
    
    /// Language to transcribe (e.g., "en", "auto" for auto-detect)
    pub language: String,
    
    /// Number of threads to use
    pub num_threads: usize,
    
    /// Enable GPU acceleration if available
    pub use_gpu: bool,
    
    /// Translate to English if not English
    pub translate: bool,
    
    /// Print progress information
    pub print_progress: bool,
    
    /// Maximum segment length in characters
    pub max_segment_length: usize,
}

impl Default for WhisperConfig {
    fn default() -> Self {
        Self {
            model_path: PathBuf::from("models/ggml-base.en.bin"),
            language: "en".to_string(),
            num_threads: num_cpus::get(),
            use_gpu: true,
            translate: false,
            print_progress: false,
            max_segment_length: 1000,
        }
    }
}

impl WhisperConfig {
    /// Validate configuration
    pub fn validate(&self) -> Result<(), WhisperError> {
        // For mock mode, skip file check
        #[cfg(feature = "whisper")]
        {
            if !self.model_path.exists() {
                return Err(WhisperError::ModelNotFound(self.model_path.clone()));
            }
        }
        
        if self.num_threads == 0 {
            return Err(WhisperError::InitializationError(
                "num_threads must be > 0".to_string()
            ));
        }
        
        Ok(())
    }
}

// Real Whisper implementation
#[cfg(feature = "whisper")]
mod real_impl {
    use super::*;
    
    /// Whisper STT processor
    pub struct WhisperProcessor {
        context: Arc<Mutex<WhisperContext>>,
        config: WhisperConfig,
    }

    impl WhisperProcessor {
        /// Create a new Whisper processor
        pub fn new(config: WhisperConfig) -> Result<Self, WhisperError> {
            config.validate()?;
            
            info!("Loading Whisper model: {:?}", config.model_path);
            info!("Using {} threads", config.num_threads);
            
            // Create context parameters
            let ctx_params = WhisperContextParameters::default();
            
            // Load model
            let context = WhisperContext::new_with_params(
                config.model_path.to_str().unwrap(),
                ctx_params,
            )
            .map_err(|e| WhisperError::ModelLoadError(e.to_string()))?;
            
            info!("Whisper model loaded successfully");
            
            Ok(Self {
                context: Arc::new(Mutex::new(context)),
                config,
            })
        }
        
        /// Transcribe audio samples
        pub fn transcribe(&self, audio: &[AudioSample]) -> Result<TranscriptionResult, WhisperError> {
            if audio.is_empty() {
                return Err(WhisperError::InvalidAudioFormat(
                    "Empty audio buffer".to_string()
                ));
            }
            
            debug!("Transcribing {} samples", audio.len());
            let start_time = std::time::Instant::now();
            
            // Create transcription parameters
            let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
            
            // Configure parameters
            params.set_language(Some(&self.config.language));
            params.set_translate(self.config.translate);
            params.set_print_progress(self.config.print_progress);
            params.set_print_special(false);
            params.set_print_realtime(false);
            params.set_n_threads(self.config.num_threads as i32);
            
            // Lock context and transcribe
            let mut ctx = self.context.lock();
            
            ctx.full(params, audio)
                .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
            
            // Extract results
            let num_segments = ctx
                .full_n_segments()
                .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
            
            let mut segments = Vec::new();
            let mut full_text = String::new();
            let mut total_confidence = 0.0;
            
            for i in 0..num_segments {
                let segment_text = ctx
                    .full_get_segment_text(i)
                    .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
                
                let start_time_seg = ctx
                    .full_get_segment_t0(i)
                    .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
                
                let end_time = ctx
                    .full_get_segment_t1(i)
                    .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
                
                // Estimate confidence
                let confidence = Self::estimate_confidence(&segment_text);
                total_confidence += confidence;
                
                segments.push(TranscriptionSegment {
                    start_ms: start_time_seg,
                    end_ms: end_time,
                    text: segment_text.trim().to_string(),
                    confidence,
                });
                
                full_text.push_str(&segment_text);
            }
            
            let avg_confidence = if num_segments > 0 {
                total_confidence / num_segments as f32
            } else {
                0.0
            };
            
            let elapsed = start_time.elapsed().as_millis() as u64;
            
            debug!(
                "Transcription complete: {} segments, {:.2}s, confidence={:.2}",
                num_segments,
                elapsed as f32 / 1000.0,
                avg_confidence
            );
            
            Ok(TranscriptionResult {
                text: full_text.trim().to_string(),
                confidence: avg_confidence,
                processing_time_ms: elapsed,
                language: self.config.language.clone(),
                segments,
            })
        }
        
        /// Estimate confidence score (heuristic)
        fn estimate_confidence(text: &str) -> f32 {
            let trimmed = text.trim();
            
            if trimmed.is_empty() {
                return 0.0;
            }
            
            let mut confidence = 0.8;
            
            // Repeated characters/words indicate low confidence
            let repeated_chars = trimmed.chars().collect::<Vec<_>>();
            let mut repeated_count = 0;
            
            for window in repeated_chars.windows(3) {
                if window[0] == window[1] && window[1] == window[2] {
                    repeated_count += 1;
                }
            }
            
            if repeated_count > 2 {
                confidence -= 0.3;
            }
            
            // Very short segments may be hallucinations
            if trimmed.len() < 3 {
                confidence -= 0.2;
            }
            
            // Common Whisper hallucinations
            let hallucinations = ["[BLANK_AUDIO]", "Thank you.", "Thanks for watching!"];
            for hallucination in &hallucinations {
                if trimmed.contains(hallucination) {
                    confidence -= 0.4;
                }
            }
            
            confidence.max(0.0).min(1.0)
        }
        
        /// Get model configuration
        pub fn config(&self) -> &WhisperConfig {
            &self.config
        }
    }
}

// Mock implementation for testing without Whisper
#[cfg(not(feature = "whisper"))]
mod mock_impl {
    use super::*;
    
    /// Mock Whisper STT processor
    pub struct WhisperProcessor {
        config: WhisperConfig,
    }

    impl WhisperProcessor {
        /// Create a new mock Whisper processor
        pub fn new(config: WhisperConfig) -> Result<Self, WhisperError> {
            config.validate()?;
            
            warn!("Using MOCK Whisper implementation (whisper feature not enabled)");
            info!("Mock model path: {:?}", config.model_path);
            info!("Using {} threads (mock)", config.num_threads);
            
            Ok(Self { config })
        }
        
        /// Mock transcribe audio samples
        pub fn transcribe(&self, audio: &[AudioSample]) -> Result<TranscriptionResult, WhisperError> {
            if audio.is_empty() {
                return Err(WhisperError::InvalidAudioFormat(
                    "Empty audio buffer".to_string()
                ));
            }
            
            debug!("MOCK transcribing {} samples", audio.len());
            
            // Simulate processing time
            let processing_time = (audio.len() as f32 / WHISPER_SAMPLE_RATE as f32 * 100.0) as u64;
            std::thread::sleep(std::time::Duration::from_millis(processing_time.min(500)));
            
            // Generate mock transcription
            let duration_secs = audio.len() as f32 / WHISPER_SAMPLE_RATE as f32;
            let num_segments = (duration_secs / 2.0).ceil() as usize; // ~2s per segment
            
            let mut segments = Vec::new();
            let mut full_text = String::new();
            
            for i in 0..num_segments {
                let start_ms = (i as f32 * 2000.0) as i64;
                let end_ms = ((i + 1) as f32 * 2000.0).min(duration_secs * 1000.0) as i64;
                
                let segment_text = format!(" Mock segment {} at {:.1}s", i + 1, start_ms as f32 / 1000.0);
                
                segments.push(TranscriptionSegment {
                    start_ms,
                    end_ms,
                    text: segment_text.clone(),
                    confidence: 0.85,
                });
                
                full_text.push_str(&segment_text);
            }
            
            debug!("MOCK transcription complete: {} segments", segments.len());
            
            Ok(TranscriptionResult {
                text: full_text.trim().to_string(),
                confidence: 0.85,
                processing_time_ms: processing_time,
                language: self.config.language.clone(),
                segments,
            })
        }
        
        /// Get model configuration
        pub fn config(&self) -> &WhisperConfig {
            &self.config
        }
    }
}

// Export the appropriate implementation
#[cfg(feature = "whisper")]
pub use real_impl::WhisperProcessor;

#[cfg(not(feature = "whisper"))]
pub use mock_impl::WhisperProcessor;

// Tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_whisper_config_default() {
        let config = WhisperConfig::default();
        assert_eq!(config.language, "en");
        assert!(!config.translate);
        assert!(!config.print_progress);
        assert!(config.num_threads > 0);
    }

    #[test]
    fn test_whisper_config_validation() {
        let mut config = WhisperConfig::default();
        config.num_threads = 0;
        
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_mock_whisper_processor() {
        let config = WhisperConfig::default();
        let processor = WhisperProcessor::new(config).unwrap();
        
        // Generate 1 second of test audio
        let audio: Vec<f32> = (0..16000).map(|i| (i as f32 * 0.001).sin()).collect();
        
        let result = processor.transcribe(&audio).unwrap();
        
        assert!(!result.text.is_empty());
        assert!(result.confidence >= 0.0 && result.confidence <= 1.0);
        assert!(result.processing_time_ms > 0);
        assert_eq!(result.language, "en");
        assert!(!result.segments.is_empty());
    }

    #[test]
    fn test_empty_audio() {
        let config = WhisperConfig::default();
        let processor = WhisperProcessor::new(config).unwrap();
        
        let empty: Vec<f32> = vec![];
        let result = processor.transcribe(&empty);
        
        assert!(result.is_err());
    }
}

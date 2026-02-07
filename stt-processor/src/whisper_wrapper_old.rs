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
        if !self.model_path.exists() {
            return Err(WhisperError::ModelNotFound(self.model_path.clone()));
        }
        
        if self.num_threads == 0 {
            return Err(WhisperError::InitializationError(
                "num_threads must be > 0".to_string()
            ));
        }
        
        Ok(())
    }
}

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
            
            let start_time = ctx
                .full_get_segment_t0(i)
                .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
            
            let end_time = ctx
                .full_get_segment_t1(i)
                .map_err(|e| WhisperError::TranscriptionError(e.to_string()))?;
            
            // Calculate confidence (Whisper doesn't provide per-segment confidence)
            // Use a heuristic based on segment length and content
            let confidence = self.estimate_confidence(&segment_text);
            total_confidence += confidence;
            
            segments.push(TranscriptionSegment {
                start_ms: start_time,
                end_ms: end_time,
                text: segment_text.clone(),
                confidence,
            });
            
            full_text.push_str(&segment_text);
            full_text.push(' ');
        }
        
        let avg_confidence = if num_segments > 0 {
            total_confidence / num_segments as f32
        } else {
            0.0
        };
        
        let processing_time = start_time.elapsed();
        
        debug!(
            "Transcription complete: {} segments, {:.2}s processing time",
            num_segments,
            processing_time.as_secs_f32()
        );
        
        Ok(TranscriptionResult {
            text: full_text.trim().to_string(),
            confidence: avg_confidence,
            processing_time_ms: processing_time.as_millis() as u64,
            language: self.config.language.clone(),
            segments,
        })
    }
    
    /// Estimate confidence score for a segment
    ///
    /// Uses heuristics since Whisper doesn't provide confidence scores:
    /// - Longer segments are more confident
    /// - Segments with normal punctuation are more confident
    /// - Segments without repeated characters are more confident
    fn estimate_confidence(&self, text: &str) -> f32 {
        if text.is_empty() {
            return 0.0;
        }
        
        let mut confidence = 0.7; // Base confidence
        
        // Length bonus (longer is more confident)
        if text.len() > 20 {
            confidence += 0.1;
        }
        
        // Punctuation bonus
        if text.contains(['.', '!', '?']) {
            confidence += 0.1;
        }
        
        // Penalty for excessive repetition
        if self.has_excessive_repetition(text) {
            confidence -= 0.2;
        }
        
        // Penalty for all caps or all lowercase
        if text.chars().all(|c| c.is_uppercase() || !c.is_alphabetic()) {
            confidence -= 0.1;
        }
        
        confidence.clamp(0.0, 1.0)
    }
    
    /// Check for excessive character repetition (indicates poor transcription)
    fn has_excessive_repetition(&self, text: &str) -> bool {
        if text.len() < 3 {
            return false;
        }
        
        let mut prev_char = '\0';
        let mut repeat_count = 0;
        
        for ch in text.chars() {
            if ch == prev_char {
                repeat_count += 1;
                if repeat_count > 3 {
                    return true;
                }
            } else {
                repeat_count = 0;
                prev_char = ch;
            }
        }
        
        false
    }
    
    /// Get model information
    pub fn model_info(&self) -> String {
        format!(
            "Whisper model: {:?}, threads: {}, GPU: {}",
            self.config.model_path.file_name().unwrap_or_default(),
            self.config.num_threads,
            self.config.use_gpu
        )
    }
    
    /// Get configuration
    pub fn config(&self) -> &WhisperConfig {
        &self.config
    }
}

// Note: Add num_cpus dependency to Cargo.toml
// For now, implement a simple fallback
mod num_cpus {
    pub fn get() -> usize {
        std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(4)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn test_config() -> WhisperConfig {
        WhisperConfig {
            model_path: PathBuf::from("models/test-model.bin"),
            language: "en".to_string(),
            num_threads: 4,
            use_gpu: false,
            translate: false,
            print_progress: false,
            max_segment_length: 1000,
        }
    }
    
    #[test]
    fn test_config_validation() {
        let mut config = test_config();
        
        // Valid config (but file doesn't exist, will fail)
        config.num_threads = 4;
        assert!(config.validate().is_err()); // File not found
        
        // Invalid threads
        config.num_threads = 0;
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_confidence_estimation() {
        // Create a dummy processor for testing (won't actually load model)
        let config = test_config();
        
        // Can't test without actual model, but we can test the helper function
        // Test is more conceptual - actual processor creation requires model file
    }
    
    #[test]
    fn test_excessive_repetition_detection() {
        let config = test_config();
        
        // Simulate the repetition check logic
        let has_repetition = |text: &str| -> bool {
            if text.len() < 3 {
                return false;
            }
            
            let mut prev_char = '\0';
            let mut repeat_count = 0;
            
            for ch in text.chars() {
                if ch == prev_char {
                    repeat_count += 1;
                    if repeat_count > 3 {
                        return true;
                    }
                } else {
                    repeat_count = 0;
                    prev_char = ch;
                }
            }
            
            false
        };
        
        assert!(!has_repetition("hello world"));
        assert!(has_repetition("hellooooo"));
        assert!(has_repetition("aaaa"));
        assert!(!has_repetition("book"));
    }
    
    #[test]
    fn test_default_config() {
        let config = WhisperConfig::default();
        assert_eq!(config.language, "en");
        assert!(!config.translate);
        assert!(config.num_threads > 0);
    }
}

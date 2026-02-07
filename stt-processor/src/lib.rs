/// STT Processor library
///
/// Provides speech-to-text functionality using Whisper with streaming support.

pub mod audio_preprocessor;
pub mod streaming;
pub mod whisper_wrapper;

// Re-export main types
pub use audio_preprocessor::{AudioFormat, AudioPreprocessor, AudioSample, PreprocessorError, WHISPER_SAMPLE_RATE};
pub use streaming::{StreamingConfig, StreamingEvent, StreamingSTT, StreamingStats, StreamingError};
pub use whisper_wrapper::{
    TranscriptionResult, TranscriptionSegment, WhisperConfig, WhisperError, WhisperProcessor,
};

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

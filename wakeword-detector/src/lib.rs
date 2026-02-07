/// Wake-word detector library
///
/// This library provides wake-word detection functionality using Porcupine SDK,
/// VAD pre-filtering, and lock-free audio buffering.

pub mod audio_buffer;
pub mod detector;
pub mod vad;

// Re-export main types
pub use audio_buffer::{AudioBuffer, AudioSample, SAMPLE_RATE};
pub use detector::{DetectorConfig, DetectorError, WakeWordDetector, WakeWordEvent};
pub use vad::{VadConfig, VadError, VadState, VoiceActivityDetector};

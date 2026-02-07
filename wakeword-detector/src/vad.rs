/// Voice Activity Detection (VAD) module
///
/// Detects speech vs silence using energy-based and zero-crossing rate analysis.
/// This is used as a pre-filter before wake-word detection to save compute.

use crate::audio_buffer::AudioSample;
use thiserror::Error;
use tracing::{debug, trace};

#[derive(Error, Debug)]
pub enum VadError {
    #[error("Insufficient audio data: need at least {0} samples")]
    InsufficientData(usize),

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}

/// VAD configuration parameters
#[derive(Debug, Clone)]
pub struct VadConfig {
    /// Energy threshold for speech detection (0.0 - 1.0)
    pub energy_threshold: f32,

    /// Zero-crossing rate threshold for speech detection
    pub zcr_threshold: f32,

    /// Minimum frame size in samples for analysis
    pub frame_size: usize,

    /// Number of consecutive frames needed to confirm speech
    pub speech_frames_required: usize,

    /// Number of consecutive silence frames to end speech
    pub silence_frames_required: usize,
}

impl Default for VadConfig {
    fn default() -> Self {
        Self {
            energy_threshold: 0.02,        // 2% of max energy
            zcr_threshold: 0.15,           // 15% zero crossings
            frame_size: 480,               // 30ms at 16kHz
            speech_frames_required: 3,     // 90ms of speech to trigger
            silence_frames_required: 10,   // 300ms of silence to end
        }
    }
}

impl VadConfig {
    /// Validate configuration parameters
    pub fn validate(&self) -> Result<(), VadError> {
        if self.energy_threshold < 0.0 || self.energy_threshold > 1.0 {
            return Err(VadError::InvalidConfig(
                "energy_threshold must be between 0.0 and 1.0".to_string()
            ));
        }

        if self.zcr_threshold < 0.0 || self.zcr_threshold > 1.0 {
            return Err(VadError::InvalidConfig(
                "zcr_threshold must be between 0.0 and 1.0".to_string()
            ));
        }

        if self.frame_size == 0 {
            return Err(VadError::InvalidConfig(
                "frame_size must be greater than 0".to_string()
            ));
        }

        Ok(())
    }
}

/// Voice Activity Detector state machine
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VadState {
    /// Currently detecting silence
    Silence,

    /// Potential speech detected (waiting for confirmation)
    MaybeSpeech,

    /// Active speech confirmed
    Speech,

    /// Speech ending (waiting for confirmation)
    MaybeSilence,
}

/// Voice Activity Detector
pub struct VoiceActivityDetector {
    config: VadConfig,
    state: VadState,
    speech_frame_count: usize,
    silence_frame_count: usize,
}

impl VoiceActivityDetector {
    /// Create a new VAD with default configuration
    pub fn new() -> Self {
        Self::with_config(VadConfig::default())
    }

    /// Create a new VAD with custom configuration
    pub fn with_config(config: VadConfig) -> Self {
        debug!("Initializing VAD with config: {:?}", config);

        Self {
            config,
            state: VadState::Silence,
            speech_frame_count: 0,
            silence_frame_count: 0,
        }
    }

    /// Process audio frame and return whether it contains speech
    pub fn process_frame(&mut self, samples: &[AudioSample]) -> Result<bool, VadError> {
        if samples.len() < self.config.frame_size {
            return Err(VadError::InsufficientData(self.config.frame_size));
        }

        // Calculate energy and zero-crossing rate
        let energy = self.calculate_energy(samples);
        let zcr = self.calculate_zero_crossing_rate(samples);

        trace!(
            "Frame analysis: energy={:.4}, zcr={:.4}, state={:?}",
            energy, zcr, self.state
        );

        // Determine if frame contains speech
        let is_speech_frame = energy > self.config.energy_threshold
                           && zcr > self.config.zcr_threshold;

        // Update state machine
        self.update_state(is_speech_frame);

        Ok(self.is_speech_active())
    }

    /// Calculate normalized energy of audio frame
    fn calculate_energy(&self, samples: &[AudioSample]) -> f32 {
        let sum_squares: f64 = samples
            .iter()
            .map(|&s| {
                let normalized = s as f64 / i16::MAX as f64;
                normalized * normalized
            })
            .sum();

        let rms = (sum_squares / samples.len() as f64).sqrt();
        rms as f32
    }

    /// Calculate zero-crossing rate (ZCR)
    ///
    /// ZCR measures how often the signal crosses the zero amplitude line.
    /// Speech typically has moderate ZCR, while silence has very low ZCR.
    fn calculate_zero_crossing_rate(&self, samples: &[AudioSample]) -> f32 {
        if samples.len() < 2 {
            return 0.0;
        }

        let crossings = samples
            .windows(2)
            .filter(|pair| {
                (pair[0] >= 0 && pair[1] < 0) || (pair[0] < 0 && pair[1] >= 0)
            })
            .count();

        crossings as f32 / (samples.len() - 1) as f32
    }

    /// Update VAD state machine based on speech detection
    fn update_state(&mut self, is_speech_frame: bool) {
        match self.state {
            VadState::Silence => {
                if is_speech_frame {
                    self.speech_frame_count = 1;
                    self.silence_frame_count = 0;
                    self.state = VadState::MaybeSpeech;
                    debug!("State: Silence -> MaybeSpeech");
                }
            }

            VadState::MaybeSpeech => {
                if is_speech_frame {
                    self.speech_frame_count += 1;
                    if self.speech_frame_count >= self.config.speech_frames_required {
                        self.state = VadState::Speech;
                        debug!("State: MaybeSpeech -> Speech (confirmed)");
                    }
                } else {
                    self.state = VadState::Silence;
                    self.speech_frame_count = 0;
                    debug!("State: MaybeSpeech -> Silence (false alarm)");
                }
            }

            VadState::Speech => {
                if !is_speech_frame {
                    self.silence_frame_count = 1;
                    self.speech_frame_count = 0;
                    self.state = VadState::MaybeSilence;
                    debug!("State: Speech -> MaybeSilence");
                } else {
                    self.silence_frame_count = 0;
                }
            }

            VadState::MaybeSilence => {
                if !is_speech_frame {
                    self.silence_frame_count += 1;
                    if self.silence_frame_count >= self.config.silence_frames_required {
                        self.state = VadState::Silence;
                        debug!("State: MaybeSilence -> Silence (speech ended)");
                    }
                } else {
                    self.state = VadState::Speech;
                    self.silence_frame_count = 0;
                    debug!("State: MaybeSilence -> Speech (continued)");
                }
            }
        }
    }

    /// Check if speech is currently active
    pub fn is_speech_active(&self) -> bool {
        matches!(self.state, VadState::Speech | VadState::MaybeSilence)
    }

    /// Get current VAD state
    pub fn state(&self) -> VadState {
        self.state
    }

    /// Reset VAD to initial state
    pub fn reset(&mut self) {
        self.state = VadState::Silence;
        self.speech_frame_count = 0;
        self.silence_frame_count = 0;
        debug!("VAD reset to initial state");
    }

    /// Get current configuration
    pub fn config(&self) -> &VadConfig {
        &self.config
    }
}

impl Default for VoiceActivityDetector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    fn generate_silence(length: usize) -> Vec<AudioSample> {
        vec![0; length]
    }

    fn generate_tone(frequency: f32, duration_samples: usize, amplitude: f32) -> Vec<AudioSample> {
        let sample_rate = 16000.0;
        (0..duration_samples)
            .map(|i| {
                let t = i as f32 / sample_rate;
                let sample = amplitude * (2.0 * std::f32::consts::PI * frequency * t).sin();
                (sample * i16::MAX as f32) as i16
            })
            .collect()
    }

    #[test]
    fn test_vad_config_default() {
        let config = VadConfig::default();
        assert!(config.validate().is_ok());
        assert_eq!(config.frame_size, 480);
    }

    #[test]
    fn test_vad_config_validation() {
        let mut config = VadConfig::default();
        config.energy_threshold = 1.5;
        assert!(config.validate().is_err());

        config.energy_threshold = 0.5;
        config.frame_size = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_silence_detection() {
        let mut vad = VoiceActivityDetector::new();
        let silence = generate_silence(480);

        let is_speech = vad.process_frame(&silence).unwrap();
        assert!(!is_speech);
        assert_eq!(vad.state(), VadState::Silence);
    }

    #[test]
    fn test_speech_detection() {
        let mut vad = VoiceActivityDetector::new();

        // Generate speech-like signal (moderate frequency, good amplitude)
        let speech = generate_tone(200.0, 480, 0.3);

        // Process multiple frames to trigger speech state
        for _ in 0..5 {
            vad.process_frame(&speech).unwrap();
        }

        assert!(vad.is_speech_active());
    }

    #[test]
    fn test_energy_calculation() {
        let vad = VoiceActivityDetector::new();

        // Silence should have very low energy
        let silence = generate_silence(480);
        let energy_silence = vad.calculate_energy(&silence);
        assert!(energy_silence < 0.001);

        // Tone should have measurable energy
        let tone = generate_tone(200.0, 480, 0.5);
        let energy_tone = vad.calculate_energy(&tone);
        assert!(energy_tone > 0.1);
    }

    #[test]
    fn test_zero_crossing_rate() {
        let vad = VoiceActivityDetector::new();

        // Silence has no zero crossings
        let silence = generate_silence(480);
        let zcr_silence = vad.calculate_zero_crossing_rate(&silence);
        assert_relative_eq!(zcr_silence, 0.0, epsilon = 0.001);

        // Tone has regular zero crossings
        let tone = generate_tone(200.0, 480, 0.5);
        let zcr_tone = vad.calculate_zero_crossing_rate(&tone);
        assert!(zcr_tone > 0.1);
    }

    #[test]
    fn test_state_transitions() {
        let config = VadConfig {
            energy_threshold: 0.01,
            zcr_threshold: 0.1,
            frame_size: 480,
            speech_frames_required: 2,
            silence_frames_required: 2,
        };

        let mut vad = VoiceActivityDetector::with_config(config);
        let speech = generate_tone(200.0, 480, 0.3);
        let silence = generate_silence(480);

        // Initial state
        assert_eq!(vad.state(), VadState::Silence);

        // First speech frame
        vad.process_frame(&speech).unwrap();
        assert_eq!(vad.state(), VadState::MaybeSpeech);

        // Second speech frame (confirms speech)
        vad.process_frame(&speech).unwrap();
        assert_eq!(vad.state(), VadState::Speech);

        // First silence frame
        vad.process_frame(&silence).unwrap();
        assert_eq!(vad.state(), VadState::MaybeSilence);

        // Second silence frame (confirms silence)
        vad.process_frame(&silence).unwrap();
        assert_eq!(vad.state(), VadState::Silence);
    }

    #[test]
    fn test_reset() {
        let mut vad = VoiceActivityDetector::new();
        let speech = generate_tone(200.0, 480, 0.3);

        // Trigger speech state
        for _ in 0..5 {
            vad.process_frame(&speech).unwrap();
        }
        assert!(vad.is_speech_active());

        // Reset
        vad.reset();
        assert_eq!(vad.state(), VadState::Silence);
        assert!(!vad.is_speech_active());
    }

    #[test]
    fn test_insufficient_data_error() {
        let mut vad = VoiceActivityDetector::new();
        let short_frame = vec![0; 100]; // Less than frame_size

        let result = vad.process_frame(&short_frame);
        assert!(result.is_err());

        match result {
            Err(VadError::InsufficientData(required)) => {
                assert_eq!(required, 480);
            }
            _ => panic!("Expected InsufficientData error"),
        }
    }

    #[test]
    fn test_false_alarm_handling() {
        let config = VadConfig {
            speech_frames_required: 3,
            ..Default::default()
        };

        let mut vad = VoiceActivityDetector::with_config(config);
        let speech = generate_tone(200.0, 480, 0.3);
        let silence = generate_silence(480);

        // One speech frame
        vad.process_frame(&speech).unwrap();
        assert_eq!(vad.state(), VadState::MaybeSpeech);

        // Followed by silence (false alarm)
        vad.process_frame(&silence).unwrap();
        assert_eq!(vad.state(), VadState::Silence);
        assert!(!vad.is_speech_active());
    }
}

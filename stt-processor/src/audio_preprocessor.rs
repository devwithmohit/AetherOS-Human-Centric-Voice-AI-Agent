/// Audio preprocessing module
///
/// Handles resampling, normalization, and format conversion for STT.
/// Ensures audio is in the correct format for Whisper (16kHz, mono, f32).

use thiserror::Error;
use tracing::{debug, trace, warn};

/// Target sample rate for Whisper (16kHz)
pub const WHISPER_SAMPLE_RATE: u32 = 16000;

/// Audio sample format (f32 normalized to -1.0 to 1.0)
pub type AudioSample = f32;

#[derive(Error, Debug)]
pub enum PreprocessorError {
    #[error("Invalid sample rate: {0} Hz (must be > 0)")]
    InvalidSampleRate(u32),

    #[error("Invalid channel count: {0} (must be 1 or 2)")]
    InvalidChannelCount(u16),

    #[error("Resampling failed: {0}")]
    ResamplingError(String),

    #[error("Empty audio buffer")]
    EmptyBuffer,

    #[error("Audio format conversion failed: {0}")]
    FormatConversionError(String),
}

/// Audio format specification
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AudioFormat {
    pub sample_rate: u32,
    pub channels: u16,
    pub bits_per_sample: u16,
}

impl AudioFormat {
    /// Create a new audio format
    pub fn new(sample_rate: u32, channels: u16, bits_per_sample: u16) -> Self {
        Self {
            sample_rate,
            channels,
            bits_per_sample,
        }
    }

    /// Whisper's expected format (16kHz, mono, 32-bit float)
    pub fn whisper_format() -> Self {
        Self {
            sample_rate: WHISPER_SAMPLE_RATE,
            channels: 1,
            bits_per_sample: 32,
        }
    }

    /// Validate format parameters
    pub fn validate(&self) -> Result<(), PreprocessorError> {
        if self.sample_rate == 0 {
            return Err(PreprocessorError::InvalidSampleRate(self.sample_rate));
        }

        if self.channels == 0 || self.channels > 2 {
            return Err(PreprocessorError::InvalidChannelCount(self.channels));
        }

        Ok(())
    }
}

/// Audio preprocessor for STT
pub struct AudioPreprocessor {
    input_format: AudioFormat,
    output_format: AudioFormat,
}

impl AudioPreprocessor {
    /// Create a new preprocessor
    pub fn new(input_format: AudioFormat) -> Result<Self, PreprocessorError> {
        input_format.validate()?;

        debug!(
            "Creating audio preprocessor: {}Hz, {} channels -> {}Hz mono",
            input_format.sample_rate, input_format.channels, WHISPER_SAMPLE_RATE
        );

        Ok(Self {
            input_format,
            output_format: AudioFormat::whisper_format(),
        })
    }

    /// Process audio samples (full pipeline)
    pub fn process(&self, samples: &[AudioSample]) -> Result<Vec<AudioSample>, PreprocessorError> {
        if samples.is_empty() {
            return Err(PreprocessorError::EmptyBuffer);
        }

        trace!("Processing {} input samples", samples.len());

        // Step 1: Convert to mono if needed
        let mono_samples = if self.input_format.channels == 2 {
            self.stereo_to_mono(samples)
        } else {
            samples.to_vec()
        };

        // Step 2: Resample if needed
        let resampled = if self.input_format.sample_rate != WHISPER_SAMPLE_RATE {
            self.resample(&mono_samples)?
        } else {
            mono_samples
        };

        // Step 3: Normalize
        let normalized = self.normalize(&resampled);

        debug!(
            "Preprocessed {} -> {} samples",
            samples.len(),
            normalized.len()
        );

        Ok(normalized)
    }

    /// Convert stereo to mono by averaging channels
    fn stereo_to_mono(&self, stereo: &[AudioSample]) -> Vec<AudioSample> {
        if stereo.len() % 2 != 0 {
            warn!("Stereo buffer has odd length, truncating last sample");
        }

        stereo
            .chunks_exact(2)
            .map(|pair| (pair[0] + pair[1]) / 2.0)
            .collect()
    }

    /// Resample audio to target sample rate
    fn resample(&self, samples: &[AudioSample]) -> Result<Vec<AudioSample>, PreprocessorError> {
        use rubato::{
            Resampler, SincFixedIn, SincInterpolationParameters, SincInterpolationType,
            WindowFunction,
        };

        let input_rate = self.input_format.sample_rate as usize;
        let output_rate = WHISPER_SAMPLE_RATE as usize;

        debug!("Resampling: {} Hz -> {} Hz", input_rate, output_rate);

        // Calculate resampling parameters
        let params = SincInterpolationParameters {
            sinc_len: 256,
            f_cutoff: 0.95,
            interpolation: SincInterpolationType::Linear,
            oversampling_factor: 256,
            window: WindowFunction::BlackmanHarris2,
        };

        // Create resampler
        let mut resampler = SincFixedIn::<f32>::new(
            output_rate as f64 / input_rate as f64,
            2.0,
            params,
            samples.len(),
            1, // mono
        )
        .map_err(|e| PreprocessorError::ResamplingError(e.to_string()))?;

        // Prepare input as 2D array (channels × samples)
        let input_waves = vec![samples.to_vec()];

        // Resample
        let output_waves = resampler
            .process(&input_waves, None)
            .map_err(|e| PreprocessorError::ResamplingError(e.to_string()))?;

        Ok(output_waves[0].clone())
    }

    /// Normalize audio to prevent clipping
    ///
    /// Ensures all samples are in the range [-1.0, 1.0]
    fn normalize(&self, samples: &[AudioSample]) -> Vec<AudioSample> {
        // Find peak amplitude
        let peak = samples
            .iter()
            .map(|&s| s.abs())
            .fold(0.0f32, f32::max);

        if peak == 0.0 {
            debug!("Silent audio detected, skipping normalization");
            return samples.to_vec();
        }

        if peak > 1.0 {
            // Normalize to prevent clipping
            let scale = 0.95 / peak; // Leave 5% headroom
            debug!("Normalizing audio: peak={:.3}, scale={:.3}", peak, scale);
            samples.iter().map(|&s| s * scale).collect()
        } else {
            // Already in valid range
            samples.to_vec()
        }
    }

    /// Convert i16 PCM samples to f32
    pub fn i16_to_f32(samples: &[i16]) -> Vec<AudioSample> {
        samples
            .iter()
            .map(|&s| s as f32 / i16::MAX as f32)
            .collect()
    }

    /// Convert f32 samples to i16 PCM
    pub fn f32_to_i16(samples: &[AudioSample]) -> Vec<i16> {
        samples
            .iter()
            .map(|&s| {
                let clamped = s.clamp(-1.0, 1.0);
                (clamped * i16::MAX as f32) as i16
            })
            .collect()
    }

    /// Get input format
    pub fn input_format(&self) -> AudioFormat {
        self.input_format
    }

    /// Get output format
    pub fn output_format(&self) -> AudioFormat {
        self.output_format
    }

    /// Calculate expected output length after resampling
    pub fn calculate_output_length(&self, input_length: usize) -> usize {
        let input_rate = self.input_format.sample_rate as f64;
        let output_rate = WHISPER_SAMPLE_RATE as f64;
        let ratio = output_rate / input_rate;

        (input_length as f64 * ratio) as usize
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    #[test]
    fn test_audio_format_validation() {
        let valid = AudioFormat::new(16000, 1, 16);
        assert!(valid.validate().is_ok());

        let invalid_rate = AudioFormat::new(0, 1, 16);
        assert!(invalid_rate.validate().is_err());

        let invalid_channels = AudioFormat::new(16000, 3, 16);
        assert!(invalid_channels.validate().is_err());
    }

    #[test]
    fn test_whisper_format() {
        let format = AudioFormat::whisper_format();
        assert_eq!(format.sample_rate, 16000);
        assert_eq!(format.channels, 1);
        assert_eq!(format.bits_per_sample, 32);
    }

    #[test]
    fn test_stereo_to_mono() {
        let format = AudioFormat::new(16000, 2, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let stereo = vec![0.5, 0.3, 0.2, 0.4];
        let mono = preprocessor.stereo_to_mono(&stereo);

        assert_eq!(mono.len(), 2);
        assert_relative_eq!(mono[0], 0.4, epsilon = 0.001);
        assert_relative_eq!(mono[1], 0.3, epsilon = 0.001);
    }

    #[test]
    fn test_normalize_clipping() {
        let format = AudioFormat::new(16000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        // Audio with values exceeding [-1, 1]
        let samples = vec![1.5, -2.0, 0.5];
        let normalized = preprocessor.normalize(&samples);

        // Should be scaled to fit in [-1, 1]
        assert!(normalized.iter().all(|&s| s >= -1.0 && s <= 1.0));
        assert!(normalized.iter().map(|&s| s.abs()).fold(0.0f32, f32::max) <= 0.95);
    }

    #[test]
    fn test_normalize_silent() {
        let format = AudioFormat::new(16000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let silent = vec![0.0; 100];
        let normalized = preprocessor.normalize(&silent);

        assert_eq!(normalized, silent);
    }

    #[test]
    fn test_i16_to_f32_conversion() {
        let i16_samples = vec![i16::MAX, 0, i16::MIN];
        let f32_samples = AudioPreprocessor::i16_to_f32(&i16_samples);

        assert_relative_eq!(f32_samples[0], 1.0, epsilon = 0.001);
        assert_relative_eq!(f32_samples[1], 0.0, epsilon = 0.001);
        assert_relative_eq!(f32_samples[2], -1.0, epsilon = 0.001);
    }

    #[test]
    fn test_f32_to_i16_conversion() {
        let f32_samples = vec![1.0, 0.0, -1.0];
        let i16_samples = AudioPreprocessor::f32_to_i16(&f32_samples);

        assert_eq!(i16_samples[0], i16::MAX);  // 32767
        assert_eq!(i16_samples[1], 0);
        assert_eq!(i16_samples[2], -i16::MAX); // -32767 (not -32768, which is i16::MIN)
    }

    #[test]
    fn test_f32_to_i16_clamping() {
        let f32_samples = vec![1.5, -2.0, 0.5];
        let i16_samples = AudioPreprocessor::f32_to_i16(&f32_samples);

        assert_eq!(i16_samples[0], i16::MAX);  // Clamped to 1.0
        assert_eq!(i16_samples[1], -i16::MAX); // Clamped to -1.0, then scaled
    }

    #[test]
    fn test_process_empty_buffer() {
        let format = AudioFormat::new(16000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let result = preprocessor.process(&[]);
        assert!(result.is_err());
    }

    #[test]
    fn test_process_no_conversion_needed() {
        // Already in correct format
        let format = AudioFormat::new(16000, 1, 32);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let samples = vec![0.1, 0.2, 0.3, 0.4];
        let processed = preprocessor.process(&samples).unwrap();

        // Should be similar (only normalized if needed)
        assert_eq!(processed.len(), samples.len());
    }

    #[test]
    fn test_calculate_output_length() {
        // 48kHz -> 16kHz: should be 1/3 the length
        let format = AudioFormat::new(48000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let output_len = preprocessor.calculate_output_length(48000);
        assert_eq!(output_len, 16000);
    }

    #[test]
    fn test_resample_upsampling() {
        // 8kHz -> 16kHz
        let format = AudioFormat::new(8000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let samples = vec![0.0; 8000]; // 1 second at 8kHz
        let resampled = preprocessor.resample(&samples).unwrap();

        // Should be approximately 16000 samples (1 second at 16kHz)
        // Rubato's SincFixedIn may produce slightly different lengths
        let expected = 16000;
        let tolerance = 500; // 3% tolerance
        assert!(
            (resampled.len() as i32 - expected).abs() < tolerance,
            "Expected ~{} samples, got {}",
            expected,
            resampled.len()
        );
    }

    #[test]
    fn test_resample_downsampling() {
        // 48kHz -> 16kHz
        let format = AudioFormat::new(48000, 1, 16);
        let preprocessor = AudioPreprocessor::new(format).unwrap();

        let samples = vec![0.0; 48000]; // 1 second at 48kHz
        let resampled = preprocessor.resample(&samples).unwrap();

        // Should be approximately 16000 samples (1 second at 16kHz)
        assert!((resampled.len() as i32 - 16000).abs() < 100);
    }
}

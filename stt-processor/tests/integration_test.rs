/// Integration tests for STT processor
///
/// Tests end-to-end transcription with real and synthetic audio.

use stt_processor::{
    AudioFormat, AudioPreprocessor, AudioSample, StreamingConfig, StreamingEvent,
    StreamingSTT, WhisperConfig, WhisperProcessor, WHISPER_SAMPLE_RATE,
};
use std::sync::Arc;
use test_case::test_case;

/// Generate test audio (sine wave)
fn generate_test_audio(duration_secs: f32, frequency: f32) -> Vec<AudioSample> {
    let num_samples = (WHISPER_SAMPLE_RATE as f32 * duration_secs) as usize;

    (0..num_samples)
        .map(|i| {
            let t = i as f32 / WHISPER_SAMPLE_RATE as f32;
            (2.0 * std::f32::consts::PI * frequency * t).sin() * 0.5
        })
        .collect()
}

/// Generate speech-like audio pattern
fn generate_speech_like_audio(duration_secs: f32) -> Vec<AudioSample> {
    let num_samples = (WHISPER_SAMPLE_RATE as f32 * duration_secs) as usize;

    (0..num_samples)
        .map(|i| {
            let t = i as f32 / WHISPER_SAMPLE_RATE as f32;

            // Mix multiple frequencies to simulate speech formants
            let f1 = (2.0 * std::f32::consts::PI * 500.0 * t).sin() * 0.3;
            let f2 = (2.0 * std::f32::consts::PI * 1500.0 * t).sin() * 0.2;
            let f3 = (2.0 * std::f32::consts::PI * 2500.0 * t).sin() * 0.1;

            // Add envelope
            let envelope = (t * 2.0).min(1.0) * ((duration_secs - t) * 2.0).max(0.0).min(1.0);

            (f1 + f2 + f3) * envelope
        })
        .collect()
}

#[test]
fn test_audio_preprocessor_creation() {
    let format = AudioFormat::new(16000, 1, 16);
    let preprocessor = AudioPreprocessor::new(format);

    assert!(preprocessor.is_ok());
    assert_eq!(preprocessor.unwrap().output_format().sample_rate, 16000);
}

#[test]
fn test_invalid_audio_format() {
    let invalid_format = AudioFormat::new(0, 1, 16);
    let result = AudioPreprocessor::new(invalid_format);

    assert!(result.is_err());
}

#[test_case(8000, 16000 ; "upsample_8k_to_16k")]
#[test_case(22050, 16000 ; "downsample_22k_to_16k")]
#[test_case(44100, 16000 ; "downsample_44k_to_16k")]
#[test_case(48000, 16000 ; "downsample_48k_to_16k")]
fn test_resampling_rates(input_rate: u32, expected_output_rate: u32) {
    let format = AudioFormat::new(input_rate, 1, 16);
    let preprocessor = AudioPreprocessor::new(format).unwrap();

    // 1 second of audio
    let input = vec![0.1f32; input_rate as usize];
    let output = preprocessor.process(&input).unwrap();

    // Check output is approximately correct length
    let expected_len = expected_output_rate as usize;
    let tolerance = (expected_len as f32 * 0.05) as usize; // 5% tolerance

    assert!(
        (output.len() as i32 - expected_len as i32).abs() < tolerance as i32,
        "Output length {} not within tolerance of expected {}",
        output.len(),
        expected_len
    );
}

#[test]
fn test_stereo_to_mono_conversion() {
    let format = AudioFormat::new(16000, 2, 16);
    let preprocessor = AudioPreprocessor::new(format).unwrap();

    // Stereo audio: left channel = 0.5, right channel = 0.3
    let stereo: Vec<f32> = (0..1000)
        .flat_map(|_| vec![0.5, 0.3])
        .collect();

    let mono = preprocessor.process(&stereo).unwrap();

    // Mono should be approximately 0.4 (average of 0.5 and 0.3)
    assert!(mono.len() > 0);
    let avg = mono.iter().sum::<f32>() / mono.len() as f32;
    assert!((avg - 0.4).abs() < 0.01);
}

#[test]
fn test_normalization() {
    let format = AudioFormat::new(16000, 1, 16);
    let preprocessor = AudioPreprocessor::new(format).unwrap();

    // Audio with values exceeding [-1, 1]
    let audio = vec![1.5, -2.0, 0.8, -1.2];
    let normalized = preprocessor.process(&audio).unwrap();

    // All values should be in [-1, 1]
    assert!(normalized.iter().all(|&v| v >= -1.0 && v <= 1.0));

    // Peak should be close to 0.95 (with 5% headroom)
    let peak = normalized.iter().map(|&v| v.abs()).fold(0.0f32, f32::max);
    assert!(peak <= 0.96);
}

#[test]
fn test_i16_f32_conversion_roundtrip() {
    let original_i16: Vec<i16> = vec![i16::MIN, -1000, 0, 1000, i16::MAX];

    // i16 -> f32 -> i16
    let f32_samples = AudioPreprocessor::i16_to_f32(&original_i16);
    let roundtrip_i16 = AudioPreprocessor::f32_to_i16(&f32_samples);

    // Should be approximately equal (small precision loss is acceptable)
    for (original, roundtrip) in original_i16.iter().zip(roundtrip_i16.iter()) {
        let diff = (*original as i32 - *roundtrip as i32).abs();
        assert!(diff <= 1, "Conversion error too large: {} vs {}", original, roundtrip);
    }
}

#[test]
fn test_empty_audio_handling() {
    let format = AudioFormat::new(16000, 1, 16);
    let preprocessor = AudioPreprocessor::new(format).unwrap();

    let empty: Vec<f32> = vec![];
    let result = preprocessor.process(&empty);

    assert!(result.is_err());
}

#[test]
fn test_whisper_config_default() {
    let config = WhisperConfig::default();

    assert_eq!(config.language, "en");
    assert!(!config.translate);
    assert!(config.num_threads > 0);
    assert!(!config.print_progress);
}

#[test]
#[cfg(feature = "whisper")]
fn test_whisper_config_validation_missing_model() {
    let config = WhisperConfig {
        model_path: "nonexistent.bin".into(),
        ..Default::default()
    };

    assert!(config.validate().is_err());
}

#[test]
fn test_whisper_config_validation_invalid_threads() {
    let mut config = WhisperConfig::default();
    config.num_threads = 0;

    assert!(config.validate().is_err());
}

#[test]
fn test_streaming_config_default() {
    let config = StreamingConfig::default();

    assert_eq!(config.chunk_duration_ms, 500);
    assert_eq!(config.overlap_ms, 50);
    assert!(config.enable_partial_results);
    assert!(config.max_queue_size > 0);
}

#[test]
fn test_chunk_size_calculations() {
    let config = StreamingConfig::default();

    // 500ms at 16kHz = 8000 samples
    let chunk_samples = (config.chunk_duration_ms * 16) as usize;
    assert_eq!(chunk_samples, 8000);

    // 50ms at 16kHz = 800 samples
    let overlap_samples = (config.overlap_ms * 16) as usize;
    assert_eq!(overlap_samples, 800);
}

// Note: Tests requiring Whisper model are commented out
// Uncomment when model file is available

/*
#[tokio::test]
async fn test_whisper_transcription_basic() {
    let config = WhisperConfig::default();
    let whisper = WhisperProcessor::new(config).unwrap();

    // Generate 1 second of test audio
    let audio = generate_test_audio(1.0, 440.0);

    let result = whisper.transcribe(&audio);
    assert!(result.is_ok());

    let transcription = result.unwrap();
    assert!(transcription.processing_time_ms > 0);
    assert!(transcription.confidence >= 0.0 && transcription.confidence <= 1.0);
}

#[tokio::test]
async fn test_whisper_latency_requirement() {
    let config = WhisperConfig::default();
    let whisper = WhisperProcessor::new(config).unwrap();

    // Generate 10 seconds of audio
    let audio = generate_speech_like_audio(10.0);

    let start = std::time::Instant::now();
    let result = whisper.transcribe(&audio).unwrap();
    let elapsed = start.elapsed();

    println!("Transcribed 10s audio in {:.2}s", elapsed.as_secs_f32());
    println!("Transcription: {}", result.text);
    println!("Confidence: {:.2}", result.confidence);

    // Requirement: <2s for 10s audio
    assert!(elapsed.as_secs() < 2, "Transcription too slow: {:.2}s", elapsed.as_secs_f32());
}

#[tokio::test]
async fn test_streaming_stt_basic() {
    let config = WhisperConfig::default();
    let whisper = Arc::new(WhisperProcessor::new(config).unwrap());

    let input_format = AudioFormat::whisper_format();
    let streaming_config = StreamingConfig::default();

    let streaming_stt = StreamingSTT::new(whisper, input_format, streaming_config).unwrap();

    streaming_stt.start().await.unwrap();

    // Process chunks of audio
    for _ in 0..5 {
        let chunk = generate_test_audio(0.5, 440.0); // 500ms chunks
        let result = streaming_stt.process_chunk(&chunk).await;

        if let Ok(Some(event)) = result {
            match event {
                StreamingEvent::Partial { text, confidence, .. } => {
                    println!("Partial: {} (conf: {:.2})", text, confidence);
                }
                StreamingEvent::Final { text, confidence, .. } => {
                    println!("Final: {} (conf: {:.2})", text, confidence);
                }
                _ => {}
            }
        }
    }

    streaming_stt.stop().await.unwrap();
}

#[tokio::test]
async fn test_streaming_stats() {
    let config = WhisperConfig::default();
    let whisper = Arc::new(WhisperProcessor::new(config).unwrap());

    let input_format = AudioFormat::whisper_format();
    let streaming_config = StreamingConfig::default();

    let streaming_stt = StreamingSTT::new(whisper, input_format, streaming_config).unwrap();

    streaming_stt.start().await.unwrap();

    let chunk = generate_test_audio(0.5, 440.0);
    let _ = streaming_stt.process_chunk(&chunk).await;

    let stats = streaming_stt.stats().await;
    assert!(stats.is_active);
    assert!(stats.total_samples_processed > 0);

    streaming_stt.stop().await.unwrap();
}
*/

#[test]
fn test_audio_generation_functions() {
    let audio1 = generate_test_audio(1.0, 440.0);
    assert_eq!(audio1.len(), 16000); // 1 second at 16kHz

    let audio2 = generate_speech_like_audio(1.0);
    assert_eq!(audio2.len(), 16000);

    // Check audio is not silent
    let rms1: f32 = audio1.iter().map(|&s| s * s).sum::<f32>() / audio1.len() as f32;
    assert!(rms1.sqrt() > 0.01);

    let rms2: f32 = audio2.iter().map(|&s| s * s).sum::<f32>() / audio2.len() as f32;
    assert!(rms2.sqrt() > 0.01);
}

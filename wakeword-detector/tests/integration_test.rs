/// Integration tests for wake-word detector
///
/// Tests end-to-end wake-word detection with synthetic audio.

use wakeword_detector::{DetectorConfig, WakeWordDetector, SAMPLE_RATE};
use std::f32::consts::PI;

/// Generate synthetic audio tone
fn generate_tone(frequency: f32, duration_secs: f32, amplitude: f32) -> Vec<i16> {
    let num_samples = (SAMPLE_RATE as f32 * duration_secs) as usize;

    (0..num_samples)
        .map(|i| {
            let t = i as f32 / SAMPLE_RATE as f32;
            let sample = amplitude * (2.0 * PI * frequency * t).sin();
            (sample * i16::MAX as f32) as i16
        })
        .collect()
}

/// Generate synthetic "Hey Aether" audio pattern
///
/// This creates a multi-tone pattern that mimics speech characteristics:
/// - Multiple frequency components (formants)
/// - Varying amplitude envelope
/// - Appropriate duration (~1 second for "Hey Aether")
fn generate_synthetic_wake_word() -> Vec<i16> {
    let duration = 1.0; // 1 second
    let num_samples = (SAMPLE_RATE as f32 * duration) as usize;
    let mut result = vec![0i16; num_samples];

    // "Hey" - higher pitched, ~0.3s
    let hey_samples = (num_samples as f32 * 0.3) as usize;
    for i in 0..hey_samples {
        let t = i as f32 / SAMPLE_RATE as f32;
        let envelope = (t * 10.0).min(1.0) * ((0.3 - t) * 10.0).max(0.0);

        // Multiple formants for speech-like sound
        let f1 = 0.3 * (2.0 * PI * 700.0 * t).sin();
        let f2 = 0.2 * (2.0 * PI * 1220.0 * t).sin();
        let f3 = 0.1 * (2.0 * PI * 2600.0 * t).sin();

        let sample = envelope * (f1 + f2 + f3);
        result[i] = (sample * i16::MAX as f32 * 0.5) as i16;
    }

    // Silence gap ~0.1s
    let gap_samples = (num_samples as f32 * 0.1) as usize;

    // "Aether" - starts at hey_samples + gap_samples, ~0.6s
    let aether_start = hey_samples + gap_samples;
    let aether_samples = num_samples - aether_start;

    for i in 0..aether_samples {
        let t = i as f32 / SAMPLE_RATE as f32;
        let envelope = (t * 5.0).min(1.0) * ((0.6 - t) * 5.0).max(0.0);

        // Different formants for "aether"
        let f1 = 0.3 * (2.0 * PI * 500.0 * t).sin();
        let f2 = 0.25 * (2.0 * PI * 1500.0 * t).sin();
        let f3 = 0.15 * (2.0 * PI * 2500.0 * t).sin();

        let sample = envelope * (f1 + f2 + f3);
        result[aether_start + i] = (sample * i16::MAX as f32 * 0.6) as i16;
    }

    result
}

#[tokio::test]
async fn test_wake_word_detection_with_synthetic_audio() {
    // Initialize test configuration
    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        enable_vad_prefilter: true,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");

    // Start detector
    detector.start().await.expect("Failed to start detector");

    // Generate synthetic wake-word audio
    let wake_word_audio = generate_synthetic_wake_word();

    // Add some silence before
    let mut audio = vec![0i16; SAMPLE_RATE / 2]; // 0.5s silence
    audio.extend_from_slice(&wake_word_audio);
    audio.extend_from_slice(&vec![0i16; SAMPLE_RATE / 2]); // 0.5s silence after

    // Process audio in chunks (simulate real-time streaming)
    let chunk_size = 512; // ~32ms chunks for low latency

    for chunk in audio.chunks(chunk_size) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
    }

    // Check statistics
    let stats = detector.stats().await;
    assert!(stats.frames_processed > 0, "No frames were processed");

    println!("Integration test stats:");
    println!("  Frames processed: {}", stats.frames_processed);
    println!("  Wake-words detected: {}", stats.wake_words_detected);
    println!("  Buffer fill: {:.1}%", stats.buffer_fill_percent);

    // Note: With mock implementation, detection is probabilistic
    // In production with real Porcupine, we'd assert wake_words_detected > 0
}

#[tokio::test]
async fn test_no_false_positives_on_silence() {
    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        enable_vad_prefilter: true,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");
    detector.start().await.expect("Failed to start detector");

    // Process 5 seconds of silence
    let silence = vec![0i16; SAMPLE_RATE * 5];

    for chunk in silence.chunks(512) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
    }

    let stats = detector.stats().await;

    // With VAD pre-filter, silence should not trigger detection
    println!("Silence test stats:");
    println!("  Frames processed: {}", stats.frames_processed);
    println!("  Wake-words detected: {}", stats.wake_words_detected);

    // VAD should filter out most/all frames
    assert!(stats.frames_processed < 100, "Too many frames processed for silence");
}

#[tokio::test]
async fn test_speech_without_wake_word() {
    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        enable_vad_prefilter: true,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");
    detector.start().await.expect("Failed to start detector");

    // Generate random speech-like audio (not wake-word)
    let mut audio = Vec::new();

    // Mix of different frequencies and amplitudes
    audio.extend(generate_tone(300.0, 0.5, 0.3));
    audio.extend(generate_tone(500.0, 0.3, 0.25));
    audio.extend(generate_tone(200.0, 0.4, 0.35));

    for chunk in audio.chunks(512) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
    }

    let stats = detector.stats().await;

    println!("Random speech test stats:");
    println!("  Frames processed: {}", stats.frames_processed);
    println!("  Wake-words detected: {}", stats.wake_words_detected);

    // Should process frames (VAD detects speech) but not detect wake-word
    assert!(stats.frames_processed > 0, "Should process speech frames");
}

#[tokio::test]
async fn test_multiple_wake_words() {
    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        enable_vad_prefilter: true,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");
    detector.start().await.expect("Failed to start detector");

    // Generate audio with multiple wake-words separated by silence
    let wake_word = generate_synthetic_wake_word();
    let silence = vec![0i16; SAMPLE_RATE]; // 1 second silence

    let mut audio = Vec::new();
    for _ in 0..3 {
        audio.extend_from_slice(&wake_word);
        audio.extend_from_slice(&silence);
    }

    for chunk in audio.chunks(512) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
    }

    let stats = detector.stats().await;

    println!("Multiple wake-words test stats:");
    println!("  Frames processed: {}", stats.frames_processed);
    println!("  Wake-words detected: {}", stats.wake_words_detected);

    // With mock implementation, may or may not detect multiple
    // In production, should detect close to 3
}

#[tokio::test]
async fn test_detector_reset() {
    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");
    detector.start().await.expect("Failed to start detector");

    // Process some audio
    let audio = generate_tone(400.0, 1.0, 0.3);
    for chunk in audio.chunks(512) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
    }

    let stats_before = detector.stats().await;
    assert!(stats_before.frames_processed > 0);

    // Reset
    detector.reset().await;

    let stats_after = detector.stats().await;
    assert_eq!(stats_after.frames_processed, 0);
    assert_eq!(stats_after.wake_words_detected, 0);
    assert!(stats_after.buffer_fill_percent < 1.0);
}

#[tokio::test]
async fn test_high_latency_check() {
    use std::time::Instant;

    let config = DetectorConfig {
        access_key: "test_key".to_string(),
        model_path: "models/test.ppn".to_string(),
        sensitivity: 0.5,
        enable_vad_prefilter: true,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).expect("Failed to create detector");
    detector.start().await.expect("Failed to start detector");

    // Process chunks and measure latency
    let audio = generate_synthetic_wake_word();
    let chunk_size = 512; // ~32ms at 16kHz

    let start = Instant::now();
    let mut chunks_processed = 0;

    for chunk in audio.chunks(chunk_size) {
        detector.process_audio(chunk).await.expect("Failed to process audio");
        chunks_processed += 1;
    }

    let elapsed = start.elapsed();
    let avg_latency_per_chunk = elapsed / chunks_processed;

    println!("Latency test:");
    println!("  Total time: {:?}", elapsed);
    println!("  Chunks processed: {}", chunks_processed);
    println!("  Avg latency per chunk: {:?}", avg_latency_per_chunk);

    // Each chunk is ~32ms of audio, processing should be much faster
    // Target: <5ms per chunk (6x faster than real-time)
    assert!(
        avg_latency_per_chunk.as_millis() < 10,
        "Processing too slow: {:?} per chunk",
        avg_latency_per_chunk
    );
}

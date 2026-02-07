/// Transcription benchmarks
///
/// Measures latency and throughput of STT processing.

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use stt_processor::{AudioFormat, AudioPreprocessor, AudioSample, WHISPER_SAMPLE_RATE};
use std::time::Duration;

/// Generate synthetic audio for benchmarking
fn generate_audio(duration_secs: f32) -> Vec<AudioSample> {
    let num_samples = (WHISPER_SAMPLE_RATE as f32 * duration_secs) as usize;

    // Generate a simple sine wave
    (0..num_samples)
        .map(|i| {
            let t = i as f32 / WHISPER_SAMPLE_RATE as f32;
            let freq = 440.0; // A4 note
            (2.0 * std::f32::consts::PI * freq * t).sin() * 0.3
        })
        .collect()
}

fn bench_audio_preprocessing(c: &mut Criterion) {
    let mut group = c.benchmark_group("audio_preprocessing");

    // Test different input sample rates
    for &sample_rate in &[8000u32, 16000, 22050, 44100, 48000] {
        let input_format = AudioFormat::new(sample_rate, 1, 16);
        let preprocessor = AudioPreprocessor::new(input_format).unwrap();

        // 1 second of audio
        let audio = vec![0.0f32; sample_rate as usize];

        group.bench_with_input(
            BenchmarkId::new("resample", format!("{}Hz", sample_rate)),
            &audio,
            |b, audio| {
                b.iter(|| {
                    let result = preprocessor.process(black_box(audio)).unwrap();
                    black_box(result);
                });
            },
        );
    }

    group.finish();
}

fn bench_stereo_to_mono(c: &mut Criterion) {
    let mut group = c.benchmark_group("stereo_conversion");

    let input_format = AudioFormat::new(16000, 2, 16);
    let preprocessor = AudioPreprocessor::new(input_format).unwrap();

    // 1 second of stereo audio
    let stereo_audio = vec![0.1f32; 16000 * 2];

    group.bench_function("stereo_to_mono_1s", |b| {
        b.iter(|| {
            let result = preprocessor.process(black_box(&stereo_audio)).unwrap();
            black_box(result);
        });
    });

    group.finish();
}

fn bench_normalization(c: &mut Criterion) {
    let mut group = c.benchmark_group("normalization");

    let input_format = AudioFormat::new(16000, 1, 16);
    let preprocessor = AudioPreprocessor::new(input_format).unwrap();

    for &duration_secs in &[1.0, 5.0, 10.0] {
        let audio = generate_audio(duration_secs);

        group.bench_with_input(
            BenchmarkId::new("normalize", format!("{}s", duration_secs)),
            &audio,
            |b, audio| {
                b.iter(|| {
                    let result = preprocessor.process(black_box(audio)).unwrap();
                    black_box(result);
                });
            },
        );
    }

    group.finish();
}

fn bench_format_conversion(c: &mut Criterion) {
    let mut group = c.benchmark_group("format_conversion");

    // i16 to f32 conversion
    let i16_samples: Vec<i16> = (0..16000).map(|i| (i % 100) as i16).collect();

    group.bench_function("i16_to_f32_1s", |b| {
        b.iter(|| {
            let result = AudioPreprocessor::i16_to_f32(black_box(&i16_samples));
            black_box(result);
        });
    });

    // f32 to i16 conversion
    let f32_samples: Vec<f32> = (0..16000).map(|i| ((i % 100) as f32 / 100.0)).collect();

    group.bench_function("f32_to_i16_1s", |b| {
        b.iter(|| {
            let result = AudioPreprocessor::f32_to_i16(black_box(&f32_samples));
            black_box(result);
        });
    });

    group.finish();
}

// Note: Whisper transcription benchmarks require model file
// Commented out to avoid test failures without model
/*
fn bench_whisper_transcription(c: &mut Criterion) {
    use stt_processor::{WhisperConfig, WhisperProcessor};
    use std::sync::Arc;

    let config = WhisperConfig::default();
    let whisper = Arc::new(WhisperProcessor::new(config).unwrap());

    let mut group = c.benchmark_group("whisper_transcription");
    group.measurement_time(Duration::from_secs(30)); // Longer measurement time

    for &duration_secs in &[1.0, 5.0, 10.0] {
        let audio = generate_audio(duration_secs);

        group.bench_with_input(
            BenchmarkId::new("transcribe", format!("{}s", duration_secs)),
            &audio,
            |b, audio| {
                b.iter(|| {
                    let result = whisper.transcribe(black_box(audio)).unwrap();
                    black_box(result);
                });
            },
        );
    }

    group.finish();
}
*/

criterion_group!(
    benches,
    bench_audio_preprocessing,
    bench_stereo_to_mono,
    bench_normalization,
    bench_format_conversion,
    // bench_whisper_transcription, // Uncomment when model is available
);

criterion_main!(benches);

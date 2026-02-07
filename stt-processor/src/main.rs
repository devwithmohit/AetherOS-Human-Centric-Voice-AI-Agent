/// STT Service binary
///
/// Standalone speech-to-text service with gRPC interface.

use stt_processor::{
    AudioFormat, StreamingConfig, StreamingSTT, WhisperConfig, WhisperProcessor,
};
use std::sync::Arc;
use tracing::{error, info};
use tracing_subscriber;

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("stt_processor=info".parse().unwrap()),
        )
        .init();

    info!("Starting AetherOS STT Service");

    // Load configuration
    let whisper_config = match load_whisper_config() {
        Ok(cfg) => cfg,
        Err(e) => {
            error!("Failed to load Whisper configuration: {}", e);
            std::process::exit(1);
        }
    };

    // Create Whisper processor
    let whisper = match WhisperProcessor::new(whisper_config.clone()) {
        Ok(w) => Arc::new(w),
        Err(e) => {
            error!("Failed to create Whisper processor: {}", e);
            std::process::exit(1);
        }
    };

    info!("Whisper model loaded: {:?}", whisper_config.model_path);
    info!("Language: {}, Threads: {}", whisper_config.language, whisper_config.num_threads);

    // Create streaming STT
    let input_format = AudioFormat::whisper_format();
    let streaming_config = StreamingConfig::default();

    let streaming_stt = match StreamingSTT::new(whisper, input_format, streaming_config) {
        Ok(stt) => stt,
        Err(e) => {
            error!("Failed to create streaming STT: {}", e);
            std::process::exit(1);
        }
    };

    info!("STT service initialized successfully");
    info!("Ready to process audio");

    // In production: start gRPC server here
    // For now: keep service running
    tokio::signal::ctrl_c().await.expect("Failed to listen for Ctrl+C");

    info!("Shutting down STT service");
}

/// Load Whisper configuration from environment
fn load_whisper_config() -> Result<WhisperConfig, Box<dyn std::error::Error>> {
    let model_path = std::env::var("WHISPER_MODEL_PATH")
        .unwrap_or_else(|_| "models/ggml-base.en.bin".to_string());

    let language = std::env::var("WHISPER_LANGUAGE").unwrap_or_else(|_| "en".to_string());

    let num_threads = std::env::var("WHISPER_THREADS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or_else(|| std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4));

    let use_gpu = std::env::var("WHISPER_USE_GPU")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(true);

    Ok(WhisperConfig {
        model_path: model_path.into(),
        language,
        num_threads,
        use_gpu,
        translate: false,
        print_progress: false,
        max_segment_length: 1000,
    })
}

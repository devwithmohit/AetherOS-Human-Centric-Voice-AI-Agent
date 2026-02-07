/// Wake-word detection service binary
///
/// Standalone service that listens for the "Hey Aether" wake-word.

use tracing::{error, info};
use tracing_subscriber;
use wakeword_detector::{DetectorConfig, WakeWordDetector};

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("wakeword_detector=debug".parse().unwrap())
        )
        .init();

    info!("Starting AetherOS Wake-word Detection Service");

    // Load configuration
    let config = match load_config() {
        Ok(cfg) => cfg,
        Err(e) => {
            error!("Failed to load configuration: {}", e);
            std::process::exit(1);
        }
    };

    // Create detector
    let detector = match WakeWordDetector::new(config) {
        Ok(det) => det,
        Err(e) => {
            error!("Failed to create detector: {}", e);
            std::process::exit(1);
        }
    };

    // Start detector
    if let Err(e) = detector.start().await {
        error!("Failed to start detector: {}", e);
        std::process::exit(1);
    }

    info!("Wake-word detector running. Listening for 'Hey Aether'...");

    // Event loop
    loop {
        match detector.recv_event().await {
            Some(event) => {
                info!(
                    "Wake-word detected! confidence={:.2}, timestamp={}",
                    event.confidence, event.timestamp
                );

                // In production: send event to Agent Core via gRPC
                // For now: just log
            }
            None => {
                info!("Event channel closed, shutting down");
                break;
            }
        }
    }

    // Cleanup
    if let Err(e) = detector.stop().await {
        error!("Error stopping detector: {}", e);
    }

    info!("Wake-word detection service stopped");
}

/// Load configuration from environment or config file
fn load_config() -> Result<DetectorConfig, Box<dyn std::error::Error>> {
    // In production: load from config file or environment
    // For now: use defaults with placeholder access key

    let access_key = std::env::var("PORCUPINE_ACCESS_KEY")
        .unwrap_or_else(|_| {
            eprintln!("Warning: PORCUPINE_ACCESS_KEY not set, using test key");
            "test_key".to_string()
        });

    let model_path = std::env::var("WAKEWORD_MODEL_PATH")
        .unwrap_or_else(|_| "models/aether.ppn".to_string());

    let sensitivity = std::env::var("WAKEWORD_SENSITIVITY")
        .unwrap_or_else(|_| "0.5".to_string())
        .parse::<f32>()?;

    Ok(DetectorConfig {
        access_key,
        model_path,
        sensitivity,
        ..Default::default()
    })
}

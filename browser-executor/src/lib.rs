//! Browser Executor - Secure browser automation with sandboxing
//!
//! This library provides secure browser automation capabilities with:
//! - Headless Chrome automation via chromiumoxide
//! - Resource limits (CPU, memory, time)
//! - Process isolation with nsjail (Linux)
//! - Screenshot capture
//! - Error recovery and automatic browser restart

pub mod actions;
pub mod executor;
pub mod sandbox;
pub mod screenshot;

pub use actions::{ActionExecutor, ActionOutput, ActionResult, BrowserAction, WaitCondition};
pub use executor::{BrowserExecutor, ExecutorConfig, ExecutorStats};
pub use sandbox::{MountPoint, SandboxConfig, SandboxedProcess};
pub use screenshot::{Screenshot, ScreenshotCapturer, ScreenshotFormat, ScreenshotOptions};

use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

/// Initialize logging
pub fn init_logging() {
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "browser_executor=info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_library_exports() {
        // Verify all public exports are accessible
        let _config = ExecutorConfig::default();
        let _sandbox_config = SandboxConfig::default();
        let _screenshot_opts = ScreenshotOptions::default();
    }
}

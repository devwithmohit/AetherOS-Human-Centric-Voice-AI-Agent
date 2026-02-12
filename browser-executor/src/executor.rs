//! Browser executor with resource limits and error recovery

use crate::actions::{ActionExecutor, ActionOutput, ActionResult, BrowserAction};
use chromiumoxide::browser::{Browser, BrowserConfig};
use chromiumoxide::page::Page;
use futures::StreamExt;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

/// Browser executor errors
#[derive(Error, Debug)]
pub enum ExecutorError {
    #[error("Failed to launch browser: {0}")]
    LaunchFailed(String),

    #[error("Browser crashed: {0}")]
    BrowserCrashed(String),

    #[error("Page error: {0}")]
    PageError(String),

    #[error("Timeout exceeded: {0}")]
    Timeout(String),

    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),

    #[error("Action failed: {0}")]
    ActionFailed(String),
}

/// Browser executor configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutorConfig {
    /// Maximum memory usage (MB)
    pub max_memory_mb: u64,

    /// Maximum execution time (seconds)
    pub max_execution_time_secs: u64,

    /// Default action timeout (seconds)
    pub default_timeout_secs: u64,

    /// Headless mode
    pub headless: bool,

    /// Disable images
    pub disable_images: bool,

    /// Disable JavaScript
    pub disable_javascript: bool,

    /// User agent string
    pub user_agent: Option<String>,

    /// Viewport width
    pub viewport_width: u32,

    /// Viewport height
    pub viewport_height: u32,

    /// Enable sandboxing
    pub enable_sandbox: bool,
}

impl Default for ExecutorConfig {
    fn default() -> Self {
        Self {
            max_memory_mb: 512,
            max_execution_time_secs: 30,
            default_timeout_secs: 10,
            headless: true,
            disable_images: false,
            disable_javascript: false,
            user_agent: Some(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36".to_string(),
            ),
            viewport_width: 1920,
            viewport_height: 1080,
            enable_sandbox: true,
        }
    }
}

/// Browser execution statistics
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ExecutorStats {
    pub total_actions: u64,
    pub successful_actions: u64,
    pub failed_actions: u64,
    pub crashes: u64,
    pub restarts: u64,
    pub total_execution_time_ms: u64,
}

/// Browser executor with automatic recovery
pub struct BrowserExecutor {
    config: ExecutorConfig,
    browser: Arc<RwLock<Option<Browser>>>,
    current_page: Arc<RwLock<Option<Page>>>,
    stats: Arc<RwLock<ExecutorStats>>,
}

impl BrowserExecutor {
    /// Create new browser executor
    pub async fn new(config: ExecutorConfig) -> Result<Self, ExecutorError> {
        let executor = Self {
            config,
            browser: Arc::new(RwLock::new(None)),
            current_page: Arc::new(RwLock::new(None)),
            stats: Arc::new(RwLock::new(ExecutorStats::default())),
        };

        executor.launch_browser().await?;

        Ok(executor)
    }

    /// Execute a browser action
    pub async fn execute(&self, action: BrowserAction) -> Result<ActionOutput, ExecutorError> {
        let start = std::time::Instant::now();

        // Update stats
        {
            let mut stats = self.stats.write().await;
            stats.total_actions += 1;
        }

        // Ensure browser is running
        if !self.is_browser_alive().await {
            warn!("Browser not alive, restarting...");
            self.restart_browser().await?;
        }

        // Execute action
        let result = self.execute_with_timeout(action.clone()).await;

        // Update stats
        {
            let mut stats = self.stats.write().await;
            stats.total_execution_time_ms += start.elapsed().as_millis() as u64;

            match &result {
                Ok(_) => stats.successful_actions += 1,
                Err(_) => stats.failed_actions += 1,
            }
        }

        match result {
            Ok(output) => Ok(output),
            Err(e) => {
                error!("Action failed: {}", e);
                Err(ExecutorError::ActionFailed(e.to_string()))
            }
        }
    }

    /// Execute action with timeout
    async fn execute_with_timeout(
        &self,
        action: BrowserAction,
    ) -> ActionResult<ActionOutput> {
        let timeout = Duration::from_secs(self.config.max_execution_time_secs);

        tokio::time::timeout(timeout, self.execute_action(action))
            .await
            .map_err(|_| {
                crate::actions::ActionError::ActionFailed("Execution timeout".to_string())
            })?
    }

    /// Execute action on current page
    async fn execute_action(&self, action: BrowserAction) -> ActionResult<ActionOutput> {
        let page_lock = self.current_page.read().await;

        let page = page_lock
            .as_ref()
            .ok_or(crate::actions::ActionError::BrowserError(
                "No page available".to_string(),
            ))?
            .clone();

        drop(page_lock);

        let mut executor = ActionExecutor::new(
            page,
            Duration::from_secs(self.config.default_timeout_secs),
        );

        executor.execute(action).await
    }

    /// Launch browser
    async fn launch_browser(&self) -> Result<(), ExecutorError> {
        info!("Launching browser...");

        let mut config_builder = BrowserConfig::builder();

        // Set headless mode
        if self.config.headless {
            config_builder = config_builder.with_head();
        }

        // Set viewport
        config_builder = config_builder.viewport(chromiumoxide::handler::viewport::Viewport {
            width: self.config.viewport_width,
            height: self.config.viewport_height,
            device_scale_factor: Some(1.0),
            emulating_mobile: false,
            is_landscape: false,
            has_touch: false,
        });

        // Build config
        let config = config_builder.build().map_err(|e| {
            ExecutorError::LaunchFailed(format!("Failed to build config: {}", e))
        })?;

        // Launch browser
        let (browser, mut handler) = Browser::launch(config)
            .await
            .map_err(|e| ExecutorError::LaunchFailed(e.to_string()))?;

        // Spawn handler
        let _handle = tokio::task::spawn(async move {
            while let Some(event) = handler.next().await {
                debug!("Browser event: {:?}", event);
            }
        });

        // Create new page
        let page = browser
            .new_page("about:blank")
            .await
            .map_err(|e| ExecutorError::PageError(e.to_string()))?;

        // Set user agent if specified
        if let Some(user_agent) = &self.config.user_agent {
            page.set_user_agent(user_agent)
                .await
                .map_err(|e| ExecutorError::PageError(e.to_string()))?;
        }

        // Store browser and page
        *self.browser.write().await = Some(browser);
        *self.current_page.write().await = Some(page);

        info!("Browser launched successfully");

        Ok(())
    }

    /// Check if browser is alive
    async fn is_browser_alive(&self) -> bool {
        let browser_lock = self.browser.read().await;

        if let Some(_browser) = browser_lock.as_ref() {
            // Try to get page
            let page_lock = self.current_page.read().await;
            page_lock.is_some()
        } else {
            false
        }
    }

    /// Restart browser after crash
    async fn restart_browser(&self) -> Result<(), ExecutorError> {
        warn!("Restarting browser...");

        // Update crash stats
        {
            let mut stats = self.stats.write().await;
            stats.crashes += 1;
            stats.restarts += 1;
        }

        // Close existing browser
        self.close_browser().await;

        // Launch new browser
        self.launch_browser().await?;

        info!("Browser restarted successfully");

        Ok(())
    }

    /// Close browser
    async fn close_browser(&self) {
        debug!("Closing browser...");

        // Clear page
        *self.current_page.write().await = None;

        // Close browser
        let mut browser_lock = self.browser.write().await;
        if let Some(mut browser) = browser_lock.take() {
            if let Err(e) = browser.close().await {
                warn!("Failed to close browser gracefully: {}", e);
            }
        }
    }

    /// Get executor statistics
    pub async fn get_stats(&self) -> ExecutorStats {
        self.stats.read().await.clone()
    }

    /// Get current page URL
    pub async fn get_current_url(&self) -> Option<String> {
        let page_lock = self.current_page.read().await;

        if let Some(page) = page_lock.as_ref() {
            page.url().await.ok().flatten()
        } else {
            None
        }
    }

    /// Close and cleanup
    pub async fn shutdown(&self) {
        info!("Shutting down browser executor...");
        self.close_browser().await;
    }
}

impl Drop for BrowserExecutor {
    fn drop(&mut self) {
        debug!("BrowserExecutor dropped");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_executor_creation() {
        let config = ExecutorConfig::default();
        let executor = BrowserExecutor::new(config).await;

        assert!(executor.is_ok());
    }

    #[tokio::test]
    async fn test_browser_alive() {
        let config = ExecutorConfig::default();
        let executor = BrowserExecutor::new(config).await.unwrap();

        assert!(executor.is_browser_alive().await);
    }
}

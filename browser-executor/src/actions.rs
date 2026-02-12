//! Browser action primitives for web automation

use chromiumoxide::element::Element;
use chromiumoxide::page::Page;
use chromiumoxide::cdp::browser_protocol::page::CaptureScreenshotParams;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use thiserror::Error;

/// Browser action errors
#[derive(Error, Debug)]
pub enum ActionError {
    #[error("Element not found: {0}")]
    ElementNotFound(String),

    #[error("Timeout waiting for element: {0}")]
    Timeout(String),

    #[error("Invalid selector: {0}")]
    InvalidSelector(String),

    #[error("Action failed: {0}")]
    ActionFailed(String),

    #[error("Navigation failed: {0}")]
    NavigationFailed(String),

    #[error("Browser error: {0}")]
    BrowserError(String),
}

/// Result type for actions
pub type ActionResult<T> = Result<T, ActionError>;

/// Browser action types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum BrowserAction {
    /// Navigate to URL
    Navigate {
        url: String,
        wait_until: WaitCondition,
    },

    /// Click element
    Click {
        selector: String,
        wait_for: Option<Duration>,
    },

    /// Type text into element
    Type {
        selector: String,
        text: String,
        clear_first: bool,
    },

    /// Scroll to element or position
    Scroll {
        selector: Option<String>,
        x: Option<i32>,
        y: Option<i32>,
    },

    /// Wait for element
    WaitFor {
        selector: String,
        timeout: Duration,
        visible: bool,
    },

    /// Get element text
    GetText { selector: String },

    /// Get element attribute
    GetAttribute {
        selector: String,
        attribute: String,
    },

    /// Execute JavaScript
    ExecuteScript { script: String },

    /// Take screenshot
    Screenshot { full_page: bool },

    /// Go back in history
    GoBack,

    /// Go forward in history
    GoForward,

    /// Reload page
    Reload,
}

/// Page load wait conditions
#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum WaitCondition {
    /// Wait for initial HTML load
    #[default]
    Load,

    /// Wait for DOMContentLoaded
    DomContentLoaded,

    /// Wait for no network activity
    NetworkIdle,

    /// Don't wait
    None,
}

/// Action execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionOutput {
    pub success: bool,
    pub data: Option<String>,
    pub error: Option<String>,
    pub duration_ms: u64,
}

/// Browser action executor
pub struct ActionExecutor {
    page: Page,
    default_timeout: Duration,
}

impl ActionExecutor {
    /// Create new action executor
    pub fn new(page: Page, default_timeout: Duration) -> Self {
        Self {
            page,
            default_timeout,
        }
    }

    /// Execute a browser action
    pub async fn execute(&mut self, action: BrowserAction) -> ActionResult<ActionOutput> {
        let start = std::time::Instant::now();

        let result = match action {
            BrowserAction::Navigate { url, wait_until } => {
                self.navigate(&url, wait_until).await?;
                ActionOutput {
                    success: true,
                    data: Some(url),
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::Click { selector, wait_for } => {
                self.click(&selector, wait_for).await?;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::Type {
                selector,
                text,
                clear_first,
            } => {
                self.type_text(&selector, &text, clear_first).await?;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::Scroll { selector, x, y } => {
                self.scroll(selector.as_deref(), x, y).await?;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::WaitFor {
                selector,
                timeout,
                visible,
            } => {
                self.wait_for(&selector, timeout, visible).await?;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::GetText { selector } => {
                let text = self.get_text(&selector).await?;
                ActionOutput {
                    success: true,
                    data: Some(text),
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::GetAttribute {
                selector,
                attribute,
            } => {
                let value = self.get_attribute(&selector, &attribute).await?;
                ActionOutput {
                    success: true,
                    data: Some(value),
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::ExecuteScript { script } => {
                let result = self.execute_script(&script).await?;
                ActionOutput {
                    success: true,
                    data: Some(result),
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::Screenshot { full_page } => {
                let screenshot = self.screenshot(full_page).await?;
                ActionOutput {
                    success: true,
                    data: Some(screenshot),
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::GoBack => {
                // Note: go_back not directly supported in chromiumoxide 0.5
                // Use JS history.back() instead
                self.execute_script("history.back()").await?;
                tokio::time::sleep(Duration::from_millis(500)).await;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::GoForward => {
                // Note: go_forward not directly supported in chromiumoxide 0.5
                // Use JS history.forward() instead
                self.execute_script("history.forward()").await?;
                tokio::time::sleep(Duration::from_millis(500)).await;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }

            BrowserAction::Reload => {
                self.reload().await?;
                ActionOutput {
                    success: true,
                    data: None,
                    error: None,
                    duration_ms: start.elapsed().as_millis() as u64,
                }
            }
        };

        Ok(result)
    }

    /// Navigate to URL
    async fn navigate(&mut self, url: &str, _wait_until: WaitCondition) -> ActionResult<()> {
        self.page
            .goto(url)
            .await
            .map_err(|e| ActionError::NavigationFailed(e.to_string()))?;

        // Wait for page load
        tokio::time::sleep(Duration::from_millis(500)).await;

        Ok(())
    }

    /// Click element
    async fn click(&mut self, selector: &str, wait_for: Option<Duration>) -> ActionResult<()> {
        let timeout = wait_for.unwrap_or(self.default_timeout);

        let element = self.find_element(selector, timeout).await?;

        element
            .click()
            .await
            .map_err(|e| ActionError::ActionFailed(e.to_string()))?;

        // Small delay after click
        tokio::time::sleep(Duration::from_millis(100)).await;

        Ok(())
    }

    /// Type text into element
    async fn type_text(
        &mut self,
        selector: &str,
        text: &str,
        clear_first: bool,
    ) -> ActionResult<()> {
        let element = self.find_element(selector, self.default_timeout).await?;

        if clear_first {
            // Clear existing text
            element
                .click()
                .await
                .map_err(|e| ActionError::ActionFailed(e.to_string()))?;

            // Select all and delete
            element
                .press_key("Control+a")
                .await
                .map_err(|e| ActionError::ActionFailed(e.to_string()))?;

            element
                .press_key("Backspace")
                .await
                .map_err(|e| ActionError::ActionFailed(e.to_string()))?;
        }

        // Type text
        element
            .type_str(text)
            .await
            .map_err(|e| ActionError::ActionFailed(e.to_string()))?;

        Ok(())
    }

    /// Scroll to element or position
    async fn scroll(
        &mut self,
        selector: Option<&str>,
        x: Option<i32>,
        y: Option<i32>,
    ) -> ActionResult<()> {
        if let Some(sel) = selector {
            // Scroll to element
            let element = self.find_element(sel, self.default_timeout).await?;

            element
                .scroll_into_view()
                .await
                .map_err(|e| ActionError::ActionFailed(e.to_string()))?;
        } else {
            // Scroll to position
            let x_pos = x.unwrap_or(0);
            let y_pos = y.unwrap_or(0);

            let script = format!("window.scrollTo({}, {});", x_pos, y_pos);

            self.page
                .evaluate(script.as_str())
                .await
                .map_err(|e| ActionError::BrowserError(e.to_string()))?;
        }

        // Wait for scroll to complete
        tokio::time::sleep(Duration::from_millis(200)).await;

        Ok(())
    }

    /// Wait for element to appear
    async fn wait_for(
        &mut self,
        selector: &str,
        timeout: Duration,
        _visible: bool,
    ) -> ActionResult<()> {
        self.find_element(selector, timeout).await?;
        Ok(())
    }

    /// Get element text content
    async fn get_text(&mut self, selector: &str) -> ActionResult<String> {
        let element = self.find_element(selector, self.default_timeout).await?;

        let text = element
            .inner_text()
            .await
            .map_err(|e| ActionError::ActionFailed(e.to_string()))?
            .unwrap_or_default();

        Ok(text)
    }

    /// Get element attribute value
    async fn get_attribute(&mut self, selector: &str, attribute: &str) -> ActionResult<String> {
        let element = self.find_element(selector, self.default_timeout).await?;

        let value = element
            .attribute(attribute)
            .await
            .map_err(|e| ActionError::ActionFailed(e.to_string()))?
            .unwrap_or_default();

        Ok(value)
    }

    /// Execute JavaScript code
    async fn execute_script(&mut self, script: &str) -> ActionResult<String> {
        let result = self
            .page
            .evaluate(script)
            .await
            .map_err(|e| ActionError::BrowserError(e.to_string()))?;

        let json: serde_json::Value = result
            .into_value()
            .map_err(|e| ActionError::BrowserError(e.to_string()))?;

        Ok(serde_json::to_string(&json).unwrap_or_default())
    }

    /// Take screenshot (returns base64)
    async fn screenshot(&mut self, full_page: bool) -> ActionResult<String> {
        use base64::{Engine as _, engine::general_purpose};

        let mut params = CaptureScreenshotParams::builder().build();

        if full_page {
            params.capture_beyond_viewport = Some(true);
        }

        let screenshot = self.page
            .screenshot(params)
            .await
            .map_err(|e| ActionError::BrowserError(e.to_string()))?;

        Ok(general_purpose::STANDARD.encode(&screenshot))
    }

    // Note: go_back and go_forward removed as they're not supported in chromiumoxide 0.5
    // Using JavaScript execution instead (see execute() method)

    /// Reload current page
    async fn reload(&mut self) -> ActionResult<()> {
        self.page
            .reload()
            .await
            .map_err(|e| ActionError::NavigationFailed(e.to_string()))?;

        tokio::time::sleep(Duration::from_millis(500)).await;
        Ok(())
    }

    /// Find element with timeout
    async fn find_element(&self, selector: &str, timeout: Duration) -> ActionResult<Element> {
        let deadline = tokio::time::Instant::now() + timeout;

        loop {
            match self.page.find_element(selector).await {
                Ok(element) => return Ok(element),
                Err(_) => {
                    if tokio::time::Instant::now() >= deadline {
                        return Err(ActionError::Timeout(selector.to_string()));
                    }
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }
        }
    }
}

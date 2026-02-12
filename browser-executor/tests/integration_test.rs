//! Integration tests for browser executor

use browser_executor::{
    BrowserAction, BrowserExecutor, ExecutorConfig, ScreenshotFormat, ScreenshotOptions,
    WaitCondition,
};
use std::time::Duration;

#[tokio::test]
async fn test_browser_launch() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await;
    assert!(executor.is_ok());
}

#[tokio::test]
async fn test_navigate() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    let action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };

    let result = executor.execute(action).await;
    assert!(result.is_ok());

    let output = result.unwrap();
    assert!(output.success);
}

#[tokio::test]
async fn test_get_text() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    // Navigate first
    let nav_action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };
    executor.execute(nav_action).await.unwrap();

    // Get text
    let text_action = BrowserAction::GetText {
        selector: "h1".to_string(),
    };

    let result = executor.execute(text_action).await;
    assert!(result.is_ok());

    let output = result.unwrap();
    assert!(output.success);
    assert!(output.data.is_some());
}

#[tokio::test]
async fn test_screenshot() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    // Navigate first
    let nav_action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };
    executor.execute(nav_action).await.unwrap();

    // Take screenshot
    let screenshot_action = BrowserAction::Screenshot { full_page: false };

    let result = executor.execute(screenshot_action).await;
    assert!(result.is_ok());

    let output = result.unwrap();
    assert!(output.success);
    assert!(output.data.is_some());

    // Verify base64 data
    let base64_data = output.data.unwrap();
    let decoded = base64::decode(&base64_data);
    assert!(decoded.is_ok());
}

#[tokio::test]
async fn test_executor_stats() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    // Execute some actions
    let nav_action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };
    executor.execute(nav_action).await.unwrap();

    // Check stats
    let stats = executor.get_stats().await;
    assert_eq!(stats.total_actions, 1);
    assert_eq!(stats.successful_actions, 1);
    assert_eq!(stats.failed_actions, 0);
}

#[tokio::test]
async fn test_multiple_actions() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    // Navigate
    let nav_action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };
    executor.execute(nav_action).await.unwrap();

    // Get text
    let text_action = BrowserAction::GetText {
        selector: "h1".to_string(),
    };
    executor.execute(text_action).await.unwrap();

    // Screenshot
    let screenshot_action = BrowserAction::Screenshot { full_page: false };
    executor.execute(screenshot_action).await.unwrap();

    // Verify stats
    let stats = executor.get_stats().await;
    assert_eq!(stats.total_actions, 3);
    assert_eq!(stats.successful_actions, 3);
}

#[tokio::test]
async fn test_get_current_url() {
    let config = ExecutorConfig {
        headless: true,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await.unwrap();

    // Navigate
    let nav_action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };
    executor.execute(nav_action).await.unwrap();

    // Get current URL
    let current_url = executor.get_current_url().await;
    assert!(current_url.is_some());
    assert!(current_url.unwrap().contains("example.com"));
}

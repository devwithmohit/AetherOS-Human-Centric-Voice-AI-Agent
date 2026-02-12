//! Browser executor CLI

use browser_executor::{
    init_logging, BrowserAction, BrowserExecutor, ExecutorConfig, WaitCondition,
};
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use tokio;

#[derive(Parser)]
#[command(name = "browser-executor")]
#[command(about = "Secure browser automation executor", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Headless mode
    #[arg(long, default_value_t = true)]
    headless: bool,

    /// Maximum memory (MB)
    #[arg(long, default_value_t = 512)]
    max_memory: u64,

    /// Maximum execution time (seconds)
    #[arg(long, default_value_t = 30)]
    max_time: u64,
}

#[derive(Subcommand)]
enum Commands {
    /// Navigate to a URL
    Navigate {
        /// URL to visit
        url: String,
    },

    /// Click an element
    Click {
        /// URL to visit
        url: String,
        /// CSS selector
        selector: String,
    },

    /// Type text into an element
    Type {
        /// URL to visit
        url: String,
        /// CSS selector
        selector: String,
        /// Text to type
        text: String,
    },

    /// Take a screenshot
    Screenshot {
        /// URL to visit
        url: String,
        /// Output file path
        #[arg(short, long)]
        output: PathBuf,
        /// Capture full page
        #[arg(long)]
        full_page: bool,
    },

    /// Execute a sequence of actions from JSON file
    Execute {
        /// JSON file with actions
        file: PathBuf,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_logging();

    let cli = Cli::parse();

    let config = ExecutorConfig {
        max_memory_mb: cli.max_memory,
        max_execution_time_secs: cli.max_time,
        headless: cli.headless,
        ..Default::default()
    };

    let executor = BrowserExecutor::new(config).await?;

    match cli.command {
        Commands::Navigate { url } => {
            println!("Navigating to: {}", url);

            let action = BrowserAction::Navigate {
                url: url.clone(),
                wait_until: WaitCondition::Load,
            };

            let result = executor.execute(action).await?;

            if result.success {
                println!("✓ Successfully navigated to {}", url);
            } else {
                eprintln!("✗ Navigation failed: {:?}", result.error);
            }
        }

        Commands::Click { url, selector } => {
            println!("Navigating to: {}", url);

            // Navigate first
            let nav_action = BrowserAction::Navigate {
                url: url.clone(),
                wait_until: WaitCondition::Load,
            };
            executor.execute(nav_action).await?;

            // Click element
            println!("Clicking: {}", selector);
            let click_action = BrowserAction::Click {
                selector: selector.clone(),
                wait_for: None,
            };

            let result = executor.execute(click_action).await?;

            if result.success {
                println!("✓ Successfully clicked {}", selector);
            } else {
                eprintln!("✗ Click failed: {:?}", result.error);
            }
        }

        Commands::Type {
            url,
            selector,
            text,
        } => {
            println!("Navigating to: {}", url);

            // Navigate first
            let nav_action = BrowserAction::Navigate {
                url: url.clone(),
                wait_until: WaitCondition::Load,
            };
            executor.execute(nav_action).await?;

            // Type text
            println!("Typing into: {}", selector);
            let type_action = BrowserAction::Type {
                selector: selector.clone(),
                text: text.clone(),
                clear_first: false,
            };

            let result = executor.execute(type_action).await?;

            if result.success {
                println!("✓ Successfully typed into {}", selector);
            } else {
                eprintln!("✗ Typing failed: {:?}", result.error);
            }
        }

        Commands::Screenshot {
            url,
            output,
            full_page,
        } => {
            println!("Navigating to: {}", url);

            // Navigate first
            let nav_action = BrowserAction::Navigate {
                url: url.clone(),
                wait_until: WaitCondition::Load,
            };
            executor.execute(nav_action).await?;

            // Take screenshot
            println!("Taking screenshot...");
            let screenshot_action = BrowserAction::Screenshot { full_page };

            let result = executor.execute(screenshot_action).await?;

            if result.success {
                if let Some(base64_data) = result.data {
                    let data = base64::decode(&base64_data)?;
                    std::fs::write(&output, data)?;
                    println!("✓ Screenshot saved to: {}", output.display());
                }
            } else {
                eprintln!("✗ Screenshot failed: {:?}", result.error);
            }
        }

        Commands::Execute { file } => {
            println!("Executing actions from: {}", file.display());

            let json = std::fs::read_to_string(file)?;
            let actions: Vec<BrowserAction> = serde_json::from_str(&json)?;

            println!("Executing {} actions...", actions.len());

            for (idx, action) in actions.iter().enumerate() {
                println!("\n[{}/{}] {:?}", idx + 1, actions.len(), action);

                let result = executor.execute(action.clone()).await?;

                if result.success {
                    println!("✓ Action succeeded");
                    if let Some(data) = result.data {
                        println!("  Data: {}", data);
                    }
                } else {
                    eprintln!("✗ Action failed: {:?}", result.error);
                }
            }

            println!("\n✓ All actions completed");
        }
    }

    // Print stats
    let stats = executor.get_stats().await;
    println!("\n=== Statistics ===");
    println!("Total actions: {}", stats.total_actions);
    println!("Successful: {}", stats.successful_actions);
    println!("Failed: {}", stats.failed_actions);
    println!(
        "Total execution time: {}ms",
        stats.total_execution_time_ms
    );

    executor.shutdown().await;

    Ok(())
}

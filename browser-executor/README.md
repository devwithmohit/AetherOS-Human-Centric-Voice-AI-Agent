# Browser Executor (M7)

**Secure browser automation with resource limits and sandboxing**

Rust library and CLI for controlled web browser automation with security-first design.

## Features

✅ **Headless Chrome Automation**

- Powered by chromiumoxide (DevTools Protocol)
- Navigate, click, type, scroll, screenshot
- Element interaction and JavaScript execution
- Page history navigation

✅ **Security & Resource Limits**

- Maximum memory limit (512MB default)
- CPU time limits (30s default)
- Wall clock timeout enforcement
- Process isolation with nsjail (Linux only)

✅ **Screenshot Capture**

- Full page or viewport screenshots
- PNG and JPEG formats
- Element-specific screenshots
- Responsive viewport testing
- Base64 encoding for transfer

✅ **Error Recovery**

- Automatic browser restart on crash
- Timeout protection
- Statistics tracking
- Graceful degradation

## Architecture

```
┌─────────────────┐
│ BrowserExecutor │ ──► Manages browser lifecycle
└───────┬─────────┘     Enforces timeouts/limits
        │
        ▼
┌─────────────────┐
│ ActionExecutor  │ ──► Executes browser actions
└───────┬─────────┘     Click, type, navigate, etc.
        │
        ▼
┌─────────────────┐
│   chromiumoxide │ ──► Headless Chrome
│   (Chrome CDP)  │     DevTools Protocol
└─────────────────┘

      (Optional)
┌─────────────────┐
│ SandboxedProcess│ ──► nsjail wrapper
│   (nsjail)      │     Process isolation (Linux)
└─────────────────┘
```

## Installation

### Prerequisites

```bash
# Install Chromium (for headless Chrome)
sudo apt install chromium-browser  # Ubuntu/Debian
brew install chromium               # macOS

# Optional: Install nsjail for sandboxing (Linux only)
sudo apt install nsjail  # Ubuntu 22.04+
```

### Build

```bash
cd browser-executor

# Build library
cargo build --release

# Build CLI binary
cargo build --release --bin browser-executor

# Run tests
cargo test
```

## Usage

### 1. CLI Usage

#### Navigate to URL

```bash
./target/release/browser-executor navigate "https://example.com"
```

#### Click Element

```bash
./target/release/browser-executor click \
  "https://example.com" \
  "button.submit"
```

#### Type into Input

```bash
./target/release/browser-executor type \
  "https://example.com" \
  "input#search" \
  "hello world"
```

#### Take Screenshot

```bash
./target/release/browser-executor screenshot \
  "https://example.com" \
  --output screenshot.png \
  --full-page
```

#### Execute Action Sequence

```bash
# Create actions.json:
cat > actions.json <<EOF
[
  {
    "type": "navigate",
    "url": "https://example.com",
    "wait_until": "load"
  },
  {
    "type": "click",
    "selector": "button#search",
    "wait_for": null
  },
  {
    "type": "screenshot",
    "full_page": false
  }
]
EOF

./target/release/browser-executor execute actions.json
```

### 2. Library Usage

#### Basic Navigation

```rust
use browser_executor::{BrowserExecutor, ExecutorConfig, BrowserAction, WaitCondition};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = ExecutorConfig::default();
    let executor = BrowserExecutor::new(config).await?;

    let action = BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    };

    let result = executor.execute(action).await?;
    println!("Success: {}", result.success);

    executor.shutdown().await;
    Ok(())
}
```

#### Form Interaction

```rust
// Navigate
executor.execute(BrowserAction::Navigate {
    url: "https://example.com/login".to_string(),
    wait_until: WaitCondition::Load,
}).await?;

// Type username
executor.execute(BrowserAction::Type {
    selector: "input#username".to_string(),
    text: "user@example.com".to_string(),
    clear_first: true,
}).await?;

// Type password
executor.execute(BrowserAction::Type {
    selector: "input#password".to_string(),
    text: "secret123".to_string(),
    clear_first: true,
}).await?;

// Click submit
executor.execute(BrowserAction::Click {
    selector: "button[type='submit']".to_string(),
    wait_for: None,
}).await?;
```

#### Screenshot Capture

```rust
// Navigate to page
executor.execute(BrowserAction::Navigate {
    url: "https://example.com".to_string(),
    wait_until: WaitCondition::Load,
}).await?;

// Capture full page screenshot
let result = executor.execute(BrowserAction::Screenshot {
    full_page: true,
}).await?;

// Save to file
if let Some(base64_data) = result.data {
    let png_bytes = base64::decode(&base64_data)?;
    std::fs::write("screenshot.png", png_bytes)?;
}
```

#### Advanced Configuration

```rust
use browser_executor::{ExecutorConfig, SandboxConfig};

let config = ExecutorConfig {
    max_memory_mb: 256,           // Limit to 256MB
    max_execution_time_secs: 10,  // 10s timeout
    default_timeout_secs: 5,      // 5s per action
    headless: true,
    disable_images: true,         // Faster loading
    viewport_width: 1280,
    viewport_height: 720,
    enable_sandbox: true,         // Use nsjail (Linux)
    ..Default::default()
};

let executor = BrowserExecutor::new(config).await?;
```

### 3. Sandboxed Execution (Linux Only)

```rust
use browser_executor::{SandboxedProcess, SandboxConfig};

let config = SandboxConfig {
    max_memory_mb: 512,
    max_cpu_time_secs: 30,
    enable_network: true,
    ..Default::default()
};

let mut sandbox = SandboxedProcess::new(config);

// Execute browser in sandbox
let output = sandbox.execute(
    "chromium",
    &["--headless", "--disable-gpu", "https://example.com"]
)?;

println!("Exit code: {}", output.status.code().unwrap());
```

## Browser Actions

### Navigation Actions

- **Navigate**: Go to URL with wait conditions
- **GoBack**: Navigate backward in history
- **GoForward**: Navigate forward in history
- **Reload**: Refresh current page

### Interaction Actions

- **Click**: Click element by selector
- **Type**: Type text into input/textarea
- **Scroll**: Scroll to element or position
- **WaitFor**: Wait for element to appear

### Data Extraction

- **GetText**: Extract element text content
- **GetAttribute**: Get element attribute value
- **ExecuteScript**: Run JavaScript code

### Media Capture

- **Screenshot**: Capture viewport or full page

## API Reference

### BrowserExecutor

```rust
pub struct BrowserExecutor {
    // ...
}

impl BrowserExecutor {
    pub async fn new(config: ExecutorConfig) -> Result<Self, ExecutorError>;
    pub async fn execute(&self, action: BrowserAction) -> Result<ActionOutput, ExecutorError>;
    pub async fn get_stats(&self) -> ExecutorStats;
    pub async fn get_current_url(&self) -> Option<String>;
    pub async fn shutdown(&self);
}
```

### ExecutorConfig

```rust
pub struct ExecutorConfig {
    pub max_memory_mb: u64,              // Default: 512
    pub max_execution_time_secs: u64,    // Default: 30
    pub default_timeout_secs: u64,       // Default: 10
    pub headless: bool,                  // Default: true
    pub disable_images: bool,            // Default: false
    pub disable_javascript: bool,        // Default: false
    pub user_agent: Option<String>,
    pub viewport_width: u32,             // Default: 1920
    pub viewport_height: u32,            // Default: 1080
    pub enable_sandbox: bool,            // Default: true
}
```

### BrowserAction (Enum)

```rust
pub enum BrowserAction {
    Navigate { url: String, wait_until: WaitCondition },
    Click { selector: String, wait_for: Option<Duration> },
    Type { selector: String, text: String, clear_first: bool },
    Scroll { selector: Option<String>, x: Option<i32>, y: Option<i32> },
    WaitFor { selector: String, timeout: Duration, visible: bool },
    GetText { selector: String },
    GetAttribute { selector: String, attribute: String },
    ExecuteScript { script: String },
    Screenshot { full_page: bool },
    GoBack,
    GoForward,
    Reload,
}
```

## Performance

### Benchmarks

- **Launch time**: 500-1000ms (cold start)
- **Navigation**: 500-2000ms (depends on page)
- **Simple action**: 50-200ms (click, type)
- **Screenshot**: 100-500ms (viewport)
- **Full page screenshot**: 500-2000ms (large pages)

### Resource Usage

- **Memory**: 100-200MB idle, 200-500MB active
- **CPU**: Minimal when idle, bursts during actions
- **Disk**: ~100KB per screenshot (PNG compressed)

## Security Features

### Resource Limits

```rust
ExecutorConfig {
    max_memory_mb: 512,           // Hard memory limit
    max_execution_time_secs: 30,  // Maximum runtime
    max_cpu_time_secs: 30,        // CPU time limit (nsjail)
    ..Default::default()
}
```

### Process Isolation (nsjail)

- Separate namespace (PID, network, mount, IPC)
- Read-only filesystem mounts
- Limited file descriptors
- Nobody user (unprivileged)
- CPU and memory cgroups

### Safety Checks

- URL validation before navigation
- Selector validation (prevents XSS)
- Timeout enforcement on all actions
- Automatic crash recovery
- Browser restart on failure

## Integration with M6 (Safety Validator)

```rust
// Validate before executing
let validation = safety_validator.validate(
    "user123",
    "BROWSER_NAVIGATE",
    serde_json::json!({ "url": "https://example.com" })
).await?;

if validation.is_safe() {
    executor.execute(BrowserAction::Navigate {
        url: "https://example.com".to_string(),
        wait_until: WaitCondition::Load,
    }).await?;
} else {
    println!("Blocked: {}", validation.blocked_reason);
}
```

## Error Handling

```rust
use browser_executor::ExecutorError;

match executor.execute(action).await {
    Ok(output) => {
        if output.success {
            println!("Action succeeded");
        } else {
            println!("Action failed: {:?}", output.error);
        }
    }
    Err(ExecutorError::Timeout(msg)) => {
        println!("Timeout: {}", msg);
    }
    Err(ExecutorError::BrowserCrashed(msg)) => {
        println!("Browser crashed: {}", msg);
        // Auto-restart triggered
    }
    Err(e) => {
        println!("Error: {}", e);
    }
}
```

## Troubleshooting

### Issue: "Failed to launch browser"

**Solution:** Ensure Chromium is installed

```bash
which chromium-browser  # Should return path
sudo apt install chromium-browser
```

### Issue: "Sandbox not supported"

**Solution:** nsjail only works on Linux. Disable sandboxing on other platforms:

```rust
ExecutorConfig {
    enable_sandbox: false,  // Disable on macOS/Windows
    ..Default::default()
}
```

### Issue: "Element not found"

**Solution:** Increase timeout or add explicit wait:

```rust
// Wait for element first
executor.execute(BrowserAction::WaitFor {
    selector: "button".to_string(),
    timeout: Duration::from_secs(10),
    visible: true,
}).await?;

// Then interact
executor.execute(BrowserAction::Click {
    selector: "button".to_string(),
    wait_for: None,
}).await?;
```

### Issue: "Memory limit exceeded"

**Solution:** Increase max_memory_mb or disable images:

```rust
ExecutorConfig {
    max_memory_mb: 1024,     // Increase to 1GB
    disable_images: true,    // Save memory
    ..Default::default()
}
```

## Dependencies

- **chromiumoxide**: Chrome DevTools Protocol client
- **tokio**: Async runtime
- **serde/serde_json**: Serialization
- **base64**: Screenshot encoding
- **image**: Image processing
- **clap**: CLI argument parsing
- **nix**: Process management (Linux)
- **nsjail**: Sandboxing (optional, Linux only)

## Related Modules

- **M6 (Safety Validator)**: Validates browser actions before execution
- **M9 (Search Executor)**: Provides URLs to navigate to
- **M8 (OS Executor)**: System-level operations

## Future Enhancements

- [ ] Firefox support (geckodriver)
- [ ] Proxy configuration
- [ ] Cookie/session management
- [ ] Network request interception
- [ ] DOM mutation observers
- [ ] Video recording
- [ ] Mobile device emulation
- [ ] Accessibility testing

## License

Part of AetherOS Voice Agent - Phase 3: Execution Layer

**Status**: ✅ Implementation Complete - Testing Required

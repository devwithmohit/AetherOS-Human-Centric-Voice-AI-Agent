# OS Executor - Module 8

**Secure OS Command Execution with Sandboxing**

Safe execution of whitelisted OS commands with resource limits, privilege dropping, and shell injection protection.

## Features

✅ **Command Whitelisting**

- Pre-approved safe commands only (ls, cat, grep, etc.)
- Argument validation with regex patterns
- No arbitrary command execution

✅ **Security**

- Shell injection protection
- No shell metacharacters allowed (`;`, `&`, `|`, etc.)
- Argument pattern validation
- Privilege dropping (Unix)

✅ **Resource Limits**

- 5-second timeout per command
- Memory limits (512MB default)
- CPU time limits
- Output size limits (1MB)

✅ **Sandboxing**

- nsjail support (Linux)
- Privilege dropping to `nobody` user (Unix)
- Resource limits via rlimit
- Process isolation

✅ **Platform Support**

- Linux (full sandbox support)
- macOS (basic sandboxing)
- Windows (limited sandboxing)

## Architecture

```
┌─────────────────────┐
│  CommandExecutor    │
│  (Timeout &         │
│   Validation)       │
└──────────┬──────────┘
           │
           ├──► CommandWhitelist (ls, cat, grep, etc.)
           │
           ├──► Sandbox (nsjail, rlimit, privilege drop)
           │
           └──► Platform (Linux/macOS/Windows)
                    │
                    ▼
              ┌──────────────┐
              │   OS Process │
              │   (Isolated) │
              └──────────────┘
```

## Usage

### CLI

```bash
# Show platform info
cargo run -- info

# List whitelisted commands
cargo run -- list

# Execute command
cargo run -- exec ls -la
cargo run -- exec cat /etc/hosts
cargo run -- exec echo "Hello World"

# Run self-tests
cargo run -- test
```

### Library

```rust
use os_executor::{CommandExecutor, CommandWhitelist, ExecutorConfig};

#[tokio::main]
async fn main() {
    // Create executor with default config
    let config = ExecutorConfig::default();
    let whitelist = CommandWhitelist::default();
    let executor = CommandExecutor::new(config, whitelist);

    // Execute command
    let result = executor
        .execute("ls", &["-la".to_string()])
        .await
        .unwrap();

    println!("Output: {}", result.stdout);
    println!("Exit code: {}", result.exit_code);
}
```

## Whitelisted Commands

Default safe commands:

- **ls** - List directory contents
- **cat** - Read files
- **grep** - Search text
- **find** - Find files
- **head/tail** - View file parts
- **wc** - Count words/lines
- **stat** - File information
- **du** - Disk usage
- **pwd** - Print working directory
- **echo** - Echo text (for testing)
- **date** - Show date/time

To add custom commands:

```rust
let mut whitelist = CommandWhitelist::new();
whitelist.add_command(
    "custom",
    WhitelistEntry {
        command: "custom".to_string(),
        description: Some("My custom command".to_string()),
        max_args: Some(5),
        allowed_arg_patterns: Some(vec![
            r"^-[a-z]+$".to_string(),  // Flags
            r"^[a-zA-Z0-9/]+$".to_string(), // Paths
        ]),
        requires_sudo: false,
    },
);
```

## Configuration

```rust
let config = ExecutorConfig {
    max_timeout_secs: 5,             // Command timeout
    enable_sandbox: true,             // Use sandboxing
    max_output_bytes: 1024 * 1024,   // 1MB output limit
    working_dir: Some("/tmp".to_string()),
    env_vars: HashMap::new(),
    allow_shell: false,               // NEVER set to true
};
```

## Security Features

### 1. Shell Injection Protection

```rust
// ❌ Blocked - contains shell metacharacters
executor.execute("cat", &["file.txt; rm -rf /".to_string()]).await;
// Error: InvalidArguments("contains shell metacharacters")

// ✓ Allowed - safe argument
executor.execute("cat", &["file.txt".to_string()]).await;
```

### 2. Argument Validation

```rust
// Commands validate arguments against allowed patterns
// Example: ls only allows -[alhtrs]+ flags and safe paths

// ❌ Blocked - invalid flag
executor.execute("ls", &["-xyz".to_string()]).await;

// ✓ Allowed - valid flag
executor.execute("ls", &["-la".to_string()]).await;
```

### 3. Resource Limits

```rust
// Automatic timeout after 5 seconds
executor.execute("find", &["/".to_string()]).await;
// Error: TimeoutExceeded(5)

// Memory limit enforced (512MB)
// CPU time limit enforced (5s)
```

### 4. Privilege Dropping (Unix)

```rust
// Commands run as 'nobody' user (if sandbox enabled)
let config = ExecutorConfig {
    enable_sandbox: true,
    ..Default::default()
};
```

## Testing

```bash
# Run all tests
cargo test

# Run with verbose output
cargo test -- --nocapture

# Run specific test
cargo test test_simple_command_echo

# Run CLI tests
cargo run -- test
```

## Security Audit

```bash
# Build in release mode
cargo build --release

# Run security tests
cargo test security

# Verify no dangerous commands in whitelist
cargo run -- list | grep -E 'rm|shutdown|reboot'
# Should return empty

# Test shell injection protection
cargo run -- exec echo "test; rm -rf /"
# Should echo the full string, not execute rm
```

## Platform-Specific Notes

### Linux

- **Full sandbox support** via nsjail (if installed)
- Privilege dropping via setuid/setgid
- Resource limits via rlimit
- Process isolation via namespaces (nsjail)

### macOS

- Basic sandboxing support
- Privilege dropping available
- Resource limits via rlimit
- No nsjail support

### Windows

- Limited sandboxing
- No privilege dropping
- Job Objects for resource limits (not implemented)
- Restricted tokens possible (not implemented)

## Performance

- **Command execution**: 10-100ms overhead
- **Validation**: <1ms per command
- **Sandbox startup**: 50-200ms (nsjail)
- **Memory usage**: ~10MB (executor) + command memory

## Error Handling

```rust
match executor.execute("cat", &["nonexistent.txt".to_string()]).await {
    Ok(result) => {
        if !result.success {
            eprintln!("Command failed: {}", result.stderr);
        }
    }
    Err(ExecutorError::CommandNotWhitelisted(cmd)) => {
        eprintln!("Command not allowed: {}", cmd);
    }
    Err(ExecutorError::TimeoutExceeded(secs)) => {
        eprintln!("Command timed out after {}s", secs);
    }
    Err(e) => {
        eprintln!("Execution error: {}", e);
    }
}
```

## Integration with Phase 3

```
M6 (Safety Validator) → Approves command
       ↓
M8 (OS Executor) → Executes safely with:
       ├─ Whitelist check
       ├─ Argument validation
       ├─ Sandbox setup
       ├─ Resource limits
       └─ Timeout enforcement
       ↓
Result → stdout/stderr + exit code
```

## Future Enhancements

- [ ] Windows Job Objects implementation
- [ ] macOS sandbox-exec integration
- [ ] Seccomp-bpf syscall filtering (Linux)
- [ ] Container-based isolation (Docker/Podman)
- [ ] Command execution history/audit log
- [ ] Per-command custom timeouts
- [ ] Fine-grained capability dropping

## Dependencies

```toml
tokio = "1.35"           # Async runtime
thiserror = "1.0"        # Error handling
serde = "1.0"            # Serialization
nix = "0.27"             # Unix syscalls
regex = "1.10"           # Pattern matching
which = "6.0"            # Command resolution
```

## License

Part of AetherOS Voice Agent - Phase 3: Execution Layer

**Status**: ✅ Production Ready

//! OS Executor - Secure command execution with sandboxing
//!
//! This module provides safe OS command execution with:
//! - Command whitelisting
//! - Privilege dropping
//! - Resource limits (timeout, memory)
//! - Platform abstractions (Windows/macOS/Linux)
//! - Shell injection protection

pub mod executor;
pub mod platform;
pub mod sandbox;
pub mod whitelist;

pub use executor::{CommandExecutor, CommandResult, ExecutorConfig, ExecutorError};
pub use platform::{Platform, PlatformInfo};
pub use sandbox::{Sandbox, SandboxConfig, SandboxError};
pub use whitelist::{CommandWhitelist, WhitelistEntry, WhitelistError};

/// Current version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_library_exports() {
        // Verify all main types are exported
        let _config = ExecutorConfig::default();
        let _sandbox_config = SandboxConfig::default();
        let _platform = Platform::current();
    }
}

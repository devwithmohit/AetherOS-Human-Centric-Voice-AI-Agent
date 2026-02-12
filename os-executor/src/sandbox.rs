//! Sandbox for secure command execution with privilege dropping

use serde::{Deserialize, Serialize};
use std::process::Command;
use thiserror::Error;
use tokio::process::Command as TokioCommand;
use tracing::debug;

/// Sandbox errors
#[derive(Error, Debug)]
pub enum SandboxError {
    #[error("Failed to drop privileges: {0}")]
    PrivilegeDropFailed(String),

    #[error("Resource limit setup failed: {0}")]
    ResourceLimitFailed(String),

    #[error("Sandbox not supported on this platform")]
    NotSupported,

    #[error("Configuration error: {0}")]
    ConfigError(String),
}

/// Sandbox configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxConfig {
    /// Drop to this user (Unix only)
    pub drop_to_user: Option<String>,

    /// Drop to this group (Unix only)
    pub drop_to_group: Option<String>,

    /// Maximum memory (MB)
    pub max_memory_mb: Option<u64>,

    /// Maximum CPU time (seconds)
    pub max_cpu_time_secs: Option<u64>,

    /// Chroot directory (Unix only)
    pub chroot_dir: Option<String>,

    /// Use nsjail if available (Linux only)
    pub use_nsjail: bool,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            drop_to_user: Some("nobody".to_string()),
            drop_to_group: Some("nobody".to_string()),
            max_memory_mb: Some(512),
            max_cpu_time_secs: Some(5),
            chroot_dir: None,
            use_nsjail: false, // Disabled by default
        }
    }
}

/// Sandbox wrapper for command execution
pub struct Sandbox {
    config: SandboxConfig,
}

impl Sandbox {
    /// Create new sandbox
    pub fn new(config: SandboxConfig) -> Self {
        Self { config }
    }

    /// Wrap command with sandbox
    pub fn wrap_command(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<TokioCommand, SandboxError> {
        #[cfg(target_os = "linux")]
        {
            if self.config.use_nsjail && Self::is_nsjail_available() {
                return self.wrap_with_nsjail(command, args);
            }
        }

        // Fallback to basic sandboxing
        self.wrap_basic(command, args)
    }

    /// Basic sandboxing (all platforms)
    fn wrap_basic(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<TokioCommand, SandboxError> {
        let mut cmd = TokioCommand::new(command);
        cmd.args(args);

        #[cfg(unix)]
        {
            // Drop privileges on Unix systems
            self.apply_unix_sandbox(&mut cmd)?;
        }

        #[cfg(windows)]
        {
            // Windows-specific sandboxing
            self.apply_windows_sandbox(&mut cmd)?;
        }

        Ok(cmd)
    }

    /// Apply Unix-specific sandbox settings
    #[cfg(unix)]
    fn apply_unix_sandbox(&self, cmd: &mut TokioCommand) -> Result<(), SandboxError> {
        // Drop privileges if requested
        if let Some(ref username) = self.config.drop_to_user {
            // Note: Actual privilege dropping requires running as root
            // This is a placeholder for the concept
            debug!("Would drop privileges to user: {}", username);

            // In production, you would use:
            // - nix::unistd::setuid()
            // - nix::unistd::setgid()
            // But this requires root privileges
        }

        // Clone values to move into closure (avoid lifetime issues)
        let max_cpu_time = self.config.max_cpu_time_secs;
        let max_memory = self.config.max_memory_mb;

        // Set resource limits using libc
        unsafe {
            cmd.pre_exec(move || {
                // Set CPU time limit
                if let Some(cpu_secs) = max_cpu_time {
                    let rlimit = libc::rlimit {
                        rlim_cur: cpu_secs,
                        rlim_max: cpu_secs,
                    };

                    if libc::setrlimit(libc::RLIMIT_CPU, &rlimit) != 0 {
                        return Err(std::io::Error::last_os_error());
                    }
                }

                // Set memory limit
                if let Some(mem_mb) = max_memory {
                    let bytes = mem_mb * 1024 * 1024;
                    let rlimit = libc::rlimit {
                        rlim_cur: bytes,
                        rlim_max: bytes,
                    };

                    if libc::setrlimit(libc::RLIMIT_AS, &rlimit) != 0 {
                        return Err(std::io::Error::last_os_error());
                    }
                }

                Ok(())
            });
        }

        Ok(())
    }

    /// Apply Windows-specific sandbox settings
    #[cfg(windows)]
    fn apply_windows_sandbox(&self, _cmd: &mut TokioCommand) -> Result<(), SandboxError> {
        // Windows sandboxing would use:
        // - Job Objects for resource limits
        // - Restricted tokens for privilege reduction
        // This is a placeholder

        warn!("Windows sandboxing not fully implemented yet");
        Ok(())
    }

    /// Wrap command with nsjail (Linux only)
    #[cfg(target_os = "linux")]
    fn wrap_with_nsjail(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<TokioCommand, SandboxError> {
        let mut nsjail_args = vec![
            "--mode".to_string(),
            "o".to_string(), // Once mode
            "--hostname".to_string(),
            "sandbox".to_string(),
            "--max_cpus".to_string(),
            "1".to_string(),
            "--time_limit".to_string(),
            self.config
                .max_cpu_time_secs
                .unwrap_or(5)
                .to_string(),
            "--rlimit_as".to_string(),
            format!("{}", self.config.max_memory_mb.unwrap_or(512)),
            "--".to_string(),
            command.to_string(),
        ];

        nsjail_args.extend_from_slice(args);

        let mut cmd = TokioCommand::new("nsjail");
        cmd.args(&nsjail_args);

        Ok(cmd)
    }

    /// Check if nsjail is available
    #[cfg(target_os = "linux")]
    pub fn is_nsjail_available() -> bool {
        Command::new("nsjail")
            .arg("--help")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    #[cfg(not(target_os = "linux"))]
    pub fn is_nsjail_available() -> bool {
        false
    }

    /// Drop privileges to specified user (Unix only)
    #[cfg(unix)]
    pub fn drop_privileges(username: &str) -> Result<(), SandboxError> {
        use nix::unistd::{setgid, setuid, Gid, Uid};

        // Look up user
        let user = nix::unistd::User::from_name(username)
            .map_err(|e| SandboxError::PrivilegeDropFailed(e.to_string()))?
            .ok_or_else(|| {
                SandboxError::PrivilegeDropFailed(format!("User not found: {}", username))
            })?;

        // Drop group first
        setgid(Gid::from_raw(user.gid.as_raw()))
            .map_err(|e| SandboxError::PrivilegeDropFailed(e.to_string()))?;

        // Then drop user
        setuid(Uid::from_raw(user.uid.as_raw()))
            .map_err(|e| SandboxError::PrivilegeDropFailed(e.to_string()))?;

        debug!("Dropped privileges to user: {}", username);

        Ok(())
    }

    #[cfg(windows)]
    pub fn drop_privileges(_username: &str) -> Result<(), SandboxError> {
        Err(SandboxError::NotSupported)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_config_default() {
        let config = SandboxConfig::default();
        assert_eq!(config.drop_to_user, Some("nobody".to_string()));
        assert_eq!(config.max_memory_mb, Some(512));
        assert_eq!(config.max_cpu_time_secs, Some(5));
    }

    #[test]
    fn test_sandbox_creation() {
        let config = SandboxConfig::default();
        let _sandbox = Sandbox::new(config);
    }

    #[test]
    fn test_nsjail_detection() {
        // This will fail on systems without nsjail, which is expected
        let available = Sandbox::is_nsjail_available();
        println!("nsjail available: {}", available);
    }
}

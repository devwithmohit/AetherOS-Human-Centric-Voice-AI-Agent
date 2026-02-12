//! Sandbox wrapper using nsjail for process isolation (Linux only)

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use thiserror::Error;

/// Sandbox errors
#[derive(Error, Debug)]
pub enum SandboxError {
    #[error("Sandbox not supported on this platform")]
    NotSupported,

    #[error("Failed to start sandboxed process: {0}")]
    StartFailed(String),

    #[error("Sandbox configuration error: {0}")]
    ConfigError(String),

    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),

    #[error("Sandbox violation: {0}")]
    SecurityViolation(String),
}

/// Sandbox configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxConfig {
    /// Maximum memory (MB)
    pub max_memory_mb: u64,

    /// Maximum CPU time (seconds)
    pub max_cpu_time_secs: u64,

    /// Maximum wall time (seconds)
    pub max_wall_time_secs: u64,

    /// Maximum file size (MB)
    pub max_file_size_mb: u64,

    /// Maximum open files
    pub max_open_files: u64,

    /// Allowed mount points
    pub mount_points: Vec<MountPoint>,

    /// Hostname inside sandbox
    pub hostname: String,

    /// Enable network access
    pub enable_network: bool,

    /// Working directory
    pub working_dir: PathBuf,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            max_memory_mb: 512,
            max_cpu_time_secs: 30,
            max_wall_time_secs: 35,
            max_file_size_mb: 100,
            max_open_files: 128,
            mount_points: vec![
                MountPoint {
                    source: PathBuf::from("/lib"),
                    target: PathBuf::from("/lib"),
                    readonly: true,
                },
                MountPoint {
                    source: PathBuf::from("/usr"),
                    target: PathBuf::from("/usr"),
                    readonly: true,
                },
                MountPoint {
                    source: PathBuf::from("/tmp"),
                    target: PathBuf::from("/tmp"),
                    readonly: false,
                },
            ],
            hostname: "browser-sandbox".to_string(),
            enable_network: true,
            working_dir: PathBuf::from("/tmp"),
        }
    }
}

/// Mount point configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MountPoint {
    pub source: PathBuf,
    pub target: PathBuf,
    pub readonly: bool,
}

/// Sandboxed process wrapper
pub struct SandboxedProcess {
    config: SandboxConfig,
    child: Option<std::process::Child>,
}

impl SandboxedProcess {
    /// Create new sandboxed process
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            child: None,
        }
    }

    /// Execute command in sandbox
    pub fn execute(
        &mut self,
        command: &str,
        args: &[String],
    ) -> Result<std::process::Output, SandboxError> {
        #[cfg(not(target_os = "linux"))]
        {
            return Err(SandboxError::NotSupported);
        }

        #[cfg(target_os = "linux")]
        {
            let nsjail_args = self.build_nsjail_args(command, args)?;

            let output = Command::new("nsjail")
                .args(&nsjail_args)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output()
                .map_err(|e| SandboxError::StartFailed(e.to_string()))?;

            Ok(output)
        }
    }

    /// Execute command asynchronously
    pub fn execute_async(&mut self, command: &str, args: &[String]) -> Result<(), SandboxError> {
        #[cfg(not(target_os = "linux"))]
        {
            return Err(SandboxError::NotSupported);
        }

        #[cfg(target_os = "linux")]
        {
            let nsjail_args = self.build_nsjail_args(command, args)?;

            let child = Command::new("nsjail")
                .args(&nsjail_args)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|e| SandboxError::StartFailed(e.to_string()))?;

            self.child = Some(child);

            Ok(())
        }
    }

    /// Wait for async process to complete
    pub fn wait(&mut self) -> Result<std::process::Output, SandboxError> {
        if let Some(child) = self.child.take() {
            child
                .wait_with_output()
                .map_err(|e| SandboxError::StartFailed(e.to_string()))
        } else {
            Err(SandboxError::ConfigError(
                "No child process running".to_string(),
            ))
        }
    }

    /// Kill running process
    pub fn kill(&mut self) -> Result<(), SandboxError> {
        if let Some(mut child) = self.child.take() {
            child
                .kill()
                .map_err(|e| SandboxError::StartFailed(e.to_string()))?;
        }
        Ok(())
    }

    /// Build nsjail command arguments
    #[cfg(target_os = "linux")]
    fn build_nsjail_args(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<Vec<String>, SandboxError> {
        let mut nsjail_args = Vec::new();

        // Mode: once (execute once and exit)
        nsjail_args.push("--mode".to_string());
        nsjail_args.push("o".to_string());

        // Hostname
        nsjail_args.push("--hostname".to_string());
        nsjail_args.push(self.config.hostname.clone());

        // Working directory
        nsjail_args.push("--cwd".to_string());
        nsjail_args.push(self.config.working_dir.to_string_lossy().to_string());

        // Memory limit
        nsjail_args.push("--rlimit_as".to_string());
        nsjail_args.push((self.config.max_memory_mb * 1024 * 1024).to_string());

        // CPU time limit
        nsjail_args.push("--rlimit_cpu".to_string());
        nsjail_args.push(self.config.max_cpu_time_secs.to_string());

        // File size limit
        nsjail_args.push("--rlimit_fsize".to_string());
        nsjail_args.push((self.config.max_file_size_mb * 1024 * 1024).to_string());

        // Open files limit
        nsjail_args.push("--rlimit_nofile".to_string());
        nsjail_args.push(self.config.max_open_files.to_string());

        // Time limit
        nsjail_args.push("--time_limit".to_string());
        nsjail_args.push(self.config.max_wall_time_secs.to_string());

        // Network
        if self.config.enable_network {
            nsjail_args.push("--disable_clone_newnet".to_string());
        }

        // Mount points
        for mount in &self.config.mount_points {
            let mount_spec = if mount.readonly {
                format!("{}:{}:ro", mount.source.display(), mount.target.display())
            } else {
                format!("{}:{}", mount.source.display(), mount.target.display())
            };

            nsjail_args.push("--bindmount".to_string());
            nsjail_args.push(mount_spec);
        }

        // User/group
        nsjail_args.push("--user".to_string());
        nsjail_args.push("nobody".to_string());
        nsjail_args.push("--group".to_string());
        nsjail_args.push("nogroup".to_string());

        // Disable proc
        nsjail_args.push("--disable_proc".to_string());

        // Command separator
        nsjail_args.push("--".to_string());

        // Actual command to execute
        nsjail_args.push(command.to_string());
        nsjail_args.extend_from_slice(args);

        Ok(nsjail_args)
    }

    /// Check if nsjail is available
    pub fn is_available() -> bool {
        #[cfg(not(target_os = "linux"))]
        {
            false
        }

        #[cfg(target_os = "linux")]
        {
            Command::new("which")
                .arg("nsjail")
                .output()
                .map(|output| output.status.success())
                .unwrap_or(false)
        }
    }
}

impl Drop for SandboxedProcess {
    fn drop(&mut self) {
        let _ = self.kill();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_config_default() {
        let config = SandboxConfig::default();
        assert_eq!(config.max_memory_mb, 512);
        assert_eq!(config.max_cpu_time_secs, 30);
    }

    #[test]
    fn test_is_available() {
        // Should return false on non-Linux or true/false on Linux
        let available = SandboxedProcess::is_available();
        println!("nsjail available: {}", available);
    }

    #[test]
    #[cfg(target_os = "linux")]
    fn test_build_nsjail_args() {
        let config = SandboxConfig::default();
        let sandbox = SandboxedProcess::new(config);

        let args = sandbox
            .build_nsjail_args("echo", &["hello".to_string()])
            .unwrap();

        assert!(args.contains(&"--hostname".to_string()));
        assert!(args.contains(&"echo".to_string()));
    }
}

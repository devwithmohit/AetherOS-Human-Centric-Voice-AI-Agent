//! Command executor with timeout and resource limits

use crate::platform::Platform;
use crate::sandbox::{Sandbox, SandboxConfig};
use crate::whitelist::{CommandWhitelist, WhitelistEntry};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Stdio;
use std::time::Duration;
use thiserror::Error;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command as TokioCommand;
use tokio::time::timeout;
use tracing::{debug, info};

/// Executor errors
#[derive(Error, Debug)]
pub enum ExecutorError {
    #[error("Command not whitelisted: {0}")]
    CommandNotWhitelisted(String),

    #[error("Invalid arguments: {0}")]
    InvalidArguments(String),

    #[error("Command execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Timeout exceeded: {0}s")]
    TimeoutExceeded(u64),

    #[error("Sandbox error: {0}")]
    SandboxError(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),
}

/// Command execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandResult {
    /// Command executed
    pub command: String,

    /// Arguments provided
    pub args: Vec<String>,

    /// Standard output
    pub stdout: String,

    /// Standard error
    pub stderr: String,

    /// Exit code
    pub exit_code: i32,

    /// Execution duration (milliseconds)
    pub duration_ms: u64,

    /// Whether command succeeded
    pub success: bool,
}

/// Executor configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutorConfig {
    /// Maximum command timeout (seconds)
    pub max_timeout_secs: u64,

    /// Enable sandbox mode
    pub enable_sandbox: bool,

    /// Maximum output size (bytes)
    pub max_output_bytes: usize,

    /// Working directory
    pub working_dir: Option<String>,

    /// Environment variables
    pub env_vars: HashMap<String, String>,

    /// Enable shell execution (DANGEROUS)
    pub allow_shell: bool,
}

impl Default for ExecutorConfig {
    fn default() -> Self {
        Self {
            max_timeout_secs: 5,
            enable_sandbox: true,
            max_output_bytes: 1024 * 1024, // 1MB
            working_dir: None,
            env_vars: HashMap::new(),
            allow_shell: false,
        }
    }
}

/// Command executor
pub struct CommandExecutor {
    config: ExecutorConfig,
    whitelist: CommandWhitelist,
    sandbox: Option<Sandbox>,
    platform: Platform,
}

impl CommandExecutor {
    /// Create new executor
    pub fn new(config: ExecutorConfig, whitelist: CommandWhitelist) -> Self {
        let sandbox = if config.enable_sandbox {
            Some(Sandbox::new(SandboxConfig::default()))
        } else {
            None
        };

        Self {
            config,
            whitelist,
            sandbox,
            platform: Platform::current(),
        }
    }

    /// Execute command
    pub async fn execute(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<CommandResult, ExecutorError> {
        let start_time = std::time::Instant::now();

        // Validate command is whitelisted
        let whitelist_entry = self
            .whitelist
            .get(command)
            .ok_or_else(|| ExecutorError::CommandNotWhitelisted(command.to_string()))?;

        // Validate arguments
        self.validate_args(args, whitelist_entry)?;

        info!(
            "Executing command: {} with {} args",
            command,
            args.len()
        );

        // Execute with timeout
        let result = timeout(
            Duration::from_secs(self.config.max_timeout_secs),
            self.execute_internal(command, args, whitelist_entry),
        )
        .await
        .map_err(|_| ExecutorError::TimeoutExceeded(self.config.max_timeout_secs))?;

        let duration_ms = start_time.elapsed().as_millis() as u64;

        match result {
            Ok((stdout, stderr, exit_code)) => {
                let success = exit_code == 0;

                Ok(CommandResult {
                    command: command.to_string(),
                    args: args.to_vec(),
                    stdout,
                    stderr,
                    exit_code,
                    duration_ms,
                    success,
                })
            }
            Err(e) => Err(e),
        }
    }

    /// Execute command internally
    async fn execute_internal(
        &self,
        command: &str,
        args: &[String],
        _entry: &WhitelistEntry,
    ) -> Result<(String, String, i32), ExecutorError> {
        // Resolve full command path
        let cmd_path = self.resolve_command_path(command)?;

        debug!("Resolved command path: {}", cmd_path);

        // Build command
        let mut cmd = if self.config.enable_sandbox && self.sandbox.is_some() {
            // Execute through sandbox
            self.build_sandboxed_command(&cmd_path, args)?
        } else {
            // Direct execution
            let mut c = TokioCommand::new(&cmd_path);
            c.args(args);
            c
        };

        // Set working directory
        if let Some(ref wd) = self.config.working_dir {
            cmd.current_dir(wd);
        }

        // Set environment variables
        for (key, value) in &self.config.env_vars {
            cmd.env(key, value);
        }

        // Configure stdio
        cmd.stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Spawn process
        let mut child = cmd
            .spawn()
            .map_err(|e| ExecutorError::ExecutionFailed(e.to_string()))?;

        // Read stdout
        let stdout_handle = child.stdout.take().ok_or_else(|| {
            ExecutorError::ExecutionFailed("Failed to capture stdout".to_string())
        })?;

        let stderr_handle = child.stderr.take().ok_or_else(|| {
            ExecutorError::ExecutionFailed("Failed to capture stderr".to_string())
        })?;

        // Read output streams
        let stdout_task = tokio::spawn(async move {
            let reader = BufReader::new(stdout_handle);
            let mut lines = reader.lines();
            let mut output = String::new();

            while let Ok(Some(line)) = lines.next_line().await {
                output.push_str(&line);
                output.push('\n');
            }

            output
        });

        let stderr_task = tokio::spawn(async move {
            let reader = BufReader::new(stderr_handle);
            let mut lines = reader.lines();
            let mut output = String::new();

            while let Ok(Some(line)) = lines.next_line().await {
                output.push_str(&line);
                output.push('\n');
            }

            output
        });

        // Wait for process
        let status = child
            .wait()
            .await
            .map_err(|e| ExecutorError::ExecutionFailed(e.to_string()))?;

        // Collect output
        let stdout = stdout_task
            .await
            .map_err(|e| ExecutorError::ExecutionFailed(e.to_string()))?;
        let stderr = stderr_task
            .await
            .map_err(|e| ExecutorError::ExecutionFailed(e.to_string()))?;

        // Check output size limits
        if stdout.len() + stderr.len() > self.config.max_output_bytes {
            return Err(ExecutorError::ResourceLimitExceeded(
                "Output exceeds maximum size".to_string(),
            ));
        }

        let exit_code = status.code().unwrap_or(-1);

        Ok((stdout, stderr, exit_code))
    }

    /// Build sandboxed command
    fn build_sandboxed_command(
        &self,
        command: &str,
        args: &[String],
    ) -> Result<TokioCommand, ExecutorError> {
        if let Some(ref sandbox) = self.sandbox {
            sandbox
                .wrap_command(command, args)
                .map_err(|e| ExecutorError::SandboxError(e.to_string()))
        } else {
            Err(ExecutorError::SandboxError(
                "Sandbox not available".to_string(),
            ))
        }
    }

    /// Resolve command path
    fn resolve_command_path(&self, command: &str) -> Result<String, ExecutorError> {
        // Check if it's already an absolute path
        if std::path::Path::new(command).is_absolute() {
            return Ok(command.to_string());
        }

        // Try to find in PATH
        if let Ok(path) = which::which(command) {
            return Ok(path.to_string_lossy().to_string());
        }

        // Use command as-is if not found (will fail at execution)
        Ok(command.to_string())
    }

    /// Validate arguments
    fn validate_args(
        &self,
        args: &[String],
        entry: &WhitelistEntry,
    ) -> Result<(), ExecutorError> {
        // Check max args
        if let Some(max) = entry.max_args {
            if args.len() > max {
                return Err(ExecutorError::InvalidArguments(format!(
                    "Too many arguments: {} > {}",
                    args.len(),
                    max
                )));
            }
        }

        // Validate argument patterns
        for (i, arg) in args.iter().enumerate() {
            // Check for shell injection attempts
            if self.contains_shell_metacharacters(arg) && !self.config.allow_shell {
                return Err(ExecutorError::InvalidArguments(format!(
                    "Argument {} contains shell metacharacters: {}",
                    i, arg
                )));
            }

            // Validate against allowed patterns
            if let Some(ref patterns) = entry.allowed_arg_patterns {
                let mut matches = false;
                for pattern in patterns {
                    if let Ok(re) = regex::Regex::new(pattern) {
                        if re.is_match(arg) {
                            matches = true;
                            break;
                        }
                    }
                }

                if !matches && !patterns.is_empty() {
                    return Err(ExecutorError::InvalidArguments(format!(
                        "Argument {} does not match allowed patterns: {}",
                        i, arg
                    )));
                }
            }
        }

        Ok(())
    }

    /// Check for shell metacharacters
    fn contains_shell_metacharacters(&self, s: &str) -> bool {
        let metacharacters = [
            ';', '&', '|', '>', '<', '`', '$', '(', ')', '{', '}', '[', ']', '\\', '\n', '*', '?',
        ];

        s.chars().any(|c| metacharacters.contains(&c))
    }

    /// Get platform info
    pub fn platform(&self) -> &Platform {
        &self.platform
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_executor_config_default() {
        let config = ExecutorConfig::default();
        assert_eq!(config.max_timeout_secs, 5);
        assert!(config.enable_sandbox);
        assert!(!config.allow_shell);
    }

    #[test]
    fn test_shell_metacharacter_detection() {
        let config = ExecutorConfig::default();
        let whitelist = CommandWhitelist::default();
        let executor = CommandExecutor::new(config, whitelist);

        assert!(executor.contains_shell_metacharacters("test; rm -rf /"));
        assert!(executor.contains_shell_metacharacters("test && malicious"));
        assert!(executor.contains_shell_metacharacters("test | grep"));
        assert!(!executor.contains_shell_metacharacters("test"));
        assert!(!executor.contains_shell_metacharacters("test.txt"));
    }

    #[tokio::test]
    async fn test_simple_command_echo() {
        let mut whitelist = CommandWhitelist::default();
        whitelist.add_command(
            "echo",
            WhitelistEntry {
                command: "echo".to_string(),
                description: Some("Echo text".to_string()),
                max_args: Some(10),
                allowed_arg_patterns: None,
                requires_sudo: false,
            },
        );

        let config = ExecutorConfig {
            enable_sandbox: false, // Disable sandbox for simple test
            ..Default::default()
        };

        let executor = CommandExecutor::new(config, whitelist);

        let result = executor
            .execute("echo", &["Hello".to_string(), "World".to_string()])
            .await;

        assert!(result.is_ok());
        let cmd_result = result.unwrap();
        assert!(cmd_result.success);
        assert!(cmd_result.stdout.contains("Hello"));
    }
}

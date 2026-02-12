//! Command whitelist for allowed OS commands

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Whitelist errors
#[derive(Error, Debug)]
pub enum WhitelistError {
    #[error("Command not found: {0}")]
    CommandNotFound(String),

    #[error("Failed to load whitelist: {0}")]
    LoadFailed(String),

    #[error("Invalid whitelist format: {0}")]
    InvalidFormat(String),
}

/// Whitelist entry for a command
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WhitelistEntry {
    /// Command name
    pub command: String,

    /// Description
    pub description: Option<String>,

    /// Maximum number of arguments
    pub max_args: Option<usize>,

    /// Allowed argument patterns (regex)
    pub allowed_arg_patterns: Option<Vec<String>>,

    /// Requires sudo/admin
    pub requires_sudo: bool,
}

/// Command whitelist
#[derive(Debug, Clone)]
pub struct CommandWhitelist {
    entries: HashMap<String, WhitelistEntry>,
}

impl Default for CommandWhitelist {
    fn default() -> Self {
        Self::with_default_commands()
    }
}

impl CommandWhitelist {
    /// Create empty whitelist
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
        }
    }

    /// Create whitelist with default safe commands
    pub fn with_default_commands() -> Self {
        let mut whitelist = Self::new();

        // File listing
        whitelist.add_command(
            "ls",
            WhitelistEntry {
                command: "ls".to_string(),
                description: Some("List directory contents".to_string()),
                max_args: Some(20),
                allowed_arg_patterns: Some(vec![
                    r"^-[alhtrs]+$".to_string(),  // Flags
                    r"^[a-zA-Z0-9\./_-]+$".to_string(), // Paths
                ]),
                requires_sudo: false,
            },
        );

        // File reading
        whitelist.add_command(
            "cat",
            WhitelistEntry {
                command: "cat".to_string(),
                description: Some("Read file contents".to_string()),
                max_args: Some(10),
                allowed_arg_patterns: Some(vec![r"^[a-zA-Z0-9\./_-]+$".to_string()]),
                requires_sudo: false,
            },
        );

        // Text search
        whitelist.add_command(
            "grep",
            WhitelistEntry {
                command: "grep".to_string(),
                description: Some("Search text patterns".to_string()),
                max_args: Some(20),
                allowed_arg_patterns: Some(vec![
                    r"^-[irnvEFP]+$".to_string(), // Flags
                    r"^[a-zA-Z0-9\./_\-\s]+$".to_string(), // Patterns and paths
                ]),
                requires_sudo: false,
            },
        );

        // File info
        whitelist.add_command(
            "stat",
            WhitelistEntry {
                command: "stat".to_string(),
                description: Some("File information".to_string()),
                max_args: Some(5),
                allowed_arg_patterns: Some(vec![
                    r"^-[c]+$".to_string(),
                    r"^[a-zA-Z0-9\./_-]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        // Directory navigation (read-only)
        whitelist.add_command(
            "pwd",
            WhitelistEntry {
                command: "pwd".to_string(),
                description: Some("Print working directory".to_string()),
                max_args: Some(0),
                allowed_arg_patterns: None,
                requires_sudo: false,
            },
        );

        // File finding
        whitelist.add_command(
            "find",
            WhitelistEntry {
                command: "find".to_string(),
                description: Some("Find files".to_string()),
                max_args: Some(30),
                allowed_arg_patterns: Some(vec![
                    r"^-[name|type|size|mtime]+$".to_string(),
                    r"^[a-zA-Z0-9\./_\-\*\?]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        // File head/tail
        whitelist.add_command(
            "head",
            WhitelistEntry {
                command: "head".to_string(),
                description: Some("Show file beginning".to_string()),
                max_args: Some(5),
                allowed_arg_patterns: Some(vec![
                    r"^-n\d+$".to_string(),
                    r"^[a-zA-Z0-9\./_-]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        whitelist.add_command(
            "tail",
            WhitelistEntry {
                command: "tail".to_string(),
                description: Some("Show file end".to_string()),
                max_args: Some(5),
                allowed_arg_patterns: Some(vec![
                    r"^-n\d+$".to_string(),
                    r"^[a-zA-Z0-9\./_-]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        // Word count
        whitelist.add_command(
            "wc",
            WhitelistEntry {
                command: "wc".to_string(),
                description: Some("Count words/lines".to_string()),
                max_args: Some(10),
                allowed_arg_patterns: Some(vec![
                    r"^-[lwc]+$".to_string(),
                    r"^[a-zA-Z0-9\./_-]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        // Disk usage
        whitelist.add_command(
            "du",
            WhitelistEntry {
                command: "du".to_string(),
                description: Some("Disk usage".to_string()),
                max_args: Some(10),
                allowed_arg_patterns: Some(vec![
                    r"^-[shc]+$".to_string(),
                    r"^[a-zA-Z0-9\./_-]+$".to_string(),
                ]),
                requires_sudo: false,
            },
        );

        // Echo (for testing)
        whitelist.add_command(
            "echo",
            WhitelistEntry {
                command: "echo".to_string(),
                description: Some("Echo text".to_string()),
                max_args: Some(50),
                allowed_arg_patterns: None, // Allow any args for echo
                requires_sudo: false,
            },
        );

        // Date/time
        whitelist.add_command(
            "date",
            WhitelistEntry {
                command: "date".to_string(),
                description: Some("Show date/time".to_string()),
                max_args: Some(5),
                allowed_arg_patterns: Some(vec![r"^[\+%a-zA-Z0-9\-:/ ]+$".to_string()]),
                requires_sudo: false,
            },
        );

        whitelist
    }

    /// Add command to whitelist
    pub fn add_command(&mut self, name: &str, entry: WhitelistEntry) {
        self.entries.insert(name.to_string(), entry);
    }

    /// Remove command from whitelist
    pub fn remove_command(&mut self, name: &str) -> Option<WhitelistEntry> {
        self.entries.remove(name)
    }

    /// Get command entry
    pub fn get(&self, name: &str) -> Option<&WhitelistEntry> {
        self.entries.get(name)
    }

    /// Check if command is whitelisted
    pub fn is_whitelisted(&self, name: &str) -> bool {
        self.entries.contains_key(name)
    }

    /// Get all whitelisted commands
    pub fn commands(&self) -> Vec<String> {
        self.entries.keys().cloned().collect()
    }

    /// Load from YAML file
    pub fn from_yaml(yaml: &str) -> Result<Self, WhitelistError> {
        let entries: HashMap<String, WhitelistEntry> = serde_yaml::from_str(yaml)
            .map_err(|e| WhitelistError::InvalidFormat(e.to_string()))?;

        Ok(Self { entries })
    }

    /// Export to YAML
    pub fn to_yaml(&self) -> Result<String, WhitelistError> {
        serde_yaml::to_string(&self.entries)
            .map_err(|e| WhitelistError::InvalidFormat(e.to_string()))
    }

    /// Load from JSON file
    pub fn from_json(json: &str) -> Result<Self, WhitelistError> {
        let entries: HashMap<String, WhitelistEntry> = serde_json::from_str(json)
            .map_err(|e| WhitelistError::InvalidFormat(e.to_string()))?;

        Ok(Self { entries })
    }

    /// Export to JSON
    pub fn to_json(&self) -> Result<String, WhitelistError> {
        serde_json::to_string_pretty(&self.entries)
            .map_err(|e| WhitelistError::InvalidFormat(e.to_string()))
    }

    /// Get number of whitelisted commands
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Check if whitelist is empty
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_whitelist() {
        let whitelist = CommandWhitelist::default();
        assert!(whitelist.is_whitelisted("ls"));
        assert!(whitelist.is_whitelisted("cat"));
        assert!(whitelist.is_whitelisted("grep"));
        assert!(!whitelist.is_whitelisted("rm"));
        assert!(!whitelist.is_whitelisted("sudo"));
    }

    #[test]
    fn test_add_remove_command() {
        let mut whitelist = CommandWhitelist::new();
        assert!(!whitelist.is_whitelisted("test"));

        whitelist.add_command(
            "test",
            WhitelistEntry {
                command: "test".to_string(),
                description: None,
                max_args: None,
                allowed_arg_patterns: None,
                requires_sudo: false,
            },
        );

        assert!(whitelist.is_whitelisted("test"));

        let removed = whitelist.remove_command("test");
        assert!(removed.is_some());
        assert!(!whitelist.is_whitelisted("test"));
    }

    #[test]
    fn test_whitelist_json_roundtrip() {
        let whitelist = CommandWhitelist::default();

        let json = whitelist.to_json().unwrap();
        let restored = CommandWhitelist::from_json(&json).unwrap();

        assert_eq!(whitelist.len(), restored.len());
        assert!(restored.is_whitelisted("ls"));
    }

    #[test]
    fn test_whitelist_commands_list() {
        let whitelist = CommandWhitelist::default();
        let commands = whitelist.commands();

        assert!(commands.contains(&"ls".to_string()));
        assert!(commands.contains(&"cat".to_string()));
        assert!(commands.contains(&"echo".to_string()));
        assert!(commands.len() > 5);
    }
}

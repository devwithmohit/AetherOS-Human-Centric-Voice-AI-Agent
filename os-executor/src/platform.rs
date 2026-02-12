//! Platform abstraction for OS-specific functionality

use serde::{Deserialize, Serialize};
use std::env;

/// Platform identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Platform {
    Linux,
    MacOS,
    Windows,
    Unknown,
}

impl Platform {
    /// Get current platform
    pub fn current() -> Self {
        if cfg!(target_os = "linux") {
            Platform::Linux
        } else if cfg!(target_os = "macos") {
            Platform::MacOS
        } else if cfg!(target_os = "windows") {
            Platform::Windows
        } else {
            Platform::Unknown
        }
    }

    /// Check if platform is Unix-like
    pub fn is_unix(&self) -> bool {
        matches!(self, Platform::Linux | Platform::MacOS)
    }

    /// Check if platform is Windows
    pub fn is_windows(&self) -> bool {
        matches!(self, Platform::Windows)
    }

    /// Get platform name as string
    pub fn name(&self) -> &str {
        match self {
            Platform::Linux => "linux",
            Platform::MacOS => "macos",
            Platform::Windows => "windows",
            Platform::Unknown => "unknown",
        }
    }

    /// Get default shell for platform
    pub fn default_shell(&self) -> &str {
        match self {
            Platform::Linux | Platform::MacOS => "/bin/sh",
            Platform::Windows =>  "cmd.exe",
            Platform::Unknown => "sh",
        }
    }

    /// Get path separator for platform
    pub fn path_separator(&self) -> char {
        match self {
            Platform::Linux | Platform::MacOS => ':',
            Platform::Windows => ';',
            Platform::Unknown => ':',
        }
    }

    /// Get file separator for platform
    pub fn file_separator(&self) -> char {
        match self {
            Platform::Linux | Platform::MacOS => '/',
            Platform::Windows => '\\',
            Platform::Unknown => '/',
        }
    }
}

/// Platform information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformInfo {
    /// Platform type
    pub platform: Platform,

    /// Operating system name
    pub os_name: String,

    /// OS version
    pub os_version: String,

    /// Architecture
    pub arch: String,

    /// Number of CPUs
    pub cpu_count: usize,

    /// Total memory (MB)
    pub total_memory_mb: u64,

    /// Hostname
    pub hostname: String,

    /// Current user
    pub username: String,

    /// Home directory
    pub home_dir: Option<String>,

    /// Supports sandboxing
    pub has_sandbox_support: bool,
}

impl PlatformInfo {
    /// Get platform information
    pub fn detect() -> Self {
        let platform = Platform::current();

        Self {
            platform,
            os_name: Self::get_os_name(),
            os_version: Self::get_os_version(),
            arch: Self::get_arch(),
            cpu_count: Self::get_cpu_count(),
            total_memory_mb: Self::get_total_memory(),
            hostname: Self::get_hostname(),
            username: Self::get_username(),
            home_dir: Self::get_home_dir(),
            has_sandbox_support: Self::check_sandbox_support(platform),
        }
    }

    fn get_os_name() -> String {
        env::consts::OS.to_string()
    }

    fn get_os_version() -> String {
        #[cfg(target_os = "linux")]
        {
            std::fs::read_to_string("/etc/os-release")
                .ok()
                .and_then(|s| {
                    s.lines()
                        .find(|l| l.starts_with("VERSION_ID="))
                        .map(|l| l.trim_start_matches("VERSION_ID=").trim_matches('"').to_string())
                })
                .unwrap_or_else(|| "unknown".to_string())
        }

        #[cfg(not(target_os = "linux"))]
        {
            "unknown".to_string()
        }
    }

    fn get_arch() -> String {
        env::consts::ARCH.to_string()
    }

    fn get_cpu_count() -> usize {
        num_cpus::get()
    }

    fn get_total_memory() -> u64 {
        #[cfg(target_os = "linux")]
        {
            std::fs::read_to_string("/proc/meminfo")
                .ok()
                .and_then(|s| {
                    s.lines()
                        .find(|l| l.starts_with("MemTotal:"))
                        .and_then(|l| {
                            l.split_whitespace()
                                .nth(1)
                                .and_then(|n| n.parse::<u64>().ok())
                                .map(|kb| kb / 1024) // Convert KB to MB
                        })
                })
                .unwrap_or(0)
        }

        #[cfg(not(target_os = "linux"))]
        {
            0
        }
    }

    fn get_hostname() -> String {
        hostname::get()
            .ok()
            .and_then(|h| h.into_string().ok())
            .unwrap_or_else(|| "unknown".to_string())
    }

    fn get_username() -> String {
        env::var("USER")
            .or_else(|_| env::var("USERNAME"))
            .unwrap_or_else(|_| "unknown".to_string())
    }

    fn get_home_dir() -> Option<String> {
        env::var("HOME")
            .or_else(|_| env::var("USERPROFILE"))
            .ok()
    }

    fn check_sandbox_support(platform: Platform) -> bool {
        match platform {
            Platform::Linux => true,  // Has nsjail, seccomp, etc.
            Platform::MacOS => true,  // Has sandbox-exec
            Platform::Windows => false, // Limited sandbox support
            Platform::Unknown => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_detection() {
        let platform = Platform::current();
        assert_ne!(platform, Platform::Unknown);
    }

    #[test]
    fn test_platform_properties() {
        let platform = Platform::current();

        if cfg!(unix) {
            assert!(platform.is_unix());
            assert_eq!(platform.default_shell(), "/bin/sh");
            assert_eq!(platform.path_separator(), ':');
            assert_eq!(platform.file_separator(), '/');
        }

        if cfg!(windows) {
            assert!(platform.is_windows());
            assert_eq!(platform.default_shell(), "cmd.exe");
            assert_eq!(platform.path_separator(), ';');
            assert_eq!(platform.file_separator(), '\\');
        }
    }

    #[test]
    fn test_platform_info() {
        let info = PlatformInfo::detect();

        assert!(!info.os_name.is_empty());
        assert!(!info.arch.is_empty());
        assert!(info.cpu_count > 0);
        assert!(!info.hostname.is_empty());
        assert!(!info.username.is_empty());

        println!("Platform: {:?}", info.platform);
        println!("OS: {} {}", info.os_name, info.os_version);
        println!("Arch: {}", info.arch);
        println!("CPUs: {}", info.cpu_count);
        println!("Memory: {} MB", info.total_memory_mb);
        println!("Hostname: {}", info.hostname);
        println!("User: {}", info.username);
        println!("Sandbox support: {}", info.has_sandbox_support);
    }
}

// Helper to get number of CPUs - using external crate would be better
mod num_cpus {
    pub fn get() -> usize {
        #[cfg(unix)]
        {
            unsafe {
                let count = libc::sysconf(libc::_SC_NPROCESSORS_ONLN);
                if count > 0 {
                    count as usize
                } else {
                    1
                }
            }
        }

        #[cfg(windows)]
        {
            use std::mem;
            unsafe {
                let mut system_info: winapi::um::sysinfoapi::SYSTEM_INFO = mem::zeroed();
                winapi::um::sysinfoapi::GetSystemInfo(&mut system_info);
                system_info.dwNumberOfProcessors as usize
            }
        }

        #[cfg(not(any(unix, windows)))]
        {
            1
        }
    }
}

// Helper to get hostname
mod hostname {
    use std::ffi::OsString;

    pub fn get() -> std::io::Result<OsString> {
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            let mut buf = vec![0u8; 256];
            unsafe {
                if libc::gethostname(buf.as_mut_ptr() as *mut libc::c_char, buf.len()) == 0 {
                    let len = buf.iter().position(|&b| b == 0).unwrap_or(buf.len());
                    buf.truncate(len);
                    Ok(OsString::from_vec(buf))
                } else {
                    Err(std::io::Error::last_os_error())
                }
            }
        }

        #[cfg(windows)]
        {
            std::env::var_os("COMPUTERNAME")
                .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, "No hostname"))
        }

        #[cfg(not(any(unix, windows)))]
        {
            Ok(OsString::from("unknown"))
        }
    }
}

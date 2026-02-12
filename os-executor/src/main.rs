//! OS Executor CLI

use os_executor::{CommandExecutor, CommandWhitelist, ExecutorConfig, PlatformInfo};
use std::env;
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_usage();
        return Ok(());
    }

    match args[1].as_str() {
        "info" => {
            show_platform_info();
        }
        "list" => {
            list_commands();
        }
        "exec" => {
            if args.len() < 3 {
                eprintln!("Usage: os-executor exec <command> [args...]");
                std::process::exit(1);
            }

            let command = &args[2];
            let cmd_args: Vec<String> = args[3..].to_vec();

            execute_command(command, &cmd_args).await?;
        }
        "test" => {
            run_tests().await?;
        }
        _ => {
            eprintln!("Unknown command: {}", args[1]);
            print_usage();
            std::process::exit(1);
        }
    }

    Ok(())
}

fn print_usage() {
    println!("OS Executor v{}", os_executor::VERSION);
    println!();
    println!("Usage:");
    println!("  os-executor info              Show platform information");
    println!("  os-executor list              List whitelisted commands");
    println!("  os-executor exec <cmd> [args] Execute a whitelisted command");
    println!("  os-executor test              Run self-tests");
    println!();
    println!("Examples:");
    println!("  os-executor exec ls -la");
    println!("  os-executor exec cat /etc/hosts");
    println!("  os-executor exec echo Hello World");
}

fn show_platform_info() {
    let info = PlatformInfo::detect();

    println!("Platform Information:");
    println!("  OS: {} ({})", info.os_name, info.platform.name());
    println!("  Version: {}", info.os_version);
    println!("  Architecture: {}", info.arch);
    println!("  CPUs: {}", info.cpu_count);
    println!("  Memory: {} MB", info.total_memory_mb);
    println!("  Hostname: {}", info.hostname);
    println!("  User: {}", info.username);
    println!("  Home: {}", info.home_dir.as_deref().unwrap_or("unknown"));
    println!("  Sandbox Support: {}", info.has_sandbox_support);
}

fn list_commands() {
    let whitelist = CommandWhitelist::default();
    let commands = whitelist.commands();

    println!("Whitelisted Commands ({}):", commands.len());
    println!();

    let mut sorted_commands = commands;
    sorted_commands.sort();

    for cmd in sorted_commands {
        if let Some(entry) = whitelist.get(&cmd) {
            println!("  {} - {}", cmd, entry.description.as_deref().unwrap_or("No description"));

            if let Some(max) = entry.max_args {
                println!("    Max args: {}", max);
            }

            if entry.requires_sudo {
                println!("    Requires elevated privileges");
            }
        }
    }
}

async fn execute_command(command: &str, args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let config = ExecutorConfig {
        enable_sandbox: false, // Disable sandbox for CLI usage
        ..Default::default()
    };

    let whitelist = CommandWhitelist::default();
    let executor = CommandExecutor::new(config, whitelist);

    println!("Executing: {} {}", command, args.join(" "));
    println!();

    let result = executor.execute(command, args).await?;

    // Print stdout
    if !result.stdout.is_empty() {
        println!("{}", result.stdout.trim());
    }

    // Print stderr
    if !result.stderr.is_empty() {
        eprintln!("{}", result.stderr.trim());
    }

    println!();
    println!("Exit code: {}", result.exit_code);
    println!("Duration: {} ms", result.duration_ms);

    if !result.success {
        std::process::exit(result.exit_code);
    }

    Ok(())
}

async fn run_tests() -> Result<(), Box<dyn std::error::Error>> {
    println!("Running OS Executor Tests...");
    println!();

    let config = ExecutorConfig {
        enable_sandbox: false,
        ..Default::default()
    };

    let whitelist = CommandWhitelist::default();
    let executor = CommandExecutor::new(config, whitelist);

    // Test 1: Echo command
    println!("Test 1: Echo command");
    let result = executor.execute("echo", &["Test".to_string()]).await?;
    assert!(result.success);
    assert!(result.stdout.contains("Test"));
    println!("  ✓ Passed");

    // Test 2: Date command
    println!("Test 2: Date command");
    let result = executor.execute("date", &[]).await?;
    assert!(result.success);
    println!("  ✓ Passed");

    // Test 3: Non-whitelisted command (should fail)
    println!("Test 3: Non-whitelisted command");
    let result = executor.execute("rm", &["-rf".to_string(), "/".to_string()]).await;
    assert!(result.is_err());
    println!("  ✓ Passed (correctly blocked)");

    // Test 4: Shell injection attempt
    println!("Test 4: Shell injection protection");
    let result = executor.execute("echo", &["test; rm -rf /".to_string()]).await;
    // Should fail - shell metacharacters are blocked for security
    assert!(result.is_err());
    println!("  ✓ Passed (shell metacharacters blocked)");

    println!();
    println!("All tests passed! ✓");

    Ok(())
}

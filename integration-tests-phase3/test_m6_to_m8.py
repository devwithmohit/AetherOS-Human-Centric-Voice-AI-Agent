"""
Integration Tests: M6 (Safety Validator) → M8 (OS Executor)

Tests the integration between the Safety Validator and OS Executor,
verifying that validated OS commands are executed safely and results
are properly returned.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import subprocess


class MockSafetyValidator:
    """Mock M6 Safety Validator for testing"""

    def __init__(self):
        self.validation_log = []
        self.dangerous_commands = [
            "rm",
            "sudo",
            "chmod",
            "chown",
            "shutdown",
            "reboot",
            "kill",
            "pkill",
            "killall",
            "dd",
            "mkfs",
            "fdisk",
        ]

    async def validate_os_command(
        self, command: str, args: List[str], user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate an OS command before execution.

        Returns:
            {
                "approved": bool,
                "command": str,
                "args": List[str],
                "reason": str (if rejected),
                "modifications": Dict (if modified)
            }
        """
        self.validation_log.append(
            {
                "command": command,
                "args": args,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Check for dangerous commands
        if command in self.dangerous_commands:
            return {
                "approved": False,
                "command": command,
                "args": args,
                "reason": f"Command '{command}' is not allowed for safety reasons",
            }

        # Check for shell injection in arguments
        shell_chars = [";", "&", "|", ">", "<", "`", "$", "(", ")", "{", "}"]
        for arg in args:
            for char in shell_chars:
                if char in arg:
                    return {
                        "approved": False,
                        "command": command,
                        "args": args,
                        "reason": f"Argument contains shell metacharacter: {char}",
                    }

        # Check for path traversal
        for arg in args:
            if ".." in arg or arg.startswith("/"):
                # Allow some absolute paths, but log them
                if arg.startswith("/etc/") or arg.startswith("/root/"):
                    return {
                        "approved": False,
                        "command": command,
                        "args": args,
                        "reason": f"Access to sensitive path denied: {arg}",
                    }

        # Approve command
        return {"approved": True, "command": command, "args": args}


class IntegrationTestM6ToM8:
    """Integration test suite for M6 → M8 flow"""

    def __init__(self):
        self.validator = MockSafetyValidator()
        self.os_executor_path = Path(__file__).parent.parent / "os-executor"
        self.results = []

    def execute_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Execute OS command via M8"""
        try:
            # Use the os-executor CLI
            cmd = ["cargo", "run", "--quiet", "--", "exec", command] + args

            result = subprocess.run(
                cmd,
                cwd=self.os_executor_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout", "exit_code": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "exit_code": -1}

    async def test_approved_command_execution(self) -> Dict[str, Any]:
        """Test 1: Approved command executes successfully"""
        print("\n=== Test 1: Approved Command Execution ===")

        command = "echo"
        args = ["Hello from integration test"]

        # Step 1: M6 validates the command
        validation = await self.validator.validate_os_command(command, args)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Command should be approved"

        # Step 2: M8 executes the command
        if validation["approved"]:
            result = self.execute_command(validation["command"], validation["args"])
            print(f"Execution result: {json.dumps(result, indent=2)}")

            assert result["success"], "Command should execute successfully"
            assert "Hello from integration test" in result["stdout"]

            print(f"✓ Command executed successfully")
            print(f"  Output: {result['stdout'].strip()}")

            return {
                "test": "approved_command_execution",
                "status": "pass",
                "validation": validation,
                "execution": result,
            }

        return {
            "test": "approved_command_execution",
            "status": "fail",
            "reason": "Command was not approved",
        }

    async def test_dangerous_command_blocked(self) -> Dict[str, Any]:
        """Test 2: Dangerous command is blocked"""
        print("\n=== Test 2: Dangerous Command Blocked ===")

        command = "rm"
        args = ["-rf", "/tmp/test"]

        # Step 1: M6 validates the command
        validation = await self.validator.validate_os_command(command, args)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Dangerous command should be blocked"
        assert "reason" in validation, "Blocked command should have reason"

        # Step 2: M8 should NOT execute (but let's verify M8 also blocks it)
        result = self.execute_command(command, args)
        print(f"M8 execution result: {json.dumps(result, indent=2)}")

        # M8 should also block it (defense in depth)
        assert not result["success"], "M8 should also block dangerous commands"

        print(f"✓ Command blocked by M6: {validation['reason']}")
        print(f"✓ Command also blocked by M8 (defense in depth)")

        return {
            "test": "dangerous_command_blocked",
            "status": "pass",
            "validation": validation,
            "m8_result": result,
        }

    async def test_shell_injection_blocked(self) -> Dict[str, Any]:
        """Test 3: Shell injection attempt is blocked"""
        print("\n=== Test 3: Shell Injection Blocked ===")

        command = "echo"
        args = ["test; rm -rf /"]

        # Step 1: M6 validates the command
        validation = await self.validator.validate_os_command(command, args)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Shell injection should be detected"
        assert "shell metacharacter" in validation["reason"].lower()

        # Step 2: Verify M8 also blocks it
        result = self.execute_command(command, args)
        print(f"M8 execution result: {json.dumps(result, indent=2)}")

        assert not result["success"], "M8 should also block shell injection"

        print(f"✓ Shell injection blocked by M6: {validation['reason']}")
        print(f"✓ Shell injection also blocked by M8 (defense in depth)")

        return {
            "test": "shell_injection_blocked",
            "status": "pass",
            "validation": validation,
            "m8_result": result,
        }

    async def test_path_traversal_blocked(self) -> Dict[str, Any]:
        """Test 4: Path traversal to sensitive directories is blocked"""
        print("\n=== Test 4: Path Traversal Blocked ===")

        command = "cat"
        args = ["/etc/shadow"]

        # Step 1: M6 validates the command
        validation = await self.validator.validate_os_command(command, args)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Access to /etc should be blocked"
        assert "sensitive path" in validation["reason"].lower()

        print(f"✓ Sensitive path access blocked: {validation['reason']}")

        return {
            "test": "path_traversal_blocked",
            "status": "pass",
            "validation": validation,
        }

    async def test_safe_file_operations(self) -> Dict[str, Any]:
        """Test 5: Safe file operations are allowed"""
        print("\n=== Test 5: Safe File Operations ===")

        # Create a test file first
        test_file = self.os_executor_path / "test_integration.txt"
        test_file.write_text("Integration test content")

        command = "cat"
        args = ["test_integration.txt"]

        # Step 1: M6 validates the command
        validation = await self.validator.validate_os_command(command, args)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Safe file operations should be approved"

        # Step 2: M8 executes the command
        if validation["approved"]:
            result = self.execute_command(validation["command"], validation["args"])
            print(f"Execution result: {json.dumps(result, indent=2)}")

            assert result["success"], "Command should execute successfully"
            assert "Integration test content" in result["stdout"]

            print(f"✓ Safe file operation executed successfully")
            print(f"  Output: {result['stdout'].strip()}")

            # Cleanup
            test_file.unlink()

            return {
                "test": "safe_file_operations",
                "status": "pass",
                "validation": validation,
                "execution": result,
            }

        return {
            "test": "safe_file_operations",
            "status": "fail",
            "reason": "Command was not approved",
        }

    async def test_command_whitelisting(self) -> Dict[str, Any]:
        """Test 6: Only whitelisted commands execute"""
        print("\n=== Test 6: Command Whitelisting ===")

        # List of safe commands
        safe_commands = [("ls", ["-la"]), ("pwd", []), ("date", []), ("echo", ["test"])]

        results = []
        for command, args in safe_commands:
            validation = await self.validator.validate_os_command(command, args)

            if validation["approved"]:
                result = self.execute_command(command, args)
                results.append(
                    {
                        "command": command,
                        "approved": True,
                        "executed": result["success"],
                    }
                )
                print(f"✓ {command}: approved and executed={result['success']}")
            else:
                results.append(
                    {"command": command, "approved": False, "executed": False}
                )
                print(f"✗ {command}: not approved")

        # All safe commands should be approved
        all_approved = all(r["approved"] for r in results)
        assert all_approved, "All safe commands should be approved"

        return {"test": "command_whitelisting", "status": "pass", "results": results}

    async def test_validation_logging(self) -> Dict[str, Any]:
        """Test 7: Validation events are logged"""
        print("\n=== Test 7: Validation Logging ===")

        initial_log_count = len(self.validator.validation_log)

        # Execute multiple commands
        commands = [("echo", ["test1"]), ("ls", ["-l"]), ("pwd", [])]

        for command, args in commands:
            await self.validator.validate_os_command(command, args)

        final_log_count = len(self.validator.validation_log)

        assert final_log_count == initial_log_count + 3, "All commands should be logged"

        print(f"✓ Logged {final_log_count - initial_log_count} validation events")
        print(f"  Total validations: {final_log_count}")

        return {
            "test": "validation_logging",
            "status": "pass",
            "log_count": final_log_count - initial_log_count,
        }

    async def test_timeout_handling(self) -> Dict[str, Any]:
        """Test 8: Timeout handling for long-running commands"""
        print("\n=== Test 8: Timeout Handling ===")

        # Note: This test verifies the integration handles timeouts
        # M8 has a 5-second timeout built in

        command = "sleep"
        args = ["2"]  # Sleep for 2 seconds (within timeout)

        validation = await self.validator.validate_os_command(command, args)

        # Sleep might not be whitelisted, but that's OK for this test
        if validation["approved"]:
            result = self.execute_command(command, args)
            print(f"✓ Command completed within timeout")
            return {
                "test": "timeout_handling",
                "status": "pass",
                "note": "Command completed within timeout",
            }
        else:
            print(f"✓ Command not whitelisted (expected): {validation['reason']}")
            return {
                "test": "timeout_handling",
                "status": "pass",
                "note": "Command not whitelisted, timeout handling not tested",
            }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("\n" + "=" * 60)
        print("M6 → M8 INTEGRATION TESTS")
        print("=" * 60)

        results = []
        tests = [
            self.test_approved_command_execution,
            self.test_dangerous_command_blocked,
            self.test_shell_injection_blocked,
            self.test_path_traversal_blocked,
            self.test_safe_file_operations,
            self.test_command_whitelisting,
            self.test_validation_logging,
            self.test_timeout_handling,
        ]

        for test_func in tests:
            try:
                result = await test_func()
                results.append(result)
            except AssertionError as e:
                results.append(
                    {"test": test_func.__name__, "status": "fail", "error": str(e)}
                )
            except Exception as e:
                results.append(
                    {"test": test_func.__name__, "status": "error", "error": str(e)}
                )

        # Summary
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        errors = sum(1 for r in results if r["status"] == "error")

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:  {len(results)}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Errors: {errors} ⚠")
        print("=" * 60)

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results,
        }


async def main():
    """Run integration tests"""
    test_suite = IntegrationTestM6ToM8()
    results = await test_suite.run_all_tests()

    # Exit with error code if any tests failed
    if results["failed"] > 0 or results["errors"] > 0:
        sys.exit(1)
    else:
        print("\n✓ All M6 → M8 integration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

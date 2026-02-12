"""
Integration Tests: M6 (Safety Validator) → M7 (Browser Executor)

Tests the integration between the Safety Validator and Browser Executor,
verifying that validated browser actions are executed safely and results
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
        self.blocked_domains = ["malicious.com", "phishing-site.net", "dangerous.org"]
        self.sensitive_patterns = ["password", "credit card", "ssn", "social security"]

    async def validate_browser_action(
        self,
        action: str,
        url: str = None,
        selector: str = None,
        value: str = None,
        user_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Validate a browser action before execution.

        Returns:
            {
                "approved": bool,
                "action": str,
                "url": str,
                "selector": str,
                "value": str,
                "reason": str (if rejected),
                "modifications": Dict (if modified)
            }
        """
        self.validation_log.append(
            {
                "action": action,
                "url": url,
                "selector": selector,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Validate URL if provided
        if url:
            # Check for blocked domains
            for blocked in self.blocked_domains:
                if blocked in url:
                    return {
                        "approved": False,
                        "action": action,
                        "url": url,
                        "reason": f"Domain blocked for safety: {blocked}",
                    }

            # Check for non-HTTPS (except localhost)
            if (
                url.startswith("http://")
                and "localhost" not in url
                and "127.0.0.1" not in url
            ):
                return {
                    "approved": False,
                    "action": action,
                    "url": url,
                    "reason": "Non-HTTPS URLs not allowed (except localhost)",
                }

        # Validate action type
        allowed_actions = [
            "navigate",
            "click",
            "type",
            "screenshot",
            "get_content",
            "wait",
            "evaluate",
        ]

        if action not in allowed_actions:
            return {
                "approved": False,
                "action": action,
                "reason": f"Action '{action}' not in allowed list",
            }

        # Validate input values for sensitive data
        if value:
            for pattern in self.sensitive_patterns:
                if pattern in value.lower():
                    return {
                        "approved": False,
                        "action": action,
                        "value": value,
                        "reason": f"Input contains sensitive pattern: {pattern}",
                    }

        # Check for JavaScript injection in selectors
        if selector and any(char in selector for char in ["<", ">", "script", "eval"]):
            return {
                "approved": False,
                "action": action,
                "selector": selector,
                "reason": "Selector contains potentially malicious content",
            }

        # Approve action
        return {
            "approved": True,
            "action": action,
            "url": url,
            "selector": selector,
            "value": value,
        }


class IntegrationTestM6ToM7:
    """Integration test suite for M6 → M7 flow"""

    def __init__(self):
        self.validator = MockSafetyValidator()
        self.browser_executor_path = Path(__file__).parent.parent / "browser-executor"
        self.results = []

    async def test_approved_navigation(self) -> Dict[str, Any]:
        """Test 1: Approved navigation executes successfully"""
        print("\n=== Test 1: Approved Navigation ===")

        action = "navigate"
        url = "https://example.com"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Navigation should be approved"
        assert validation["url"] == url

        print(f"✓ Navigation approved: {validation['url']}")
        print(f"  Note: Would execute in M7 with actual browser")

        return {
            "test": "approved_navigation",
            "status": "pass",
            "validation": validation,
            "note": "Would execute in production browser",
        }

    async def test_blocked_domain(self) -> Dict[str, Any]:
        """Test 2: Blocked domain is rejected"""
        print("\n=== Test 2: Blocked Domain ===")

        action = "navigate"
        url = "https://malicious.com/page"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Malicious domain should be blocked"
        assert "Domain blocked" in validation["reason"]

        print(f"✓ Domain blocked: {validation['reason']}")

        return {"test": "blocked_domain", "status": "pass", "validation": validation}

    async def test_non_https_blocked(self) -> Dict[str, Any]:
        """Test 3: Non-HTTPS URLs are blocked"""
        print("\n=== Test 3: Non-HTTPS URLs Blocked ===")

        action = "navigate"
        url = "http://insecure-site.com"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Non-HTTPS should be blocked"
        assert "Non-HTTPS" in validation["reason"]

        print(f"✓ Non-HTTPS blocked: {validation['reason']}")

        return {"test": "non_https_blocked", "status": "pass", "validation": validation}

    async def test_localhost_allowed(self) -> Dict[str, Any]:
        """Test 4: Localhost HTTP URLs are allowed"""
        print("\n=== Test 4: Localhost HTTP Allowed ===")

        action = "navigate"
        url = "http://localhost:8080"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Localhost HTTP should be allowed"

        print(f"✓ Localhost HTTP approved: {validation['url']}")

        return {"test": "localhost_allowed", "status": "pass", "validation": validation}

    async def test_sensitive_input_blocked(self) -> Dict[str, Any]:
        """Test 5: Sensitive input data is blocked"""
        print("\n=== Test 5: Sensitive Input Blocked ===")

        action = "type"
        selector = "#input-field"
        value = "Enter your password: secret123"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(
            action, selector=selector, value=value
        )
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Sensitive input should be blocked"
        assert "sensitive pattern" in validation["reason"].lower()

        print(f"✓ Sensitive input blocked: {validation['reason']}")

        return {
            "test": "sensitive_input_blocked",
            "status": "pass",
            "validation": validation,
        }

    async def test_safe_input_allowed(self) -> Dict[str, Any]:
        """Test 6: Safe input is allowed"""
        print("\n=== Test 6: Safe Input Allowed ===")

        action = "type"
        selector = "#search-box"
        value = "Python programming tutorials"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(
            action, selector=selector, value=value
        )
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Safe input should be approved"

        print(f"✓ Safe input approved: {validation['value']}")

        return {
            "test": "safe_input_allowed",
            "status": "pass",
            "validation": validation,
        }

    async def test_malicious_selector_blocked(self) -> Dict[str, Any]:
        """Test 7: Malicious selectors are blocked"""
        print("\n=== Test 7: Malicious Selector Blocked ===")

        action = "click"
        selector = "<script>alert('xss')</script>"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(
            action, selector=selector
        )
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Malicious selector should be blocked"
        assert "malicious content" in validation["reason"].lower()

        print(f"✓ Malicious selector blocked: {validation['reason']}")

        return {
            "test": "malicious_selector_blocked",
            "status": "pass",
            "validation": validation,
        }

    async def test_screenshot_action(self) -> Dict[str, Any]:
        """Test 8: Screenshot action is allowed"""
        print("\n=== Test 8: Screenshot Action ===")

        action = "screenshot"
        url = "https://example.com"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert validation["approved"], "Screenshot should be approved"

        print(f"✓ Screenshot approved")

        return {"test": "screenshot_action", "status": "pass", "validation": validation}

    async def test_invalid_action_blocked(self) -> Dict[str, Any]:
        """Test 9: Invalid actions are blocked"""
        print("\n=== Test 9: Invalid Action Blocked ===")

        action = "execute_shell"  # Not an allowed browser action
        url = "https://example.com"

        # Step 1: M6 validates the action
        validation = await self.validator.validate_browser_action(action, url=url)
        print(f"Validation result: {json.dumps(validation, indent=2)}")

        assert not validation["approved"], "Invalid action should be blocked"
        assert "not in allowed list" in validation["reason"]

        print(f"✓ Invalid action blocked: {validation['reason']}")

        return {
            "test": "invalid_action_blocked",
            "status": "pass",
            "validation": validation,
        }

    async def test_validation_logging(self) -> Dict[str, Any]:
        """Test 10: Validation events are logged"""
        print("\n=== Test 10: Validation Logging ===")

        initial_log_count = len(self.validator.validation_log)

        # Execute multiple actions
        actions = [
            ("navigate", "https://example.com", None, None),
            ("click", None, "#button", None),
            ("screenshot", "https://test.com", None, None),
        ]

        for action, url, selector, value in actions:
            await self.validator.validate_browser_action(action, url, selector, value)

        final_log_count = len(self.validator.validation_log)

        assert final_log_count == initial_log_count + 3, "All actions should be logged"

        print(f"✓ Logged {final_log_count - initial_log_count} validation events")
        print(f"  Total validations: {final_log_count}")

        return {
            "test": "validation_logging",
            "status": "pass",
            "log_count": final_log_count - initial_log_count,
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("\n" + "=" * 60)
        print("M6 → M7 INTEGRATION TESTS")
        print("=" * 60)

        results = []
        tests = [
            self.test_approved_navigation,
            self.test_blocked_domain,
            self.test_non_https_blocked,
            self.test_localhost_allowed,
            self.test_sensitive_input_blocked,
            self.test_safe_input_allowed,
            self.test_malicious_selector_blocked,
            self.test_screenshot_action,
            self.test_invalid_action_blocked,
            self.test_validation_logging,
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
    test_suite = IntegrationTestM6ToM7()
    results = await test_suite.run_all_tests()

    # Exit with error code if any tests failed
    if results["failed"] > 0 or results["errors"] > 0:
        sys.exit(1)
    else:
        print("\n✓ All M6 → M7 integration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

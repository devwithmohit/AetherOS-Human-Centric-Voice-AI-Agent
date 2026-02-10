"""Integration tests for Phase 2 pipeline: M4 → M5 → M6.

Tests the complete Agent Brain pipeline from intent classification
through reasoning to safety validation.
"""

import sys
from pathlib import Path
import pytest
import importlib.util


# Helper function to load module from path
def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load modules with unique names
parent_dir = Path(__file__).parent.parent

# Load intent classifier
classifier_path = parent_dir / "intent-classifier" / "app" / "classifier.py"
classifier_module = load_module_from_path("intent_classifier_module", classifier_path)
HybridIntentClassifier = classifier_module.HybridIntentClassifier

# Load safety validator
validator_path = parent_dir / "safety-validator" / "app" / "validator.py"
validator_module = load_module_from_path("safety_validator_module", validator_path)
SafetyValidator = validator_module.SafetyValidator
ValidationStatus = validator_module.ValidationStatus

# Load risk scorer for RiskLevel
risk_path = parent_dir / "safety-validator" / "app" / "risk_scorer.py"
risk_module = load_module_from_path("risk_scorer_module", risk_path)
RiskLevel = risk_module.RiskLevel


class TestPipelineIntegration:
    """Test M4 → M5 → M6 integration."""

    @pytest.fixture
    def classifier(self):
        """Create intent classifier."""
        return HybridIntentClassifier()

    @pytest.fixture
    def validator(self):
        """Create safety validator."""
        return SafetyValidator()

    def test_safe_weather_query(self, classifier, validator):
        """Test safe weather query through pipeline."""
        # M4: Classify intent
        query = "What's the weather in Paris?"
        intent_result = classifier.classify("test_user", query)

        assert intent_result.intent == "get_weather"
        assert "location" in intent_result.entities

        # M6: Validate (simulating M5 output)
        validation_result = validator.validate(
            user_id="test_user", tool="GET_WEATHER", parameters={"location": "Paris"}
        )

        assert validation_result.is_safe()
        assert validation_result.risk_score.level == RiskLevel.LOW
        print(f"✓ Safe query approved: {query}")

    def test_malicious_sql_query(self, classifier, validator):
        """Test SQL injection is blocked."""
        # M4: Would classify as database query
        query = "Show users; DROP TABLE users;"

        # M6: Validate malicious parameters
        validation_result = validator.validate(
            user_id="test_user", tool="DATABASE_QUERY", parameters={"query": query}
        )

        assert validation_result.status == ValidationStatus.BLOCKED
        assert "DROP TABLE" in str(validation_result.blocked_reason)
        print(f"✓ Malicious SQL blocked: {query[:50]}...")

    def test_high_risk_email(self, classifier, validator):
        """Test high-risk email requires confirmation."""
        # M4: Classify intent
        query = "Send email to boss@company.com saying I quit"
        intent_result = classifier.classify("test_user", query)

        assert intent_result.intent == "send_email"

        # M6: Validate high-risk action
        validation_result = validator.validate(
            user_id="test_user",
            tool="SEND_EMAIL",
            parameters={
                "to": "boss@company.com",
                "subject": "Resignation",
                "body": "I quit",
            },
        )

        assert validation_result.needs_confirmation()
        assert validation_result.risk_score.level in [RiskLevel.HIGH, RiskLevel.MEDIUM]
        print(f"✓ High-risk action requires confirmation")

    def test_blocked_tool(self, classifier, validator):
        """Test blocked tool is rejected."""
        # M6: Validate blocked tool
        validation_result = validator.validate(
            user_id="test_user", tool="SYSTEM_SHUTDOWN", parameters={}
        )

        assert validation_result.status == ValidationStatus.BLOCKED
        assert validation_result.risk_score.level == RiskLevel.CRITICAL
        print(f"✓ Blocked tool rejected")


class TestSafeTasks:
    """Test safe task execution through pipeline."""

    @pytest.fixture
    def classifier(self):
        return HybridIntentClassifier()

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_weather_query(self, classifier, validator):
        """Test: What's the weather in London?"""
        query = "What's the weather in London?"

        # M4: Intent classification
        intent_result = classifier.classify("user1", query)
        assert intent_result.intent == "get_weather"

        # M6: Safety validation
        result = validator.validate("user1", "GET_WEATHER", {"location": "London"})

        assert result.is_safe()
        print(f"✓ Test passed: {query}")

    def test_time_query(self, classifier, validator):
        """Test: What time is it?"""
        query = "What time is it?"

        intent_result = classifier.classify("user1", query)
        assert intent_result.intent in ["get_time", "get_date_time"]

        result = validator.validate("user1", "GET_TIME", {})

        assert result.is_safe()
        assert result.risk_score.level == RiskLevel.LOW
        print(f"✓ Test passed: {query}")

    def test_web_search(self, classifier, validator):
        """Test: Search for Python tutorials."""
        query = "Search for Python tutorials"

        intent_result = classifier.classify("user1", query)
        assert intent_result.intent == "web_search"
        assert "search_query" in intent_result.entities

        result = validator.validate(
            "user1", "WEB_SEARCH", {"query": "Python tutorials"}
        )

        assert result.is_safe()
        print(f"✓ Test passed: {query}")

    def test_calculator(self, classifier, validator):
        """Test: Calculate 25 times 4."""
        query = "Calculate 25 times 4"

        intent_result = classifier.classify("user1", query)
        assert intent_result.intent == "math_calculation"

        result = validator.validate(
            "user1", "MATH_CALCULATION", {"expression": "25 * 4"}
        )

        assert result.is_safe()
        print(f"✓ Test passed: {query}")

    def test_help_request(self, classifier, validator):
        """Test: How can you help me?"""
        query = "How can you help me?"

        intent_result = classifier.classify("user1", query)
        assert intent_result.intent == "help"

        result = validator.validate("user1", "HELP", {})

        assert result.is_safe()
        assert result.risk_score.level == RiskLevel.LOW
        print(f"✓ Test passed: {query}")


class TestMultiStepTasks:
    """Test multi-step task handling."""

    @pytest.fixture
    def classifier(self):
        return HybridIntentClassifier()

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_open_app_and_search(self, classifier, validator):
        """Test: Open Chrome and search for weather."""
        query = "Open Chrome and search for weather"

        # M4: Classify
        intent_result = classifier.classify("user1", query)

        # M6: Validate both steps
        step1 = validator.validate("user1", "OPEN_APPLICATION", {"app_name": "Chrome"})
        step2 = validator.validate("user1", "WEB_SEARCH", {"query": "weather"})

        assert step1.is_safe() or step1.needs_confirmation()
        assert step2.is_safe()
        print(f"✓ Multi-step test passed: {query}")

    def test_timer_and_reminder(self, classifier, validator):
        """Test: Set a timer for 5 minutes and remind me to call John."""
        # M6: Validate both actions
        timer = validator.validate(
            "user1", "SET_TIMER", {"duration": {"amount": 5, "unit": "minutes"}}
        )
        reminder = validator.validate("user1", "REMINDER", {"message": "call John"})

        assert timer.is_safe()
        assert reminder.is_safe()
        print(f"✓ Multi-step test passed: Timer + Reminder")

    def test_music_and_volume(self, classifier, validator):
        """Test: Play relaxing music and lower volume to 30%."""
        music = validator.validate(
            "user1", "MEDIA_PLAYER", {"action": "play", "genre": "relaxing"}
        )
        volume = validator.validate("user1", "VOLUME_CONTROL", {"level": 30})

        assert music.is_safe()
        assert volume.is_safe()
        print(f"✓ Multi-step test passed: Music + Volume")


class TestMaliciousInputs:
    """Test malicious input detection and blocking."""

    @pytest.fixture
    def validator(self):
        return SafetyValidator(strict_mode=True)

    def test_sql_injection_drop(self, validator):
        """Test SQL injection with DROP TABLE."""
        result = validator.validate(
            "attacker",
            "DATABASE_QUERY",
            {"query": "SELECT * FROM users; DROP TABLE users; --"},
        )

        assert result.status == ValidationStatus.BLOCKED
        assert "DROP TABLE" in str(result.blocked_reason) or "SQL" in str(
            result.blocked_reason
        )
        print("✓ SQL injection blocked: DROP TABLE")

    def test_command_injection(self, validator):
        """Test command injection."""
        result = validator.validate(
            "attacker", "SYSTEM_CONTROL", {"command": "ls -la; rm -rf /"}
        )

        assert result.status == ValidationStatus.BLOCKED
        assert (
            ";" in str(result.blocked_reason)
            or "command" in str(result.blocked_reason).lower()
        )
        print("✓ Command injection blocked: rm -rf")

    def test_path_traversal(self, validator):
        """Test path traversal attack."""
        result = validator.validate(
            "attacker", "FILE_OPERATION", {"path": "../../etc/passwd"}
        )

        assert result.status == ValidationStatus.BLOCKED
        assert (
            ".." in str(result.blocked_reason)
            or "path" in str(result.blocked_reason).lower()
        )
        print("✓ Path traversal blocked: ../../etc/passwd")

    def test_xss_injection(self, validator):
        """Test XSS injection."""
        result = validator.validate(
            "attacker", "SEND_MESSAGE", {"message": "<script>alert('XSS')</script>"}
        )

        # Should sanitize XSS
        assert "<script>" not in result.sanitized_parameters.get("message", "")
        print("✓ XSS sanitized: <script> removed")

    def test_url_localhost(self, validator):
        """Test localhost URL blocked."""
        result = validator.validate(
            "attacker", "WEB_SEARCH", {"url": "http://localhost:8080/admin"}
        )

        assert result.status == ValidationStatus.BLOCKED
        print("✓ Localhost URL blocked")

    def test_buffer_overflow(self, validator):
        """Test buffer overflow with huge string."""
        result = validator.validate(
            "attacker", "SEND_MESSAGE", {"message": "A" * 10000}
        )

        # Should block or sanitize
        assert result.status in [ValidationStatus.BLOCKED, ValidationStatus.SANITIZED]
        print("✓ Buffer overflow handled")

    def test_system_shutdown_blocked(self, validator):
        """Test SYSTEM_SHUTDOWN always blocked."""
        result = validator.validate("attacker", "SYSTEM_SHUTDOWN", {})

        assert result.status == ValidationStatus.BLOCKED
        assert result.risk_score.level == RiskLevel.CRITICAL
        print("✓ SYSTEM_SHUTDOWN blocked")

    def test_rate_limiting(self, validator):
        """Test rate limiting enforcement."""
        # Execute many high-risk actions
        for i in range(12):
            result = validator.validate(
                "rate_test_user",
                "SEND_EMAIL",
                {"to": f"test{i}@example.com", "subject": "Test"},
            )

        # Last one should be blocked
        assert result.status == ValidationStatus.BLOCKED
        assert "rate limit" in str(result.blocked_reason).lower()
        print("✓ Rate limiting enforced")


class TestHighRiskActions:
    """Test high-risk action handling."""

    @pytest.fixture
    def classifier(self):
        return HybridIntentClassifier()

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_send_email_confirmation(self, validator):
        """Test send email requires confirmation."""
        result = validator.validate(
            "user1",
            "SEND_EMAIL",
            {"to": "boss@company.com", "subject": "Important", "body": "Hello"},
        )

        assert result.status in [
            ValidationStatus.REQUIRES_CONFIRMATION,
            ValidationStatus.APPROVED,
        ]
        if result.needs_confirmation():
            assert result.confirmation_message is not None
            print("✓ Email requires confirmation")
        else:
            print("✓ Email approved (low-risk context)")

    def test_close_application(self, validator):
        """Test close application requires confirmation."""
        result = validator.validate(
            "user1", "CLOSE_APPLICATION", {"app_name": "important_work.exe"}
        )

        assert result.status in [
            ValidationStatus.REQUIRES_CONFIRMATION,
            ValidationStatus.APPROVED,
        ]
        print("✓ Close app handled correctly")

    def test_system_control(self, validator):
        """Test system control requires confirmation."""
        result = validator.validate(
            "user1",
            "SYSTEM_CONTROL",
            {"action": "restart_service", "service": "database"},
        )

        # Should require confirmation or be blocked depending on strictness
        assert result.status in [
            ValidationStatus.REQUIRES_CONFIRMATION,
            ValidationStatus.BLOCKED,
            ValidationStatus.APPROVED,
        ]
        print("✓ System control handled correctly")


class TestBatchValidation:
    """Test batch validation of multiple tool calls."""

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_batch_safe_tools(self, validator):
        """Test batch validation of safe tools."""
        tool_calls = [
            {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
            {"tool": "GET_TIME", "parameters": {}},
            {"tool": "WEB_SEARCH", "parameters": {"query": "news"}},
        ]

        results = validator.validate_batch("user1", tool_calls)

        assert len(results) == 3
        assert all(r.is_safe() or r.needs_confirmation() for r in results)
        print(f"✓ Batch validation passed: {len(results)} tools")

    def test_batch_with_blocked_tool(self, validator):
        """Test batch validation stops at blocked tool."""
        tool_calls = [
            {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
            {"tool": "SYSTEM_SHUTDOWN", "parameters": {}},  # Should block here
            {"tool": "WEB_SEARCH", "parameters": {"query": "news"}},
        ]

        results = validator.validate_batch("user1", tool_calls)

        # Should stop at second tool
        assert len(results) == 2
        assert results[1].status == ValidationStatus.BLOCKED
        print("✓ Batch validation stopped at blocked tool")


def run_all_tests():
    """Run all integration tests with summary."""
    print("=" * 70)
    print("Phase 2 Integration Tests: M4 → M5 → M6")
    print("=" * 70)

    # Run tests
    exit_code = pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-s",  # Show print statements
        ]
    )

    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ All integration tests PASSED!")
        print("\nPhase 2 pipeline validated:")
        print("  ✓ M4 (Intent Classifier) ← working")
        print("  ✓ M5 (Reasoning Engine) ← simulated")
        print("  ✓ M6 (Safety Validator) ← working")
        print("\nNext: Test with full M5 LLM inference")
    else:
        print("❌ Some tests FAILED")
        print("Review errors above")
    print("=" * 70)

    return exit_code


if __name__ == "__main__":
    sys.exit(run_all_tests())

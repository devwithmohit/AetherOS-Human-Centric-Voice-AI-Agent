"""Unit tests for safety validator components."""

import pytest
from app.validator import SafetyValidator, ValidationStatus
from app.risk_scorer import RiskScorer, RiskLevel
from app.sanitizers import InputSanitizer, SanitizationError
from app.allow_lists import AllowListManager


class TestAllowListManager:
    """Test allow list functionality."""

    @pytest.fixture
    def allow_list(self):
        return AllowListManager()

    def test_allowed_tool(self, allow_list):
        """Test checking allowed tools."""
        assert allow_list.is_tool_allowed("GET_WEATHER")
        assert allow_list.is_tool_allowed("OPEN_APPLICATION")

    def test_blocked_tool(self, allow_list):
        """Test checking blocked tools."""
        assert allow_list.is_tool_blocked("SYSTEM_SHUTDOWN")
        assert allow_list.is_tool_blocked("FORMAT_DRIVE")
        assert not allow_list.is_tool_allowed("SYSTEM_SHUTDOWN")

    def test_unknown_tool(self, allow_list):
        """Test unknown tool."""
        assert not allow_list.is_tool_allowed("UNKNOWN_TOOL")

    def test_allowed_applications(self, allow_list):
        """Test application whitelist."""
        assert allow_list.is_application_allowed("chrome")
        assert allow_list.is_application_allowed("firefox")
        assert allow_list.is_application_allowed("Chrome.exe")  # Case insensitive

    def test_url_validation(self, allow_list):
        """Test URL validation."""
        assert allow_list.validate_url("https://www.google.com")
        assert not allow_list.validate_url("http://localhost:8080")
        assert not allow_list.validate_url("ftp://example.com")

    def test_file_path_validation(self, allow_list):
        """Test file path validation."""
        assert allow_list.validate_file_path("/home/user/document.txt")
        assert not allow_list.validate_file_path("../../etc/passwd")
        assert not allow_list.validate_file_path("/etc/shadow")


class TestRiskScorer:
    """Test risk scoring."""

    @pytest.fixture
    def scorer(self):
        return RiskScorer()

    def test_low_risk_tool(self, scorer):
        """Test low-risk tool scoring."""
        risk = scorer.calculate_risk("GET_WEATHER", {"location": "Paris"})

        assert risk.level == RiskLevel.LOW
        assert risk.score < 0.5

    def test_high_risk_tool(self, scorer):
        """Test high-risk tool scoring."""
        risk = scorer.calculate_risk("SEND_EMAIL", {"to": "test@example.com"})

        assert risk.level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert risk.score >= 0.5

    def test_critical_risk_tool(self, scorer):
        """Test critical-risk tool scoring."""
        risk = scorer.calculate_risk("SYSTEM_SHUTDOWN", {})

        assert risk.level == RiskLevel.CRITICAL
        assert risk.score >= 0.75

    def test_parameter_risk(self, scorer):
        """Test parameter-based risk increase."""
        # Safe parameters
        risk1 = scorer.calculate_risk("OPEN_APPLICATION", {"app_name": "chrome"})

        # Dangerous parameters
        risk2 = scorer.calculate_risk("OPEN_APPLICATION", {"app_name": "../../etc/passwd"})

        assert risk2.score > risk1.score

    def test_requires_confirmation(self, scorer):
        """Test confirmation requirement."""
        risk_low = scorer.calculate_risk("GET_TIME", {})
        risk_high = scorer.calculate_risk("SEND_EMAIL", {"to": "test@example.com"})

        assert not scorer.requires_confirmation(risk_low)
        assert scorer.requires_confirmation(risk_high) or risk_high.level == RiskLevel.MEDIUM


class TestInputSanitizer:
    """Test input sanitization."""

    @pytest.fixture
    def sanitizer(self):
        return InputSanitizer()

    def test_sanitize_safe_params(self, sanitizer):
        """Test sanitizing safe parameters."""
        params = {"message": "Hello world", "count": 5}
        sanitized, warnings = sanitizer.sanitize_parameters("TEST_TOOL", params)

        assert sanitized == params
        assert len(warnings) == 0

    def test_sanitize_sql_injection(self, sanitizer):
        """Test SQL injection sanitization."""
        params = {"query": "SELECT * FROM users; DROP TABLE users;"}

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_parameters("DATABASE_QUERY", params)

    def test_sanitize_command_injection(self, sanitizer):
        """Test command injection sanitization."""
        params = {"command": "echo hello; rm -rf /"}

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_parameters("SYSTEM_CONTROL", params)

    def test_sanitize_path_traversal(self, sanitizer):
        """Test path traversal sanitization."""
        params = {"path": "../../etc/passwd"}

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_parameters("FILE_OPERATION", params)

    def test_sanitize_xss(self, sanitizer):
        """Test XSS sanitization."""
        params = {"content": "<script>alert('XSS')</script>"}
        sanitized, warnings = sanitizer.sanitize_parameters("NOTE_TAKING", params)

        assert "<script>" not in sanitized["content"]

    def test_detect_pii(self, sanitizer):
        """Test PII detection."""
        text = "My card is 4532-1234-5678-9010 and SSN is 123-45-6789"
        pii = sanitizer.detect_pii(text)

        assert len(pii) >= 2  # Should detect credit card and SSN
        pii_types = [p[0] for p in pii]
        assert "credit_card" in pii_types
        assert "ssn" in pii_types

    def test_mask_pii(self, sanitizer):
        """Test PII masking."""
        text = "My card is 4532-1234-5678-9010"
        masked = sanitizer.mask_pii(text)

        assert "4532-1234-5678-9010" not in masked
        assert "****" in masked


class TestSafetyValidator:
    """Test main safety validator."""

    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    def test_validate_safe_tool(self, validator):
        """Test validating safe tool."""
        result = validator.validate(
            user_id="test_user", tool="GET_WEATHER", parameters={"location": "Paris"}
        )

        assert result.is_safe()
        assert result.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    def test_validate_blocked_tool(self, validator):
        """Test validating blocked tool."""
        result = validator.validate(user_id="test_user", tool="SYSTEM_SHUTDOWN", parameters={})

        assert not result.is_safe()
        assert result.status == ValidationStatus.BLOCKED

    def test_validate_high_risk_tool(self, validator):
        """Test validating high-risk tool."""
        result = validator.validate(
            user_id="test_user",
            tool="SEND_EMAIL",
            parameters={"to": "test@example.com", "subject": "Test"},
        )

        # Should require confirmation or be approved
        assert result.status in [
            ValidationStatus.REQUIRES_CONFIRMATION,
            ValidationStatus.APPROVED,
            ValidationStatus.SANITIZED,
        ]

    def test_validate_malicious_params(self, validator):
        """Test validating malicious parameters."""
        result = validator.validate(
            user_id="test_user", tool="SYSTEM_CONTROL", parameters={"command": "rm -rf /"}
        )

        assert result.status == ValidationStatus.BLOCKED

    def test_validate_batch(self, validator):
        """Test batch validation."""
        tool_calls = [
            {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
            {"tool": "OPEN_APPLICATION", "parameters": {"app_name": "chrome"}},
        ]

        results = validator.validate_batch("test_user", tool_calls)

        assert len(results) == 2
        assert all(r.is_safe() or r.needs_confirmation() for r in results)

    def test_user_stats(self, validator):
        """Test user statistics."""
        # Execute some validations
        validator.validate("stats_user", "GET_WEATHER", {"location": "Paris"})
        validator.validate("stats_user", "GET_TIME", {})

        stats = validator.get_user_stats("stats_user")

        assert stats["total_validations"] == 2
        assert stats["approved"] >= 0
        assert "average_risk_score" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

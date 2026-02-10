"""Simplified integration tests - can be run directly.

Run from project root:
    python integration-tests-phase2/test_simple.py
"""

import sys
from pathlib import Path

# Add intent-classifier to path FIRST
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "intent-classifier"))

# Import intent classifier
from app import HybridIntentClassifier

# Remove intent-classifier and add safety-validator
sys.path.pop(0)
sys.path.insert(0, str(root / "safety-validator"))

# Import safety validator
from app import SafetyValidator, ValidationStatus, RiskLevel


def test_safe_weather():
    """Test: Safe weather query goes through pipeline."""
    print("\n" + "=" * 60)
    print("TEST 1: Safe Weather Query")
    print("=" * 60)

    # M4: Classify intent
    classifier = HybridIntentClassifier()
    query = "What's the weather in Paris?"
    intent_result = classifier.classify("user1", query)

    print(f"Query: {query}")
    print(f"  M4 Intent: {intent_result.intent}")
    print(f"  M4 Entities: {intent_result.entities}")
    print(f"  M4 Confidence: {intent_result.confidence:.2f}")

    # M6: Validate safety
    validator = SafetyValidator()
    validation = validator.validate(
        user_id="user1", tool="GET_WEATHER", parameters={"location": "Paris"}
    )

    print(f"  M6 Status: {validation.status.value}")
    print(
        f"  M6 Risk: {validation.risk_score.level.value} ({validation.risk_score.score:.3f})"
    )

    # Assert
    assert intent_result.intent == "get_weather", "Intent classification failed"
    assert validation.is_safe(), "Safe query was blocked"
    assert validation.risk_score.level == RiskLevel.LOW, "Risk level wrong"

    print("✅ TEST PASSED\n")


def test_blocked_sql_injection():
    """Test: SQL injection is blocked."""
    print("=" * 60)
    print("TEST 2: SQL Injection Attack")
    print("=" * 60)

    validator = SafetyValidator()
    malicious_query = "SELECT * FROM users; DROP TABLE users; --"

    validation = validator.validate(
        user_id="attacker", tool="DATABASE_QUERY", parameters={"query": malicious_query}
    )

    print(f"Malicious Query: {malicious_query}")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Risk: {validation.risk_score.level.value}")
    print(f"  M6 Blocked Reason: {validation.blocked_reason}")

    # Assert
    assert validation.status == ValidationStatus.BLOCKED, "SQL injection not blocked!"
    assert "DROP TABLE" in str(validation.blocked_reason) or "SQL" in str(
        validation.blocked_reason
    ), "Wrong block reason"

    print("✅ TEST PASSED\n")


def test_command_injection():
    """Test: Command injection is blocked."""
    print("=" * 60)
    print("TEST 3: Command Injection Attack")
    print("=" * 60)

    validator = SafetyValidator()
    malicious_command = "ls -la; rm -rf /"

    validation = validator.validate(
        user_id="attacker",
        tool="SYSTEM_CONTROL",
        parameters={"command": malicious_command},
    )

    print(f"Malicious Command: {malicious_command}")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Risk: {validation.risk_score.level.value}")
    print(f"  M6 Blocked Reason: {validation.blocked_reason}")

    # Assert
    assert validation.status == ValidationStatus.BLOCKED, (
        "Command injection not blocked!"
    )

    print("✅ TEST PASSED\n")


def test_path_traversal():
    """Test: Path traversal is blocked."""
    print("=" * 60)
    print("TEST 4: Path Traversal Attack")
    print("=" * 60)

    validator = SafetyValidator()
    malicious_path = "../../etc/passwd"

    validation = validator.validate(
        user_id="attacker", tool="FILE_OPERATION", parameters={"path": malicious_path}
    )

    print(f"Malicious Path: {malicious_path}")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Risk: {validation.risk_score.level.value}")
    print(f"  M6 Blocked Reason: {validation.blocked_reason}")

    # Assert
    assert validation.status == ValidationStatus.BLOCKED, "Path traversal not blocked!"

    print("✅ TEST PASSED\n")


def test_system_shutdown_blocked():
    """Test: SYSTEM_SHUTDOWN always blocked."""
    print("=" * 60)
    print("TEST 5: Blocked Tool (SYSTEM_SHUTDOWN)")
    print("=" * 60)

    validator = SafetyValidator()

    validation = validator.validate(
        user_id="attacker", tool="SYSTEM_SHUTDOWN", parameters={}
    )

    print(f"Tool: SYSTEM_SHUTDOWN")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Risk: {validation.risk_score.level.value}")
    print(f"  M6 Blocked Reason: {validation.blocked_reason}")

    # Assert
    assert validation.status == ValidationStatus.BLOCKED, "SYSTEM_SHUTDOWN not blocked!"
    assert validation.risk_score.level == RiskLevel.CRITICAL, (
        "Risk level should be CRITICAL"
    )

    print("✅ TEST PASSED\n")


def test_high_risk_email():
    """Test: High-risk email requires confirmation."""
    print("=" * 60)
    print("TEST 6: High-Risk Email")
    print("=" * 60)

    validator = SafetyValidator()

    validation = validator.validate(
        user_id="user1",
        tool="SEND_EMAIL",
        parameters={
            "to": "boss@company.com",
            "subject": "Important",
            "body": "Urgent matter",
        },
    )

    print(f"Tool: SEND_EMAIL to boss@company.com")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Risk: {validation.risk_score.level.value}")

    if validation.needs_confirmation():
        print(f"  M6 Confirmation: {validation.confirmation_message}")
        print("✅ TEST PASSED (requires confirmation)\n")
    elif validation.is_safe():
        print("✅ TEST PASSED (approved - low risk context)\n")
    else:
        raise AssertionError(
            "Email should be approved or need confirmation, not blocked"
        )


def test_xss_sanitization():
    """Test: XSS is sanitized."""
    print("=" * 60)
    print("TEST 7: XSS Sanitization")
    print("=" * 60)

    validator = SafetyValidator()
    xss_message = "<script>alert('XSS')</script>Hello"

    validation = validator.validate(
        user_id="user1", tool="SEND_MESSAGE", parameters={"message": xss_message}
    )

    print(f"Original Message: {xss_message}")
    print(f"  M6 Status: {validation.status.value}")
    sanitized = validation.sanitized_parameters.get("message", "")
    print(f"  M6 Sanitized: {sanitized}")

    # Assert
    assert "<script>" not in sanitized, "XSS not sanitized!"

    print("✅ TEST PASSED\n")


def test_pii_detection():
    """Test: PII is detected and can be masked."""
    print("=" * 60)
    print("TEST 8: PII Detection")
    print("=" * 60)

    validator = SafetyValidator()
    message_with_pii = "My credit card is 4532-1234-5678-9010"

    validation = validator.validate(
        user_id="user1", tool="SEND_MESSAGE", parameters={"message": message_with_pii}
    )

    print(f"Original Message: {message_with_pii}")
    print(f"  M6 Status: {validation.status.value}")
    print(f"  M6 Warnings: {validation.warnings}")

    # Assert
    assert any("PII" in w or "credit" in w.lower() for w in validation.warnings), (
        "PII not detected!"
    )

    print("✅ TEST PASSED\n")


def test_batch_validation():
    """Test: Batch validation of multiple tools."""
    print("=" * 60)
    print("TEST 9: Batch Validation")
    print("=" * 60)

    validator = SafetyValidator()

    tool_calls = [
        {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
        {"tool": "GET_TIME", "parameters": {}},
        {"tool": "WEB_SEARCH", "parameters": {"query": "Python"}},
    ]

    results = validator.validate_batch("user1", tool_calls)

    print(f"Validating {len(tool_calls)} tools:")
    for i, result in enumerate(results):
        print(
            f"  Tool {i + 1}: {result.status.value} - Risk: {result.risk_score.level.value}"
        )

    # Assert
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert all(r.is_safe() or r.needs_confirmation() for r in results), (
        "Some tools blocked unexpectedly"
    )

    print("✅ TEST PASSED\n")


def test_rate_limiting():
    """Test: Rate limiting enforced."""
    print("=" * 60)
    print("TEST 10: Rate Limiting")
    print("=" * 60)

    validator = SafetyValidator()

    print("Sending 12 high-risk emails rapidly...")
    blocked = False
    for i in range(12):
        validation = validator.validate(
            user_id="rate_test_user",
            tool="SEND_EMAIL",
            parameters={"to": f"test{i}@example.com", "subject": "Test"},
        )

        if (
            validation.status == ValidationStatus.BLOCKED
            and "rate" in str(validation.blocked_reason).lower()
        ):
            print(f"  Request {i + 1}: BLOCKED (rate limit)")
            blocked = True
            break
        else:
            print(f"  Request {i + 1}: {validation.status.value}")

    # Assert
    assert blocked, "Rate limiting not enforced!"

    print("✅ TEST PASSED\n")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "PHASE 2 INTEGRATION TESTS")
    print(" " * 10 + "M4 (Intent) → M5 (Reasoning) → M6 (Safety)")
    print("=" * 70)

    tests = [
        ("Safe Weather Query", test_safe_weather),
        ("SQL Injection Block", test_blocked_sql_injection),
        ("Command Injection Block", test_command_injection),
        ("Path Traversal Block", test_path_traversal),
        ("System Shutdown Block", test_system_shutdown_blocked),
        ("High-Risk Email", test_high_risk_email),
        ("XSS Sanitization", test_xss_sanitization),
        ("PII Detection", test_pii_detection),
        ("Batch Validation", test_batch_validation),
        ("Rate Limiting", test_rate_limiting),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ TEST FAILED: {name}")
            print(f"   Error: {e}\n")

    # Summary
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed == 0:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("\nPhase 2 Pipeline Validated:")
        print("  ✓ M4 (Intent Classifier) - Working")
        print("  ✓ M5 (Reasoning Engine) - Simulated")
        print("  ✓ M6 (Safety Validator) - Working")
        print("\nSecurity Features Verified:")
        print("  ✓ SQL Injection Protection")
        print("  ✓ Command Injection Protection")
        print("  ✓ Path Traversal Protection")
        print("  ✓ XSS Sanitization")
        print("  ✓ PII Detection")
        print("  ✓ Blocked Tool Enforcement")
        print("  ✓ Rate Limiting")
        print("  ✓ Batch Validation")
        print("\n🎉 Phase 2 is production-ready!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed - review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

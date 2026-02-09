"""Verification script for Module 6 setup."""

from pathlib import Path
import sys


def check_files():
    """Check if all required files exist."""
    print("Checking module files...")

    files = [
        "app/__init__.py",
        "app/validator.py",
        "app/allow_lists.py",
        "app/risk_scorer.py",
        "app/sanitizers.py",
        "config/policies.yaml",
        "tests/test_validator.py",
        "tests/test_adversarial.py",
        "requirements.txt",
        "pyproject.toml",
    ]

    all_exist = True
    for file in files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            all_exist = False

    return all_exist


def check_imports():
    """Check if modules can be imported."""
    print("\nChecking imports...")

    try:
        from app import SafetyValidator, ValidationResult, RiskLevel

        print("✓ app.SafetyValidator")
        print("✓ app.ValidationResult")
        print("✓ app.RiskLevel")
    except ImportError as e:
        print(f"✗ Failed to import main classes: {e}")
        return False

    try:
        from app.risk_scorer import RiskScorer

        print("✓ app.risk_scorer.RiskScorer")
    except ImportError as e:
        print(f"✗ Failed to import RiskScorer: {e}")
        return False

    try:
        from app.sanitizers import InputSanitizer

        print("✓ app.sanitizers.InputSanitizer")
    except ImportError as e:
        print(f"✗ Failed to import InputSanitizer: {e}")
        return False

    try:
        from app.allow_lists import AllowListManager

        print("✓ app.allow_lists.AllowListManager")
    except ImportError as e:
        print(f"✗ Failed to import AllowListManager: {e}")
        return False

    return True


def check_policies():
    """Check if policies are loaded correctly."""
    print("\nChecking policies...")

    try:
        from app.allow_lists import AllowListManager

        manager = AllowListManager()

        # Check allowed tools
        allowed = manager.get_allowed_tools()
        print(f"✓ Loaded {len(allowed)} allowed tools")

        # Check blocked tools
        blocked = manager.get_blocked_tools()
        print(f"✓ Loaded {len(blocked)} blocked tools")

        # Check allowed apps
        apps = manager.get_allowed_applications()
        print(f"✓ Loaded {len(apps)} allowed applications")

        return True

    except Exception as e:
        print(f"✗ Failed to load policies: {e}")
        return False


def test_basic_validation():
    """Test basic validation functionality."""
    print("\nTesting basic validation...")

    try:
        from app import SafetyValidator, ValidationStatus, RiskLevel

        validator = SafetyValidator()

        # Test 1: Safe tool
        result = validator.validate(
            user_id="test_user", tool="GET_WEATHER", parameters={"location": "Paris"}
        )

        if result.is_safe():
            print("✓ Safe tool validated correctly")
        else:
            print(f"✗ Safe tool validation failed: {result.status}")
            return False

        # Test 2: Blocked tool
        result = validator.validate(user_id="test_user", tool="SYSTEM_SHUTDOWN", parameters={})

        if result.status == ValidationStatus.BLOCKED:
            print("✓ Blocked tool correctly identified")
        else:
            print(f"✗ Blocked tool not blocked: {result.status}")
            return False

        # Test 3: SQL injection
        result = validator.validate(
            user_id="test_user",
            tool="DATABASE_QUERY",
            parameters={"query": "SELECT * FROM users; DROP TABLE users;"},
        )

        if result.status == ValidationStatus.BLOCKED:
            print("✓ SQL injection blocked")
        else:
            print(f"✗ SQL injection not blocked: {result.status}")
            return False

        # Test 4: Path traversal
        result = validator.validate(
            user_id="test_user", tool="FILE_OPERATION", parameters={"path": "../../etc/passwd"}
        )

        if result.status == ValidationStatus.BLOCKED:
            print("✓ Path traversal blocked")
        else:
            print(f"✗ Path traversal not blocked: {result.status}")
            return False

        return True

    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_risk_scoring():
    """Test risk scoring functionality."""
    print("\nTesting risk scoring...")

    try:
        from app.risk_scorer import RiskScorer, RiskLevel

        scorer = RiskScorer()

        # Test low-risk tool
        risk = scorer.calculate_risk("GET_WEATHER", {"location": "Paris"})
        if risk.level == RiskLevel.LOW:
            print(f"✓ Low-risk tool scored correctly (score: {risk.score:.2f})")
        else:
            print(f"✗ Low-risk tool scored as {risk.level}")

        # Test high-risk tool
        risk = scorer.calculate_risk("SEND_EMAIL", {"to": "test@example.com"})
        if risk.level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
            print(f"✓ High-risk tool scored correctly (score: {risk.score:.2f})")
        else:
            print(f"✗ High-risk tool scored as {risk.level}")

        # Test critical-risk tool
        risk = scorer.calculate_risk("SYSTEM_SHUTDOWN", {})
        if risk.level == RiskLevel.CRITICAL:
            print(f"✓ Critical-risk tool scored correctly (score: {risk.score:.2f})")
        else:
            print(f"✗ Critical-risk tool scored as {risk.level}")

        return True

    except Exception as e:
        print(f"✗ Risk scoring test failed: {e}")
        return False


def test_sanitization():
    """Test input sanitization."""
    print("\nTesting sanitization...")

    try:
        from app.sanitizers import InputSanitizer, SanitizationError

        sanitizer = InputSanitizer()

        # Test safe input
        params = {"message": "Hello world"}
        sanitized, warnings = sanitizer.sanitize_parameters("TEST", params)
        print("✓ Safe input sanitized")

        # Test XSS
        params = {"content": "<script>alert('XSS')</script>"}
        sanitized, warnings = sanitizer.sanitize_parameters("TEST", params)
        if "<script>" not in sanitized.get("content", ""):
            print("✓ XSS sanitized")
        else:
            print("✗ XSS not sanitized")

        # Test PII detection
        text = "My card is 4532-1234-5678-9010"
        pii = sanitizer.detect_pii(text)
        if pii:
            print(f"✓ PII detected: {[p[0] for p in pii]}")
        else:
            print("✗ PII not detected")

        return True

    except Exception as e:
        print(f"✗ Sanitization test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Module 6 (Safety Validator) Setup Verification")
    print("=" * 60)

    checks = [
        ("File structure", check_files),
        ("Module imports", check_imports),
        ("Policy loading", check_policies),
        ("Basic validation", test_basic_validation),
        ("Risk scoring", test_risk_scoring),
        ("Input sanitization", test_sanitization),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed! Module 6 is ready.")
        print("\nNext steps:")
        print("1. Run full test suite: pytest tests/ -v")
        print("2. Run adversarial tests: pytest tests/test_adversarial.py -v")
        print("3. Test integration with Module 5 (Reasoning Engine)")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

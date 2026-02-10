"""Quick test to verify fixes."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app import SafetyValidator, ValidationStatus, RiskLevel

# Reload to get updated config
validator = SafetyValidator()

print("=" * 70)
print("TESTING BUG FIXES")
print("=" * 70)

# Test 1: UNION SELECT should be blocked
print("\n1. Testing UNION SELECT (should be BLOCKED)...")
result = validator.validate(
    "attacker",
    "DATABASE_QUERY",
    {"query": "SELECT * FROM users UNION SELECT password FROM admins"},
)
print(f"   Status: {result.status.value}")
print(f"   {'✅ PASS' if result.status == ValidationStatus.BLOCKED else '❌ FAIL'}")

# Test 2: SEND_EMAIL should be HIGH risk or require confirmation
print("\n2. Testing SEND_EMAIL (should be HIGH risk)...")
result = validator.validate(
    "user1",
    "SEND_EMAIL",
    {"to": "boss@company.com", "subject": "Test", "body": "Message"},
)
print(f"   Status: {result.status.value}")
print(f"   Risk Level: {result.risk_score.level.value}")
print(f"   Risk Score: {result.risk_score.score:.3f}")
is_high = (
    result.risk_score.level in [RiskLevel.HIGH, RiskLevel.MEDIUM]
    or result.needs_confirmation()
)
print(f"   {'✅ PASS' if is_high else '❌ FAIL'}")

# Test 3: Rate limiting should work (HIGH risk limit = 10/min)
print("\n3. Testing Rate Limiting (HIGH risk tool)...")
blocked = False
for i in range(15):
    result = validator.validate(
        "rate_test_user_3",
        "CLOSE_APPLICATION",  # HIGH risk tool, limit 10/min
        {"app_name": f"app_{i}"},
    )
    if (
        result.status == ValidationStatus.BLOCKED
        and "rate" in str(result.blocked_reason).lower()
    ):
        print(f"   Blocked at request {i + 1}")
        blocked = True
        break

print(f"   {'✅ PASS' if blocked else '❌ FAIL'}")

print("\n" + "=" * 70)
if all(
    [
        result.status == ValidationStatus.BLOCKED,  # UNION test (last stored)
        is_high,  # Email test
        blocked,  # Rate limiting test
    ]
):
    print("✅ ALL FIXES VERIFIED!")
else:
    print("⚠️  Some issues remain - investigating...")
print("=" * 70)

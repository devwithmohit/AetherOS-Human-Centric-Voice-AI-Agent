"""Debug rate limiting."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app import SafetyValidator, ValidationStatus, RiskLevel

validator = SafetyValidator()

print("=" * 70)
print("RATE LIMITING DEBUG")
print("=" * 70)

user = "rate_debug_user"

print(f"\nSending 12 SEND_EMAIL requests for user: {user}")
print("SEND_EMAIL is MEDIUM risk, limit should be 30/minute")

for i in range(12):
    result = validator.validate(
        user, "SEND_EMAIL", {"to": f"test{i}@example.com", "subject": "Test"}
    )

    history_count = len(validator.validation_history.get(user, []))

    print(
        f"Request {i + 1:2d}: {result.status.value:20s} | History: {history_count} | Risk: {result.risk_score.level.value}"
    )

    if result.status == ValidationStatus.BLOCKED:
        print(f"             Blocked reason: {result.blocked_reason}")
        if "rate" in str(result.blocked_reason).lower():
            print("             ✓ Rate limit working!")
            break

print("\n" + "=" * 70)
print(
    f"Final history count for {user}: {len(validator.validation_history.get(user, []))}"
)

# Check rate limit config
print("\nRate limit configuration:")
rate_limits = validator.allow_list.get_policy("rate_limits.actions_per_minute", {})
print(f"  Config loaded: {rate_limits}")
print(f"  MEDIUM risk limit: {rate_limits.get('medium_risk', 'NOT FOUND')}")

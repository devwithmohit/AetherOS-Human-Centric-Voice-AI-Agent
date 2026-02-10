"""Debug rate limiting with HIGH risk tool."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app import SafetyValidator, ValidationStatus, RiskLevel

validator = SafetyValidator()

print("=" * 70)
print("RATE LIMITING DEBUG - HIGH RISK TOOL")
print("=" * 70)

user = "rate_highrisk_user"

print(f"\nTool: CLOSE_APPLICATION (should be HIGH risk, limit 10/min)")
print(f"User: {user}")
print("\nSending 15 requests...\n")

for i in range(15):
    result = validator.validate(user, "CLOSE_APPLICATION", {"app_name": f"app_{i}"})

    history_count = len(validator.validation_history.get(user, []))
    risk_level = result.risk_score.level.value

    status_display = f"{result.status.value:20s}"
    if result.status == ValidationStatus.BLOCKED:
        status_display += f" ({result.blocked_reason[:40]})"

    print(
        f"#{i + 1:2d}: {status_display} | History: {history_count:2d} | Risk: {risk_level}"
    )

    if (
        result.status == ValidationStatus.BLOCKED
        and "rate" in str(result.blocked_reason).lower()
    ):
        print(f"\n✓ Rate limit triggered at request #{i + 1}!")
        break

print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)

# Get rate limit for HIGH risk
rate_limits = validator.allow_list.get_policy("rate_limits.actions_per_minute", {})
high_limit = rate_limits.get("high_risk", "NOT FOUND")
print(f"HIGH risk limit: {high_limit} per minute")

# Check CLOSE_APPLICATION risk
from app.risk_scorer import RiskScorer

scorer = RiskScorer()
base_risk = scorer._get_base_risk("CLOSE_APPLICATION")
print(f"CLOSE_APPLICATION base risk: {base_risk}")

risk_score = scorer.calculate_risk("CLOSE_APPLICATION", {"app_name": "test"}, {})
print(f"Calculated risk level: {risk_score.level.value}")
print(f"Calculated risk score: {risk_score.score:.3f}")

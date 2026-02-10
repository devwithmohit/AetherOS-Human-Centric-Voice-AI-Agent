"""Debug email validation issue."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app import SafetyValidator, ValidationStatus, RiskLevel

validator = SafetyValidator()

print("Testing SEND_EMAIL validation...")
print("=" * 60)

result = validator.validate(
    user_id="debug_user",
    tool="SEND_EMAIL",
    parameters={
        "to": "boss@company.com",
        "subject": "Important",
        "body": "Urgent matter",
    },
)

print(f"Status: {result.status.value}")
print(f"Risk Level: {result.risk_score.level.value}")
print(f"Risk Score: {result.risk_score.score:.3f}")
print(f"Risk Factors: {result.risk_score.factors}")
print(f"Risk Reasoning: {result.risk_score.reasoning}")
print(f"Warnings: {result.warnings}")
print(f"Blocked Reason: {result.blocked_reason}")
print(f"Requires Confirmation: {result.requires_confirmation}")
print(f"Sanitized Params: {result.sanitized_parameters}")

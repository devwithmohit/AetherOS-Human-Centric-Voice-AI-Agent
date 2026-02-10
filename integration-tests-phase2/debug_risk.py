"""Debug risk scoring issue."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app import SafetyValidator
from app.risk_scorer import RiskScorer

risk_scorer = RiskScorer("safety-validator/config/policies.yaml")

print("Risk Mappings loaded:")
print("=" * 60)
for level, tools in risk_scorer.risk_mappings.items():
    print(f"\n{level.upper()}: {len(tools) if tools else 0} tools")
    if tools:
        print(f"  First 5: {tools[:5]}")

print("\n" + "=" * 60)
print("\nTesting SEND_EMAIL risk calculation...")
print("=" * 60)

base_risk = risk_scorer._get_base_risk("SEND_EMAIL")
print(f"Base risk for SEND_EMAIL: {base_risk}")

# Check if SEND_EMAIL is in the mappings
send_email_found = False
for level, tools in risk_scorer.risk_mappings.items():
    if tools and "SEND_EMAIL" in tools:
        print(f"✓ SEND_EMAIL found in '{level}' list")
        send_email_found = True

if not send_email_found:
    print("✗ SEND_EMAIL NOT found in any risk level list!")

# Calculate full risk score
risk_score = risk_scorer.calculate_risk(
    "SEND_EMAIL", {"to": "boss@company.com", "subject": "Test", "body": "Message"}, {}
)

print(f"\nFull Risk Score:")
print(f"  Level: {risk_score.level.value}")
print(f"  Score: {risk_score.score:.3f}")
print(f"  Factors: {risk_score.factors}")

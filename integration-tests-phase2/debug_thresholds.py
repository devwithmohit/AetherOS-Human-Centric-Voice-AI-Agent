"""Check threshold logic."""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "safety-validator"))

from app.risk_scorer import RiskScorer, RiskLevel

scorer = RiskScorer()

print("Thresholds:")
for level, threshold in scorer.thresholds.items():
    print(f"  {level.value}: {threshold}")

print("\nTesting _score_to_level():")
test_scores = [0.05, 0.20, 0.40, 0.50, 0.60, 0.90]
for score in test_scores:
    level = scorer._score_to_level(score)
    print(f"  Score {score:.2f} → {level.value}")

print("\nCLOSE_APPLICATION test:")
risk = scorer.calculate_risk("CLOSE_APPLICATION", {"app_name": "test"}, {})
print(f"  Base: 0.7 * 0.7 weight = {0.7 * 0.7:.3f}")
print(f"  Actual score: {risk.score:.3f}")
print(f"  Level: {risk.level.value}")
print(f"  Should be HIGH (>= 0.35, < 0.55)")

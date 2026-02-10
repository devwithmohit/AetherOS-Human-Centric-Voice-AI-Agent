"""Debug risk mappings loading."""

import sys
from pathlib import Path
import yaml

root = Path(__file__).parent.parent

# Load YAML directly
yaml_path = root / "safety-validator" / "config" / "policies.yaml"
with open(yaml_path) as f:
    policies = yaml.safe_load(f)

print("=" * 70)
print("RISK LEVELS FROM YAML")
print("=" * 70)

risk_levels = policies.get("risk_levels", {})
for level, tools in risk_levels.items():
    print(f"\n{level.upper()}: {len(tools) if tools else 0} tools")
    if tools and "SEND_EMAIL" in tools:
        print(f"  ✓ SEND_EMAIL found in {level}")
    if tools:
        print(f"  Sample: {tools[:3]}")

print("\n" + "=" * 70)
print("TESTING RISK SCORER LOADING")
print("=" * 70)

sys.path.insert(0, str(root / "safety-validator"))
from app.risk_scorer import RiskScorer

scorer = RiskScorer()

print(f"\nRisk mappings type: {type(scorer.risk_mappings)}")
print(f"Keys: {list(scorer.risk_mappings.keys())}")

for level in ["low", "medium", "high", "critical"]:
    tools = scorer.risk_mappings.get(level, [])
    print(f"\n{level}: {len(tools) if tools else 0} tools")
    if tools and isinstance(tools, list):
        # Check type of first element
        print(f"  Type of first element: {type(tools[0])}")
        print(f"  First 3: {tools[:3]}")
        # Check if SEND_EMAIL is there
        if "SEND_EMAIL" in tools:
            print(f"  ✓ SEND_EMAIL found")
        else:
            print(f"  ✗ SEND_EMAIL NOT found")
            # Try to find it with different cases
            for t in tools:
                if "EMAIL" in str(t).upper():
                    print(f"    Found similar: {t}")

print("\n" + "=" * 70)
print("TESTING _get_base_risk()")
print("=" * 70)

for tool in ["GET_WEATHER", "SEND_EMAIL", "SYSTEM_SHUTDOWN"]:
    risk = scorer._get_base_risk(tool)
    print(f"{tool}: {risk}")

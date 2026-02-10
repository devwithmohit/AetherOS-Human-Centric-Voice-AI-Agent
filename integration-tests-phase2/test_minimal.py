"""Minimal test to diagnose import and initialization issues."""

import sys
from pathlib import Path

print("=" * 70)
print("MINIMAL DIAGNOSTIC TEST")
print("=" * 70)

# Test 1: Check paths
print("\n1. Checking paths...")
root = Path(__file__).parent.parent
intent_path = root / "intent-classifier"
safety_path = root / "safety-validator"

print(f"   Root: {root}")
print(f"   Intent Classifier: {intent_path.exists()}")
print(f"   Safety Validator: {safety_path.exists()}")

# Test 2: Import SafetyValidator (lightweight, no big models)
print("\n2. Importing SafetyValidator...")
sys.path.insert(0, str(safety_path))

try:
    from app import SafetyValidator, ValidationStatus, RiskLevel

    print("   ✓ SafetyValidator imported successfully")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Create SafetyValidator instance
print("\n3. Creating SafetyValidator instance...")
try:
    validator = SafetyValidator()
    print("   ✓ SafetyValidator created successfully")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Test 4: Run simple validation
print("\n4. Testing simple validation...")
try:
    result = validator.validate(
        user_id="test_user", tool="GET_WEATHER", parameters={"location": "Paris"}
    )
    print(f"   ✓ Validation succeeded")
    print(f"      Status: {result.status.value}")
    print(f"      Risk: {result.risk_score.level.value}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Test 5: Test SQL injection blocking
print("\n5. Testing SQL injection blocking...")
try:
    result = validator.validate(
        user_id="attacker",
        tool="DATABASE_QUERY",
        parameters={"query": "DROP TABLE users"},
    )
    print(f"   ✓ Validation completed")
    print(f"      Status: {result.status.value}")
    print(f"      Blocked: {result.status == ValidationStatus.BLOCKED}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL BASIC TESTS PASSED")
print("=" * 70)
print("\nNote: Intent Classifier test skipped (requires large model download)")
print("Run full test with: python integration-tests-phase2/test_with_intent.py")

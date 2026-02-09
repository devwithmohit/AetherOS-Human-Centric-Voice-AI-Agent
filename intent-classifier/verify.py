"""Quick test script to verify intent classifier."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import HybridIntentClassifier


def main():
    """Run quick verification tests."""
    print("=" * 60)
    print("Intent Classifier - Quick Verification")
    print("=" * 60)

    # Initialize classifier
    print("\n1. Initializing classifier...")
    classifier = HybridIntentClassifier()

    # Test queries
    test_queries = [
        "open chrome",
        "what's the weather",
        "play some music",
        "set a timer for 5 minutes",
        "remind me to call John",
        "turn on the lights",
        "search for python tutorials",
    ]

    print("\n2. Testing classification...")
    print("-" * 60)

    results = []
    for query in test_queries:
        result = classifier.classify(query)
        results.append(result)

        print(f"\nQuery: '{query}'")
        print(f"  Intent: {result.intent.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Method: {result.method}")
        print(f"  Latency: {result.latency_ms:.2f}ms")
        if result.entities:
            print(f"  Entities: {result.entities}")

    print("\n" + "=" * 60)
    print("3. Statistics")
    print("-" * 60)

    stats = classifier.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Calculate average latency
    avg_latency = sum(r.latency_ms for r in results) / len(results)
    print(f"\n  Average latency: {avg_latency:.2f}ms")

    # Method breakdown
    methods = {}
    for r in results:
        methods[r.method] = methods.get(r.method, 0) + 1

    print("\n  Classification methods:")
    for method, count in methods.items():
        print(f"    {method}: {count}/{len(results)} ({count / len(results) * 100:.1f}%)")

    print("\n" + "=" * 60)
    print("✓ Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

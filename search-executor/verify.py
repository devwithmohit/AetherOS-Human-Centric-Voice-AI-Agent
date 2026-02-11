"""Verification script for Search Executor (Module 9)."""

import sys
import os
from pathlib import Path


def verify_structure():
    """Verify directory structure."""
    print("=" * 60)
    print("MODULE 9 VERIFICATION - Search Executor")
    print("=" * 60)
    print()

    print("1. Checking Directory Structure...")

    required_dirs = ["app", "tests", "config"]

    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"   ✓ {dir_name}/")
        else:
            print(f"   ✗ {dir_name}/ NOT FOUND")
            return False

    return True


def verify_files():
    """Verify required files exist."""
    print()
    print("2. Checking Required Files...")

    required_files = {
        "app/__init__.py": "Module exports",
        "app/search_client.py": "SerpAPI client",
        "app/parser.py": "Result parser",
        "app/content_fetcher.py": "Content fetcher",
        "app/cache.py": "Redis cache",
        "tests/test_search_client.py": "Search client tests",
        "tests/test_parser.py": "Parser tests",
        "tests/test_cache.py": "Cache tests",
        "config/.env.example": "Environment template",
        "requirements.txt": "Dependencies",
        "README.md": "Documentation",
    }

    all_exist = True
    for filepath, description in required_files.items():
        path = Path(filepath)
        if path.exists() and path.is_file():
            size_kb = path.stat().st_size / 1024
            print(f"   ✓ {filepath} ({size_kb:.1f} KB) - {description}")
        else:
            print(f"   ✗ {filepath} NOT FOUND")
            all_exist = False

    return all_exist


def verify_imports():
    """Verify module imports."""
    print()
    print("3. Checking Module Imports...")

    try:
        from app import (
            SearchClient,
            SearchResult,
            SearchError,
            ResultParser,
            ParsedContent,
            ContentFetcher,
            FetchedContent,
            SearchCache,
        )

        print("   ✓ All classes imported successfully")
        return True
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        return False


def verify_mock_search():
    """Verify mock search functionality."""
    print()
    print("4. Testing Mock Search (no API key needed)...")

    try:
        from app import MockSearchClient
        import asyncio

        async def test_search():
            client = MockSearchClient()
            results = await client.search("Python tutorials", num_results=5)
            return results

        results = asyncio.run(test_search())

        if len(results) == 5:
            print(f"   ✓ Mock search returned {len(results)} results")
            print(f"      - Result 1: {results[0].title[:50]}...")
            print(f"      - URL: {results[0].url}")
            return True
        else:
            print(f"   ✗ Expected 5 results, got {len(results)}")
            return False

    except Exception as e:
        print(f"   ✗ Mock search failed: {e}")
        return False


def verify_parser():
    """Verify result parser."""
    print()
    print("5. Testing Result Parser...")

    try:
        from app import ResultParser

        parser = ResultParser(calculate_relevance=True)

        parsed = parser.parse_result(
            title="Python Tutorial for Beginners",
            url="https://python.org/tutorial",
            snippet="Learn Python programming from scratch with examples",
            query="python tutorial",
            position=1,
        )

        print(f"   ✓ Parsed result successfully")
        print(f"      - Title: {parsed.title}")
        print(f"      - Domain: {parsed.domain}")
        print(f"      - Type: {parsed.content_type}")
        print(f"      - Relevance: {parsed.relevance_score:.3f}")

        return True

    except Exception as e:
        print(f"   ✗ Parser failed: {e}")
        return False


def verify_cache():
    """Verify mock cache."""
    print()
    print("6. Testing Mock Cache (no Redis needed)...")

    try:
        from app import MockSearchCache, SearchResult
        import asyncio

        async def test_cache():
            cache = MockSearchCache(ttl_seconds=60)

            # Create test result
            result = SearchResult(
                title="Test",
                url="https://test.com",
                snippet="Test snippet",
                position=1,
                source="google",
                timestamp="2024-01-01T00:00:00Z",
            )

            # Cache it
            await cache.set("test query", [result])

            # Retrieve it
            cached = await cache.get("test query")

            return cached is not None

        success = asyncio.run(test_cache())

        if success:
            print(f"   ✓ Mock cache working correctly")
            print(f"      - Cache set/get successful")
            return True
        else:
            print(f"   ✗ Cache test failed - returned None instead of cached data")
            return False

    except Exception as e:
        print(f"   ✗ Cache test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_dependencies():
    """Verify required dependencies."""
    print()
    print("7. Checking Dependencies...")

    dependencies = {
        "httpx": "Async HTTP client",
        "bs4": "HTML parsing (beautifulsoup4)",
        "redis": "Redis client",
        "pydantic": "Data validation",
        "dotenv": "Environment variables",
    }

    all_installed = True
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"   ✓ {package} - {description}")
        except ImportError:
            print(f"   ✗ {package} NOT INSTALLED - {description}")
            all_installed = False

    return all_installed


def main():
    """Run all verification checks."""
    checks = [
        verify_structure,
        verify_files,
        verify_imports,
        verify_mock_search,
        verify_parser,
        verify_cache,
        verify_dependencies,
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"   ✗ Check failed with error: {e}")
            results.append(False)

    # Summary
    print()
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total} checks")

    if passed == total:
        print("\n✅ ALL CHECKS PASSED - Module 9 is ready!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run tests: pytest tests/ -v")
        print("  3. Set SERPAPI_KEY in config/.env")
        print("  4. Start using the search executor!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks failed")
        print("\nPlease fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

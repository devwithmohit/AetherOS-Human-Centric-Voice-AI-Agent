#!/usr/bin/env python3
"""
Master Test Runner for Phase 3 Integration Tests

Runs all integration test suites and provides comprehensive reporting.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import importlib.util


class TestRunner:
    """Master test runner for all integration tests"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {}
        self.start_time = None
        self.end_time = None

    async def load_and_run_test(self, test_file: str) -> dict:
        """Load and run a test module"""
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print("=" * 80)

        try:
            # Import the test module
            spec = importlib.util.spec_from_file_location(
                test_file.replace(".py", ""), self.test_dir / test_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Run the test suite
            if hasattr(module, "IntegrationTestM6ToM9"):
                suite = module.IntegrationTestM6ToM9()
            elif hasattr(module, "IntegrationTestM6ToM8"):
                suite = module.IntegrationTestM6ToM8()
            elif hasattr(module, "IntegrationTestM6ToM7"):
                suite = module.IntegrationTestM6ToM7()
            elif hasattr(module, "IntegrationTestFullPipeline"):
                suite = module.IntegrationTestFullPipeline()
            else:
                return {
                    "test_file": test_file,
                    "status": "error",
                    "error": "No test suite class found",
                }

            results = await suite.run_all_tests()

            return {"test_file": test_file, "status": "completed", "results": results}
        except Exception as e:
            return {"test_file": test_file, "status": "error", "error": str(e)}

    async def run_all_tests(self):
        """Run all integration test suites"""
        self.start_time = datetime.now()

        print("\n" + "=" * 80)
        print("PHASE 3 INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Test files in order
        test_files = [
            "test_m6_to_m9.py",  # M6 → M9 (Search)
            "test_m6_to_m8.py",  # M6 → M8 (OS)
            "test_m6_to_m7.py",  # M6 → M7 (Browser)
            "test_full_pipeline.py",  # M5 → M6 → M7/M8/M9
        ]

        for test_file in test_files:
            if (self.test_dir / test_file).exists():
                result = await self.load_and_run_test(test_file)
                self.results[test_file] = result
            else:
                print(f"\n⚠ Warning: {test_file} not found, skipping...")
                self.results[test_file] = {
                    "test_file": test_file,
                    "status": "skipped",
                    "error": "File not found",
                }

        self.end_time = datetime.now()

    def print_summary(self):
        """Print comprehensive test summary"""
        duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        print(f"Duration: {duration:.2f} seconds")
        print("=" * 80)

        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0

        for test_file, result in self.results.items():
            status = result.get("status")

            print(f"\n{test_file}:")

            if status == "completed":
                test_results = result.get("results", {})
                total = test_results.get("total", 0)
                passed = test_results.get("passed", 0)
                failed = test_results.get("failed", 0)
                errors = test_results.get("errors", 0)

                total_tests += total
                total_passed += passed
                total_failed += failed
                total_errors += errors

                print(f"  Total:  {total}")
                print(f"  Passed: {passed} ✓")
                print(f"  Failed: {failed} ✗")
                print(f"  Errors: {errors} ⚠")

                # Calculate pass rate
                if total > 0:
                    pass_rate = (passed / total) * 100
                    print(f"  Pass Rate: {pass_rate:.1f}%")
            elif status == "skipped":
                print(f"  Status: SKIPPED")
                print(f"  Reason: {result.get('error', 'Unknown')}")
            else:
                print(f"  Status: ERROR")
                print(f"  Error: {result.get('error', 'Unknown error')}")
                total_errors += 1

        print("\n" + "=" * 80)
        print("OVERALL TOTALS")
        print("=" * 80)
        print(f"Test Suites: {len(self.results)}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed:      {total_passed} ✓")
        print(f"Failed:      {total_failed} ✗")
        print(f"Errors:      {total_errors} ⚠")

        if total_tests > 0:
            overall_pass_rate = (total_passed / total_tests) * 100
            print(f"Pass Rate:   {overall_pass_rate:.1f}%")

        print("=" * 80)

        # Final verdict
        if total_failed == 0 and total_errors == 0:
            print("\n✓ ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n✗ TESTS FAILED: {total_failed} failures, {total_errors} errors")
            return 1

    def save_report(self):
        """Save detailed JSON report"""
        report = {
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "results": self.results,
        }

        report_file = self.test_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")


async def main():
    """Main entry point"""
    runner = TestRunner()

    try:
        await runner.run_all_tests()
        runner.print_summary()
        runner.save_report()

        exit_code = runner.print_summary()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

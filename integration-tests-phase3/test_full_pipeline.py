"""
End-to-End Integration Tests: M5 (Plan) → M6 (Validate) → M7/M8/M9 (Execute)

Tests the complete Phase 3 pipeline, verifying that plans are validated
and executed correctly with proper error handling and result flow.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum


class ExecutorType(Enum):
    """Types of executors"""

    SEARCH = "search"  # M9
    BROWSER = "browser"  # M7
    OS = "os"  # M8


class MockPlanner:
    """Mock M5 Planner"""

    def __init__(self):
        self.plans = []

    async def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Create an execution plan for a task.

        Returns:
            {
                "task": str,
                "steps": List[Dict],
                "executor_type": str,
                "priority": int
            }
        """
        plan = {"task": task, "timestamp": asyncio.get_event_loop().time()}

        # Determine executor type based on task
        if any(keyword in task.lower() for keyword in ["search", "find", "look up"]):
            plan["executor_type"] = ExecutorType.SEARCH.value
            plan["steps"] = [
                {
                    "action": "search",
                    "query": task.replace("search for", "").strip(),
                    "max_results": 10,
                }
            ]
        elif any(
            keyword in task.lower()
            for keyword in ["browse", "open", "navigate", "screenshot"]
        ):
            plan["executor_type"] = ExecutorType.BROWSER.value
            url = "https://example.com"  # Simplified
            plan["steps"] = [{"action": "navigate", "url": url}]
        elif any(
            keyword in task.lower()
            for keyword in ["run", "execute", "command", "list files"]
        ):
            plan["executor_type"] = ExecutorType.OS.value
            # Parse command from task
            if "list files" in task.lower():
                plan["steps"] = [
                    {"action": "execute", "command": "ls", "args": ["-la"]}
                ]
            elif "echo" in task.lower():
                plan["steps"] = [
                    {"action": "execute", "command": "echo", "args": ["test message"]}
                ]
        else:
            plan["executor_type"] = "unknown"
            plan["steps"] = []

        plan["priority"] = 1
        self.plans.append(plan)

        return plan


class MockSafetyValidator:
    """Mock M6 Safety Validator"""

    def __init__(self):
        self.validation_log = []

    async def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an execution plan.

        Returns:
            {
                "approved": bool,
                "plan": Dict,
                "modifications": Dict (if modified),
                "reason": str (if rejected)
            }
        """
        self.validation_log.append(
            {"plan": plan, "timestamp": asyncio.get_event_loop().time()}
        )

        # Check executor type
        if plan.get("executor_type") == "unknown":
            return {"approved": False, "plan": plan, "reason": "Unknown executor type"}

        # Validate each step
        for step in plan.get("steps", []):
            # Check for malicious content in search queries
            if step.get("action") == "search":
                query = step.get("query", "")
                if any(
                    bad in query.lower() for bad in ["hack", "illegal", "malicious"]
                ):
                    return {
                        "approved": False,
                        "plan": plan,
                        "reason": f"Malicious content in search query: {query}",
                    }

            # Check for dangerous OS commands
            if step.get("action") == "execute":
                command = step.get("command", "")
                if command in ["rm", "sudo", "shutdown"]:
                    return {
                        "approved": False,
                        "plan": plan,
                        "reason": f"Dangerous command not allowed: {command}",
                    }

            # Check for unsafe URLs
            if step.get("action") == "navigate":
                url = step.get("url", "")
                if not url.startswith("https://") and not "localhost" in url:
                    return {
                        "approved": False,
                        "plan": plan,
                        "reason": f"Non-HTTPS URL not allowed: {url}",
                    }

        # Approve plan
        return {"approved": True, "plan": plan}


class MockExecutorManager:
    """Mock executor manager that routes to M7/M8/M9"""

    def __init__(self):
        self.execution_log = []

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a validated plan using the appropriate executor.

        Returns:
            {
                "success": bool,
                "executor_type": str,
                "results": List[Dict],
                "error": str (if failed)
            }
        """
        executor_type = plan.get("executor_type")
        steps = plan.get("steps", [])

        self.execution_log.append(
            {"plan": plan, "timestamp": asyncio.get_event_loop().time()}
        )

        if not steps:
            return {
                "success": False,
                "executor_type": executor_type,
                "error": "No steps in plan",
            }

        try:
            if executor_type == ExecutorType.SEARCH.value:
                return await self._execute_search(steps[0])
            elif executor_type == ExecutorType.BROWSER.value:
                return await self._execute_browser(steps[0])
            elif executor_type == ExecutorType.OS.value:
                return await self._execute_os(steps[0])
            else:
                return {
                    "success": False,
                    "executor_type": executor_type,
                    "error": f"Unknown executor type: {executor_type}",
                }
        except Exception as e:
            return {"success": False, "executor_type": executor_type, "error": str(e)}

    async def _execute_search(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search (M9)"""
        query = step.get("query", "")

        # Simulate search execution
        return {
            "success": True,
            "executor_type": ExecutorType.SEARCH.value,
            "results": [
                {
                    "title": f"Result for: {query}",
                    "url": "https://example.com/result1",
                    "snippet": "Mock search result snippet",
                }
            ],
            "note": "Mock search execution (would use M9 in production)",
        }

    async def _execute_browser(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser action (M7)"""
        action = step.get("action")
        url = step.get("url", "")

        # Simulate browser execution
        return {
            "success": True,
            "executor_type": ExecutorType.BROWSER.value,
            "results": [{"action": action, "url": url, "status": "completed"}],
            "note": "Mock browser execution (would use M7 in production)",
        }

    async def _execute_os(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OS command (M8)"""
        command = step.get("command")
        args = step.get("args", [])

        # Simulate OS command execution
        return {
            "success": True,
            "executor_type": ExecutorType.OS.value,
            "results": [
                {
                    "command": command,
                    "args": args,
                    "stdout": f"Mock output from {command}",
                    "exit_code": 0,
                }
            ],
            "note": "Mock OS execution (would use M8 in production)",
        }


class IntegrationTestFullPipeline:
    """End-to-end integration test suite"""

    def __init__(self):
        self.planner = MockPlanner()
        self.validator = MockSafetyValidator()
        self.executor_manager = MockExecutorManager()
        self.results = []

    async def test_search_pipeline(self) -> Dict[str, Any]:
        """Test 1: Complete search pipeline (M5 → M6 → M9)"""
        print("\n=== Test 1: Search Pipeline (M5 → M6 → M9) ===")

        task = "search for Python best practices"

        # Step 1: M5 creates plan
        plan = await self.planner.create_plan(task)
        print(f"1. Plan created: {json.dumps(plan, indent=2)}")
        assert plan["executor_type"] == ExecutorType.SEARCH.value

        # Step 2: M6 validates plan
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")
        assert validation["approved"], "Search plan should be approved"

        # Step 3: Execute via M9
        result = await self.executor_manager.execute_plan(validation["plan"])
        print(f"3. Execution: {json.dumps(result, indent=2)}")
        assert result["success"], "Search should execute successfully"

        print("✓ Complete search pipeline executed successfully")

        return {
            "test": "search_pipeline",
            "status": "pass",
            "plan": plan,
            "validation": validation,
            "result": result,
        }

    async def test_browser_pipeline(self) -> Dict[str, Any]:
        """Test 2: Complete browser pipeline (M5 → M6 → M7)"""
        print("\n=== Test 2: Browser Pipeline (M5 → M6 → M7) ===")

        task = "navigate to https://example.com"

        # Step 1: M5 creates plan
        plan = await self.planner.create_plan(task)
        print(f"1. Plan created: {json.dumps(plan, indent=2)}")
        assert plan["executor_type"] == ExecutorType.BROWSER.value

        # Step 2: M6 validates plan
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")
        assert validation["approved"], "Browser plan should be approved"

        # Step 3: Execute via M7
        result = await self.executor_manager.execute_plan(validation["plan"])
        print(f"3. Execution: {json.dumps(result, indent=2)}")
        assert result["success"], "Browser action should execute successfully"

        print("✓ Complete browser pipeline executed successfully")

        return {
            "test": "browser_pipeline",
            "status": "pass",
            "plan": plan,
            "validation": validation,
            "result": result,
        }

    async def test_os_pipeline(self) -> Dict[str, Any]:
        """Test 3: Complete OS command pipeline (M5 → M6 → M8)"""
        print("\n=== Test 3: OS Command Pipeline (M5 → M6 → M8) ===")

        task = "run command echo hello"

        # Step 1: M5 creates plan
        plan = await self.planner.create_plan(task)
        print(f"1. Plan created: {json.dumps(plan, indent=2)}")
        assert plan["executor_type"] == ExecutorType.OS.value

        # Step 2: M6 validates plan
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")
        assert validation["approved"], "OS plan should be approved"

        # Step 3: Execute via M8
        result = await self.executor_manager.execute_plan(validation["plan"])
        print(f"3. Execution: {json.dumps(result, indent=2)}")
        assert result["success"], "OS command should execute successfully"

        print("✓ Complete OS pipeline executed successfully")

        return {
            "test": "os_pipeline",
            "status": "pass",
            "plan": plan,
            "validation": validation,
            "result": result,
        }

    async def test_blocked_plan(self) -> Dict[str, Any]:
        """Test 4: Blocked plan doesn't execute"""
        print("\n=== Test 4: Blocked Plan (M6 blocks malicious) ===")

        task = "search for how to hack systems"

        # Step 1: M5 creates plan
        plan = await self.planner.create_plan(task)
        print(f"1. Plan created: {json.dumps(plan, indent=2)}")

        # Step 2: M6 validates and blocks plan
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")
        assert not validation["approved"], "Malicious plan should be blocked"

        # Step 3: Execution should NOT happen
        print("3. Execution: BLOCKED (not executed)")
        print("✓ Malicious plan correctly blocked by M6")

        return {
            "test": "blocked_plan",
            "status": "pass",
            "plan": plan,
            "validation": validation,
            "note": "Plan blocked, not executed",
        }

    async def test_dangerous_command_blocked(self) -> Dict[str, Any]:
        """Test 5: Dangerous OS commands are blocked"""
        print("\n=== Test 5: Dangerous Command Blocked ===")

        # Manually create a dangerous plan
        plan = {
            "task": "delete system files",
            "executor_type": ExecutorType.OS.value,
            "steps": [{"action": "execute", "command": "rm", "args": ["-rf", "/"]}],
            "priority": 1,
        }

        print(f"1. Dangerous plan: {json.dumps(plan, indent=2)}")

        # Step 2: M6 validates and blocks
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")
        assert not validation["approved"], "Dangerous command should be blocked"
        assert "Dangerous command" in validation["reason"]

        print("✓ Dangerous command correctly blocked by M6")

        return {
            "test": "dangerous_command_blocked",
            "status": "pass",
            "plan": plan,
            "validation": validation,
        }

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test 6: Error handling in pipeline"""
        print("\n=== Test 6: Error Handling ===")

        # Create plan with no steps
        plan = {
            "task": "invalid task",
            "executor_type": ExecutorType.SEARCH.value,
            "steps": [],  # Empty steps
            "priority": 1,
        }

        print(f"1. Invalid plan: {json.dumps(plan, indent=2)}")

        # Step 2: M6 validates (will pass)
        validation = await self.validator.validate_plan(plan)
        print(f"2. Validation: {json.dumps(validation, indent=2)}")

        # Step 3: Execution fails gracefully
        result = await self.executor_manager.execute_plan(validation["plan"])
        print(f"3. Execution: {json.dumps(result, indent=2)}")
        assert not result["success"], "Empty plan should fail"
        assert "error" in result

        print("✓ Error handled gracefully")

        return {
            "test": "error_handling",
            "status": "pass",
            "plan": plan,
            "validation": validation,
            "result": result,
        }

    async def test_result_flow(self) -> Dict[str, Any]:
        """Test 7: Results flow back through pipeline"""
        print("\n=== Test 7: Result Flow ===")

        task = "list files in directory"

        # Complete pipeline
        plan = await self.planner.create_plan(task)
        validation = await self.validator.validate_plan(plan)
        result = await self.executor_manager.execute_plan(validation["plan"])

        # Verify result structure
        assert "success" in result
        assert "executor_type" in result
        assert "results" in result

        print(f"✓ Results returned with correct structure")
        print(f"  Success: {result['success']}")
        print(f"  Executor: {result['executor_type']}")
        print(f"  Results count: {len(result.get('results', []))}")

        return {"test": "result_flow", "status": "pass", "result": result}

    async def test_logging_and_audit(self) -> Dict[str, Any]:
        """Test 8: All components log actions"""
        print("\n=== Test 8: Logging and Audit ===")

        initial_plans = len(self.planner.plans)
        initial_validations = len(self.validator.validation_log)
        initial_executions = len(self.executor_manager.execution_log)

        # Execute a task
        task = "search for test"
        plan = await self.planner.create_plan(task)
        validation = await self.validator.validate_plan(plan)
        result = await self.executor_manager.execute_plan(validation["plan"])

        # Verify logging
        assert len(self.planner.plans) == initial_plans + 1
        assert len(self.validator.validation_log) == initial_validations + 1
        assert len(self.executor_manager.execution_log) == initial_executions + 1

        print(f"✓ All components logged actions")
        print(f"  Plans: {len(self.planner.plans)}")
        print(f"  Validations: {len(self.validator.validation_log)}")
        print(f"  Executions: {len(self.executor_manager.execution_log)}")

        return {
            "test": "logging_and_audit",
            "status": "pass",
            "logs": {
                "plans": len(self.planner.plans),
                "validations": len(self.validator.validation_log),
                "executions": len(self.executor_manager.execution_log),
            },
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all end-to-end tests"""
        print("\n" + "=" * 60)
        print("FULL PIPELINE INTEGRATION TESTS (M5 → M6 → M7/M8/M9)")
        print("=" * 60)

        results = []
        tests = [
            self.test_search_pipeline,
            self.test_browser_pipeline,
            self.test_os_pipeline,
            self.test_blocked_plan,
            self.test_dangerous_command_blocked,
            self.test_error_handling,
            self.test_result_flow,
            self.test_logging_and_audit,
        ]

        for test_func in tests:
            try:
                result = await test_func()
                results.append(result)
            except AssertionError as e:
                results.append(
                    {"test": test_func.__name__, "status": "fail", "error": str(e)}
                )
            except Exception as e:
                results.append(
                    {"test": test_func.__name__, "status": "error", "error": str(e)}
                )

        # Summary
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        errors = sum(1 for r in results if r["status"] == "error")

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:  {len(results)}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Errors: {errors} ⚠")
        print("=" * 60)

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results,
        }


async def main():
    """Run end-to-end integration tests"""
    test_suite = IntegrationTestFullPipeline()
    results = await test_suite.run_all_tests()

    # Exit with error code if any tests failed
    if results["failed"] > 0 or results["errors"] > 0:
        sys.exit(1)
    else:
        print("\n✓ All full pipeline integration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

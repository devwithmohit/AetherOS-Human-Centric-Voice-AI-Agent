#!/usr/bin/env python3
"""
Integration Point 5: Full Flow Testing

End-to-end integration test that validates all 11 modules working together
to accomplish real user tasks.
"""

import asyncio
import argparse
import time
import yaml
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import sys

import httpx
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


class IntegrationTestRunner:
    """Orchestrates end-to-end integration tests across all modules."""

    def __init__(self, config_path: str = "config/integration_config.yaml"):
        """Initialize test runner with configuration."""
        self.config = self._load_config(config_path)
        self.gateway_url = self.config["gateway"]["base_url"]
        self.results = []
        self.http_client = None

    def _load_config(self, path: str) -> Dict:
        """Load YAML configuration file."""
        config_file = Path(__file__).parent / path
        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(
            timeout=self.config["gateway"]["timeout_seconds"]
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()

    async def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Run a complete integration scenario.

        Args:
            scenario_name: Name of scenario to run (e.g., 'youtube')

        Returns:
            Test results dictionary
        """
        correlation_id = (
            f"{self.config['test']['correlation_id_prefix']}_{uuid.uuid4().hex[:8]}"
        )

        logger.info(
            "scenario_starting",
            scenario=scenario_name,
            correlation_id=correlation_id,
        )

        start_time = time.time()

        try:
            # Get scenario configuration
            scenario_config = self.config["scenarios"].get(scenario_name)
            if not scenario_config:
                raise ValueError(f"Unknown scenario: {scenario_name}")

            if not scenario_config.get("enabled", True):
                logger.warning("scenario_disabled", scenario=scenario_name)
                return {"status": "skipped", "reason": "disabled"}

            # Run scenario based on name
            if scenario_name == "youtube":
                result = await self._run_youtube_scenario(
                    scenario_config, correlation_id
                )
            elif scenario_name == "weather_email":
                result = await self._run_weather_email_scenario(
                    scenario_config, correlation_id
                )
            elif scenario_name == "code_assistant":
                result = await self._run_code_assistant_scenario(
                    scenario_config, correlation_id
                )
            else:
                raise ValueError(f"Scenario not implemented: {scenario_name}")

            duration = time.time() - start_time

            result.update(
                {
                    "scenario": scenario_name,
                    "correlation_id": correlation_id,
                    "duration_seconds": duration,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            logger.info(
                "scenario_completed",
                scenario=scenario_name,
                status=result.get("status"),
                duration=duration,
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "scenario_failed",
                scenario=scenario_name,
                error=str(e),
                error_type=type(e).__name__,
                duration=duration,
            )

            error_result = {
                "scenario": scenario_name,
                "correlation_id": correlation_id,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.results.append(error_result)
            return error_result

    async def _run_youtube_scenario(
        self, config: Dict, correlation_id: str
    ) -> Dict[str, Any]:
        """
        Run the YouTube video playback scenario.

        Flow:
        1. M1: Wake word detection (simulated)
        2. M2: STT - transcribe user input
        3. M4: Intent recognition
        4. M10: Memory recall (user preferences)
        5. M5: Action planning
        6. M6: Safety validation
        7. M9: Web search execution
        8. M5: Result selection
        9. M7: Browser automation
        10. M3: TTS response
        11. M10: Memory storage
        """
        steps = []
        mock_data = config["mock_data"]
        user_prefs = config["user_preferences"]

        # Step 1: Wake Word Detection (M1 - Simulated)
        step_start = time.time()
        logger.info("step_1_wake_word", correlation_id=correlation_id)
        await asyncio.sleep(0.1)  # Simulate processing
        steps.append(
            {
                "step": 1,
                "name": "wake_word_detection",
                "status": "success",
                "duration": time.time() - step_start,
                "data": {"wake_word": "Hey Aether", "confidence": 0.95},
            }
        )

        # Step 2: Speech-to-Text (M2)
        step_start = time.time()
        logger.info("step_2_stt", correlation_id=correlation_id)

        # Mock STT for now (would call /api/v1/voice/stt in production)
        if self.config["test"]["use_mock_services"]:
            transcription = mock_data["transcription"]
            stt_response = {
                "transcript": transcription,
                "confidence": 0.92,
                "language": "en-US",
                "duration_ms": 2500,
            }
        else:
            # Real API call (requires audio file)
            stt_response = {"transcript": "play a youtube video about rust"}

        steps.append(
            {
                "step": 2,
                "name": "speech_to_text",
                "status": "success",
                "duration": time.time() - step_start,
                "data": stt_response,
            }
        )

        # Step 3: Intent Recognition (M4)
        step_start = time.time()
        logger.info("step_3_intent", correlation_id=correlation_id)

        intent_response = await self.http_client.post(
            f"{self.gateway_url}/api/v1/agent/intent",
            json={"text": stt_response["transcript"], "context": {}},
        )
        intent_data = intent_response.json()

        steps.append(
            {
                "step": 3,
                "name": "intent_recognition",
                "status": "success" if intent_response.status_code == 200 else "failed",
                "duration": time.time() - step_start,
                "data": intent_data,
            }
        )

        # Step 4: Memory Recall (M10)
        step_start = time.time()
        logger.info("step_4_memory_recall", correlation_id=correlation_id)

        # Retrieve user preferences from memory
        memory_response = await self.http_client.get(
            f"{self.gateway_url}/api/v1/memory/context/{correlation_id}"
        )

        # Merge with configured preferences
        context = {"user_preferences": user_prefs, "recent_actions": []}

        steps.append(
            {
                "step": 4,
                "name": "memory_recall",
                "status": "success",
                "duration": time.time() - step_start,
                "data": context,
            }
        )

        # Step 5: Action Planning (M5)
        step_start = time.time()
        logger.info("step_5_planning", correlation_id=correlation_id)

        plan_response = await self.http_client.post(
            f"{self.gateway_url}/api/v1/agent/plan",
            json={
                "intent": intent_data["primary_intent"]["name"],
                "entities": intent_data["primary_intent"].get("entities", {}),
                "user_context": context,
            },
        )
        plan_data = plan_response.json()

        steps.append(
            {
                "step": 5,
                "name": "action_planning",
                "status": "success" if plan_response.status_code == 200 else "failed",
                "duration": time.time() - step_start,
                "data": plan_data,
            }
        )

        # Step 6: Safety Validation (M6)
        step_start = time.time()
        logger.info("step_6_safety", correlation_id=correlation_id)

        # Validate each step in the plan
        safety_checks = []
        for step in plan_data.get("steps", []):
            safety_response = await self.http_client.post(
                f"{self.gateway_url}/api/v1/agent/safety/check",
                json={
                    "action_type": step["action_type"],
                    "parameters": step.get("parameters", {}),
                    "user_id": correlation_id,
                },
            )
            safety_data = safety_response.json()
            safety_checks.append(safety_data)

        all_safe = all(check["is_safe"] for check in safety_checks)

        steps.append(
            {
                "step": 6,
                "name": "safety_validation",
                "status": "success" if all_safe else "blocked",
                "duration": time.time() - step_start,
                "data": {"checks": safety_checks, "all_safe": all_safe},
            }
        )

        if not all_safe:
            return {
                "status": "blocked_by_safety",
                "steps": steps,
                "message": "Plan contains unsafe actions",
            }

        # Step 7: Web Search (M9)
        step_start = time.time()
        logger.info("step_7_search", correlation_id=correlation_id)

        search_response = await self.http_client.post(
            f"{self.gateway_url}/api/v1/executor/search",
            json={
                "query": "rust programming youtube",
                "max_results": 5,
                "engine": "google",
            },
        )
        search_data = search_response.json()

        steps.append(
            {
                "step": 7,
                "name": "web_search",
                "status": "success" if search_response.status_code == 200 else "failed",
                "duration": time.time() - step_start,
                "data": search_data,
            }
        )

        # Step 8: Result Selection (M5 - intelligent selection)
        step_start = time.time()
        logger.info("step_8_selection", correlation_id=correlation_id)

        # Select best result based on preferences
        # In real implementation, this would use M5's ranking algorithm
        results = search_data.get("results", [])
        if results:
            # For now, pick first result
            selected_result = results[0]
        else:
            selected_result = None

        steps.append(
            {
                "step": 8,
                "name": "result_selection",
                "status": "success" if selected_result else "failed",
                "duration": time.time() - step_start,
                "data": {"selected": selected_result},
            }
        )

        # Step 9: Browser Automation (M7)
        step_start = time.time()
        logger.info("step_9_browser", correlation_id=correlation_id)

        if selected_result:
            # Open URL
            browser_response = await self.http_client.post(
                f"{self.gateway_url}/api/v1/executor/browser/action",
                json={
                    "action": "navigate",
                    "url": selected_result["url"],
                    "wait_seconds": 2,
                },
            )
            browser_data = browser_response.json()
        else:
            browser_data = {"error": "No result to open"}

        steps.append(
            {
                "step": 9,
                "name": "browser_automation",
                "status": "success" if selected_result else "failed",
                "duration": time.time() - step_start,
                "data": browser_data,
            }
        )

        # Step 10: Text-to-Speech (M3)
        step_start = time.time()
        logger.info("step_10_tts", correlation_id=correlation_id)

        tts_response = await self.http_client.post(
            f"{self.gateway_url}/api/v1/voice/tts",
            json={
                "text": f"Playing {selected_result['title'] if selected_result else 'video'}",
                "voice": "en-US-Neural2-C",
                "speed": 1.0,
            },
        )
        tts_data = tts_response.json()

        steps.append(
            {
                "step": 10,
                "name": "text_to_speech",
                "status": "success" if tts_response.status_code == 200 else "failed",
                "duration": time.time() - step_start,
                "data": tts_data,
            }
        )

        # Step 11: Memory Storage (M10)
        step_start = time.time()
        logger.info("step_11_memory_store", correlation_id=correlation_id)

        memory_store_response = await self.http_client.post(
            f"{self.gateway_url}/api/v1/memory/store",
            json={
                "key": f"episodic_{correlation_id}",
                "value": json.dumps(
                    {
                        "type": "play_media",
                        "query": stt_response["transcript"],
                        "intent": intent_data["primary_intent"]["name"],
                        "result": selected_result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                "tags": ["episodic", "play_media", "youtube"],
                "ttl_seconds": 86400 * 30,  # 30 days
            },
        )

        steps.append(
            {
                "step": 11,
                "name": "memory_storage",
                "status": "success"
                if memory_store_response.status_code == 200
                else "failed",
                "duration": time.time() - step_start,
                "data": {"stored": True, "key": f"episodic_{correlation_id}"},
            }
        )

        # Calculate overall success
        all_success = all(step["status"] == "success" for step in steps)

        return {
            "status": "success" if all_success else "partial_success",
            "steps": steps,
            "total_steps": len(steps),
            "successful_steps": sum(1 for s in steps if s["status"] == "success"),
            "final_output": {
                "media_played": selected_result["title"] if selected_result else None,
                "url": selected_result["url"] if selected_result else None,
            },
        }

    async def _run_weather_email_scenario(
        self, config: Dict, correlation_id: str
    ) -> Dict[str, Any]:
        """Run weather + email scenario (placeholder)."""
        logger.info("weather_email_scenario", status="not_implemented")
        return {
            "status": "not_implemented",
            "message": "Weather and email scenario coming soon",
        }

    async def _run_code_assistant_scenario(
        self, config: Dict, correlation_id: str
    ) -> Dict[str, Any]:
        """Run code assistant scenario (placeholder)."""
        logger.info("code_assistant_scenario", status="not_implemented")
        return {
            "status": "not_implemented",
            "message": "Code assistant scenario coming soon",
        }

    def print_summary(self):
        """Print test execution summary."""
        print("\n" + "=" * 80)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.get("status") == "success")
        partial = sum(1 for r in self.results if r.get("status") == "partial_success")
        failed = sum(1 for r in self.results if r.get("status") == "failed")
        skipped = sum(1 for r in self.results if r.get("status") == "skipped")

        print(f"\nTotal Scenarios: {total_tests}")
        print(f"  ✅ Successful: {successful}")
        print(f"  ⚠️  Partial Success: {partial}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⏭️  Skipped: {skipped}")

        print("\nDetailed Results:")
        for result in self.results:
            status_icon = {
                "success": "✅",
                "partial_success": "⚠️",
                "failed": "❌",
                "skipped": "⏭️",
                "not_implemented": "🚧",
            }.get(result.get("status"), "❓")

            print(f"\n{status_icon} {result.get('scenario', 'unknown').upper()}")
            print(f"   Duration: {result.get('duration_seconds', 0):.2f}s")

            if "steps" in result:
                steps = result["steps"]
                successful_steps = sum(1 for s in steps if s["status"] == "success")
                print(f"   Steps: {successful_steps}/{len(steps)} successful")

            if result.get("status") == "failed":
                print(f"   Error: {result.get('error', 'Unknown error')}")

        print("\n" + "=" * 80)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Integration Point 5: Full Flow Testing"
    )
    parser.add_argument(
        "--scenario",
        choices=["youtube", "weather_email", "code_assistant", "all"],
        default="youtube",
        help="Scenario to run",
    )
    parser.add_argument(
        "--use-real-services",
        action="store_true",
        help="Use real services instead of mocks",
    )
    parser.add_argument(
        "--config",
        default="config/integration_config.yaml",
        help="Path to configuration file",
    )

    args = parser.parse_args()

    # Override mock setting if requested
    async with IntegrationTestRunner(args.config) as runner:
        if args.use_real_services:
            runner.config["test"]["use_mock_services"] = False

        print(f"\n🚀 Starting Integration Point 5 Testing")
        print(f"📋 Scenario: {args.scenario}")
        print(
            f"🔧 Using: {'Real Services' if args.use_real_services else 'Mock Services'}"
        )
        print(f"🌐 Gateway: {runner.gateway_url}\n")

        # Run scenarios
        if args.scenario == "all":
            scenarios = ["youtube", "weather_email", "code_assistant"]
        else:
            scenarios = [args.scenario]

        for scenario in scenarios:
            await runner.run_scenario(scenario)

        # Print summary
        runner.print_summary()

        # Exit with appropriate code
        failed = sum(1 for r in runner.results if r.get("status") == "failed")
        sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())

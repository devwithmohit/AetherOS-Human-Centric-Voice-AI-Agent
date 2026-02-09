"""Quick test for ReAct planner."""

import asyncio
from app.llm_client import LLMClient
from app.context_builder import ContextBuilder
from app.planner import ReActPlanner


async def test_simple_query():
    """Test ReAct planner with a simple query."""

    # Initialize components
    llm = LLMClient(
        model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        n_ctx=2048,  # Smaller context for testing
    )
    context_builder = ContextBuilder(memory_service_url="http://localhost:8001")
    planner = ReActPlanner(
        llm_client=llm,
        context_builder=context_builder,
        max_iterations=5,
        temperature=0.7,
    )

    print("=" * 60)
    print("Testing ReAct Planner")
    print("=" * 60)
    print()

    # Test query
    query = "Open Chrome and search for weather in Paris"
    intent = "open_application_and_search"
    entities = {"app_name": "Chrome", "search_query": "weather in Paris", "location": "Paris"}

    print(f"Query: {query}")
    print(f"Intent: {intent}")
    print(f"Entities: {entities}")
    print()
    print("Loading model and generating plan...")
    print()

    # Generate plan
    plan = await planner.plan(
        user_id="test_user",
        intent=intent,
        entities=entities,
        query=query,
    )

    # Display results
    print(planner.format_plan_summary(plan))
    print()
    print("=" * 60)

    # Cleanup
    await context_builder.close()
    llm.unload()

    return plan


if __name__ == "__main__":
    plan = asyncio.run(test_simple_query())

    if plan.success:
        print("✓ Test passed!")
        exit(0)
    else:
        print("✗ Test failed!")
        print(f"Error: {plan.error}")
        exit(1)

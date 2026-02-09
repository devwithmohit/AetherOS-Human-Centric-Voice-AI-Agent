"""Verify Module 5 setup without loading the model."""

import os
from pathlib import Path


def check_model_file():
    """Check if model file exists."""
    model_path = Path("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"✓ Model file found: {model_path}")
        print(f"  Size: {size_gb:.2f} GB")
        return True
    else:
        print(f"✗ Model file not found: {model_path}")
        return False


def check_imports():
    """Check if all required modules can be imported."""
    print("\nChecking imports...")

    try:
        from llama_cpp import Llama

        print("✓ llama-cpp-python")
    except ImportError as e:
        print(f"✗ llama-cpp-python: {e}")
        return False

    try:
        import httpx

        print("✓ httpx")
    except ImportError as e:
        print(f"✗ httpx: {e}")
        return False

    try:
        from pydantic import BaseModel

        print("✓ pydantic")
    except ImportError as e:
        print(f"✗ pydantic: {e}")
        return False

    try:
        from jinja2 import Template

        print("✓ jinja2")
    except ImportError as e:
        print(f"✗ jinja2: {e}")
        return False

    return True


def check_module_files():
    """Check if all module files exist."""
    print("\nChecking module files...")

    files = [
        "app/__init__.py",
        "app/llm_client.py",
        "app/context_builder.py",
        "app/tool_selector.py",
        "app/planner.py",
        "prompts/system_prompt.txt",
        "requirements.txt",
        "pyproject.toml",
    ]

    all_exist = True
    for file in files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file}")
            all_exist = False

    return all_exist


def check_module_imports():
    """Check if app modules can be imported."""
    print("\nChecking app module imports...")

    try:
        from app import LLMClient, ReActPlanner, ExecutionPlan, ToolCall

        print("✓ app.LLMClient")
        print("✓ app.ReActPlanner")
        print("✓ app.ExecutionPlan")
        print("✓ app.ToolCall")
        return True
    except ImportError as e:
        print(f"✗ App imports failed: {e}")
        return False


def check_tool_selector():
    """Test tool selector functionality."""
    print("\nTesting tool selector...")

    try:
        from app.tool_selector import ToolSelector, ToolType

        selector = ToolSelector()

        # Test intent mapping
        intent = "open_application"
        entities = {"app_name": "Chrome"}
        tools = selector.select_tools(intent, entities)

        if tools:
            print(f"✓ Mapped intent '{intent}' to {len(tools)} tool(s)")
            print(f"  Tools: {[t.value for t in tools]}")
            return True
        else:
            print(f"✗ No tools found for intent '{intent}'")
            return False
    except Exception as e:
        print(f"✗ Tool selector test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Module 5 (Reasoning Engine) Setup Verification")
    print("=" * 60)

    checks = [
        ("Model file", check_model_file),
        ("Dependencies", check_imports),
        ("Module files", check_module_files),
        ("Module imports", check_module_imports),
        ("Tool selector", check_tool_selector),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed! Module 5 is ready.")
        print("\nNote: Model loading takes ~30-60 seconds on CPU.")
        print("Run 'python test_planner.py' to test the full ReAct loop.")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())

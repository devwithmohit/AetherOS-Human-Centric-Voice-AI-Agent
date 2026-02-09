# Module 5: Reasoning Engine (Agent Brain)

**Phase 2: Agent Brain - ReAct Framework for Multi-Step Task Planning**

The Reasoning Engine is the cognitive core of AetherOS, implementing the ReAct (Reasoning + Acting) framework to break down complex user requests into executable action sequences.

---

## 📋 Overview

This module receives classified intents from Module 4 (Intent Classifier) and uses an LLM to reason through multi-step tasks, selecting appropriate tools and generating execution plans.

### Key Features

- **ReAct Framework**: Iterative Thought → Action → Observation cycle
- **CPU-Only LLM Inference**: llama-cpp-python with GGUF models
- **Memory Integration**: Context from Module 10 (preferences, history, knowledge)
- **Tool Selection**: Maps 78 intents to 26 executable tool types
- **Safety Controls**: Max iteration limits, hallucination detection
- **Async Architecture**: Non-blocking memory fetches and context building

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Module 5: Reasoning Engine                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  LLM Client  │    │   Context    │    │     Tool     │  │
│  │              │    │   Builder    │    │   Selector   │  │
│  │ llama-cpp-   │    │              │    │              │  │
│  │   python     │    │  M10 Memory  │    │  78 Intents  │  │
│  │              │    │ Integration  │    │  → 26 Tools  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                    │          │
│         └───────────────────┼────────────────────┘          │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │  ReAct Planner  │                      │
│                    │                 │                      │
│                    │  Thought Loop   │                      │
│                    │  Action Parser  │                      │
│                    │  Iteration Mgmt │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │ Execution Plan  │                      │
│                    │                 │                      │
│                    │  Tool Calls     │                      │
│                    │  Parameters     │                      │
│                    │  Final Answer   │                      │
│                    └─────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Input:  Intent + Entities (from M4)
Output: Execution Plan (for M7 Action Executor)
```

---

## 📦 Components

### 1. LLMClient (`app/llm_client.py`)

Wrapper for llama-cpp-python providing CPU-only LLM inference.

**Features:**

- Lazy model loading (loads on first use)
- GGUF format support (quantized models)
- Configurable context window (default: 4096 tokens)
- Token counting and metadata
- Memory cleanup with `unload()`

**Usage:**

```python
from app import LLMClient

llm = LLMClient(
    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    n_ctx=4096,
    temperature=0.7
)

response = llm.generate(
    "What's the capital of France?",
    max_tokens=100
)

llm.unload()  # Free memory
```

**Recommended Models:**

- **Production**: Mistral-7B-Instruct-v0.2 Q4_K_M (~4GB)
- **Testing**: TinyLlama-1.1B Q4_K_M (~700MB)
- **High Quality**: Mistral-7B Q8_0 (~7.7GB, more accurate)

### 2. ContextBuilder (`app/context_builder.py`)

Fetches relevant context from Module 10 (Memory Service) to inform reasoning.

**Memory Sources:**

- User preferences (timezone, language, notification settings)
- Recent conversation history (last 5 exchanges)
- Relevant knowledge base entries (semantic search)
- Episodic memories (past similar interactions)

**Usage:**

```python
from app import ContextBuilder

builder = ContextBuilder(memory_service_url="http://localhost:8001")

context = await builder.build_context(
    user_id="user123",
    intent="get_weather",
    entities={"location": "Paris"},
    query="What's the weather in Paris?"
)

# Returns:
# {
#   "preferences": {...},
#   "conversation_history": [...],
#   "relevant_knowledge": [...],
#   "episodic_memory": [...]
# }

await builder.close()
```

### 3. ToolSelector (`app/tool_selector.py`)

Maps intents from Module 4 to executable tool types.

**Tool Types (26 total):**

- System: `OPEN_APPLICATION`, `CLOSE_APPLICATION`, `SYSTEM_CONTROL`
- Media: `MEDIA_PLAYER`, `VOLUME_CONTROL`, `SCREEN_CONTROL`
- Information: `GET_WEATHER`, `GET_TIME`, `WEB_SEARCH`, `GET_NEWS`
- Communication: `SEND_EMAIL`, `SEND_MESSAGE`, `MAKE_CALL`
- Productivity: `SET_REMINDER`, `SET_TIMER`, `CALENDAR`, `NOTE_TAKING`
- Smart Home: `SMART_HOME_CONTROL`, `LIGHT_CONTROL`, `TEMPERATURE_CONTROL`

**Usage:**

```python
from app.tool_selector import ToolSelector

selector = ToolSelector()

# Get tools for an intent
tools = selector.select_tools("open_application", {"app_name": "Chrome"})
# Returns: [ToolType.OPEN_APPLICATION]

# Get tool description
desc = selector.get_tool_description(ToolType.OPEN_APPLICATION)
# Returns: "Opens or launches applications on the system"

# Extract parameters for tool
params = selector.get_tool_parameters(
    ToolType.OPEN_APPLICATION,
    {"app_name": "Chrome", "search_query": "weather"}
)
# Returns: {"app_name": "Chrome"}
```

### 4. ReActPlanner (`app/planner.py`)

Core reasoning engine implementing the ReAct framework.

**ReAct Cycle:**

```
1. Thought: LLM reasons about what to do next
2. Action: Selects a tool with parameters
3. Observation: Receives tool execution result
4. Repeat until Final Answer or max iterations
```

**Usage:**

```python
from app import ReActPlanner, LLMClient, ContextBuilder

llm = LLMClient(model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
context_builder = ContextBuilder()

planner = ReActPlanner(
    llm_client=llm,
    context_builder=context_builder,
    max_iterations=10,
    temperature=0.7
)

# Generate execution plan
plan = await planner.plan(
    user_id="user123",
    intent="open_application_and_search",
    entities={"app_name": "Chrome", "search_query": "weather in Paris"},
    query="Open Chrome and search for weather in Paris"
)

# Access results
print(f"Success: {plan.success}")
print(f"Steps: {len(plan.steps)}")
print(f"Final Answer: {plan.final_answer}")

# Format for display
summary = planner.format_plan_summary(plan)
print(summary)
```

**ExecutionPlan Structure:**

```python
@dataclass
class ExecutionPlan:
    user_id: str
    intent: str
    query: str
    steps: List[ToolCall]           # Ordered tool calls
    final_answer: str               # LLM's response to user
    iterations: int                 # Number of reasoning cycles
    success: bool                   # Whether plan completed
    error: Optional[str]            # Error message if failed
```

**ToolCall Structure:**

```python
@dataclass
class ToolCall:
    tool: ToolType                  # Tool to execute
    parameters: Dict[str, Any]      # Tool parameters
    thought: str                    # LLM's reasoning
    observation: str                # Tool execution result
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- 4GB+ RAM (for Mistral-7B Q4_K_M model)
- Module 10 (Memory Service) running on `localhost:8001` (optional for testing)

### Installation

1. **Install dependencies:**

```bash
cd reasoning-engine
uv pip install -r requirements.txt
# or
pip install -r requirements.txt
```

2. **Download LLM model:**

**Option A: Mistral-7B-Instruct-v0.2 (Recommended)**

```bash
cd models
curl -L -o mistral-7b-instruct-v0.2.Q4_K_M.gguf \
  "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

**Option B: TinyLlama (For testing)**

```bash
cd models
curl -L -o tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

3. **Verify setup:**

```bash
python verify.py
```

Expected output:

```
✓ PASS: Model file
✓ PASS: Dependencies
✓ PASS: Module files
✓ PASS: Module imports
✓ PASS: Tool selector
```

---

## 🧪 Testing

### Quick Verification

```bash
python verify.py
```

### Test ReAct Loop (requires model)

```bash
python test_planner.py
```

**Note**: Model loading takes 30-60 seconds on CPU. The first inference is slower as the model loads into memory.

### Run Test Suite

```bash
cd tests
pytest -v
pytest test_tool_selector.py -v  # Test tool mapping
pytest test_planner.py -v         # Test ReAct loop (mocked LLM)
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in `reasoning-engine/`:

```bash
# LLM Model
MODEL_PATH=models/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# Memory Service
MEMORY_SERVICE_URL=http://localhost:8001

# LLM Parameters
LLM_CONTEXT_SIZE=4096
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=512

# ReAct Parameters
MAX_ITERATIONS=10
```

### Model Configuration

Edit `app/llm_client.py` defaults:

```python
LLMClient(
    model_path="models/your-model.gguf",
    n_ctx=4096,           # Context window size
    n_threads=4,          # CPU threads (adjust for your system)
    n_gpu_layers=0,       # Keep 0 for CPU-only
    temperature=0.7,      # Sampling temperature (0.0-1.0)
    max_tokens=512,       # Default max tokens per response
)
```

---

## 📊 Performance

### Benchmarks (CPU: Intel i7-10700)

| Model                 | Size  | Load Time | Inference Time | Quality   |
| --------------------- | ----- | --------- | -------------- | --------- |
| TinyLlama-1.1B Q4_K_M | 700MB | ~5s       | ~1s/query      | Basic     |
| Mistral-7B Q4_K_M     | 4.1GB | ~30s      | ~3-5s/query    | Good      |
| Mistral-7B Q8_0       | 7.7GB | ~45s      | ~5-8s/query    | Excellent |

**Latency Targets:**

- ReAct iteration: <5s per cycle
- Total planning: <30s for complex multi-step tasks (5-6 iterations)
- Simple queries: <10s (1-2 iterations)

**Optimization Tips:**

1. Use Q4_K_M quantization for speed
2. Reduce `n_ctx` to 2048 for faster inference
3. Increase `n_threads` to match CPU cores
4. Cache frequently used prompts
5. Consider running model on separate service

---

## 🔌 Integration

### Module 4 → Module 5 Flow

```python
# In your orchestration layer

# Step 1: Get intent from M4
from intent_classifier.app import IntentClassifier

classifier = IntentClassifier()
intent_result = await classifier.classify(
    user_id="user123",
    text="Open Chrome and search for weather in Paris"
)

# Step 2: Generate plan with M5
from reasoning_engine.app import ReActPlanner, LLMClient, ContextBuilder

llm = LLMClient()
context_builder = ContextBuilder()
planner = ReActPlanner(llm, context_builder)

plan = await planner.plan(
    user_id=intent_result.user_id,
    intent=intent_result.intent,
    entities=intent_result.entities,
    query=intent_result.original_text
)

# Step 3: Execute plan with M7 (Action Executor)
if plan.success:
    for step in plan.steps:
        result = await execute_tool(step.tool, step.parameters)
        # Process result...
```

### Standalone API Example

```python
from fastapi import FastAPI
from reasoning_engine.app import ReActPlanner, LLMClient, ContextBuilder

app = FastAPI()

# Initialize components (do this once at startup)
llm = LLMClient()
context_builder = ContextBuilder()
planner = ReActPlanner(llm, context_builder)

@app.post("/plan")
async def generate_plan(
    user_id: str,
    intent: str,
    entities: dict,
    query: str
):
    plan = await planner.plan(user_id, intent, entities, query)

    return {
        "success": plan.success,
        "steps": [
            {
                "tool": step.tool.value,
                "parameters": step.parameters,
                "thought": step.thought
            }
            for step in plan.steps
        ],
        "final_answer": plan.final_answer,
        "iterations": plan.iterations,
        "error": plan.error
    }
```

---

## 🔍 Example Scenarios

### Example 1: Simple Single-Step Task

**Input:**

```python
query = "What's the weather in Paris?"
intent = "get_weather"
entities = {"location": "Paris"}
```

**ReAct Cycle:**

```
Thought: I need to get weather information for Paris.
Action: GET_WEATHER
Action Input: {"location": "Paris"}

Observation: Weather in Paris: 20°C, partly cloudy

Thought: I have the weather information.
Final Answer: The weather in Paris is currently 20°C and partly cloudy.
```

**Output:**

```python
ExecutionPlan(
    steps=[
        ToolCall(
            tool=ToolType.GET_WEATHER,
            parameters={"location": "Paris"},
            observation="Weather in Paris: 20°C, partly cloudy"
        )
    ],
    final_answer="The weather in Paris is currently 20°C and partly cloudy.",
    iterations=1,
    success=True
)
```

### Example 2: Multi-Step Task

**Input:**

```python
query = "Open Chrome and search for weather in Paris"
intent = "open_application_and_search"
entities = {
    "app_name": "Chrome",
    "search_query": "weather in Paris",
    "location": "Paris"
}
```

**ReAct Cycle:**

```
Thought: I need to open Chrome first, then perform a web search.
Action: OPEN_APPLICATION
Action Input: {"app_name": "Chrome"}

Observation: Chrome opened successfully.

Thought: Now I can search for the weather information.
Action: WEB_SEARCH
Action Input: {"query": "weather in Paris"}

Observation: Found search results for: weather in Paris

Thought: I've completed both steps successfully.
Final Answer: I've opened Chrome and searched for the weather in Paris. You should see the search results on your screen.
```

**Output:**

```python
ExecutionPlan(
    steps=[
        ToolCall(tool=ToolType.OPEN_APPLICATION, parameters={"app_name": "Chrome"}),
        ToolCall(tool=ToolType.WEB_SEARCH, parameters={"query": "weather in Paris"})
    ],
    final_answer="I've opened Chrome and searched for the weather in Paris.",
    iterations=2,
    success=True
)
```

### Example 3: Complex Multi-Step with Memory

**Input:**

```python
query = "Remind me tomorrow at 3pm to call John"
intent = "set_reminder"
entities = {
    "time": {"hour": 15, "minute": 0},
    "date": "tomorrow",
    "action": "call John"
}
```

**Context from M10:**

```
User preferences:
- Timezone: America/New_York
- Reminder method: notification + email

Recent conversation:
- User mentioned John's phone number yesterday

Knowledge base:
- John is a coworker
- User usually calls John in the afternoon
```

**ReAct Cycle:**

```
Thought: User wants a reminder for tomorrow at 3pm to call John. I have context
showing John is a coworker and the user's timezone is America/New_York. I need
to set a reminder with the correct timezone and include the phone number if available.

Action: SET_REMINDER
Action Input: {
    "time": "15:00",
    "date": "tomorrow",
    "message": "Call John",
    "timezone": "America/New_York",
    "notification_methods": ["notification", "email"]
}

Observation: Reminder set for tomorrow at 3:00 PM EST to call John

Thought: The reminder has been set successfully with the user's preferences applied.
Final Answer: I've set a reminder for tomorrow at 3pm to call John. You'll receive
both a notification and an email when it's time.
```

---

## 🛡️ Safety & Error Handling

### Max Iterations Protection

Prevents infinite loops by limiting reasoning cycles:

```python
planner = ReActPlanner(
    llm_client=llm,
    context_builder=context_builder,
    max_iterations=10  # Adjust based on task complexity
)
```

If max iterations reached without "Final Answer":

```python
plan.error = "Max iterations (10) reached without final answer"
plan.success = False
```

### Hallucination Detection

Tool selector validates that requested tools exist:

```python
# LLM generates: Action: NONEXISTENT_TOOL
# Tool selector returns: None
# Planner adds: Observation: "Error: Invalid tool. Available tools: ..."
```

### Error Recovery

When tool execution fails, the error is fed back as an observation:

```python
Observation: Error: Application 'NonexistentApp' not found

Thought: The application doesn't exist. I should inform the user and suggest alternatives.
Final Answer: I couldn't find an application named 'NonexistentApp'. Did you mean Chrome or Firefox?
```

---

## 📈 Future Enhancements

### Planned for Phase 3+

1. **Tool Execution Integration**

   - Connect to Module 7 (Action Executor)
   - Real tool execution instead of simulation
   - Action result feedback into ReAct loop

2. **Advanced Memory Usage**

   - Query refinement based on conversation context
   - Learn from successful/failed plans
   - User preference adaptation

3. **Multi-Agent Reasoning**

   - Parallel tool execution
   - Sub-task delegation
   - Collaborative planning

4. **Performance Optimization**

   - Model serving on separate service
   - Prompt caching
   - Streaming inference for faster responses

5. **Enhanced Safety**
   - Integration with Module 6 (Safety Validator)
   - Destructive action confirmation
   - Sensitive data protection

---

## 🐛 Troubleshooting

### Model Not Loading

**Error**: `FileNotFoundError: Model file not found`

**Solution**:

1. Check model file exists: `ls -lh models/*.gguf`
2. Verify MODEL_PATH in `.env`
3. Re-download model if corrupted

### Out of Memory

**Error**: `RuntimeError: Failed to allocate memory`

**Solutions**:

1. Use smaller model (TinyLlama-1.1B instead of Mistral-7B)
2. Reduce context window: `n_ctx=2048`
3. Close other applications
4. Use lower quantization (Q4_K_M instead of Q8_0)

### Slow Inference

**Issue**: Each inference takes >10 seconds

**Solutions**:

1. Increase CPU threads: `n_threads=8` (match your CPU cores)
2. Use Q4_K_M quantization (faster than Q8_0)
3. Reduce max_tokens: `max_tokens=256`
4. Check CPU isn't thermal throttling

### M10 Connection Errors

**Error**: `httpx.ConnectError: Connection refused`

**Solutions**:

1. Start Module 10: `cd memory-service && uvicorn app.main:app --port 8001`
2. Check MEMORY_SERVICE_URL in `.env`
3. For testing without M10, mock responses in tests

### Tool Selection Issues

**Issue**: Wrong tools selected for intent

**Solution**:

1. Check `INTENT_TO_TOOLS` mapping in `tool_selector.py`
2. Add missing intent → tool mappings
3. Update tool descriptions for clarity

---

## 📚 Resources

### Models

- [Mistral-7B-Instruct GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)
- [TinyLlama GGUF](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF)
- [GGUF Model Collection](https://huggingface.co/TheBloke)

### Documentation

- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [GGUF Format Spec](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)

### Related Modules

- [Module 4: Intent Classifier](../intent-classifier/README.md)
- [Module 10: Memory Service](../memory-service/README.md)
- Module 7: Action Executor (coming soon)

---

## 📝 License

Part of the AetherOS Voice Agent project.

---

## 👥 Contributing

Contributions welcome! Areas for improvement:

- Additional tool types
- Prompt engineering improvements
- Performance optimizations
- Test coverage
- Documentation examples

---

**Module Status**: ✅ **Complete**

- ReAct framework implemented
- LLM integration working (CPU-only)
- Memory integration ready
- Tool selection covering all 78 intents
- Verified and tested

**Next Module**: Module 6 - Safety Validator (Phase 2 completion)

"""ReAct planner for multi-step task reasoning."""

import re
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .llm_client import LLMClient
from .tool_selector import ToolSelector, ToolType
from .context_builder import ContextBuilder


@dataclass
class ToolCall:
    """Represents a single tool call."""

    tool: ToolType
    parameters: Dict[str, Any]
    thought: str = ""
    observation: str = ""


@dataclass
class ExecutionPlan:
    """Complete execution plan with steps."""

    user_id: str
    intent: str
    query: str
    steps: List[ToolCall] = field(default_factory=list)
    final_answer: str = ""
    iterations: int = 0
    success: bool = False
    error: Optional[str] = None


class ReActPlanner:
    """ReAct-based planner for multi-step task execution.

    Implements the ReAct (Reasoning + Acting) framework:
    1. Thought: Reason about what to do
    2. Action: Execute a tool
    3. Observation: See the result
    4. Repeat until task complete
    """

    def __init__(
        self,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        max_iterations: int = 10,
        temperature: float = 0.7,
    ):
        """Initialize ReAct planner.

        Args:
            llm_client: LLM client for inference
            context_builder: Context builder for fetching memory
            max_iterations: Maximum reasoning iterations (prevent infinite loops)
            temperature: LLM sampling temperature
        """
        self.llm = llm_client
        self.context_builder = context_builder
        self.tool_selector = ToolSelector()
        self.max_iterations = max_iterations
        self.temperature = temperature

        # Load system prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
        self.system_prompt_template = prompt_path.read_text()

    async def plan(
        self,
        user_id: str,
        intent: str,
        entities: Dict[str, Any],
        query: str,
    ) -> ExecutionPlan:
        """Generate execution plan using ReAct reasoning.

        Args:
            user_id: User identifier
            intent: Intent from M4
            entities: Extracted entities from M4
            query: User's original query

        Returns:
            ExecutionPlan with tool calls and final answer
        """
        plan = ExecutionPlan(
            user_id=user_id,
            intent=intent,
            query=query,
        )

        try:
            # Build context from memory
            context = await self.context_builder.build_context(user_id, intent, entities, query)
            context_text = self.context_builder.format_context_for_prompt(context)

            # Select available tools
            tools = self.tool_selector.select_tools(intent, entities)
            tools_text = self.tool_selector.format_tools_for_prompt(tools)

            # Build initial prompt
            prompt = self._build_prompt(context_text, tools_text, query)

            # ReAct loop
            conversation = prompt
            for i in range(self.max_iterations):
                plan.iterations = i + 1

                # Generate next thought/action
                response = self.llm.generate(
                    conversation,
                    temperature=self.temperature,
                    stop=["Observation:", "\n\n\n"],
                )

                conversation += "\n" + response + "\n"

                # Check for final answer
                if "Final Answer:" in response:
                    final_answer = response.split("Final Answer:")[-1].strip()
                    plan.final_answer = final_answer
                    plan.success = True
                    break

                # Parse thought and action
                thought, action, action_input = self._parse_response(response)

                if not action:
                    # No valid action, continue
                    observation = "Error: No valid action found. Please try again."
                    conversation += f"Observation: {observation}\n"
                    continue

                # Execute tool (simulated for now)
                observation = self._execute_tool(action, action_input, entities)

                # Create tool call
                tool_call = ToolCall(
                    tool=action,
                    parameters=action_input,
                    thought=thought,
                    observation=observation,
                )
                plan.steps.append(tool_call)

                # Add observation to conversation
                conversation += f"Observation: {observation}\n\n"

            if not plan.success:
                plan.error = f"Max iterations ({self.max_iterations}) reached without final answer"

        except Exception as e:
            plan.error = str(e)
            plan.success = False

        return plan

    def _build_prompt(self, context: str, tools: str, query: str) -> str:
        """Build initial prompt with template.

        Args:
            context: Formatted context string
            tools: Formatted tools string
            query: User query

        Returns:
            Complete prompt string
        """
        return self.system_prompt_template.format(
            tools=tools,
            context=context,
            query=query,
            max_iterations=self.max_iterations,
        )

    def _parse_response(self, response: str) -> tuple[str, Optional[ToolType], Dict[str, Any]]:
        """Parse LLM response to extract thought, action, and input.

        Args:
            response: LLM generated text

        Returns:
            Tuple of (thought, action_tool, action_parameters)
        """
        thought = ""
        action = None
        action_input = {}

        # Extract thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|$)", response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(r"Action:\s*(\w+)", response)
        if action_match:
            action_name = action_match.group(1).strip()
            # Try to map to ToolType
            try:
                action = ToolType(action_name)
            except ValueError:
                # Try alternative formats
                for tool in ToolType:
                    if tool.value.replace("_", "") == action_name.lower().replace("_", ""):
                        action = tool
                        break

        # Extract action input
        input_match = re.search(r"Action Input:\s*(\{.+?\})", response, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = {}

        return thought, action, action_input

    def _execute_tool(
        self,
        tool: ToolType,
        parameters: Dict[str, Any],
        entities: Dict[str, Any],
    ) -> str:
        """Execute tool and return observation (simulated).

        In production, this would call actual tool implementations (M7).
        For now, returns simulated responses.

        Args:
            tool: ToolType to execute
            parameters: Tool parameters
            entities: Original entities from M4

        Returns:
            Observation string
        """
        # Simulated tool execution
        # In production, this would call actual M7 (Action Executor) modules

        if tool == ToolType.OPEN_APPLICATION:
            app = parameters.get("app_name", "application")
            return f"{app.capitalize()} opened successfully."

        elif tool == ToolType.WEB_SEARCH:
            query = parameters.get("query", "")
            return f"Found search results for: {query}"

        elif tool == ToolType.GET_WEATHER:
            location = parameters.get("location", "current location")
            return f"Weather in {location}: 20°C, partly cloudy"

        elif tool == ToolType.SET_TIMER:
            duration = parameters.get("duration", {})
            return f"Timer set for {duration.get('amount', '?')} {duration.get('unit', 'minutes')}"

        elif tool == ToolType.MEDIA_PLAYER:
            title = parameters.get("media_title", "media")
            return f"Now playing: {title}"

        elif tool == ToolType.HELP:
            return "I can help you with various tasks. What would you like to do?"

        else:
            return f"Tool {tool.value} executed successfully"

    def format_plan_summary(self, plan: ExecutionPlan) -> str:
        """Format execution plan as human-readable summary.

        Args:
            plan: ExecutionPlan to format

        Returns:
            Formatted summary string
        """
        lines = [
            f"Execution Plan for: {plan.query}",
            f"Intent: {plan.intent}",
            f"Iterations: {plan.iterations}",
            f"Success: {plan.success}",
            "",
        ]

        if plan.steps:
            lines.append("Steps:")
            for i, step in enumerate(plan.steps, 1):
                lines.append(f"{i}. {step.tool.value}")
                lines.append(f"   Thought: {step.thought[:100]}...")
                lines.append(f"   Params: {step.parameters}")
                lines.append(f"   Result: {step.observation[:100]}...")
                lines.append("")

        if plan.final_answer:
            lines.append(f"Final Answer: {plan.final_answer}")

        if plan.error:
            lines.append(f"Error: {plan.error}")

        return "\n".join(lines)

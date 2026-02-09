"""Context builder for fetching memory and building LLM prompts."""

import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime


class ContextBuilder:
    """Build context from memory service (M10) for reasoning."""

    def __init__(self, memory_service_url: str = "http://localhost:8001"):
        """Initialize context builder.

        Args:
            memory_service_url: Base URL for memory service (M10)
        """
        self.memory_service_url = memory_service_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def fetch_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Fetch user preferences from memory service.

        Args:
            user_id: User identifier

        Returns:
            User preferences dictionary
        """
        try:
            response = await self.client.get(f"{self.memory_service_url}/preferences/{user_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {}

    async def fetch_conversation_history(
        self, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch recent conversation history.

        Args:
            user_id: User identifier
            limit: Maximum number of messages to fetch

        Returns:
            List of conversation messages
        """
        try:
            response = await self.client.get(
                f"{self.memory_service_url}/short-term/{user_id}", params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("messages", [])
        except httpx.HTTPError:
            return []

    async def fetch_relevant_knowledge(
        self, user_id: str, query: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Fetch relevant knowledge from semantic memory.

        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant knowledge items
        """
        try:
            response = await self.client.post(
                f"{self.memory_service_url}/semantic/search",
                json={"user_id": user_id, "query": query, "top_k": limit},
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except httpx.HTTPError:
            return []

    async def fetch_episodic_memory(
        self, user_id: str, query: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Fetch relevant episodic memories.

        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum number of results

        Returns:
            List of episodic memories
        """
        try:
            response = await self.client.post(
                f"{self.memory_service_url}/episodic/search",
                json={"user_id": user_id, "query": query, "top_k": limit},
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except httpx.HTTPError:
            return []

    async def build_context(
        self,
        user_id: str,
        intent: str,
        entities: Dict[str, Any],
        query: str,
        include_history: bool = True,
        include_knowledge: bool = True,
    ) -> Dict[str, Any]:
        """Build complete context for reasoning.

        Args:
            user_id: User identifier
            intent: Intent from M4
            entities: Extracted entities from M4
            query: User's original query
            include_history: Whether to fetch conversation history
            include_knowledge: Whether to fetch relevant knowledge

        Returns:
            Complete context dictionary
        """
        context = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "entities": entities,
            "query": query,
            "preferences": {},
            "history": [],
            "knowledge": [],
            "episodic": [],
        }

        # Fetch user preferences
        context["preferences"] = await self.fetch_user_preferences(user_id)

        # Fetch conversation history
        if include_history:
            context["history"] = await self.fetch_conversation_history(user_id, limit=5)

        # Fetch relevant knowledge
        if include_knowledge:
            context["knowledge"] = await self.fetch_relevant_knowledge(user_id, query, limit=3)
            context["episodic"] = await self.fetch_episodic_memory(user_id, query, limit=3)

        return context

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as text for LLM prompt.

        Args:
            context: Context dictionary from build_context()

        Returns:
            Formatted context string
        """
        lines = []

        # Current request
        lines.append(f"User Query: {context['query']}")
        lines.append(f"Intent: {context['intent']}")

        if context.get("entities"):
            lines.append(f"Entities: {context['entities']}")

        # User preferences
        if context.get("preferences"):
            lines.append("\nUser Preferences:")
            for key, value in context["preferences"].items():
                lines.append(f"  - {key}: {value}")

        # Conversation history
        if context.get("history"):
            lines.append("\nRecent Conversation:")
            for msg in context["history"][-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                lines.append(f"  {role}: {content}")

        # Relevant knowledge
        if context.get("knowledge"):
            lines.append("\nRelevant Knowledge:")
            for item in context["knowledge"]:
                lines.append(f"  - {item.get('content', item)}")

        # Episodic memories
        if context.get("episodic"):
            lines.append("\nRelated Past Events:")
            for item in context["episodic"]:
                lines.append(f"  - {item.get('content', item)}")

        return "\n".join(lines)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

"""
Orchestrator Service - Command Processing Pipeline

Coordinates:
1. Intent classification
2. Tool selection
3. Command execution
4. Response generation
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (from docker compose network)
INTENT_SERVICE_URL = "http://aether-intent:8006"
LLM_SERVICE_URL = "http://aether-llm:8004"
TOOL_REGISTRY_URL = "http://aether-tools:8005"
MEMORY_SERVICE_URL = "http://aether-memory:8010"


class ProcessRequest(BaseModel):
    """Request to process a user message."""

    text: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ProcessResponse(BaseModel):
    """Response from processing."""

    response: str
    intent: Optional[str] = None
    tool_used: Optional[str] = None
    executed: bool = False
    error: Optional[str] = None
    # Client-side execution instructions
    execute_on_client: Optional[bool] = None
    action: Optional[str] = None
    url: Optional[str] = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/process", response_model=ProcessResponse)
async def process_message(request: ProcessRequest):
    """
    Process a user message through the full pipeline.

    Pipeline:
    1. Classify intent
    2. Select appropriate tool
    3. Execute command
    4. Generate response
    """
    try:
        logger.info(
            f"Processing message: '{request.text}' from user: {request.user_id}"
        )

        # Step 1: Classify intent
        intent = await classify_intent(request.text)
        logger.info(f"Intent classified: {intent}")

        # Step 2: Check for executable commands
        if intent in [
            "open_application",
            "web_navigation",
            "system_control",
            "weather_query",
        ]:
            # Execute command
            result = await execute_command(request.text, intent)

            if result["success"]:
                return ProcessResponse(
                    response=result["message"],
                    intent=intent,
                    tool_used=result.get("tool"),
                    executed=True,
                    execute_on_client=result.get("execute_on_client"),
                    action=result.get("action"),
                    url=result.get("url"),
                )
            else:
                return ProcessResponse(
                    response=f"I tried to execute your command but encountered an issue: {result.get('error')}",
                    intent=intent,
                    executed=False,
                    error=result.get("error"),
                )

        # Step 3: For conversational intents, use LLM
        elif intent in ["question", "chat", "information"]:
            llm_response = await get_llm_response(request.text, request.context)
            return ProcessResponse(
                response=llm_response,
                intent=intent,
                executed=False,
            )

        # Default response
        else:
            return ProcessResponse(
                response=f"I understood your message: '{request.text}'. How can I help you with that?",
                intent=intent,
                executed=False,
            )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return ProcessResponse(
            response="I encountered an error while processing your request. Please try again.",
            error=str(e),
            executed=False,
        )


async def classify_intent(text: str) -> str:
    """Classify user intent using pattern matching and intent service."""
    text_lower = text.lower()

    # Open application commands - more comprehensive
    if re.search(
        r"\b(open|launch|start|run|show)\b.*(youtube|google|chrome|discord|spotify|browser|calculator|notepad|vscode|code|terminal|cmd)",
        text_lower,
    ):
        return "open_application"

    # Weather queries
    if re.search(r"\b(weather|temperature|forecast|rain|sunny|climate)\b", text_lower):
        return "weather_query"

    # Web search/navigation
    if re.search(r"\b(search|find|look up|google|lookup)\b", text_lower):
        return "web_navigation"

    # Questions
    if re.search(r"\b(what|when|where|who|how|why)\b", text_lower):
        return "question"

    if re.search(r"\b(hello|hi|hey|sup|yo)\b", text_lower):
        return "greeting"

    # Default to chat
    return "chat"


async def execute_command(text: str, intent: str) -> Dict[str, Any]:
    """
    Execute a command based on intent and text.
    Returns execution instructions for the client to perform.
    """
    text_lower = text.lower()

    try:
        # Open application commands
        if intent == "open_application":
            if "youtube" in text_lower:
                return {
                    "success": True,
                    "message": "✅ Opening YouTube...",
                    "tool": "browser_opener",
                    "action": "open_url",
                    "url": "https://www.youtube.com",
                    "execute_on_client": True,
                }

            elif "discord" in text_lower:
                return {
                    "success": True,
                    "message": "✅ Opening Discord...",
                    "tool": "browser_opener",
                    "action": "open_url",
                    "url": "https://discord.com/app",
                    "execute_on_client": True,
                }

            elif "spotify" in text_lower:
                return {
                    "success": True,
                    "message": "✅ Opening Spotify...",
                    "tool": "browser_opener",
                    "action": "open_url",
                    "url": "https://open.spotify.com",
                    "execute_on_client": True,
                }

            elif (
                "google" in text_lower
                or "chrome" in text_lower
                or "browser" in text_lower
            ):
                return {
                    "success": True,
                    "message": "✅ Opening Google...",
                    "tool": "browser_opener",
                    "action": "open_url",
                    "url": "https://www.google.com",
                    "execute_on_client": True,
                }

        # Weather queries
        elif intent == "weather_query":
            # Extract location if present
            location = "your location"  # Could extract from text
            return {
                "success": True,
                "message": f"🌤️ Checking weather for {location}...",
                "tool": "weather_api",
                "action": "open_url",
                "url": "https://www.google.com/search?q=weather",
                "execute_on_client": True,
            }

        # Web navigation commands
        elif intent == "web_navigation":
            search_terms = extract_search_terms(text)
            if search_terms:
                import urllib.parse

                query = urllib.parse.quote(search_terms)
                search_url = f"https://www.google.com/search?q={query}"
                return {
                    "success": True,
                    "message": f"🔍 Searching for '{search_terms}'...",
                    "tool": "web_search",
                    "action": "open_url",
                    "url": search_url,
                    "query": search_terms,
                    "execute_on_client": True,
                }

        # If we reach here, command recognized but not yet implemented
        return {
            "success": False,
            "error": "Command recognized but execution not yet implemented",
            "message": f"I recognized your command (intent: {intent}), but the execution module is still being developed.",
        }

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "An error occurred while trying to execute your command.",
        }


def extract_search_terms(text: str) -> Optional[str]:
    """Extract search terms from text."""
    # Remove common command words
    text_lower = text.lower()
    for phrase in ["search for", "find", "look up", "google"]:
        text_lower = text_lower.replace(phrase, "")

    return text_lower.strip() if text_lower.strip() else None


async def get_llm_response(text: str, context: Optional[Dict] = None) -> str:
    """Get response from LLM service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{LLM_SERVICE_URL}/generate",
                json={"prompt": text, "context": context or {}},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "I'm not sure how to respond to that.")
            else:
                logger.warning(f"LLM service returned status {response.status_code}")
                return "I'm having trouble generating a response right now."

    except Exception as e:
        logger.error(f"Error calling LLM service: {e}")
        return "I'm processing your request, but my language model is temporarily unavailable."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

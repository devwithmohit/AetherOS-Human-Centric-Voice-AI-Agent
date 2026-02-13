"""
WebSocket Support for Streaming Responses

Provides real-time bidirectional communication for streaming results
from voice processing, execution progress, and memory updates.
"""

import asyncio
import json
from typing import Dict, Any, Set
from datetime import datetime
import structlog

from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.routing import APIRouter

from app.config import settings

logger = structlog.get_logger()

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> {session_ids}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str = None,
    ):
        """
        Accept WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Unique session ID
            user_id: User ID if authenticated
        """
        await websocket.accept()

        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "message_count": 0,
        }

        if user_id:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

        logger.info(
            "websocket_connected",
            session_id=session_id,
            user_id=user_id,
            total_connections=len(self.active_connections),
        )

    def disconnect(self, session_id: str):
        """
        Remove WebSocket connection.

        Args:
            session_id: Session ID to disconnect
        """
        if session_id in self.active_connections:
            metadata = self.connection_metadata.get(session_id, {})
            user_id = metadata.get("user_id")

            # Remove from user sessions
            if user_id and user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]

            # Remove connection
            del self.active_connections[session_id]
            del self.connection_metadata[session_id]

            logger.info(
                "websocket_disconnected",
                session_id=session_id,
                user_id=user_id,
                total_connections=len(self.active_connections),
            )

    async def send_message(
        self,
        session_id: str,
        message: Dict[str, Any],
    ):
        """
        Send message to specific session.

        Args:
            session_id: Target session ID
            message: Message data
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
                self.connection_metadata[session_id]["message_count"] += 1
            except Exception as e:
                logger.error(
                    "websocket_send_failed",
                    session_id=session_id,
                    error=str(e),
                )
                self.disconnect(session_id)

    async def broadcast_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
    ):
        """
        Broadcast message to all sessions of a user.

        Args:
            user_id: User ID
            message: Message data
        """
        if user_id in self.user_sessions:
            session_ids = list(self.user_sessions[user_id])
            for session_id in session_ids:
                await self.send_message(session_id, message)

    async def broadcast_all(self, message: Dict[str, Any]):
        """
        Broadcast message to all connections.

        Args:
            message: Message data
        """
        disconnected = []
        for session_id in list(self.active_connections.keys()):
            try:
                await self.send_message(session_id, message)
            except:
                disconnected.append(session_id)

        for session_id in disconnected:
            self.disconnect(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_sessions),
            "max_connections": settings.WS_MAX_CONNECTIONS,
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """WebSocket endpoint with explicit session ID."""
    await _handle_websocket(websocket, session_id)


@router.websocket("/ws")
async def websocket_endpoint_default(
    websocket: WebSocket,
):
    """WebSocket endpoint with auto-generated session ID."""
    import uuid

    session_id = str(uuid.uuid4())
    await _handle_websocket(websocket, session_id)


async def _handle_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """
    Internal WebSocket handler.

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier
    """
    # Check connection limit
    if len(manager.active_connections) >= settings.WS_MAX_CONNECTIONS:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Max connections reached",
        )
        return

    # Extract user_id from query params if authenticated
    user_id = websocket.query_params.get("user_id")

    await manager.connect(websocket, session_id, user_id)

    # Send welcome message
    await manager.send_message(
        session_id,
        {
            "type": "connection",
            "status": "connected",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat(session_id))

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                logger.debug(
                    "websocket_message_received",
                    session_id=session_id,
                    type=message_type,
                )

                # Route message based on type
                if message_type == "ping":
                    await manager.send_message(
                        session_id,
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                    )

                elif message_type == "message":
                    # Handle regular text message (chat/command)
                    await handle_message(session_id, message)

                elif message_type == "stt_stream":
                    # Handle streaming STT
                    await handle_stt_stream(session_id, message)

                elif message_type == "tts_stream":
                    # Handle streaming TTS
                    await handle_tts_stream(session_id, message)

                elif message_type == "execution_subscribe":
                    # Subscribe to execution progress
                    await handle_execution_subscribe(session_id, message)

                elif message_type == "memory_subscribe":
                    # Subscribe to memory updates
                    await handle_memory_subscribe(session_id, message)

                else:
                    await manager.send_message(
                        session_id,
                        {
                            "type": "error",
                            "error": f"Unknown message type: {message_type}",
                        },
                    )

            except json.JSONDecodeError:
                await manager.send_message(
                    session_id,
                    {"type": "error", "error": "Invalid JSON"},
                )

    except WebSocketDisconnect:
        logger.info("websocket_disconnect", session_id=session_id)

    finally:
        heartbeat_task.cancel()
        manager.disconnect(session_id)


async def heartbeat(session_id: str):
    """
    Send periodic heartbeat to keep connection alive.

    Args:
        session_id: Session ID
    """
    try:
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            await manager.send_message(
                session_id,
                {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()},
            )
    except asyncio.CancelledError:
        pass


async def handle_message(session_id: str, message: Dict[str, Any]):
    """
    Handle regular text message/command.

    Args:
        session_id: WebSocket session ID
        message: Message containing 'text' field
    """
    text = message.get("text", "")

    # Send status update
    await manager.send_message(
        session_id,
        {
            "type": "status",
            "status": "processing",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    # Call orchestrator service to process the message
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "http://aether-orchestrator:8001/process",
                json={
                    "text": text,
                    "session_id": session_id,
                },
            )

            if response.status_code == 200:
                result = response.json()

                response_text = result.get("response", "I processed your request.")
                intent = result.get("intent")
                executed = result.get("executed", False)
                error = result.get("error")

                # Check if result includes client-side execution instructions
                execute_on_client = result.get("execute_on_client", False)
                action = result.get("action")
                url = result.get("url")

                # Log the result
                logger.info(
                    f"Orchestrator processed message",
                    session_id=session_id,
                    intent=intent,
                    executed=executed,
                    execute_on_client=execute_on_client,
                )

                # Send response with execution instructions
                response_data = {
                    "type": "response",
                    "text": response_text,
                    "intent": intent,
                    "executed": executed,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Add execution instructions if present
                if execute_on_client and url:
                    response_data["execute"] = {
                        "action": action,
                        "url": url,
                    }

                await manager.send_message(session_id, response_data)
            else:
                logger.error(
                    f"Orchestrator returned error",
                    status_code=response.status_code,
                )
                await manager.send_message(
                    session_id,
                    {
                        "type": "response",
                        "text": "I encountered an issue while processing your request. Please try again.",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

    except httpx.TimeoutException:
        logger.error("Orchestrator timeout")
        await manager.send_message(
            session_id,
            {
                "type": "response",
                "text": "The request is taking longer than expected. Please try again.",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Error calling orchestrator: {e}", exc_info=True)
        await manager.send_message(
            session_id,
            {
                "type": "response",
                "text": "I'm having trouble processing your request right now. Please try again later.",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # Send completion status
    await manager.send_message(
        session_id,
        {
            "type": "status",
            "status": "complete",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def handle_stt_stream(session_id: str, message: Dict[str, Any]):
    """Handle STT streaming request."""
    # TODO: Integrate with M2 STT service
    await manager.send_message(
        session_id,
        {
            "type": "stt_result",
            "transcript": "Streaming transcript...",
            "is_final": False,
        },
    )


async def handle_tts_stream(session_id: str, message: Dict[str, Any]):
    """Handle TTS streaming request."""
    # TODO: Integrate with M3 TTS service
    await manager.send_message(
        session_id,
        {
            "type": "tts_chunk",
            "audio_data": "base64_audio_chunk",
            "chunk_index": 0,
        },
    )


async def handle_execution_subscribe(session_id: str, message: Dict[str, Any]):
    """Handle execution progress subscription."""
    plan_id = message.get("plan_id")
    await manager.send_message(
        session_id,
        {
            "type": "execution_progress",
            "plan_id": plan_id,
            "step": 1,
            "status": "running",
            "progress": 0.25,
        },
    )


async def handle_memory_subscribe(session_id: str, message: Dict[str, Any]):
    """Handle memory update subscription."""
    await manager.send_message(
        session_id,
        {
            "type": "memory_update",
            "key": "example_key",
            "action": "created",
        },
    )


@router.get("/ws/stats")
async def websocket_stats() -> Dict[str, Any]:
    """
    Get WebSocket connection statistics.

    Returns:
        Connection statistics
    """
    return manager.get_stats()

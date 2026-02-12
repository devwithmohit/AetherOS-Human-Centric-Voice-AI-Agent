"""
Memory Services Router

Routes requests to:
- M10: Memory Manager
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models


class MemoryItem(BaseModel):
    """Memory item."""

    key: str = Field(..., description="Memory key")
    value: Any = Field(..., description="Memory value")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    ttl_seconds: Optional[int] = Field(None, description="Time-to-live in seconds")


class MemoryResponse(BaseModel):
    """Memory operation response."""

    success: bool = Field(..., description="Whether operation succeeded")
    key: Optional[str] = Field(None, description="Memory key")
    value: Optional[Any] = Field(None, description="Stored value")
    error: Optional[str] = Field(None, description="Error message if failed")


class SearchMemoryRequest(BaseModel):
    """Memory search request."""

    query: str = Field(..., description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")


class MemorySearchResult(BaseModel):
    """Memory search result."""

    key: str = Field(..., description="Memory key")
    value: Any = Field(..., description="Memory value")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    created_at: datetime = Field(..., description="Creation timestamp")


class MemorySearchResponse(BaseModel):
    """Memory search response."""

    results: List[MemorySearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total matching results")
    search_time_ms: int = Field(..., description="Search time in milliseconds")


class ConversationContext(BaseModel):
    """Conversation context."""

    session_id: str = Field(..., description="Session ID")
    turns: List[Dict[str, Any]] = Field(..., description="Conversation turns")
    summary: Optional[str] = Field(None, description="Conversation summary")


# Endpoints


@router.post("/store", response_model=MemoryResponse)
async def store_memory(
    request: Request,
    memory: MemoryItem,
) -> MemoryResponse:
    """
    Store information in memory (M10).

    Args:
        memory: Memory item to store

    Returns:
        Storage confirmation
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        memory_client = grpc_manager.get_client("memory")

        if not memory_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory Manager service unavailable",
            )

        logger.info(
            "memory_store_request",
            key=memory.key,
            has_ttl=memory.ttl_seconds is not None,
            tag_count=len(memory.tags),
        )

        # TODO: Make gRPC call to M10
        # Mock response for now
        response = MemoryResponse(
            success=True,
            key=memory.key,
            value=memory.value,
            error=None,
        )

        logger.info("memory_stored", key=memory.key)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_store_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory storage failed: {str(e)}",
        )


@router.get("/retrieve/{key}", response_model=MemoryResponse)
async def retrieve_memory(
    request: Request,
    key: str,
) -> MemoryResponse:
    """
    Retrieve information from memory (M10).

    Args:
        key: Memory key

    Returns:
        Retrieved memory value
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        memory_client = grpc_manager.get_client("memory")

        if not memory_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory Manager service unavailable",
            )

        logger.info("memory_retrieve_request", key=key)

        # TODO: Make gRPC call to M10
        # Mock response for now
        response = MemoryResponse(
            success=True,
            key=key,
            value="Sample stored value",
            error=None,
        )

        logger.info("memory_retrieved", key=key)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_retrieve_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory retrieval failed: {str(e)}",
        )


@router.delete("/delete/{key}")
async def delete_memory(
    request: Request,
    key: str,
) -> Dict[str, Any]:
    """
    Delete memory entry (M10).

    Args:
        key: Memory key to delete

    Returns:
        Deletion confirmation
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        memory_client = grpc_manager.get_client("memory")

        if not memory_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory Manager service unavailable",
            )

        logger.info("memory_delete_request", key=key)

        # TODO: Make gRPC call to M10
        # Mock response for now
        logger.info("memory_deleted", key=key)
        return {"success": True, "key": key}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_delete_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory deletion failed: {str(e)}",
        )


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    request: Request,
    search_request: SearchMemoryRequest,
) -> MemorySearchResponse:
    """
    Search memory (M10).

    Args:
        search_request: Search parameters

    Returns:
        Matching memory items
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        memory_client = grpc_manager.get_client("memory")

        if not memory_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory Manager service unavailable",
            )

        logger.info(
            "memory_search_request",
            query=search_request.query,
            has_tags=search_request.tags is not None,
            limit=search_request.limit,
        )

        # TODO: Make gRPC call to M10
        # Mock response for now
        response = MemorySearchResponse(
            results=[
                MemorySearchResult(
                    key="user_preference_1",
                    value="Dark mode enabled",
                    relevance_score=0.95,
                    tags=["preference", "ui"],
                    created_at=datetime.utcnow(),
                ),
            ],
            total_count=1,
            search_time_ms=42,
        )

        logger.info(
            "memory_search_complete",
            query=search_request.query,
            result_count=len(response.results),
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_search_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory search failed: {str(e)}",
        )


@router.get("/context/{session_id}", response_model=ConversationContext)
async def get_conversation_context(
    request: Request,
    session_id: str,
) -> ConversationContext:
    """
    Get conversation context (M10).

    Args:
        session_id: Session identifier

    Returns:
        Conversation history and context
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        memory_client = grpc_manager.get_client("memory")

        if not memory_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory Manager service unavailable",
            )

        logger.info("context_retrieve_request", session_id=session_id)

        # TODO: Make gRPC call to M10
        # Mock response for now
        response = ConversationContext(
            session_id=session_id,
            turns=[
                {"role": "user", "content": "Hello", "timestamp": datetime.utcnow().isoformat()},
                {
                    "role": "assistant",
                    "content": "Hi! How can I help?",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ],
            summary="User greeted the assistant",
        )

        logger.info("context_retrieved", session_id=session_id, turn_count=len(response.turns))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("context_retrieve_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context retrieval failed: {str(e)}",
        )

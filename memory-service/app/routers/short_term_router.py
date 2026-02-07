"""Short-term memory API endpoints."""

from fastapi import APIRouter, HTTPException, status
from typing import Any
from app.schemas import ShortTermMemoryCreate, ShortTermMemoryResponse, StatusResponse
from app.stores.short_term import short_term_memory
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/short-term", tags=["Short-Term Memory"])


@router.post("/set", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def set_memory(memory: ShortTermMemoryCreate) -> StatusResponse:
    """Store value in short-term memory."""
    try:
        success = await short_term_memory.set(
            key=memory.key,
            value=memory.value,
            ttl=memory.ttl,
            namespace=memory.namespace,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store memory",
            )

        return StatusResponse(
            status="success",
            message=f"Stored key: {memory.key}",
            data={"key": memory.key, "namespace": memory.namespace},
        )
    except Exception as e:
        logger.error(f"Error setting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/get/{namespace}/{key}", response_model=ShortTermMemoryResponse)
async def get_memory(namespace: str, key: str) -> ShortTermMemoryResponse:
    """Retrieve value from short-term memory."""
    try:
        value = await short_term_memory.get(key=key, namespace=namespace)
        exists = value is not None

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key not found: {namespace}:{key}",
            )

        ttl = await short_term_memory.get_ttl(key=key, namespace=namespace)

        return ShortTermMemoryResponse(
            key=key,
            value=value,
            ttl=ttl,
            exists=exists,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/delete/{namespace}/{key}", response_model=StatusResponse)
async def delete_memory(namespace: str, key: str) -> StatusResponse:
    """Delete value from short-term memory."""
    try:
        success = await short_term_memory.delete(key=key, namespace=namespace)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key not found: {namespace}:{key}",
            )

        return StatusResponse(
            status="success",
            message=f"Deleted key: {namespace}:{key}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/conversation/{session_id}", response_model=dict[str, Any])
async def get_conversation_context(session_id: str) -> dict[str, Any]:
    """Get conversation context from short-term memory."""
    try:
        context = await short_term_memory.get_conversation_context(session_id)

        if context is None:
            return {"session_id": session_id, "context": {}}

        return {"session_id": session_id, "context": context}
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/conversation/{session_id}", response_model=StatusResponse)
async def set_conversation_context(session_id: str, context: dict[str, Any]) -> StatusResponse:
    """Set conversation context in short-term memory."""
    try:
        success = await short_term_memory.set_conversation_context(
            session_id=session_id,
            context=context,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store conversation context",
            )

        return StatusResponse(
            status="success",
            message=f"Stored conversation context for session: {session_id}",
        )
    except Exception as e:
        logger.error(f"Error setting conversation context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

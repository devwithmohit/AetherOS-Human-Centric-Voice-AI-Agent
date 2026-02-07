"""Long-term memory API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas import (
    UserPreferencesCreate,
    UserPreferencesResponse,
    ConsentCreate,
    ConsentResponse,
    ExecutionCreate,
    ExecutionResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    KnowledgeCreate,
    KnowledgeResponse,
    StatusResponse,
)
from app.stores.long_term import long_term_memory
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/long-term", tags=["Long-Term Memory"])


# User Preferences
@router.post(
    "/preferences", response_model=UserPreferencesResponse, status_code=status.HTTP_201_CREATED
)
async def create_preferences(
    prefs: UserPreferencesCreate,
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Create or update user preferences."""
    try:
        result = await long_term_memory.set_user_preferences(
            session=db,
            user_id=prefs.user_id,
            preferences=prefs.preferences,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/preferences/{user_id}", response_model=UserPreferencesResponse)
async def get_preferences(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Get user preferences."""
    try:
        result = await long_term_memory.get_user_preferences(session=db, user_id=user_id)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preferences not found for user: {user_id}",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Consent Management
@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def record_consent(
    consent: ConsentCreate,
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    """Record user consent."""
    try:
        result = await long_term_memory.record_consent(
            session=db,
            user_id=consent.user_id,
            consent_type=consent.consent_type,
            granted=consent.granted,
            ip_address=consent.ip_address,
            user_agent=consent.user_agent,
        )
        return result
    except Exception as e:
        logger.error(f"Error recording consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/consent/{user_id}/{consent_type}", response_model=dict)
async def check_consent(
    user_id: str,
    consent_type: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check consent status."""
    try:
        granted = await long_term_memory.get_consent_status(
            session=db,
            user_id=user_id,
            consent_type=consent_type,
        )
        return {"user_id": user_id, "consent_type": consent_type, "granted": granted}
    except Exception as e:
        logger.error(f"Error checking consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Execution History
@router.post("/execution", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def log_execution(
    execution: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """Log command execution."""
    try:
        result = await long_term_memory.log_execution(
            session=db,
            user_id=execution.user_id,
            session_id=execution.session_id,
            command=execution.command,
            tool_name=execution.tool_name,
            parameters=execution.parameters,
            result=execution.result,
            success=execution.success,
            error_message=execution.error_message,
            execution_time_ms=execution.execution_time_ms,
        )
        return result
    except Exception as e:
        logger.error(f"Error logging execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/execution/{user_id}", response_model=List[ExecutionResponse])
async def get_execution_history(
    user_id: str,
    session_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[ExecutionResponse]:
    """Get execution history."""
    try:
        result = await long_term_memory.get_execution_history(
            session=db,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Conversations
@router.post(
    "/conversation", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create new conversation."""
    try:
        result = await long_term_memory.create_conversation(
            session=db,
            user_id=conversation.user_id,
            session_id=conversation.session_id,
            title=conversation.title,
            context=conversation.context,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/conversation/{session_id}", response_model=ConversationResponse)
async def get_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get conversation by session ID."""
    try:
        result = await long_term_memory.get_conversation(session=db, session_id=session_id)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {session_id}",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch("/conversation/{session_id}", response_model=StatusResponse)
async def update_conversation(
    session_id: str,
    update_data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """Update conversation."""
    try:
        success = await long_term_memory.update_conversation(
            session=db,
            session_id=session_id,
            title=update_data.title,
            context=update_data.context,
            increment_message_count=update_data.increment_message_count,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {session_id}",
            )

        return StatusResponse(status="success", message="Conversation updated")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/conversation/{session_id}", response_model=StatusResponse)
async def end_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """End conversation."""
    try:
        success = await long_term_memory.end_conversation(session=db, session_id=session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {session_id}",
            )

        return StatusResponse(status="success", message="Conversation ended")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Knowledge Base
@router.post("/knowledge", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def store_knowledge(
    knowledge: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """Store knowledge item."""
    try:
        result = await long_term_memory.store_knowledge(
            session=db,
            user_id=knowledge.user_id,
            category=knowledge.category,
            key=knowledge.key,
            value=knowledge.value,
            confidence=knowledge.confidence,
            source=knowledge.source,
            metadata=knowledge.metadata,
            expires_at=knowledge.expires_at,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/knowledge/{user_id}", response_model=List[KnowledgeResponse])
async def get_knowledge(
    user_id: str,
    category: Optional[str] = None,
    key: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeResponse]:
    """Get knowledge items."""
    try:
        result = await long_term_memory.get_knowledge(
            session=db,
            user_id=user_id,
            category=category,
            key=key,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/knowledge/{user_id}", response_model=StatusResponse)
async def delete_knowledge(
    user_id: str,
    category: Optional[str] = None,
    key: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """Delete knowledge items."""
    try:
        count = await long_term_memory.delete_knowledge(
            session=db,
            user_id=user_id,
            category=category,
            key=key,
        )

        return StatusResponse(
            status="success",
            message=f"Deleted {count} knowledge items",
            data={"deleted_count": count},
        )
    except Exception as e:
        logger.error(f"Error deleting knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

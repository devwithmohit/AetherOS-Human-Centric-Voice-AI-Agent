"""Memory Dashboard API - Query and visualize stored memory."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models import (
    UserPreference,
    ConsentRecord,
    ExecutionHistory,
    Conversation,
    KnowledgeBase,
)
from app.stores.short_term import short_term_memory
from app.stores.episodic import episodic_memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Memory Dashboard"])


@router.get("/overview/{user_id}", response_model=Dict[str, Any])
async def get_memory_overview(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get comprehensive memory overview for a user.

    Returns statistics across all memory tiers (short-term, long-term, episodic).
    """
    try:
        overview = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "short_term": {},
            "long_term": {},
            "episodic": {},
        }

        # Short-term memory stats
        try:
            # Count keys for this user
            pattern = f"{user_id}:*"
            keys = await short_term_memory.redis.keys(pattern)
            overview["short_term"] = {
                "total_keys": len(keys) if keys else 0,
                "storage_type": "redis",
                "ttl_seconds": 3600,
            }
        except Exception as e:
            logger.error(f"Error getting short-term stats: {e}")
            overview["short_term"] = {"error": str(e)}

        # Long-term memory stats
        try:
            # Count preferences
            pref_result = await db.execute(
                select(func.count(UserPreference.id)).where(UserPreference.user_id == user_id)
            )
            pref_count = pref_result.scalar() or 0

            # Count consents
            consent_result = await db.execute(
                select(func.count(ConsentRecord.id)).where(ConsentRecord.user_id == user_id)
            )
            consent_count = consent_result.scalar() or 0

            # Count executions
            exec_result = await db.execute(
                select(func.count(ExecutionHistory.id)).where(ExecutionHistory.user_id == user_id)
            )
            exec_count = exec_result.scalar() or 0

            # Count conversations
            conv_result = await db.execute(
                select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
            )
            conv_count = conv_result.scalar() or 0

            # Count knowledge entries
            kb_result = await db.execute(
                select(func.count(KnowledgeBase.id)).where(KnowledgeBase.user_id == user_id)
            )
            kb_count = kb_result.scalar() or 0

            overview["long_term"] = {
                "preferences": pref_count,
                "consents": consent_count,
                "executions": exec_count,
                "conversations": conv_count,
                "knowledge_entries": kb_count,
                "total_records": pref_count + consent_count + exec_count + conv_count + kb_count,
                "storage_type": "postgresql",
            }
        except Exception as e:
            logger.error(f"Error getting long-term stats: {e}")
            overview["long_term"] = {"error": str(e)}

        # Episodic memory stats
        try:
            episode_count = await episodic_memory.count_episodes(user_id)
            overview["episodic"] = {
                "total_episodes": episode_count,
                "storage_type": "chromadb",
                "retention_days": 90,
            }
        except Exception as e:
            logger.error(f"Error getting episodic stats: {e}")
            overview["episodic"] = {"error": str(e)}

        return overview

    except Exception as e:
        logger.error(f"Error getting memory overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory overview: {str(e)}",
        )


@router.get("/activity/{user_id}", response_model=Dict[str, Any])
async def get_user_activity(
    user_id: str,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get user activity statistics over time.

    Args:
        user_id: User identifier
        days: Number of days to look back (default: 7)
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get execution history
        exec_result = await db.execute(
            select(ExecutionHistory)
            .where(
                and_(
                    ExecutionHistory.user_id == user_id,
                    ExecutionHistory.timestamp >= start_date,
                )
            )
            .order_by(ExecutionHistory.timestamp.desc())
        )
        executions = exec_result.scalars().all()

        # Calculate statistics
        total_executions = len(executions)
        successful = sum(1 for e in executions if e.success)
        failed = total_executions - successful

        # Group by tool
        tools_used = {}
        for execution in executions:
            tool = execution.tool_name
            if tool not in tools_used:
                tools_used[tool] = {"count": 0, "success": 0, "fail": 0}
            tools_used[tool]["count"] += 1
            if execution.success:
                tools_used[tool]["success"] += 1
            else:
                tools_used[tool]["fail"] += 1

        # Average execution time
        avg_time = (
            sum(e.execution_time_ms for e in executions if e.execution_time_ms) / total_executions
            if total_executions > 0
            else 0
        )

        return {
            "user_id": user_id,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "total_executions": total_executions,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_executions if total_executions > 0 else 0,
            "average_execution_time_ms": avg_time,
            "tools_used": tools_used,
        }

    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity: {str(e)}",
        )


@router.get("/conversations/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_conversations(
    user_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get recent conversations for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of conversations to return
    """
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        conversations = result.scalars().all()

        return [
            {
                "session_id": conv.session_id,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "message_count": conv.message_count,
                "context": conv.context,
            }
            for conv in conversations
        ]

    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}",
        )


@router.get("/knowledge/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_knowledge(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get knowledge entries for a user.

    Args:
        user_id: User identifier
        category: Filter by category (optional)
        limit: Maximum number of entries to return
    """
    try:
        query = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)

        if category:
            query = query.where(KnowledgeBase.category == category)

        query = query.order_by(KnowledgeBase.confidence.desc()).limit(limit)

        result = await db.execute(query)
        knowledge_entries = result.scalars().all()

        return [
            {
                "key": kb.key,
                "value": kb.value,
                "category": kb.category,
                "confidence": kb.confidence,
                "created_at": kb.created_at.isoformat() if kb.created_at else None,
                "expires_at": kb.expires_at.isoformat() if kb.expires_at else None,
            }
            for kb in knowledge_entries
        ]

    except Exception as e:
        logger.error(f"Error getting knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get knowledge: {str(e)}",
        )


@router.get("/search", response_model=Dict[str, Any])
async def search_memories(
    user_id: str,
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Search across all memory types.

    Args:
        user_id: User identifier
        query: Search query text
        memory_type: Filter by memory type (short-term, long-term, episodic)
        limit: Maximum results per type
    """
    try:
        results = {
            "query": query,
            "user_id": user_id,
            "results": {},
        }

        # Search episodic memory (semantic search)
        if not memory_type or memory_type == "episodic":
            try:
                episodes = await episodic_memory.query_episodes(
                    user_id=user_id,
                    query_text=query,
                    n_results=limit,
                )
                results["results"]["episodic"] = [
                    {
                        "id": ep["id"],
                        "content": ep["content"],
                        "distance": ep.get("distance", 0),
                        "metadata": ep.get("metadata", {}),
                    }
                    for ep in episodes
                ]
            except Exception as e:
                logger.error(f"Error searching episodic: {e}")
                results["results"]["episodic"] = {"error": str(e)}

        # Search knowledge base
        if not memory_type or memory_type == "long-term":
            try:
                kb_result = await db.execute(
                    select(KnowledgeBase)
                    .where(
                        and_(
                            KnowledgeBase.user_id == user_id,
                            KnowledgeBase.value.ilike(f"%{query}%"),
                        )
                    )
                    .limit(limit)
                )
                knowledge = kb_result.scalars().all()
                results["results"]["knowledge"] = [
                    {
                        "key": kb.key,
                        "value": kb.value,
                        "category": kb.category,
                        "confidence": kb.confidence,
                    }
                    for kb in knowledge
                ]
            except Exception as e:
                logger.error(f"Error searching knowledge: {e}")
                results["results"]["knowledge"] = {"error": str(e)}

        return results

    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.delete("/purge/{user_id}", response_model=Dict[str, Any])
async def purge_user_data(
    user_id: str,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Purge all data for a user (GDPR compliance).

    Args:
        user_id: User identifier
        confirm: Must be True to proceed with deletion
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=True to purge user data",
        )

    try:
        deleted_counts = {
            "user_id": user_id,
            "deleted": {},
        }

        # Delete short-term memory
        try:
            pattern = f"{user_id}:*"
            keys = await short_term_memory.redis.keys(pattern)
            if keys:
                await short_term_memory.redis.delete(*keys)
                deleted_counts["deleted"]["short_term_keys"] = len(keys)
        except Exception as e:
            logger.error(f"Error deleting short-term: {e}")
            deleted_counts["deleted"]["short_term_error"] = str(e)

        # Delete long-term memory
        try:
            # Delete preferences
            pref_result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            prefs = pref_result.scalars().all()
            for pref in prefs:
                await db.delete(pref)

            # Delete consents
            consent_result = await db.execute(
                select(ConsentRecord).where(ConsentRecord.user_id == user_id)
            )
            consents = consent_result.scalars().all()
            for consent in consents:
                await db.delete(consent)

            # Delete executions
            exec_result = await db.execute(
                select(ExecutionHistory).where(ExecutionHistory.user_id == user_id)
            )
            executions = exec_result.scalars().all()
            for execution in executions:
                await db.delete(execution)

            # Delete conversations
            conv_result = await db.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversations = conv_result.scalars().all()
            for conv in conversations:
                await db.delete(conv)

            # Delete knowledge
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
            )
            knowledge = kb_result.scalars().all()
            for kb in knowledge:
                await db.delete(kb)

            await db.commit()

            deleted_counts["deleted"]["long_term"] = {
                "preferences": len(prefs),
                "consents": len(consents),
                "executions": len(executions),
                "conversations": len(conversations),
                "knowledge": len(knowledge),
            }
        except Exception as e:
            logger.error(f"Error deleting long-term: {e}")
            await db.rollback()
            deleted_counts["deleted"]["long_term_error"] = str(e)

        # Delete episodic memory
        try:
            success = await episodic_memory.delete_user_episodes(user_id)
            deleted_counts["deleted"]["episodic"] = "success" if success else "failed"
        except Exception as e:
            logger.error(f"Error deleting episodic: {e}")
            deleted_counts["deleted"]["episodic_error"] = str(e)

        return deleted_counts

    except Exception as e:
        logger.error(f"Error purging user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge data: {str(e)}",
        )

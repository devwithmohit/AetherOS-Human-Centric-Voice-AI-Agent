"""Episodic memory API endpoints."""

from fastapi import APIRouter, HTTPException, status
from typing import List
from app.schemas import (
    EpisodeCreate,
    EpisodeQuery,
    EpisodeResponse,
    StatusResponse,
)
from app.stores.episodic import episodic_memory
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/episodic", tags=["Episodic Memory"])


@router.post("/store", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def store_episode(episode: EpisodeCreate) -> StatusResponse:
    """Store episodic memory."""
    try:
        episode_id = await episodic_memory.store_episode(
            user_id=episode.user_id,
            session_id=episode.session_id,
            content=episode.content,
            metadata=episode.metadata,
            episode_id=episode.episode_id,
        )

        return StatusResponse(
            status="success",
            message="Episode stored successfully",
            data={"episode_id": episode_id},
        )
    except Exception as e:
        logger.error(f"Error storing episode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/query", response_model=List[EpisodeResponse])
async def query_episodes(query: EpisodeQuery) -> List[EpisodeResponse]:
    """Query episodic memories using semantic search."""
    try:
        results = await episodic_memory.query_episodes(
            user_id=query.user_id,
            query_text=query.query_text,
            n_results=query.n_results,
            session_id=query.session_id,
            filters=query.filters,
        )

        return [
            EpisodeResponse(
                id=ep["id"],
                content=ep["content"] or "",
                metadata=ep["metadata"],
                distance=ep.get("distance"),
            )
            for ep in results
        ]
    except Exception as e:
        logger.error(f"Error querying episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/episode/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str) -> EpisodeResponse:
    """Get specific episode by ID."""
    try:
        episode = await episodic_memory.get_episode(episode_id)

        if episode is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode not found: {episode_id}",
            )

        return EpisodeResponse(
            id=episode["id"],
            content=episode["content"] or "",
            metadata=episode["metadata"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting episode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/recent/{user_id}", response_model=List[EpisodeResponse])
async def get_recent_episodes(
    user_id: str,
    limit: int = 100,
    session_id: str = None,
) -> List[EpisodeResponse]:
    """Get recent episodes for a user."""
    try:
        results = await episodic_memory.get_recent_episodes(
            user_id=user_id,
            limit=limit,
            session_id=session_id,
        )

        return [
            EpisodeResponse(
                id=ep["id"],
                content=ep["content"] or "",
                metadata=ep["metadata"],
            )
            for ep in results
        ]
    except Exception as e:
        logger.error(f"Error getting recent episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/episode/{episode_id}", response_model=StatusResponse)
async def delete_episode(episode_id: str) -> StatusResponse:
    """Delete specific episode."""
    try:
        success = await episodic_memory.delete_episode(episode_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode not found: {episode_id}",
            )

        return StatusResponse(
            status="success",
            message=f"Episode deleted: {episode_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting episode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/user/{user_id}", response_model=StatusResponse)
async def delete_user_episodes(user_id: str, session_id: str = None) -> StatusResponse:
    """Delete all episodes for a user or session."""
    try:
        count = await episodic_memory.delete_user_episodes(
            user_id=user_id,
            session_id=session_id,
        )

        return StatusResponse(
            status="success",
            message=f"Deleted {count} episodes",
            data={"deleted_count": count},
        )
    except Exception as e:
        logger.error(f"Error deleting user episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/count/{user_id}", response_model=dict)
async def count_episodes(user_id: str, session_id: str = None) -> dict:
    """Count episodes for a user or session."""
    try:
        count = await episodic_memory.count_episodes(
            user_id=user_id,
            session_id=session_id,
        )

        return {
            "user_id": user_id,
            "session_id": session_id,
            "count": count,
        }
    except Exception as e:
        logger.error(f"Error counting episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

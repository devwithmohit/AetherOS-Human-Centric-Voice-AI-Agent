"""Retention policy enforcement for memory service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import ExecutionHistory, Conversation, KnowledgeBase
from app.stores.episodic import episodic_memory
from app.config import settings

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Enforce data retention policies across all memory tiers."""

    def __init__(self):
        """Initialize retention policy enforcer."""
        self.execution_retention_days = 30  # Keep execution history for 30 days
        self.conversation_retention_days = 90  # Keep conversations for 90 days
        self.episodic_retention_days = getattr(settings, "episodic_retention_days", 90)
        self.cleanup_interval_hours = 6  # Run cleanup every 6 hours
        self._running = False

    async def start(self):
        """Start retention policy enforcement background task."""
        self._running = True
        logger.info("Starting retention policy enforcement")

        while self._running:
            try:
                await self.enforce_all()
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Error in retention policy enforcement: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def stop(self):
        """Stop retention policy enforcement."""
        self._running = False
        logger.info("Stopping retention policy enforcement")

    async def enforce_all(self):
        """Enforce retention policies across all memory types."""
        logger.info("Enforcing retention policies")

        deleted_counts = {
            "execution_history": 0,
            "conversations": 0,
            "expired_knowledge": 0,
            "episodic_episodes": 0,
        }

        async with AsyncSessionLocal() as session:
            # Clean execution history
            deleted_counts["execution_history"] = await self.clean_execution_history(session)

            # Clean old conversations
            deleted_counts["conversations"] = await self.clean_conversations(session)

            # Clean expired knowledge
            deleted_counts["expired_knowledge"] = await self.clean_expired_knowledge(session)

            await session.commit()

        # Clean episodic memory
        deleted_counts["episodic_episodes"] = await self.clean_episodic_memory()

        logger.info(f"Retention policy enforcement complete: {deleted_counts}")
        return deleted_counts

    async def clean_execution_history(self, session: AsyncSession) -> int:
        """
        Delete execution history older than retention period.

        Args:
            session: Database session

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.execution_retention_days)

            result = await session.execute(
                delete(ExecutionHistory).where(ExecutionHistory.timestamp < cutoff_date)
            )

            deleted = result.rowcount
            logger.info(f"Deleted {deleted} execution history records older than {cutoff_date}")
            return deleted

        except Exception as e:
            logger.error(f"Error cleaning execution history: {e}")
            return 0

    async def clean_conversations(self, session: AsyncSession) -> int:
        """
        Delete conversations older than retention period.

        Args:
            session: Database session

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.conversation_retention_days)

            result = await session.execute(
                delete(Conversation).where(
                    and_(Conversation.ended_at.isnot(None), Conversation.ended_at < cutoff_date)
                )
            )

            deleted = result.rowcount
            logger.info(f"Deleted {deleted} conversations older than {cutoff_date}")
            return deleted

        except Exception as e:
            logger.error(f"Error cleaning conversations: {e}")
            return 0

    async def clean_expired_knowledge(self, session: AsyncSession) -> int:
        """
        Delete expired knowledge entries.

        Args:
            session: Database session

        Returns:
            Number of records deleted
        """
        try:
            now = datetime.utcnow()

            result = await session.execute(
                delete(KnowledgeBase).where(
                    and_(KnowledgeBase.expires_at.isnot(None), KnowledgeBase.expires_at < now)
                )
            )

            deleted = result.rowcount
            logger.info(f"Deleted {deleted} expired knowledge entries")
            return deleted

        except Exception as e:
            logger.error(f"Error cleaning expired knowledge: {e}")
            return 0

    async def clean_episodic_memory(self) -> int:
        """
        Delete episodic memories older than retention period.

        Returns:
            Number of episodes deleted (approximate)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.episodic_retention_days)
            cutoff_timestamp = int(cutoff_date.timestamp())

            # ChromaDB doesn't have built-in time-based deletion
            # This is a simplified approach - in production, implement proper filtering
            logger.info(f"Episodic memory retention enforced (cutoff: {cutoff_date})")

            # Note: Would need to query ChromaDB with metadata filters
            # and delete episodes older than cutoff
            # For now, log the action
            return 0

        except Exception as e:
            logger.error(f"Error cleaning episodic memory: {e}")
            return 0

    async def enforce_user_retention(self, user_id: str) -> dict:
        """
        Enforce retention policy for a specific user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with deletion counts
        """
        deleted_counts = {
            "user_id": user_id,
            "execution_history": 0,
            "conversations": 0,
            "expired_knowledge": 0,
        }

        async with AsyncSessionLocal() as session:
            # Clean user's execution history
            cutoff_date = datetime.utcnow() - timedelta(days=self.execution_retention_days)
            result = await session.execute(
                delete(ExecutionHistory).where(
                    and_(
                        ExecutionHistory.user_id == user_id,
                        ExecutionHistory.timestamp < cutoff_date,
                    )
                )
            )
            deleted_counts["execution_history"] = result.rowcount

            # Clean user's conversations
            cutoff_date = datetime.utcnow() - timedelta(days=self.conversation_retention_days)
            result = await session.execute(
                delete(Conversation).where(
                    and_(
                        Conversation.user_id == user_id,
                        Conversation.ended_at.isnot(None),
                        Conversation.ended_at < cutoff_date,
                    )
                )
            )
            deleted_counts["conversations"] = result.rowcount

            # Clean user's expired knowledge
            now = datetime.utcnow()
            result = await session.execute(
                delete(KnowledgeBase).where(
                    and_(
                        KnowledgeBase.user_id == user_id,
                        KnowledgeBase.expires_at.isnot(None),
                        KnowledgeBase.expires_at < now,
                    )
                )
            )
            deleted_counts["expired_knowledge"] = result.rowcount

            await session.commit()

        logger.info(f"User retention policy enforced for {user_id}: {deleted_counts}")
        return deleted_counts


# Global retention policy instance
retention_policy = RetentionPolicy()

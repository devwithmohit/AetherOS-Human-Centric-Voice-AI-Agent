"""Long-term memory store using PostgreSQL."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    UserPreference,
    ConsentRecord,
    ExecutionHistory,
    Conversation,
    KnowledgeBase,
)

logger = logging.getLogger(__name__)


class LongTermMemory:
    """PostgreSQL-based long-term memory store."""

    # User Preferences
    async def set_user_preferences(
        self, session: AsyncSession, user_id: str, preferences: Dict[str, Any]
    ) -> UserPreference:
        """Store or update user preferences."""
        try:
            stmt = select(UserPreference).where(UserPreference.user_id == user_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.preferences = preferences
                existing.updated_at = datetime.utcnow()
                await session.flush()
                return existing
            else:
                new_pref = UserPreference(user_id=user_id, preferences=preferences)
                session.add(new_pref)
                await session.flush()
                return new_pref
        except Exception as e:
            logger.error(f"Failed to set preferences for user {user_id}: {e}")
            raise

    async def get_user_preferences(
        self, session: AsyncSession, user_id: str
    ) -> Optional[UserPreference]:
        """Retrieve user preferences."""
        try:
            stmt = select(UserPreference).where(UserPreference.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            return None

    # Consent Management
    async def record_consent(
        self,
        session: AsyncSession,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Record user consent."""
        try:
            consent = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                granted_at=datetime.utcnow() if granted else None,
                revoked_at=None if granted else datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(consent)
            await session.flush()
            return consent
        except Exception as e:
            logger.error(f"Failed to record consent for user {user_id}: {e}")
            raise

    async def get_consent_status(
        self, session: AsyncSession, user_id: str, consent_type: str
    ) -> bool:
        """Check if user has granted consent."""
        try:
            stmt = (
                select(ConsentRecord)
                .where(
                    and_(
                        ConsentRecord.user_id == user_id,
                        ConsentRecord.consent_type == consent_type,
                        ConsentRecord.granted == True,
                        ConsentRecord.revoked_at.is_(None),
                    )
                )
                .order_by(ConsentRecord.created_at.desc())
            )
            result = await session.execute(stmt)
            consent = result.scalar_one_or_none()
            return consent is not None
        except Exception as e:
            logger.error(f"Failed to check consent for user {user_id}: {e}")
            return False

    # Execution History
    async def log_execution(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        command: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ) -> ExecutionHistory:
        """Log command execution."""
        try:
            execution = ExecutionHistory(
                user_id=user_id,
                session_id=session_id,
                command=command,
                tool_name=tool_name,
                parameters=parameters or {},
                result=result,
                success=success,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
            )
            session.add(execution)
            await session.flush()
            return execution
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
            raise

    async def get_execution_history(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionHistory]:
        """Retrieve execution history."""
        try:
            stmt = select(ExecutionHistory).where(ExecutionHistory.user_id == user_id)

            if session_id:
                stmt = stmt.where(ExecutionHistory.session_id == session_id)

            stmt = stmt.order_by(ExecutionHistory.executed_at.desc()).limit(limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            return []

    # Conversation Management
    async def create_conversation(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        """Create new conversation."""
        try:
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                title=title,
                context=context or {},
                is_active=True,
            )
            session.add(conversation)
            await session.flush()
            return conversation
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise

    async def get_conversation(
        self, session: AsyncSession, session_id: str
    ) -> Optional[Conversation]:
        """Retrieve conversation by session ID."""
        try:
            stmt = select(Conversation).where(Conversation.session_id == session_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None

    async def update_conversation(
        self,
        session: AsyncSession,
        session_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        increment_message_count: bool = False,
    ) -> bool:
        """Update conversation metadata."""
        try:
            stmt = (
                update(Conversation)
                .where(Conversation.session_id == session_id)
                .values(last_activity_at=datetime.utcnow())
            )

            if title is not None:
                stmt = stmt.values(title=title)
            if context is not None:
                stmt = stmt.values(context=context)
            if increment_message_count:
                stmt = stmt.values(message_count=Conversation.message_count + 1)

            await session.execute(stmt)
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation: {e}")
            return False

    async def end_conversation(self, session: AsyncSession, session_id: str) -> bool:
        """Mark conversation as ended."""
        try:
            stmt = (
                update(Conversation)
                .where(Conversation.session_id == session_id)
                .values(ended_at=datetime.utcnow(), is_active=False)
            )
            await session.execute(stmt)
            return True
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")
            return False

    async def get_active_conversations(
        self, session: AsyncSession, user_id: str
    ) -> List[Conversation]:
        """Get all active conversations for a user."""
        try:
            stmt = (
                select(Conversation)
                .where(and_(Conversation.user_id == user_id, Conversation.is_active == True))
                .order_by(Conversation.last_activity_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get active conversations: {e}")
            return []

    # Knowledge Base
    async def store_knowledge(
        self,
        session: AsyncSession,
        user_id: str,
        category: str,
        key: str,
        value: str,
        confidence: int = 100,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> KnowledgeBase:
        """Store knowledge item."""
        try:
            knowledge = KnowledgeBase(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                metadata=metadata or {},
                expires_at=expires_at,
            )
            session.add(knowledge)
            await session.flush()
            return knowledge
        except Exception as e:
            logger.error(f"Failed to store knowledge: {e}")
            raise

    async def get_knowledge(
        self,
        session: AsyncSession,
        user_id: str,
        category: Optional[str] = None,
        key: Optional[str] = None,
    ) -> List[KnowledgeBase]:
        """Retrieve knowledge items."""
        try:
            stmt = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)

            if category:
                stmt = stmt.where(KnowledgeBase.category == category)
            if key:
                stmt = stmt.where(KnowledgeBase.key == key)

            # Filter out expired items
            stmt = stmt.where(
                or_(
                    KnowledgeBase.expires_at.is_(None),
                    KnowledgeBase.expires_at > datetime.utcnow(),
                )
            )

            stmt = stmt.order_by(KnowledgeBase.updated_at.desc())

            result = await session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get knowledge: {e}")
            return []

    async def delete_knowledge(
        self,
        session: AsyncSession,
        user_id: str,
        category: Optional[str] = None,
        key: Optional[str] = None,
    ) -> int:
        """Delete knowledge items."""
        try:
            stmt = delete(KnowledgeBase).where(KnowledgeBase.user_id == user_id)

            if category:
                stmt = stmt.where(KnowledgeBase.category == category)
            if key:
                stmt = stmt.where(KnowledgeBase.key == key)

            result = await session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Failed to delete knowledge: {e}")
            return 0


# Global instance
long_term_memory = LongTermMemory()

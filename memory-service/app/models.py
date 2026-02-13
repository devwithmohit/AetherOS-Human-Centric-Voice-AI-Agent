"""SQLAlchemy models for long-term memory storage."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserPreference(Base):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    preferences = Column(JSON, nullable=False, default=dict)
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    voice_settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_user_preferences_user_id", "user_id"),
        {"comment": "User preferences and personalization settings"},
    )


class ConsentRecord(Base):
    """User consent tracking for privacy compliance."""

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    consent_type = Column(
        String(50), nullable=False
    )  # 'data_collection', 'personalization', 'analytics'
    granted = Column(Boolean, default=False, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_consent_user_id_type", "user_id", "consent_type"),
        CheckConstraint("consent_type IN ('data_collection', 'personalization', 'analytics')"),
        {"comment": "Privacy consent tracking (GDPR/CCPA compliance)"},
    )


class ExecutionHistory(Base):
    """History of command executions and tool usage."""

    __tablename__ = "execution_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    command = Column(Text, nullable=False)
    tool_name = Column(String(100), nullable=True)
    parameters = Column(JSON, default=dict)
    result = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_execution_user_session", "user_id", "session_id"),
        Index("ix_execution_tool_name", "tool_name"),
        Index("ix_execution_executed_at", "executed_at"),
        {"comment": "Command execution history for learning and debugging"},
    )


class Conversation(Base):
    """Conversation threads and context."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=True)
    context = Column(JSON, default=dict)
    message_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_conversation_user_active", "user_id", "is_active"),
        Index("ix_conversation_last_activity", "last_activity_at"),
        {"comment": "Conversation threads with metadata"},
    )


class KnowledgeBase(Base):
    """Long-term knowledge and learned facts."""

    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Integer, default=100)  # 0-100
    source = Column(String(100), nullable=True)  # 'user_input', 'learned', 'inferred'
    meta_data = Column("metadata", JSON, default=dict)  # Renamed to avoid SQLAlchemy reserved word
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_knowledge_user_category", "user_id", "category"),
        Index("ix_knowledge_key", "key"),
        CheckConstraint("confidence >= 0 AND confidence <= 100"),
        {"comment": "Long-term knowledge base with confidence scoring"},
    )
